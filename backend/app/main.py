import asyncio
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import Body, Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.dependencies import get_current_user
from app.models import (
    LinkCategory,
    LinkItem,
    NotificationLog,
    TodoContent,
    TodoImage,
    TodoItem,
    User,
    UserLlmSetting,
    UserPreference,
    UserSmtpSetting,
    WeeklyReport,
)
from app.schemas import (
    CategoryCreate,
    CategoryOut,
    CategoryPatch,
    LinkBatchIn,
    LinkOut,
    LinkPatch,
    LlmSettingUpdate,
    PreferenceUpdate,
    SmtpSettingUpdate,
    TodoCreate,
    TodoOut,
    TodoPatch,
    Token,
    UserCreate,
    UserLogin,
    UserOut,
    WeeklyReportGenerateIn,
    WeeklyReportOut,
)
from app.scheduler import start_scheduler
from app.security import create_access_token, hash_password, verify_password
from app.services.link_meta import fetch_link_meta
from app.services.llm_service import llm_service
from app.services.smtp_service import send_email

Base.metadata.create_all(bind=engine)


def run_sqlite_lightweight_migrations() -> None:
    if not str(engine.url).startswith("sqlite"):
        return

    inspector = inspect(engine)
    with engine.begin() as conn:
        if inspector.has_table("link_items"):
            link_item_cols = {col["name"] for col in inspector.get_columns("link_items")}
            if "is_archived" not in link_item_cols:
                conn.execute(
                    text("ALTER TABLE link_items ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT 0")
                )
            if "archived_at" not in link_item_cols:
                conn.execute(text("ALTER TABLE link_items ADD COLUMN archived_at DATETIME"))

        if inspector.has_table("user_preferences"):
            pref_cols = {col["name"] for col in inspector.get_columns("user_preferences")}
            if "link_classification_prompt_template" not in pref_cols:
                conn.execute(
                    text(
                        "ALTER TABLE user_preferences "
                        "ADD COLUMN link_classification_prompt_template TEXT "
                        "NOT NULL DEFAULT ''"
                    )
                )
                conn.execute(
                    text(
                        "UPDATE user_preferences "
                        "SET link_classification_prompt_template = :prompt "
                        "WHERE link_classification_prompt_template = ''"
                    ),
                    {
                        "prompt": (
                            "你是链接标签助手。请严格先从 {existing_tags} 中选择一个最匹配标签；"
                            "只有都不匹配时才创建新标签。"
                            "链接标题：{title}；链接摘要：{summary}。"
                            "输出JSON: {\"category\":\"...\",\"confidence\":0-1,\"reason\":\"...\"}"
                        )
                    },
                )


run_sqlite_lightweight_migrations()

CLASSIFICATION_QUEUE: dict[int, set[int]] = {}
CLASSIFICATION_WORKERS: set[int] = set()


def _normalize_new_tag_name(raw_name: str) -> str:
    name = str(raw_name or "").strip()
    if not name:
        return "待分组"

    cleaned = re.sub(r"\s+", " ", name)
    has_cjk = bool(re.search(r"[\u4e00-\u9fff]", cleaned))
    if has_cjk:
        cjk_chars = re.findall(r"[\u4e00-\u9fff]", cleaned)
        normalized = "".join(cjk_chars[:5])
        return normalized or "待分组"

    words = re.findall(r"[A-Za-z0-9_-]+", cleaned)
    if not words:
        return "待分组"
    return " ".join(words[:2])


