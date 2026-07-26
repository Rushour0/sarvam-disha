# Next.js standalone build. Built in GitHub Actions and pushed to GHCR, not
# built on the server — the box is 2 vCPU with the ludexel stack already on it,
# and a Next build there competes with a live call.

FROM node:22-alpine AS deps
WORKDIR /app
RUN corepack enable
COPY web/package.json web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

FROM node:22-alpine AS builder
WORKDIR /app
RUN corepack enable
COPY --from=deps /app/node_modules ./node_modules
COPY web/ ./
# NEXT_PUBLIC_* values are inlined at build time, so they have to be present
# here rather than at runtime.
ARG NEXT_PUBLIC_DISHA_API=/api/disha
ARG NEXT_PUBLIC_CONN_DETAILS_ENDPOINT
ENV NEXT_PUBLIC_DISHA_API=$NEXT_PUBLIC_DISHA_API \
    NEXT_PUBLIC_CONN_DETAILS_ENDPOINT=$NEXT_PUBLIC_CONN_DETAILS_ENDPOINT \
    NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup -g 10001 -S nodejs && adduser -u 10001 -S nextjs -G nodejs

# `output: 'standalone'` emits everything the server needs except these two.
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
