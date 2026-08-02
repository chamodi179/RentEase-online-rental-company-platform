FROM node:26-slim AS deps
WORKDIR /app
COPY package.json ./
RUN npm install

FROM node:26-slim AS builder
WORKDIR /app
# See apps/admin/Dockerfile for why this needs to be a build ARG rather
# than relying on docker-compose's `environment:` (that only applies at
# container start, after NEXT_PUBLIC_* values are already baked in).
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
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
EXPOSE 3000
CMD ["npm", "start"]
