FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm install --force \
    && npm cache clean --force 

COPY . .

EXPOSE 3000

CMD ["npm", "run", "start"]