def _choose_or_create_category_by_rule(
    *,
    db: Session,
    current_user: User,
    categories: list[LinkCategory],
    category_names: list[str],
    classify: dict,
) -> tuple[LinkCategory | None, float]:
    confidence = float(classify.get("confidence", 0.0) or 0.0)
    ai_name = str(classify.get("category") or "").strip()

    # 1) 高置信命中已有标签 -> 直接采用
    if confidence >= 0.7 and ai_name:
        matched = next((c for c in categories if c.name == ai_name), None)
        if matched:
            return matched, confidence

    # 2) 其余情况统一走新建/复用标签逻辑，避免 category_id 为空长期挂起
    candidate_name = _normalize_new_tag_name(ai_name)
    if not candidate_name:
        candidate_name = "待分组"

    existing = next((c for c in categories if c.name == candidate_name), None)
    if existing:
        return existing, confidence

    try:
        created = LinkCategory(
            owner_id=current_user.id,
            name=candidate_name,
            created_by="ai",
        )
        db.add(created)
        db.flush()
        categories.append(created)
        category_names.append(created.name)
        return created, confidence
    except Exception:
        db.rollback()
        existing_after = (
            db.query(LinkCategory)
            .filter(LinkCategory.owner_id == current_user.id, LinkCategory.name == candidate_name)
            .first()
        )
        if existing_after:
            return existing_after, confidence
        return None, confidence


async def _classify_link_item(link_id: int, owner_id: int) -> None:
    db = next(get_db())
    try:
        link = db.query(LinkItem).filter(LinkItem.id == link_id, LinkItem.owner_id == owner_id).first()
        if not link:
            return

        user = db.query(User).filter(User.id == owner_id).first()
        if not user:
            return

        categories = db.query(LinkCategory).filter(LinkCategory.owner_id == owner_id).all()
        category_names = [c.name for c in categories]

        prefs = db.query(UserPreference).filter(UserPreference.owner_id == owner_id).first()
        classify_prompt = (
            prefs.link_classification_prompt_template
            if prefs and getattr(prefs, "link_classification_prompt_template", None)
            else (
                "你是链接标签助手。请严格先从 {existing_tags} 中选择一个最匹配标签；"
                "只有都不匹配时才创建新标签。"
                "链接标题：{title}；链接摘要：{summary}。"
                "输出JSON: {\"category\":\"...\",\"confidence\":0-1,\"reason\":\"...\"}"
            )
        )
        provider_config = resolve_active_llm_provider_config(db, owner_id)
        classify = await llm_service.classify_link(
            link.title or "",
            link.summary or "",
            category_names,
            provider_config=provider_config,
            classification_prompt_template=classify_prompt,
        )

        category, confidence = _choose_or_create_category_by_rule(
            db=db,
            current_user=user,
            categories=categories,
            category_names=category_names,
            classify=classify,
        )

        link.category_id = category.id if category else None
        link.classification_source = "ai"
        link.classification_confidence = confidence
        db.commit()
    finally:
        db.close()


async def _run_classification_worker(owner_id: int) -> None:
    if owner_id in CLASSIFICATION_WORKERS:
        return
    CLASSIFICATION_WORKERS.add(owner_id)
    try:
        while CLASSIFICATION_QUEUE.get(owner_id):
            link_id = CLASSIFICATION_QUEUE[owner_id].pop()
            try:
                await _classify_link_item(link_id, owner_id)
            except Exception:
                # 避免单条失败导致整个队列停摆
                continue
        CLASSIFICATION_QUEUE.pop(owner_id, None)
    finally:
        CLASSIFICATION_WORKERS.discard(owner_id)


