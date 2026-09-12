# Stage 1: Build production React SPA bundle
FROM node:20-alpine AS builder

WORKDIR /app

# Enable pnpm matching packageManager defined in package.json
RUN npm install -g pnpm@12.3.4

# Install dependencies using lockfile
COPY package.json pnpm-lock.yaml* package-lock.json* ./
RUN pnpm install

# Copy source code and build production assets
COPY . .
RUN pnpm run build

# Stage 2: Serve production bundle with Nginx
FROM nginx:alpine AS runner

# Remove default Nginx welcome configuration
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom Nginx configuration with reverse proxy and SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
