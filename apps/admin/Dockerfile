FROM node:26-slim AS deps
WORKDIR /app
COPY package.json ./
RUN npm install

FROM node:26-slim AS builder
WORKDIR /app
# NEXT_PUBLIC_* variables are inlined into the client bundle at build time
# (next build), not read at container start. Passing this only via
# docker-compose's `environment:` (which applies at `docker run` time) had
# no effect on the actual built JS — it silently fell back to the
# hardcoded default in lib/api.ts, which happened to match by coincidence.
# Declaring it as a build ARG/ENV here makes docker-compose's build.args
# (see docker-compose.yml) the actual source of truth.
ARG NEXT_PUBLIC_ADMIN_API_URL
ENV NEXT_PUBLIC_ADMIN_API_URL=${NEXT_PUBLIC_ADMIN_API_URL}
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:26-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/next.config.js ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
EXPOSE 3001
CMD ["npm", "start"]
