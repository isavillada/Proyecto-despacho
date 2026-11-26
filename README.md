# Plataforma de Gestión del Despacho de la Secretaría de Cultura de Pereira

**Entrega candidata 4.0 — Ingeniería de Software III**

Equipo del documento original: Iván Andrés Barrios Barinas, Juan José Bautista Muñoz e Isabela Villada Osorio. Basada en el Documento de Visión y Alcance del 17/09/2026 (CAR-01 a CAR-20, releases 1.0–4.0) y en las secciones del Despacho del Manual de Procedimientos de Cultura 2024. No modifica esos documentos ni incorpora el alcance académico de estudiantes y docentes de la propuesta Lucy Tejada.

## Estado de la entrega: léase antes de ejecutar

| Modalidad | Componentes | Estado de verificación |
|---|---|---|
| Arquitectura objetivo | React 18 + Spring Boot 3.4.5 (Java 21) + PostgreSQL 16 + API REST | Código, migración Flyway, pruebas Java y configuración de despliegue incluidos. Análisis sintáctico Java y prueba aislada de calendario realizados. **Compilación Maven, build Vite y ejecución real con PostgreSQL pendientes de validación**. |
| Demostración local | La misma interfaz React (vista previa offline con React 16) + FastAPI + SQLite | Seis pruebas API y una prueba de interfaz Chromium con puente local hacia la API real superadas. No usar para producción ni datos personales reales. |

Se conserva el backend Python original, mejorado, como demostración y referencia de migración. El backend objetivo es el de `backend/`, NO un proxy hacia Python. La configuración Docker despliega únicamente React, Spring Boot y PostgreSQL. Las dos modalidades no comparten bases de datos. No se presupone autorización para cambiar el stack comprometido.

No existe un hosting público ni un repositorio GitHub publicado desde esta entrega. Staging, producción y HTTPS están preparados como configuración y requieren un servidor, dominios, credenciales y ejecución por el equipo. No se certifica aún la aceptación institucional o compatibilidad en todos los navegadores.

## 1. Demostración rápida en Windows

1. Descomprima todo el ZIP. Abra en Visual Studio Code la carpeta que contiene este README.
2. Tenga Python 3.11 o superior (las pruebas se ejecutaron con Python 3.13). La primera instalación requiere acceso a las dependencias de PyPI.
3. Ejecute `iniciar_demo.bat` o use la terminal PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abra **http://127.0.0.1:8000**. Usuario `admin`; en la primera ejecución se genera una contraseña aleatoria y aparece una única vez en la terminal. Si desea establecerla antes de la primera ejecución, configure `$env:ADMIN_PASSWORD` con una clave propia de 10–128 caracteres, mayúscula, minúscula, número y símbolo. No reutilice claves de ejemplo. Al reiniciar se mantiene la cuenta de la base existente; cambiar la variable no restablece una cuenta ya creada. Detenga el servidor con Ctrl+C. La documentación de la API de compatibilidad está en `/docs`.

El archivo `despacho.db` (o `demo.db` al usar el .bat) y los documentos locales se generan automáticamente. Use una base nueva: el ZIP original no incluía datos y las tablas antiguas no son migradas automáticamente por `create_all` de Python. Si cuenta con una base previa, haga copia y planifique una migración, no la borre.

## 2. Ejecutar la arquitectura acordada (candidata a validación)

Requiere Docker Engine/Desktop con Compose v2, Java 21/Maven si prueba el backend fuera de Docker, Node 22/npm si desarrolla el frontend fuera de Docker y conexión a los repositorios de dependencias e imágenes. Desde la raíz, en PowerShell:

```powershell
Copy-Item deploy/staging.env.example .env.staging
notepad .env.staging
```

Complete `POSTGRES_PASSWORD`, `APP_SECRET` (mínimo 32 bytes aleatorios), `ADMIN_PASSWORD` (compleja) y `APP_PORT=8081`. Use valores únicos y secretos. Una clave aleatoria se puede generar con `python -c "import secrets; print(secrets.token_urlsafe(48))"` o un gestor de contraseñas.

```powershell
docker compose --env-file .env.staging -p cultura-staging up --build -d
docker compose --env-file .env.staging -p cultura-staging ps
docker compose --env-file .env.staging -p cultura-staging logs -f app
```

