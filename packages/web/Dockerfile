FROM node:20.19.0-slim AS build

WORKDIR /app

# Copy root workspace files first so npm can resolve hoisted dependencies
COPY package*.json ./
COPY packages/web/package*.json ./packages/web/

RUN npm install --workspace=packages/web

COPY packages/web ./packages/web

RUN npm run build --workspace=packages/web

FROM nginx:1.27-alpine

COPY --from=build /app/packages/web/dist /usr/share/nginx/html
COPY packages/web/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000
