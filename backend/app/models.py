from datetime import datetime, date
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(100), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserPreference(Base, TimestampMixin):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    unread_link_threshold: Mapped[int] = mapped_column(Integer, default=30)
    weekly_report_day_of_week: Mapped[int] = mapped_column(Integer, default=5)
    weekly_report_prompt_template: Mapped[str] = mapped_column(
        Text, default="请根据以下已完成事项，输出简洁执行版周报。"
    )
    link_classification_prompt_template: Mapped[str] = mapped_column(
        Text,
        default=(
            "你是链接标签助手。请严格先从 {existing_tags} 中选择一个最匹配标签；"
            "只有都不匹配时才创建新标签。"
            "链接标题：{title}；链接摘要：{summary}。"
            "输出JSON: {\"category\":\"...\",\"confidence\":0-1,\"reason\":\"...\"}"
        ),
    )
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Shanghai")


class UserSmtpSetting(Base, TimestampMixin):
    __tablename__ = "user_smtp_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    smtp_host: Mapped[str] = mapped_column(String(255), default="")
    smtp_port: Mapped[int] = mapped_column(Integer, default=465)
    smtp_username: Mapped[str] = mapped_column(String(255), default="")
    smtp_password: Mapped[str] = mapped_column(String(255), default="")
    smtp_use_ssl: Mapped[bool] = mapped_column(Boolean, default=True)
    smtp_from_email: Mapped[str] = mapped_column(String(255), default="")
    smtp_from_name: Mapped[str] = mapped_column(String(100), default="Second Brain Tool")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class UserLlmSetting(Base, TimestampMixin):
    __tablename__ = "user_llm_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    active_provider: Mapped[str] = mapped_column(String(50), default="openai_compatible")
    providers_json: Mapped[str] = mapped_column(Text, default="{}")


class LinkCategory(Base, TimestampMixin):
    __tablename__ = "link_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str] = mapped_column(String(255), default="")
    created_by: Mapped[str] = mapped_column(String(20), default="ai")


class LinkItem(Base, TimestampMixin):
    __tablename__ = "link_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(500), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    domain: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(20), default="unread")
    category_id: Mapped[int | None] = mapped_column(ForeignKey("link_categories.id"), nullable=True)
    classification_source: Mapped[str] = mapped_column(String(20), default="ai")
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TodoItem(Base, TimestampMixin):
    __tablename__ = "todo_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="todo")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tags_json: Mapped[str] = mapped_column(Text, default="[]")


class TodoContent(Base, TimestampMixin):
    __tablename__ = "todo_contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    todo_id: Mapped[int] = mapped_column(ForeignKey("todo_items.id"), index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    content_markdown: Mapped[str] = mapped_column(Text, default="")
    content_richtext: Mapped[str] = mapped_column(Text, default="")


class TodoImage(Base):
    __tablename__ = "todo_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    todo_id: Mapped[int] = mapped_column(ForeignKey("todo_items.id"), index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    file_path: Mapped[str] = mapped_column(String(500))
    file_name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WeeklyReport(Base):
    __tablename__ = "weekly_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    prompt_used: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    llm_model: Mapped[str] = mapped_column(String(100))
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(50))
    subject: Mapped[str] = mapped_column(String(255))
    recipient: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="success")
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
