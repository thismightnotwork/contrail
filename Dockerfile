FROM node:24-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
COPY integrate-acars.mjs /web/integrate-acars.mjs
RUN node integrate-acars.mjs && npm run build

FROM python:3.12-slim
WORKDIR /app
COPY server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt 'python-socketio[client]>=5.12,<6'
COPY server/flightmap ./flightmap
COPY --from=web /web/dist /app/web-dist
ENV HOST=0.0.0.0 STATIC_DIR=/app/web-dist DATA_DIR=/data GZIP=1 DEMO_MODE=0 USER_AGENT_CONTACT=https://github.com/thismightnotwork/contrail
RUN mkdir -p /data
CMD ["python", "-m", "flightmap.combined"]
