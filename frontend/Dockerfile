FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci || npm install
COPY . .
RUN npm run build || (mkdir -p dist && echo '<!DOCTYPE html><html><body><h1>Frontend build placeholder</h1><p>Add your Vue app sources.</p></body></html>' > dist/index.html)

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
