ARG NODE_BASE_IMAGE=docker.m.daocloud.io/library/node:22-alpine
FROM ${NODE_BASE_IMAGE}

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

# Copy sources so the image works even without bind mounts.
COPY . /app

EXPOSE 3000
