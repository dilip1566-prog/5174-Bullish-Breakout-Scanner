# Bullish Breakout Scanner -- web UI
# Stage 1: build the static bundle.
FROM node:24-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Vite inlines env vars at BUILD time, so the API base has to be known here --
# it cannot be changed by setting an env var on the running container.
#
# The browser runs on the host, not inside this network, so this must be an
# address the host can reach: the backend's published port, not "backend:8000".
ARG VITE_API_BASE=http://127.0.0.1:8000
ENV VITE_API_BASE=$VITE_API_BASE

RUN npm run build

# Stage 2: serve it.
FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 5174

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:5174/ || exit 1
