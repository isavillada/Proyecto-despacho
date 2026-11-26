# Build the agreed React + Spring Boot architecture; the Python preview is not deployed.
FROM node:22-bookworm-slim AS frontend-build
WORKDIR /work
COPY frontend/package.json frontend/vite.config.js ./
RUN npm install --no-audit --no-fund
COPY frontend/index.html frontend/main.js frontend/ui.js frontend/style.css ./
RUN npm run build

FROM maven:3.9.9-eclipse-temurin-21 AS backend-build
WORKDIR /work
COPY backend/pom.xml ./
COPY backend/src ./src
COPY --from=frontend-build /work/dist/ ./src/main/resources/static/
RUN mvn -B -DskipTests package

FROM eclipse-temurin:21-jre
WORKDIR /app
RUN groupadd --system cultura && useradd --system --gid cultura --no-create-home cultura && mkdir -p /app/uploads && chown -R cultura:cultura /app
COPY --from=backend-build /work/target/despacho-cultura-1.0.0.jar /app/app.jar
USER cultura
EXPOSE 8080
ENTRYPOINT ["java","-jar","/app/app.jar"]
