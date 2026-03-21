# 本系统 Docker 运行说明（SQLite 版本）

按你的要求，Docker 方案已改为 **不依赖 PostgreSQL**，统一使用 SQLite。

## 目录结构

- `docker/docker-compose.yml`
- `docker/backend.Dockerfile`
- `docker/frontend.Dockerfile`
- `docker/README.md`（本说明）

## 启动前准备

1. 安装并启动 Docker Desktop。
2. 在项目根目录准备环境变量文件：
   - 如果没有 `.env`，请从 `.env.example` 复制一份：
     - Windows PowerShell: `Copy-Item .env.example .env`
3. 确认 `.env` 中关键项：
   - `DATABASE_URL=sqlite:///./data/brain_tool.db`
   - `VITE_API_BASE_URL=http://localhost:8000`
4. 确保项目根目录存在 `data/`（compose 已挂载到后端容器）。

## 运行方式

> 以下命令均在 **项目根目录** 执行。

### 1) 首次启动（构建 + 后台运行）

```bash
docker compose -f docker/docker-compose.yml up --build -d
```

### 2) 查看运行状态

```bash
docker compose -f docker/docker-compose.yml ps
```

### 3) 查看日志

```bash
# 全部服务日志
docker compose -f docker/docker-compose.yml logs -f --tail=200

# 后端日志
docker compose -f docker/docker-compose.yml logs -f backend

# 前端日志
docker compose -f docker/docker-compose.yml logs -f frontend
```

### 4) 停止服务

```bash
docker compose -f docker/docker-compose.yml down
```

### 5) 强制重建镜像

```bash
docker compose -f docker/docker-compose.yml build --no-cache
docker compose -f docker/docker-compose.yml up -d
```

## 访问地址

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`
- Swagger：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`

## SQLite 数据位置

- 宿主机：`./data/brain_tool.db`
- 容器内：`/app/data/brain_tool.db`

## 常见问题排查

### 1. 前端启动了但无法请求后端
- 检查 `.env` 的 `VITE_API_BASE_URL` 是否为 `http://localhost:8000`
- 查看后端日志是否报错

### 2. 数据库文件未创建
- 检查 `.env` 中 `DATABASE_URL` 是否为 `sqlite:///./data/brain_tool.db`
- 检查项目根目录 `data/` 是否存在且可写
- 查看后端启动日志是否有建表错误

### 3. 邮件发送失败
- 检查 SMTP 参数是否正确（建议使用邮箱专用授权码）
- 在系统设置页先测试 SMTP

### 4. 链接分类不生效
- 检查 LLM API Key / Base URL / Model 配置
- 未配置 LLM 时系统会降级到默认分类
