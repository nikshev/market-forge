# The chart application as PRD §6.2's `web` service.
#
# @trace: REQ-WP-064
#
# The build output is static files; the runtime is a web server holding them.
# `npm ci` against the committed lockfile, the same command CI runs, so the
# image cannot contain a dependency tree nobody tested against.
#
# `VITE_API_BASE` is left empty on purpose: the browser then calls the same
# origin it loaded from, and nginx forwards `/api` to the API service. Baking an
# absolute URL would put a deployment's hostname inside an artifact meant to be
# promoted between deployments.

FROM node:22-alpine AS build

WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build


FROM nginx:1.27-alpine AS runtime

COPY --from=build /src/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080
