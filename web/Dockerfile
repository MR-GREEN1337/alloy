FROM node:20 AS base

# Dependencies stage
FROM base AS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
  libc6 \
  build-essential \
  python3 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Add caching for npm
COPY package.json package-lock.json* ./
RUN \
  if [ -f package-lock.json ]; then export CI=1 &&   npm ci --omit=dev; \
  else echo "Warning: Lockfile not found." && npm install --omit=dev; \
  fi

# Builder stage
FROM base AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED=1

# Robust NPM download
RUN npm config set fetch-retry-maxtimeout 600000
RUN npm config set fetch-retries 5

RUN npm install --force && npm rebuild && npm run build


# Runner stage
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV NPM_CONFIG_PRODUCTION=true
ENV PORT=3000

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy public files and built application
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Set up .next directory
RUN mkdir -p .next && chown nextjs:nodejs .next

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/api/health || exit 1

CMD ["node", "server.js"]
