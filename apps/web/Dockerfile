FROM node:20-alpine AS builder
WORKDIR /app

# Copy package files first
COPY apps/web/package.json ./package.json

# Remove workspace dependency for Docker
RUN node -e "const p = require('./package.json'); delete p.dependencies['@aegis/types']; require('fs').writeFileSync('./package.json', JSON.stringify(p, null, 2))"

# Install dependencies
RUN npm install --include=dev

# Copy source files individually to avoid overwriting node_modules
COPY apps/web/src ./src
COPY apps/web/public ./public
COPY apps/web/next.config.ts ./next.config.ts
COPY apps/web/tsconfig.json ./tsconfig.json
COPY apps/web/tailwind.config.ts* ./
COPY apps/web/postcss.config.* ./
COPY apps/web/components.json* ./

ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=$NEXT_PUBLIC_SUPABASE_ANON_KEY

RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
CMD ["node", "server.js"]