Abra **http://127.0.0.1:8081** y **http://127.0.0.1:8081/api/salud**. Ingrese con `admin` y la contraseña propia configurada. Si una dependencia, compilación o migración falla, revise los logs antes de declarar la entrega aceptada. No use datos reales hasta pasar las pruebas de aceptación y revisión de seguridad.

Para producción, copie `deploy/production.env.example` a `.env.production`, utilice secretos distintos, puerto 8080 y proyecto Compose `cultura-production`. Los nombres distintos de proyecto separan redes, volúmenes de PostgreSQL y documentos. La configuración `deploy/Caddyfile` es para un hosting con dos dominios reales y TLS; consulte el manual de administración. No exponga directamente el puerto de la base de datos.

## 3. Estructura

```text
app/                       Backend de compatibilidad FastAPI
backend/                   Backend objetivo Spring Boot (Maven)
  src/main/java/           Controladores, servicios, autenticación, validaciones
  src/main/resources/      Configuración y migración Flyway de PostgreSQL
  src/test/java/           Pruebas JUnit y Testcontainers
frontend/                  Interfaz React compartida
  preview/                 Runtime offline SOLO para la demostración local
  ui.js, style.css         Componentes y estilos responsivos
  main.js, package.json    Build de React 18 con Vite
 tests/                     Pytest y prueba local de navegador
 deploy/                    Plantillas de staging, producción y HTTPS
 evidencia/                 Capturas de pruebas con datos ficticios y resultados
 docs/                      Manuales, trazabilidad, pruebas de aceptación
 Dockerfile, compose.yaml   Build y ejecución de arquitectura objetivo
 .github/workflows/ci.yml   Pipeline propuesto para GitHub Actions
```

## 4. Verificación

Demostración (desde raíz):

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip install playwright
.\.venv\Scripts\python.exe -m playwright install chromium
$env:PYTHONPATH = '.'
.\.venv\Scripts\python.exe tests/ui_smoke.py
```

La prueba de navegador usa un puente local hacia FastAPI TestClient, no un despliegue HTTP real. Las capturas son de la interfaz efectivamente renderizada; solo contienen datos ficticios. El navegador de este entorno bloqueó la navegación a la URL local, por lo que el flujo HTTP desde navegador queda por comprobar en el equipo de ustedes.

Arquitectura acordada (con Maven y Docker disponibles):

```powershell
cd frontend
npm install
npm run build
cd ../backend
mvn clean test
mvn package
```

El test integrado Java usa Testcontainers; si Docker no está disponible se omite y la aceptación sigue pendiente. Compruebe en `target/surefire-reports` que `FlujoPostgresTest` se ejecutó sin omitirse. El build de frontend independiente puede usarse con `npm run dev` y Spring Boot activo en 8080; el Dockerfile copia automáticamente `dist` dentro de los recursos estáticos de Spring Boot.

## 5. Documentación

- [Manual técnico](docs/Manual_tecnico.md) y su PDF.
- [Manual de administración](docs/Manual_administracion.md) y su PDF.
- [Manual de usuario](docs/Manual_usuario.md) y su PDF.
- [Matriz de trazabilidad CAR-01 a CAR-20](docs/Matriz_trazabilidad.md).
- [Plan de pruebas y criterios de aceptación](docs/Pruebas_aceptacion.md).
- [Decisiones y pendientes verificables](docs/Decisiones_y_pendientes.md).
- [Contrato de la API REST](docs/Contrato_API.md).

## 6. Git y GitHub

Se creó un historial Git local con la base original y las modificaciones. El archivo `historial-git.bundle` incluido en la distribución permite recuperar el historial: desde la carpeta descomprimida, ejecute `git clone historial-git.bundle ../cultura-versionada`. Trabaje desde el clon. Cree un repositorio privado vacío en la cuenta del equipo, copie su URL real y ejecute `git remote add origin URL_DEL_REPOSITORIO` y `git push -u origin HEAD`. No incluya `.env.*`, datos de ciudadanos ni contraseñas. Este paso no se ejecutó externamente.

## 7. Límites del alcance

El sistema no radica solicitudes oficialmente, no accede a SAIA/SIIF/Ventanilla Única, no realiza pagos o desembolsos, no firma o aprueba documentos en nombre de funcionarios, no reemplaza soportes externos. Solo registra y consulta información, estados, responsables, documentos y reportes. El cálculo del vencimiento es una ayuda orientativa, no una certificación jurídica. Los registros de revisión reflejan actuaciones efectivamente realizadas por el personal autorizado.
