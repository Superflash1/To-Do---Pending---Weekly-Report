# 整体项目规划（Plan）

> 本文已根据当前确认需求冻结为 V1（2026-03-20）。

## 1. 需求冻结（V1）

### 1.1 产品目标
构建一套可演进的「链接沉淀 + 待办执行 + 智能周报/提醒」系统：
- 录入链接后自动分类，支持人工纠正；
- 待办采用左列表右详情，支持文字与图片；
- 支持邮件提醒与周报生成；
- 本地 MVP 可用，同时保持 Docker 上云迁移友好。

### 1.2 已确认约束
- 用户规模：首版面向 **2-10 人小团队**。
- 架构方案：**方案 B（Vue + FastAPI 前后端分离）**。
- 登录：**邮箱 + 密码**。
- 大模型：**OpenAI 兼容接口（可替换）**。
- 链接录入：首版支持 **批量粘贴**。
- 链接解析：首版仅抓取 **标题/描述**（轻量 MVP）。
- 分类策略：**优先归入已有分类**，低置信度再新建类别。
- 待办编辑：**Markdown + 富文本双模式**。
- 图片存储：Docker 本地卷。
- 待办时间：用户可设置 **due_date**；系统自动维护 **completed_at**（用于周报统计）。
- 邮件推送：启用阈值提醒、未来 7 日提醒、周报邮件、SMTP 测试邮件。
- 周报触发：**手动 + 定时**。
- 周报风格：**简洁执行版**。
- 默认时区/语言：Asia/Shanghai + 中文。
- 未来部署：任意 VPS 上 Docker。
- 安全要求：MVP 基础安全（JWT、密码哈希、输入校验）。

---

## 2. 架构设计（方案 B）

### 2.1 技术栈
- 前端：Vue 3 + TypeScript + Vite + Pinia + Vue Router + Element Plus
- 后端：FastAPI + SQLAlchemy + Pydantic + Alembic
- 数据库：PostgreSQL
- 调度：APScheduler（后续可迁移 Celery + Redis）
- 邮件：SMTP
- 存储：本地卷（后续可切 S3/OSS）
- 部署：Docker Compose（frontend / backend / postgres）

### 2.2 分层
- `frontend/`：界面与交互
- `backend/api/`：鉴权、参数、响应
- `backend/services/`：业务规则（分类、提醒、周报）
- `backend/integrations/`：LLM/SMTP/网页抓取适配
- `backend/scheduler/`：定时任务入口

### 2.3 多用户预埋
- 全业务表带 `owner_id`（后续可扩展 `workspace_id`）
- 配置按用户隔离（SMTP、提醒规则、Prompt）
- 所有查询默认按用户过滤

---

## 3. 功能模块

## 3.1 链接管理（Link Inbox）
1. 支持批量粘贴 URL（换行分隔）
2. 自动抓取：`title`、`description`、`domain`
3. 自动分类：
   - 传入现有分类列表给 LLM；
   - 优先匹配已有分类；
   - 低置信度时新建分类。
4. 人工纠偏：前端可修改分类，标记来源为 `manual`
5. 状态：`unread / read / ignored`
6. 统计未读数量，用于阈值邮件提醒

## 3.2 待办管理（Todo Workspace）
1. 左侧：待办列表（筛选：全部/未完成/已完成/近7天）
2. 右侧：详情面板
   - 标题
   - 内容（Markdown 与富文本切换）
   - 图片上传与预览
   - 状态（todo / in_progress / done）
   - 截止日期 `due_date`
3. 自动时间规则：
   - 状态变为 `done` 时自动写入 `completed_at`
   - 从 `done` 改回其他状态时清空 `completed_at`（可配置）

## 3.3 周报（AI Weekly Report）
1. 数据源仅为：过去 7 天 `completed_at` 命中的已完成待办
2. 支持自定义 Prompt 模板
3. 支持手动触发 + 周期定时触发
4. 输出风格：简洁执行版（摘要 + 关键成果）
5. 生成后可邮件发送

## 3.4 邮件提醒（SMTP）
1. 未读链接阈值提醒
2. 未来 7 日待办提醒
3. 周报发送邮件
4. SMTP 测试邮件

---

## 4. 数据库设计（V1）

## 4.1 用户与配置
### `users`
- `id` (PK)
- `email` (unique)
- `password_hash`
- `display_name`
- `is_active`
- `created_at`, `updated_at`

### `user_smtp_settings`
- `id` (PK)
- `owner_id` (FK -> users.id)
- `smtp_host`
- `smtp_port`
- `smtp_username`
- `smtp_password_encrypted`
- `from_email`
- `from_name`
- `use_tls`
- `is_enabled`
- `created_at`, `updated_at`

### `user_preferences`
- `id` (PK)
- `owner_id` (FK)
- `timezone` (default: `Asia/Shanghai`)
- `language` (default: `zh-CN`)
- `unread_link_threshold`
- `weekly_report_day_of_week` (0-6)
- `weekly_report_prompt_template`
- `weekly_report_enabled`
- `created_at`, `updated_at`

