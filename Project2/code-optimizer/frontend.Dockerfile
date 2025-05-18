# 1) build stage
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ .
RUN npm run build

# 2) runtime stage
FROM nginx:1.25-alpine
COPY --from=build /app/dist /usr/share/nginx/html

# ensure SPA fallback
RUN sed -i '/try_files/a \\    error_page 404 /index.html;' /etc/nginx/conf.d/default.conf

# map /api to your backend in Docker local via Docker network
# docker-compose or manual: frontend and backend on same bridge network,
# and nginx hostname 'codeopt-backend' resolves to the backend container.
# so in Docker you’d run with:
#   --network codeopt-net
#   and your compose sets:
#     extra_hosts: ["host.docker.internal:host-gateway"]
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
