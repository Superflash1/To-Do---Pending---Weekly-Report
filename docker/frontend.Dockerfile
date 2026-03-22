FROM node:20-alpine AS builder

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend /app
# 生产构建：前端静态资源
RUN npm run build

FROM nginx:1.27-alpine AS runtime

# 用自定义配置处理 SPA 路由和 /api 反向代理
COPY docker/nginx.frontend.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