app = FastAPI(title="Second Brain Tool API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


def parse_tags(tags_json: str | None) -> list[str]:
    if not tags_json:
        return []
    try:
        data = json.loads(tags_json)
        if isinstance(data, list):
            return [str(t).strip() for t in data if str(t).strip()]
        return []
    except json.JSONDecodeError:
        return []


def normalize_tags(tags: list[str] | None) -> list[str]:
    if not tags:
        return ["未分类"]

    for t in tags:
        value = str(t).strip()
        if value:
            return [value]

    return ["未分类"]


def normalize_url_for_dedup(raw_url: str) -> str:
    url = str(raw_url or "").strip()
    if not url:
        return ""

    normalized = re.sub(r"/+$", "", url)
    return normalized.lower()


def default_llm_providers() -> dict[str, dict[str, str | bool]]:
    return {
        "openai_compatible": {
            "enabled": False,
            "api_base_url": "https://api.openai.com/v1",
            "api_key": "",
            "model": "gpt-5.3-codex",
        },
        "deepseek": {
            "enabled": False,
            "api_base_url": "https://api.deepseek.com/v1",
            "api_key": "",
            "model": "deepseek-chat",
        },
        "qwen": {
            "enabled": False,
            "api_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": "",
            "model": "qwen-plus",
        },
    }


def resolve_active_llm_provider_config(db: Session, user_id: int) -> dict[str, str | bool]:
    providers = default_llm_providers()
    setting = db.query(UserLlmSetting).filter(UserLlmSetting.owner_id == user_id).first()
    if not setting:
        return {}

    try:
        raw = json.loads(setting.providers_json) if setting.providers_json else {}
    except json.JSONDecodeError:
        raw = {}

    for provider_name, provider_conf in raw.items():
        if provider_name not in providers:
            providers[provider_name] = {}
        providers[provider_name].update(provider_conf)

    selected = providers.get(setting.active_provider, {})
    if not selected.get("enabled"):
        return {}
    return selected


@app.on_event("startup")
def on_startup():
    start_scheduler()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/auth/register", response_model=UserOut)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.email == payload.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")

    try:
        password_hash = hash_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    user = User(
        email=payload.email,
        password_hash=password_hash,
        display_name=payload.display_name,
    )
    db.add(user)
    db.flush()
    db.add(UserPreference(owner_id=user.id))
    db.commit()
    db.refresh(user)
    return user


