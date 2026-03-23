# 第二大脑系统（Vue + FastAPI）

基于 `doc/plan.md` 的可运行 MVP 实现。

## 功能概览

- 批量录入链接，自动解析标题/描述并做 AI 分类
- 链接状态管理与人工纠偏分类
- 待办左侧列表 + 右侧详情，支持 Markdown / 富文本字段与图片上传
- 完成待办自动记录 `completed_at`
- 周报（手动生成）基于过去 7 天已完成事项
- SMTP 测试邮件、未来7日提醒、未读链接提醒
- 内置调度器（APScheduler）定期执行提醒检查

## 目录结构

- `backend/` FastAPI 后端
- `frontend/` Vue3 前端
- `doc/plan.md` 需求与规划
- `run_local.bat` 本地一键启动（uv + SQLite）

## 启动步骤

1. 复制环境变量

```bash
cp .env.example .env
```

2. 修改 `.env` 中关键配置（LLM、SMTP 等；数据库默认 SQLite）

3. 启动

- Windows：双击 `run_local.bat`

4. 访问

- 前端：http://localhost:5173
- 后端：http://localhost:8000
- 健康检查：http://localhost:8000/health

## 首次使用建议

1. 注册账号并登录
2. 在「设置」中保存周报提示词
3. 到「链接池」粘贴多条链接导入
4. 到「待办池」创建条目并编辑详情
5. 在「周报」页点击生成

## 注意事项

- 当前为 MVP，数据库表由应用启动时自动创建（未接 Alembic 迁移）
- SMTP 凭据请使用应用专用密码
- 图片存储在 `./uploads` 目录（生产建议挂载该目录）
- 生产环境务必配置 `JWT_SECRET`（禁止使用默认值 `change_me`）
- 可通过 `CORS_ALLOW_ORIGINS` 配置允许的前端域名（逗号分隔）