## 4.2 链接域
### `link_categories`
- `id` (PK)
- `owner_id` (FK)
- `name`
- `description`
- `created_by` (`ai`/`manual`)
- `created_at`, `updated_at`

### `link_items`
- `id` (PK)
- `owner_id` (FK)
- `url`
- `title`
- `description`
- `domain`
- `status` (`unread`/`read`/`ignored`)
- `category_id` (FK)
- `classification_source` (`ai`/`manual`)
- `classification_confidence` (nullable)
- `created_at`, `updated_at`

### `link_classification_logs`
- `id` (PK)
- `owner_id` (FK)
- `link_item_id` (FK)
- `llm_model`
- `input_snapshot`
- `output_snapshot`
- `confidence`
- `accepted`
- `created_at`

## 4.3 待办域
### `todo_items`
- `id` (PK)
- `owner_id` (FK)
- `title`
- `status` (`todo`/`in_progress`/`done`)
- `due_date` (date, nullable)
- `completed_at` (datetime, nullable, system-managed)
- `created_at`, `updated_at`

### `todo_contents`
- `id` (PK)
- `owner_id` (FK)
- `todo_id` (FK)
- `content_markdown` (nullable)
- `content_richtext` (nullable)
- `editor_mode` (`markdown`/`richtext`)
- `created_at`, `updated_at`

### `todo_images`
- `id` (PK)
- `owner_id` (FK)
- `todo_id` (FK)
- `file_path`
- `file_name`
- `mime_type`
- `size_bytes`
- `created_at`

## 4.4 周报与通知
### `weekly_reports`
- `id` (PK)
- `owner_id` (FK)
- `period_start`
- `period_end`
- `prompt_used`
- `content`
- `llm_model`
- `generated_at`

### `notification_logs`
- `id` (PK)
- `owner_id` (FK)
- `type` (`unread_links`/`upcoming_todos`/`weekly_report`/`smtp_test`)
- `subject`
- `recipient`
- `status` (`success`/`failed`)
- `error_message` (nullable)
- `created_at`

---

## 5. API 清单（V1）

## 5.1 鉴权
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/users/me`

## 5.2 用户配置
- `PUT /api/users/me/preferences`
- `PUT /api/users/me/smtp-settings`
- `POST /api/notifications/test-email`

## 5.3 链接
- `POST /api/links/batch`（批量新增并触发分类）
- `GET /api/links`
- `PATCH /api/links/{id}`（状态、分类）
- `GET /api/link-categories`
- `POST /api/link-categories`

## 5.4 待办
- `POST /api/todos`
- `GET /api/todos`
- `GET /api/todos/{id}`
- `PATCH /api/todos/{id}`（状态变化触发 completed_at 规则）
- `DELETE /api/todos/{id}`
- `POST /api/todos/{id}/images`
- `DELETE /api/todos/{id}/images/{image_id}`

## 5.5 周报与提醒
- `POST /api/reports/weekly/generate`
- `GET /api/reports/weekly`
- `POST /api/notifications/send-unread-links`
- `POST /api/notifications/send-upcoming`
- `POST /api/notifications/send-weekly-report`

---

## 6. 前端页面（V1）

1. 登录/注册页
2. 仪表盘（未读链接、未来7日待办、最近周报）
3. 链接池：批量录入、列表、分类纠偏
4. 待办池：左列表右详情（Markdown/富文本切换 + 图片）
5. 周报页：Prompt 配置、手动生成、历史查看、发送邮件
6. 设置页：SMTP、提醒阈值、周报触发日

---

## 7. 调度与任务（V1）

APScheduler 定时任务：
1. 每日固定时间：发送未来 7 日待办提醒
2. 每小时：检查未读链接阈值并提醒
3. 每周指定周几：自动生成周报并发送（可开关）

> 说明：单实例部署可直接运行。多实例时需要分布式锁或独立 worker 避免重复触发。

---

## 8. 安全（V1）

- JWT 鉴权
- 密码哈希（bcrypt/argon2）
- 输入校验（Pydantic）
- SMTP 密码加密存储
- 图片上传类型/大小限制

---

## 9. 里程碑（建议）

### Phase 1：项目骨架
- 前后端初始化
- 鉴权与用户配置
- Docker Compose 跑通

### Phase 2：链接模块
- 批量录入
- 自动分类
- 人工纠偏

### Phase 3：待办模块
- 左右布局
- 双编辑器
- 图片上传
- 状态与时间规则

### Phase 4：周报与提醒
- 周报生成（手动+定时）
- SMTP 推送全链路

### Phase 5：稳定性
- 日志完善
- 重试策略
- 体验打磨

---

## 10. 验收标准（V1）

1. 批量粘贴链接后可自动分类，且可手动改分类。
2. 待办支持左列表右详情，支持 Markdown/富文本与图片。
3. 待办状态改为 done 时自动写入 `completed_at`，并用于周报统计。
4. 周报支持手动与定时生成，并可邮件发送。
5. 未读链接阈值提醒、未来7日提醒、SMTP测试邮件均可正常发送。
6. Docker Compose 一键启动后可在本地完整跑通主流程。