@app.post("/api/auth/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(str(user.id))
    return Token(access_token=token)


@app.get("/api/users/me", response_model=UserOut)
def me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@app.put("/api/users/me/preferences")
def update_preferences(
    payload: PreferenceUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    prefs = db.query(UserPreference).filter(UserPreference.owner_id == current_user.id).first()
    if not prefs:
        prefs = UserPreference(owner_id=current_user.id)
        db.add(prefs)
    prefs.unread_link_threshold = payload.unread_link_threshold
    prefs.weekly_report_day_of_week = payload.weekly_report_day_of_week
    prefs.weekly_report_prompt_template = payload.weekly_report_prompt_template
    prefs.link_classification_prompt_template = payload.link_classification_prompt_template
    prefs.timezone = payload.timezone
    db.commit()
    return {"ok": True}


@app.get("/api/users/me/preferences")
def get_preferences(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    prefs = db.query(UserPreference).filter(UserPreference.owner_id == current_user.id).first()
    if not prefs:
        prefs = UserPreference(owner_id=current_user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    if not getattr(prefs, "link_classification_prompt_template", None):
        prefs.link_classification_prompt_template = (
            "你是链接标签助手。请优先从已有标签中选择一个最匹配的标签；"
            "只有在都不匹配时才创建一个新标签。输出JSON:"
            '{"category":"...","confidence":0-1,"reason":"..."}'
        )
        db.commit()

    return {
        "unread_link_threshold": prefs.unread_link_threshold,
        "weekly_report_day_of_week": prefs.weekly_report_day_of_week,
        "weekly_report_prompt_template": prefs.weekly_report_prompt_template,
        "link_classification_prompt_template": prefs.link_classification_prompt_template,
        "timezone": prefs.timezone,
    }


@app.put("/api/users/me/smtp-settings")
def update_smtp_settings(
    payload: SmtpSettingUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    setting = db.query(UserSmtpSetting).filter(UserSmtpSetting.owner_id == current_user.id).first()
    if not setting:
        setting = UserSmtpSetting(owner_id=current_user.id)
        db.add(setting)
    setting.smtp_host = payload.smtp_host
    setting.smtp_port = payload.smtp_port
    setting.smtp_username = payload.smtp_username
    setting.smtp_password = payload.smtp_password
    setting.smtp_use_ssl = payload.smtp_use_ssl
    setting.smtp_from_email = payload.smtp_from_email
    setting.smtp_from_name = payload.smtp_from_name
    setting.is_enabled = payload.is_enabled
    db.commit()
    return {"ok": True}


@app.get("/api/users/me/smtp-settings")
def get_smtp_settings(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    setting = db.query(UserSmtpSetting).filter(UserSmtpSetting.owner_id == current_user.id).first()
    if not setting:
        return {
            "smtp_host": "",
            "smtp_port": 465,
            "smtp_username": "",
            "smtp_password": "",
            "smtp_use_ssl": True,
            "smtp_from_email": "",
            "smtp_from_name": "Second Brain Tool",
            "is_enabled": False,
        }
    return {
        "smtp_host": setting.smtp_host,
        "smtp_port": setting.smtp_port,
        "smtp_username": setting.smtp_username,
        "smtp_password": setting.smtp_password,
        "smtp_use_ssl": setting.smtp_use_ssl,
        "smtp_from_email": setting.smtp_from_email,
        "smtp_from_name": setting.smtp_from_name,
        "is_enabled": setting.is_enabled,
    }


@app.put("/api/users/me/llm-settings")
def update_llm_settings(
    payload: LlmSettingUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    setting = db.query(UserLlmSetting).filter(UserLlmSetting.owner_id == current_user.id).first()
    if not setting:
        setting = UserLlmSetting(owner_id=current_user.id)
        db.add(setting)

    setting.active_provider = payload.active_provider
    setting.providers_json = json.dumps(
        {k: v.model_dump() for k, v in payload.providers.items()}, ensure_ascii=False
    )
    db.commit()
    return {"ok": True}


@app.get("/api/users/me/llm-settings")
def get_llm_settings(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    setting = db.query(UserLlmSetting).filter(UserLlmSetting.owner_id == current_user.id).first()
    if not setting:
        providers = default_llm_providers()
        return {
            "active_provider": "openai_compatible",
            "providers": providers,
        }

    try:
        providers = json.loads(setting.providers_json) if setting.providers_json else {}
    except json.JSONDecodeError:
        providers = {}

    merged = default_llm_providers()
    for provider_name, provider_conf in providers.items():
        if provider_name not in merged:
            merged[provider_name] = {}
        merged[provider_name].update(provider_conf)

    return {
        "active_provider": setting.active_provider,
        "providers": merged,
    }


@app.post("/api/link-categories", response_model=CategoryOut)
def create_category(
    payload: CategoryCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    cat = LinkCategory(
        owner_id=current_user.id,
        name=payload.name,
        description=payload.description,
        created_by="manual",
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@app.get("/api/link-categories", response_model=list[CategoryOut])
def list_categories(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    return (
        db.query(LinkCategory)
        .filter(LinkCategory.owner_id == current_user.id)
        .order_by(LinkCategory.name.asc())
        .all()
    )


@app.patch("/api/link-categories/{category_id}", response_model=CategoryOut)
def patch_category(
    category_id: int,
    payload: CategoryPatch,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    cat = (
        db.query(LinkCategory)
        .filter(LinkCategory.id == category_id, LinkCategory.owner_id == current_user.id)
        .first()
    )
    if not cat:
        raise HTTPException(status_code=404, detail="Tag not found")
    if payload.name is not None:
        cat.name = payload.name
    if payload.description is not None:
        cat.description = payload.description
    db.commit()
    db.refresh(cat)
    return cat


@app.delete("/api/link-categories/{category_id}")
def delete_category(
    category_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    cat = (
        db.query(LinkCategory)
        .filter(LinkCategory.id == category_id, LinkCategory.owner_id == current_user.id)
        .first()
    )
    if not cat:
        raise HTTPException(status_code=404, detail="Tag not found")

    db.query(LinkItem).filter(
        LinkItem.owner_id == current_user.id,
        LinkItem.category_id == cat.id,
    ).update({"category_id": None, "classification_source": "manual"})

    db.delete(cat)
    db.commit()
    return {"ok": True}


@app.post("/api/links/batch", response_model=list[LinkOut])
async def create_links_batch(
    payload: LinkBatchIn,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    created_items: list[LinkItem] = []

    existing_urls = {
        normalize_url_for_dedup(url)
        for (url,) in db.query(LinkItem.url).filter(LinkItem.owner_id == current_user.id).all()
    }
    pending_urls: set[str] = set()

    for raw_url in payload.urls:
        url = str(raw_url or "").strip()
        if not url:
            continue

        dedup_key = normalize_url_for_dedup(url)
        if not dedup_key:
            continue
        if dedup_key in existing_urls or dedup_key in pending_urls:
            continue

        title, summary, domain = await fetch_link_meta(url)
        item = LinkItem(
            owner_id=current_user.id,
            url=url,
            title=title,
            summary=summary,
            domain=domain,
            status="unread",
            category_id=None,
            classification_source="queued",
            classification_confidence=0.0,
        )
        db.add(item)
        db.flush()
        created_items.append(item)
        pending_urls.add(dedup_key)

        if current_user.id not in CLASSIFICATION_QUEUE:
            CLASSIFICATION_QUEUE[current_user.id] = set()
        CLASSIFICATION_QUEUE[current_user.id].add(item.id)

    db.commit()
    for i in created_items:
        db.refresh(i)

    if created_items and current_user.id not in CLASSIFICATION_WORKERS:
        asyncio.create_task(_run_classification_worker(current_user.id))

    return created_items


@app.get("/api/links", response_model=list[LinkOut])
def list_links(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    links = (
        db.query(LinkItem)
        .filter(LinkItem.owner_id == current_user.id)
        .order_by(LinkItem.created_at.desc())
        .all()
    )
    category_map = {
        c.id: c.name
        for c in db.query(LinkCategory).filter(LinkCategory.owner_id == current_user.id).all()
    }
    return [
        {
            "id": l.id,
            "url": l.url,
            "title": l.title,
            "summary": l.summary,
            "domain": l.domain,
            "status": l.status,
            "category_id": l.category_id,
            "category_name": category_map.get(l.category_id) if l.category_id else None,
            "classification_source": l.classification_source,
            "classification_confidence": l.classification_confidence,
            "is_archived": bool(getattr(l, "is_archived", False)),
            "archived_at": getattr(l, "archived_at", None),
        }
        for l in links
    ]


@app.patch("/api/links/{link_id}", response_model=LinkOut)
def patch_link(
    link_id: int,
    payload: LinkPatch,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    link = (
        db.query(LinkItem)
        .filter(LinkItem.id == link_id, LinkItem.owner_id == current_user.id)
        .first()
    )
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    if payload.status:
        link.status = payload.status
    if payload.category_id is not None:
        link.category_id = payload.category_id
        link.classification_source = "manual"
    if payload.is_archived is not None:
        link.is_archived = payload.is_archived
        link.archived_at = datetime.utcnow() if payload.is_archived else None
    db.commit()
    db.refresh(link)
    return link


@app.post("/api/links/{link_id}/reclassify", response_model=LinkOut)
async def reclassify_link(
    link_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    link = (
        db.query(LinkItem)
        .filter(LinkItem.id == link_id, LinkItem.owner_id == current_user.id)
        .first()
    )
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    categories = db.query(LinkCategory).filter(LinkCategory.owner_id == current_user.id).all()
    category_names = [c.name for c in categories]

    prefs = db.query(UserPreference).filter(UserPreference.owner_id == current_user.id).first()
    classify_prompt = (
        prefs.link_classification_prompt_template
        if prefs and getattr(prefs, "link_classification_prompt_template", None)
        else (
            "你是链接标签助手。请严格先从 {existing_tags} 中选择一个最匹配标签；"
            "只有都不匹配时才创建新标签。"
            "链接标题：{title}；链接摘要：{summary}。"
            "输出JSON: {\"category\":\"...\",\"confidence\":0-1,\"reason\":\"...\"}"
        )
    )

    provider_config = resolve_active_llm_provider_config(db, current_user.id)
    classify = await llm_service.classify_link(
        link.title or "",
        link.summary or "",
        category_names,
        provider_config=provider_config,
        classification_prompt_template=classify_prompt,
    )

    category, confidence = _choose_or_create_category_by_rule(
        db=db,
        current_user=current_user,
        categories=categories,
        category_names=category_names,
        classify=classify,
    )

    link.category_id = category.id if category else None
    link.classification_source = "ai"
    link.classification_confidence = confidence

    db.commit()
    db.refresh(link)
    return {
        "id": link.id,
        "url": link.url,
        "title": link.title,
        "summary": link.summary,
        "domain": link.domain,
        "status": link.status,
        "category_id": link.category_id,
        "category_name": category.name if category else None,
        "classification_source": link.classification_source,
        "classification_confidence": link.classification_confidence,
        "is_archived": bool(getattr(link, "is_archived", False)),
        "archived_at": getattr(link, "archived_at", None),
    }


@app.post("/api/todos", response_model=TodoOut)
def create_todo(
    payload: TodoCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    todo = TodoItem(
        owner_id=current_user.id,
        title=payload.title,
        due_date=payload.due_date,
        tags_json=json.dumps(normalize_tags(payload.tags), ensure_ascii=False),
    )
    db.add(todo)
    db.flush()
    content = TodoContent(todo_id=todo.id, owner_id=current_user.id)
    db.add(content)
    db.commit()
    db.refresh(todo)
    return {
        "id": todo.id,
        "title": todo.title,
        "status": todo.status,
        "due_date": todo.due_date,
        "completed_at": todo.completed_at,
        "tags": parse_tags(todo.tags_json),
    }


@app.get("/api/todos", response_model=list[TodoOut])
def list_todos(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    todos = db.query(TodoItem).filter(TodoItem.owner_id == current_user.id).all()
    return [
        {
            "id": todo.id,
            "title": todo.title,
            "status": todo.status,
            "due_date": todo.due_date,
            "completed_at": todo.completed_at,
            "tags": parse_tags(todo.tags_json),
        }
        for todo in todos
    ]


@app.get("/api/todos/{todo_id}")
def get_todo(
    todo_id: int,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    todo = (
        db.query(TodoItem)
        .filter(TodoItem.id == todo_id, TodoItem.owner_id == current_user.id)
        .first()
    )
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    content = (
        db.query(TodoContent)
        .filter(TodoContent.todo_id == todo.id, TodoContent.owner_id == current_user.id)
        .first()
    )
    images = (
        db.query(TodoImage)
        .filter(TodoImage.todo_id == todo.id, TodoImage.owner_id == current_user.id)
        .all()
    )
    base_url = str(request.base_url).rstrip("/")
    images_out = [
        {
            "id": img.id,
            "file_name": img.file_name,
            "mime_type": img.mime_type,
            "size_bytes": img.size_bytes,
            "created_at": img.created_at,
            "url": f"{base_url}/uploads/{Path(img.file_path).name}",
        }
        for img in images
    ]

    return {
        "todo": {
            "id": todo.id,
            "title": todo.title,
            "status": todo.status,
            "due_date": todo.due_date,
            "completed_at": todo.completed_at,
            "tags": parse_tags(todo.tags_json),
        },
        "content": content,
        "images": images_out,
    }


@app.patch("/api/todos/{todo_id}", response_model=TodoOut)
def patch_todo(
    todo_id: int,
    payload: TodoPatch,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    todo = (
        db.query(TodoItem)
        .filter(TodoItem.id == todo_id, TodoItem.owner_id == current_user.id)
        .first()
    )
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    if payload.title is not None:
        todo.title = payload.title
    if payload.due_date is not None:
        todo.due_date = payload.due_date
    if payload.status is not None:
        todo.status = payload.status
        if payload.status == "done" and todo.completed_at is None:
            todo.completed_at = datetime.utcnow()

    if payload.tags is not None:
        todo.tags_json = json.dumps(normalize_tags(payload.tags), ensure_ascii=False)

    content = (
        db.query(TodoContent)
        .filter(TodoContent.todo_id == todo.id, TodoContent.owner_id == current_user.id)
        .first()
    )
    if content is None:
        content = TodoContent(todo_id=todo.id, owner_id=current_user.id)
        db.add(content)

    if payload.content_markdown is not None:
        content.content_markdown = payload.content_markdown
    if payload.content_richtext is not None:
        content.content_richtext = payload.content_richtext

    db.commit()
    db.refresh(todo)
    return {
        "id": todo.id,
        "title": todo.title,
        "status": todo.status,
        "due_date": todo.due_date,
        "completed_at": todo.completed_at,
        "tags": parse_tags(todo.tags_json),
    }


@app.delete("/api/links/{link_id}")
def delete_link(
    link_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    link = (
        db.query(LinkItem)
        .filter(LinkItem.id == link_id, LinkItem.owner_id == current_user.id)
        .first()
    )
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    db.delete(link)
    db.commit()
    return {"ok": True}


@app.delete("/api/todos/{todo_id}")
def delete_todo(
    todo_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    todo = (
        db.query(TodoItem)
        .filter(TodoItem.id == todo_id, TodoItem.owner_id == current_user.id)
        .first()
    )
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    db.query(TodoContent).filter(TodoContent.todo_id == todo.id).delete()
    db.query(TodoImage).filter(TodoImage.todo_id == todo.id).delete()
    db.delete(todo)
    db.commit()
    return {"ok": True}


@app.post("/api/todos/{todo_id}/images")
async def upload_todo_image(
    todo_id: int,
    request: Request,
    file: UploadFile = File(...),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    todo = (
        db.query(TodoItem)
        .filter(TodoItem.id == todo_id, TodoItem.owner_id == current_user.id)
        .first()
    )
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")

    file_name = f"{current_user.id}_{todo_id}_{int(datetime.utcnow().timestamp())}_{file.filename}"
    file_path = UPLOAD_DIR / file_name
    content = await file.read()
    file_path.write_bytes(content)

    image = TodoImage(
        todo_id=todo.id,
        owner_id=current_user.id,
        file_path=str(file_path),
        file_name=file.filename,
        mime_type=file.content_type or "",
        size_bytes=len(content),
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    base_url = str(request.base_url).rstrip("/")
    return {
        "id": image.id,
        "file_name": image.file_name,
        "url": f"{base_url}/uploads/{file_path.name}",
    }


@app.post("/api/reports/weekly/generate", response_model=WeeklyReportOut)
async def generate_weekly_report(
    current_user: Annotated[User, Depends(get_current_user)],
    payload: WeeklyReportGenerateIn | None = Body(default=None),
    db: Session = Depends(get_db),
):
    default_end = date.today()
    default_start = default_end - timedelta(days=7)

    start = payload.completed_start_date if payload and payload.completed_start_date else default_start
    end = payload.completed_end_date if payload and payload.completed_end_date else default_end
    if start > end:
        raise HTTPException(status_code=422, detail="completed_start_date 不能晚于 completed_end_date")

    done_items = (
        db.query(TodoItem)
        .filter(
            TodoItem.owner_id == current_user.id,
            TodoItem.status == "done",
            TodoItem.completed_at.isnot(None),
        )
        .all()
    )
    done_items = [
        i
        for i in done_items
        if i.completed_at and start <= i.completed_at.date() <= end
    ]

    facts = "\n".join(
        [f"- {i.title}（完成于 {i.completed_at.date()}）" for i in done_items]
    ) or "- 本周期无已完成事项"

    prefs = db.query(UserPreference).filter(UserPreference.owner_id == current_user.id).first()
    prompt = (
        prefs.weekly_report_prompt_template
        if prefs
        else "请根据以下已完成事项，输出简洁执行版周报。"
    )
    provider_config = resolve_active_llm_provider_config(db, current_user.id)
    content = await llm_service.generate_weekly_report(
        prompt=prompt,
        facts=facts,
        period_start=start,
        period_end=end,
        provider_config=provider_config,
    )

    report = WeeklyReport(
        owner_id=current_user.id,
        period_start=start,
        period_end=end,
        prompt_used=prompt,
        content=content,
        llm_model=str(provider_config.get("model") or "fallback"),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@app.get("/api/reports/weekly", response_model=list[WeeklyReportOut])
def list_reports(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    return (
        db.query(WeeklyReport)
        .filter(WeeklyReport.owner_id == current_user.id)
        .order_by(WeeklyReport.generated_at.desc())
        .all()
    )


@app.delete("/api/reports/weekly/{report_id}")
def delete_report(
    report_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    report = (
        db.query(WeeklyReport)
        .filter(WeeklyReport.id == report_id, WeeklyReport.owner_id == current_user.id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    db.delete(report)
    db.commit()
    return {"ok": True}


@app.post("/api/notifications/test-email")
def test_email(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    setting = db.query(UserSmtpSetting).filter(UserSmtpSetting.owner_id == current_user.id).first()
    try:
        send_email(current_user.email, "SMTP 测试邮件", "这是一封测试邮件，发送成功。", smtp_setting=setting)
        db.add(
            NotificationLog(
                owner_id=current_user.id,
                type="smtp_test",
                subject="SMTP 测试邮件",
                recipient=current_user.email,
                status="success",
            )
        )
        db.commit()
        return {"ok": True}
    except Exception as exc:
        db.add(
            NotificationLog(
                owner_id=current_user.id,
                type="smtp_test",
                subject="SMTP 测试邮件",
                recipient=current_user.email,
                status="failed",
                error_message=str(exc),
            )
        )
        db.commit()
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/notifications/send-upcoming")
def send_upcoming(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    today = date.today()
    within_7 = today + timedelta(days=7)
    items = (
        db.query(TodoItem)
        .filter(
            TodoItem.owner_id == current_user.id,
            TodoItem.status != "done",
            TodoItem.due_date >= today,
            TodoItem.due_date <= within_7,
        )
        .all()
    )
    lines = [f"- {i.title}（截止：{i.due_date}）" for i in items] or ["- 无"]
    body = "未来7日待办：\n" + "\n".join(lines)
    setting = db.query(UserSmtpSetting).filter(UserSmtpSetting.owner_id == current_user.id).first()
    send_email(current_user.email, "未来7日待办提醒", body, smtp_setting=setting)
    db.add(
        NotificationLog(
            owner_id=current_user.id,
            type="upcoming_todos",
            subject="未来7日待办提醒",
            recipient=current_user.email,
            status="success",
        )
    )
    db.commit()
    return {"ok": True, "count": len(items)}


@app.post("/api/notifications/send-unread-links")
def send_unread_links(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    count = (
        db.query(LinkItem)
        .filter(LinkItem.owner_id == current_user.id, LinkItem.status == "unread")
        .count()
    )
    body = f"你当前有 {count} 条未读链接。"
    setting = db.query(UserSmtpSetting).filter(UserSmtpSetting.owner_id == current_user.id).first()
    send_email(current_user.email, "未读链接提醒", body, smtp_setting=setting)
    db.add(
        NotificationLog(
            owner_id=current_user.id,
            type="unread_links",
            subject="未读链接提醒",
            recipient=current_user.email,
            status="success",
        )
    )
    db.commit()
    return {"ok": True, "count": count}
