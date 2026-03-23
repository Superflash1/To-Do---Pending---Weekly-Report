from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import (
    LinkItem,
    NotificationLog,
    TodoItem,
    User,
    UserPreference,
    UserSmtpSetting,
)
from app.services.smtp_service import send_email

scheduler = BackgroundScheduler()


def _resolve_user_today(timezone_name: str | None) -> date:
    try:
        tz = ZoneInfo(timezone_name or settings.app_timezone)
    except Exception:
        tz = ZoneInfo(settings.app_timezone)
    return datetime.now(tz).date()


def _already_sent_recent(db: Session, owner_id: int, notification_type: str, cooldown_hours: int = 20) -> bool:
    since = datetime.utcnow() - timedelta(hours=cooldown_hours)
    count = (
        db.query(NotificationLog)
        .filter(
            NotificationLog.owner_id == owner_id,
            NotificationLog.type == notification_type,
            NotificationLog.status == "success",
            NotificationLog.created_at >= since,
        )
        .count()
    )
    return count > 0


def _check_unread_links(
    db: Session, user: User, prefs: UserPreference, smtp_setting: UserSmtpSetting | None
):
    unread_count = (
        db.query(LinkItem)
        .filter(LinkItem.owner_id == user.id, LinkItem.status == "unread")
        .count()
    )
    if unread_count >= prefs.unread_link_threshold:
        if _already_sent_recent(db, user.id, "unread_links"):
            return

        subject = "未读链接提醒"
        body = f"你当前有 {unread_count} 条未读链接，请及时处理。"
        send_email(user.email, subject, body, smtp_setting=smtp_setting)
        db.add(
            NotificationLog(
                owner_id=user.id,
                type="unread_links",
                subject=subject,
                recipient=user.email,
                status="success",
            )
        )


def _check_upcoming_todos(
    db: Session,
    user: User,
    prefs: UserPreference,
    smtp_setting: UserSmtpSetting | None,
):
    today = _resolve_user_today(prefs.timezone)
    within_7 = today + timedelta(days=7)
    items = (
        db.query(TodoItem)
        .filter(
            TodoItem.owner_id == user.id,
            TodoItem.status != "done",
            TodoItem.due_date >= today,
            TodoItem.due_date <= within_7,
        )
        .all()
    )
    if items:
        if _already_sent_recent(db, user.id, "upcoming_todos"):
            return

        lines = [f"- {i.title}（截止：{i.due_date}）" for i in items]
        body = "未来7日待办：\n" + "\n".join(lines)
        subject = "未来7日待办提醒"
        send_email(user.email, subject, body, smtp_setting=smtp_setting)
        db.add(
            NotificationLog(
                owner_id=user.id,
                type="upcoming_todos",
                subject=subject,
                recipient=user.email,
                status="success",
            )
        )


def daily_notification_job():
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active.is_(True)).all()
        for user in users:
            prefs = db.query(UserPreference).filter(UserPreference.owner_id == user.id).first()
            if not prefs:
                prefs = UserPreference(owner_id=user.id)
                db.add(prefs)
                db.flush()
            smtp_setting = (
                db.query(UserSmtpSetting).filter(UserSmtpSetting.owner_id == user.id).first()
            )
            _check_unread_links(db, user, prefs, smtp_setting)
            _check_upcoming_todos(db, user, prefs, smtp_setting)
        db.commit()
    finally:
        db.close()


def start_scheduler():
    if scheduler.running:
        return
    scheduler.add_job(daily_notification_job, "interval", hours=12, id="notify_job")
    scheduler.start()
