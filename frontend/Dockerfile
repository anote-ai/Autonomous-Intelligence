FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm install && npm cache clean --force

COPY . .

EXPOSE 3000

CMD ["npm", "run", "start"]
