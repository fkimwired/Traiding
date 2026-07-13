FROM node:24.17.0-alpine

ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app

COPY package.json package-lock.json ./
COPY packages/contracts/package.json ./packages/contracts/package.json
COPY services/frontend/package.json ./services/frontend/package.json

RUN npm ci

COPY packages/contracts ./packages/contracts
COPY services/frontend ./services/frontend

ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build --workspace @fable5/frontend

EXPOSE 3000

CMD ["npm", "run", "start", "--workspace", "@fable5/frontend", "--", "--hostname", "0.0.0.0"]

