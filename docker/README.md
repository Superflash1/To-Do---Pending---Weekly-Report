# Docker 开发环境说明（SQLite）

当前 Docker 配置已按**开发模式**优化，支持前后端热更新，并保持你现有的 `docker compose -f docker/docker-compose.yml ...` 调用方式。

## 文件说明

- `docker/docker-compose.yml`：开发环境编排（热更新、健康检查、依赖顺序）
- `docker/backend.Dockerfile`：后端开发镜像
- `docker/frontend.Dockerfile`：前端开发镜像
- `.env.example`：环境变量模板

## 启动前准备

1. 安装并启动 Docker Desktop。
2. 在项目根目录准备 `.env`：
   - PowerShell：`Copy-Item .env.example .env`
3. 确认关键变量：
   - `DATABASE_URL=sqlite:///./data/brain_tool.db`
   - `VITE_API_BASE_URL=http://localhost:8000`
4. 确保项目根目录存在 `data/` 目录。

## 启动与停止

> 以下命令均在项目根目录执行。

### 首次启动 / 重建启动

```bash
docker compose -f docker/docker-compose.yml up --build -d
```

### 查看状态

```bash
docker compose -f docker/docker-compose.yml ps
```

### 查看日志

```bash
docker compose -f docker/docker-compose.yml logs -f --tail=200
docker compose -f docker/docker-compose.yml logs -f backend
docker compose -f docker/docker-compose.yml logs -f frontend
```

### 停止

```bash
docker compose -f docker/docker-compose.yml down
```

## 开发模式特性

- 后端挂载 `../backend:/app`，代码变更可立即生效（`uvicorn --reload`）
- 前端挂载 `../frontend:/app`，Vite 热更新可用
- 前端依赖后端健康检查（`/health`）通过后再启动
- 通过匿名卷保留容器内 `node_modules`，避免主机环境污染

## 访问地址

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`
- Swagger：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`

## 常见问题

### 前端能打开但接口报错

- 检查 `.env` 中 `VITE_API_BASE_URL` 是否为 `http://localhost:8000`
- 查看后端日志是否有异常

### 数据库文件未生成

- 检查 `DATABASE_URL` 是否为 `sqlite:///./data/brain_tool.db`
- 检查 `data/` 目录是否可写

### Windows 下前端热更新不稳定

已在 compose 中启用 `CHOKIDAR_USEPOLLING=true`，如仍异常可重启前端容器。
