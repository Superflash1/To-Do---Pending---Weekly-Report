# Docker 部署说明（SQLite）

当前 Docker 配置已调整为**服务器可用部署模式**：
- 前端使用 Nginx 提供静态文件
- Nginx 反向代理 `/api` 到后端容器
- 避免 Vite 开发服务器在生产环境出现一直加载的问题

## 文件说明

- `docker/docker-compose.yml`：部署编排（后端健康检查、前端依赖顺序）
- `docker/backend.Dockerfile`：后端镜像
- `docker/frontend.Dockerfile`：前端多阶段构建镜像（Node 构建 + Nginx 运行）
- `docker/nginx.frontend.conf`：前端 Nginx 配置（SPA 回退 + API 反向代理）
- `.env.example`：环境变量模板

## 启动前准备

1. 安装并启动 Docker Desktop。
2. 在项目根目录准备 `.env`：
   - PowerShell：`Copy-Item .env.example .env`
3. 确认关键变量：
   - `DATABASE_URL=sqlite:///./data/brain_tool.db`
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

## 部署模式特性

- 后端仍可热重载（`uvicorn --reload`）
- 前端使用 `npm run build` 产物，由 Nginx 提供静态页面
- 前端容器依赖后端健康检查（`/health`）通过后再启动
- Nginx 将 `/api`、`/health`、`/docs`、`/openapi.json` 转发到后端容器
- 支持 Vue Router History 模式（刷新子路由不 404）

## 访问地址

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`
- Swagger：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`

## 常见问题

### 前端页面一直转圈 / 登录后无数据

- 先执行重建：`docker compose -f docker/docker-compose.yml up --build -d`
- 查看前端日志确认 Nginx 正常启动：`docker compose -f docker/docker-compose.yml logs -f frontend`
- 查看后端健康状态：`docker compose -f docker/docker-compose.yml ps`
- 浏览器访问 `http://服务器IP:端口/health`，应返回后端健康结果

### 数据库文件未生成

- 检查 `DATABASE_URL` 是否为 `sqlite:///./data/brain_tool.db`
- 检查 `data/` 目录是否可写

### Windows 下前端热更新不稳定

已在 compose 中启用 `CHOKIDAR_USEPOLLING=true`，如仍异常可重启前端容器。
