from datetime import date, datetime
from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    display_name: str = ""


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    display_name: str

    class Config:
        from_attributes = True


class PreferenceUpdate(BaseModel):
    unread_link_threshold: int = 30
    weekly_report_day_of_week: int = 5
    weekly_report_prompt_template: str
    link_classification_prompt_template: str = (
        "你是链接标签助手。请严格先从 {existing_tags} 中选择一个最匹配标签；"
        "只有都不匹配时才创建新标签。"
        "链接标题：{title}；链接摘要：{summary}。"
        "输出JSON: {\"category\":\"...\",\"confidence\":0-1,\"reason\":\"...\"}"
    )
    timezone: str = "Asia/Shanghai"


class SmtpSettingUpdate(BaseModel):
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_use_ssl: bool = True
    smtp_from_email: str
    smtp_from_name: str = "Second Brain Tool"
    is_enabled: bool = True


class LlmProviderConfig(BaseModel):
    enabled: bool = False
    api_base_url: str = ""
    api_key: str = ""
    model: str = ""


class LlmSettingUpdate(BaseModel):
    active_provider: str = "openai_compatible"
    providers: dict[str, LlmProviderConfig] = {}


class LinkBatchIn(BaseModel):
    urls: list[str]


class LinkOut(BaseModel):
    id: int
    url: str
    title: str
    summary: str
    domain: str
    status: str
    category_id: int | None
    category_name: str | None = None
    classification_source: str
    classification_confidence: float | None
    is_archived: bool = False
    archived_at: datetime | None = None

    class Config:
        from_attributes = True


class LinkPatch(BaseModel):
    title: str | None = None
    status: str | None = None
    category_id: int | None = None
    is_archived: bool | None = None


class CategoryCreate(BaseModel):
    name: str
    description: str = ""


class CategoryPatch(BaseModel):
    name: str | None = None
    description: str | None = None


class CategoryOut(BaseModel):
    id: int
    name: str
    description: str

    class Config:
        from_attributes = True


class TodoCreate(BaseModel):
    title: str
    due_date: date | None = None
    tags: list[str] = []


class TodoPatch(BaseModel):
    title: str | None = None
    status: str | None = None
    due_date: date | None = None
    content_markdown: str | None = None
    content_richtext: str | None = None
    tags: list[str] | None = None


class TodoOut(BaseModel):
    id: int
    title: str
    status: str
    due_date: date | None
    completed_at: datetime | None
    tags: list[str] = []

    class Config:
        from_attributes = True


class WeeklyReportGenerateIn(BaseModel):
    completed_start_date: date | None = None
    completed_end_date: date | None = None


class WeeklyReportOut(BaseModel):
    id: int
    period_start: date
    period_end: date
    content: str
    generated_at: datetime

    class Config:
        from_attributes = True
