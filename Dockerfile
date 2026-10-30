# ---------- Stage 1: build ไฟล์ static ด้วย Node ----------
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# ---------- Stage 2: เสิร์ฟด้วย Nginx (image เล็ก ไม่มี Node) ----------
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
COPY docker-entrypoint.sh /docker-entrypoint.d/40-teamup-config.sh
RUN chmod +x /docker-entrypoint.d/40-teamup-config.sh
EXPOSE 80
HEALTHCHECK CMD wget -qO- http://localhost/health || exit 1
