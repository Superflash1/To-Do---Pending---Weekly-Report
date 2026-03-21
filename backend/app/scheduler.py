from datetime import date, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

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


def _check_unread_links(
    db: Session, user: User, prefs: UserPreference, smtp_setting: UserSmtpSetting | None
):
    unread_count = (
        db.query(LinkItem)
        .filter(LinkItem.owner_id == user.id, LinkItem.status == "unread")
        .count()
    )
    if unread_count >= prefs.unread_link_threshold:
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


def _check_upcoming_todos(db: Session, user: User, smtp_setting: UserSmtpSetting | None):
    today = date.today()
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
            _check_upcoming_todos(db, user, smtp_setting)
        db.commit()
    finally:
        db.close()


def start_scheduler():
    if scheduler.running:
        return
    scheduler.add_job(daily_notification_job, "interval", hours=12, id="notify_job")
    scheduler.start()
