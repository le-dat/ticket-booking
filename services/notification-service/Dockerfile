# Step 1: Base image with pnpm
FROM node:22-alpine AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

# Step 2: Build dependencies & application
FROM base AS builder
WORKDIR /app
COPY package.json ./
RUN pnpm install
COPY . .
RUN pnpm run build

# Step 3: Production dependencies & runner
FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY package.json ./
RUN pnpm install --prod
COPY --from=builder /app/dist ./dist

EXPOSE 3005
CMD ["node", "dist/main"]
