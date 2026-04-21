# TODO for frontend-container: add multi-stage builds and static asset serving optimization for production.
FROM node:20-alpine

WORKDIR /app

COPY package.json .
RUN npm install

COPY . .

CMD ["npm", "run", "dev"]
