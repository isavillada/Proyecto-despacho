# Manual técnico
## Plataforma de Gestión del Despacho de la Secretaría de Cultura de Pereira

**Versión candidata 4.0 | Ingeniería de Software III**

Documento base: Visión y Alcance, 17 de septiembre de 2026, secciones 3.2, 4.1, 5.3 y 6. Este manual documenta la implementación y su instalación; no constituye una certificación de aceptación institucional. La modalidad objetivo usa React, Spring Boot y PostgreSQL. La demostración de compatibilidad usa FastAPI y SQLite, con pruebas locales realizadas.

## 1. Objetivo y alcance

Centralizar información administrativa de peticiones y correspondencia (release 1.0), caja menor (2.0), generación de pagos y presupuesto (3.0), convenios y panel (4.0). Se incluyen autenticación, roles, trazabilidad, gestión documental y reportes XLSX/PDF. Se conserva el carácter de sistema de apoyo: ninguna operación ejecuta trámites en sistemas institucionales externos ni reemplaza las actuaciones de los funcionarios.

## 2. Arquitectura

El frontend React es una SPA (aplicación de una página). `frontend/ui.js` contiene componentes de acceso, navegación, tablas, formularios, panel, documentos, administración y reportes. `main.js` inicializa React 18 y usa `/api`. Vite compila los recursos estáticos. En la versión objetivo, Spring Boot sirve estos recursos en el mismo origen; así no se necesita CORS abierto.

El backend objetivo utiliza Spring Boot 3.4.5, Java 21, Spring MVC, JdbcTemplate, Flyway y PostgreSQL 16. `ApiController` expone la API REST; `AuthService` verifica credenciales y permisos y genera JWT; `RecordsService` implementa validación y transacciones; `DocumentService` almacena soportes; `ReportService` usa Apache POI y OpenPDF; `SecurityHeaders` aplica cabeceras de seguridad. `Calendario` apoya el cálculo de fechas. `ApiErrors` traduce errores controlados a respuestas HTTP.

El Dockerfile compila React, copia sus recursos al backend, construye el JAR Maven y ejecuta Java sin privilegios de root. La base de datos y los documentos persisten en volúmenes independientes. La configuración Compose se usa con proyectos distintos para staging y producción. Caddy, instalado en el hosting, se configura como proxy HTTPS.

Arquitectura de referencia: Navegador → HTTPS / proxy → React + Spring Boot API REST → PostgreSQL. Spring Boot también escribe y lee documentos en un volumen privado. PostgreSQL no publica puertos al exterior.

## 3. Directorios y código

- `frontend/`: interfaz React, Vite, estilos, formularios y vista previa offline de desarrollo.
- `backend/src/main/java/co/pereira/cultura/`: código Java de la arquitectura objetivo.
- `backend/src/main/resources/application.properties`: conexión, migraciones y parámetros de archivos.
- `backend/src/main/resources/db/migration/V1__esquema.sql`: esquema PostgreSQL versionado por Flyway.
- `backend/src/test/java/`: pruebas de calendario y flujo integral con PostgreSQL mediante Testcontainers.
- `app/`: implementación de compatibilidad FastAPI del ZIP original, ampliada; no se despliega en la arquitectura objetivo.
- `tests/`: seis pruebas Pytest y script local de navegador Chromium con datos sintéticos.
- `docs/`, `evidencia/`, `deploy/`: documentación, capturas/resultados y configuración de despliegue.

## 4. Modelo de datos

El esquema objetivo contiene diez tablas. Las llaves primarias son identificadores numéricos. Los valores monetarios usan NUMERIC(15,2), no flotantes en persistencia. Las fechas de los trámites usan DATE; la auditoría de Java utiliza TIMESTAMPTZ y el sistema conserva el usuario responsable. Los documentos se almacenan fuera de la base de datos, con UUID y metadatos.

- `usuarios` y `auditoria`: cuenta, nombre, rol, hash, activo, versión de token; fecha/hora, acción, entidad, registro y detalle.
- `peticiones`: radicado único, fecha de ingreso, peticionario, solicitud, modalidad, plazo, vencimiento, responsable, respuesta y estado.
- `cajas_menores`: vigencia única, resolución, fondo, ciclo, sobrante y estado.
- `gastos_caja_menor`: FK a caja, ciclo, concepto, importe, fecha, recibo, autorización y revisión.
- `reintegros_caja_menor`: FK a caja, ciclo, fecha, importe, referencia, responsable y observaciones.
- `solicitudes_presupuestales`: tipo, número, descripción, importe, fecha, estado, referencia SIIF, responsable y observaciones.
- `descuentos`: FK a una solicitud; el servicio exige que sea una orden de pago y valida los montos.
- `convenios`: número único, NIT, entidad, inicio, valor, secretaría y fechas de remisión, liquidación y remisión del acta.
- `documentos`: tipo documental, entidad asociada, identificador, nombre original, ubicación interna y usuario/fecha de carga. Relación polimórfica validada por el servicio, sin FK única; no hay eliminación de registros por API.

Relaciones principales: Caja 1:N Gastos; Caja 1:N Reintegros; Solicitud de orden de pago 1:N Descuentos. Los documentos se asocian a petición, caja, gasto, reintegro, solicitud presupuestal o convenio. La auditoría identifica el registro mediante entidad e identificador.

## 5. Instalación de la demostración local

Requisitos: Python 3.11+; acceso a las dependencias; Windows, macOS o Linux. Las pruebas de este paquete se ejecutaron en Python 3.13. En Windows, desde la raíz:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abra http://127.0.0.1:8000. Usuario inicial admin; si no se configuró `ADMIN_PASSWORD`, se genera una clave única que se imprime al crear la cuenta. Configure `SECRET_KEY` para mantener tokens entre reinicios de desarrollo. `DATABASE_URL` y `UPLOAD_DIR` permiten cambiar ubicaciones. Use una base nueva, ya que no se incluye migración automática de antiguas tablas SQLite. No use datos de ciudadanos en la modalidad de compatibilidad.

## 6. Instalación de la arquitectura objetivo

Requisitos: Docker Desktop/Engine, Compose v2 y acceso a repositorios de dependencias e imágenes. Copie `deploy/staging.env.example` a `.env.staging`; complete el puerto 8081 y secretos propios. `APP_SECRET` exige al menos 32 bytes aleatorios y `ADMIN_PASSWORD` debe cumplir la política. No copie las credenciales a Git ni a las capturas.

```powershell
docker compose --env-file .env.staging -p cultura-staging up --build -d
docker compose --env-file .env.staging -p cultura-staging ps
docker compose --env-file .env.staging -p cultura-staging logs -f app
```

Abra http://127.0.0.1:8081 y compruebe `/api/salud`. Flyway crea las tablas al iniciar; no edite una migración ya aplicada. Para cambios futuros, cree V2, V3 y siguientes. La base se configura por `SPRING_DATASOURCE_URL`, `POSTGRES_USER`, `POSTGRES_PASSWORD`; los documentos por `UPLOAD_DIR`. La configuración de producción debe usar un proyecto Compose y secretos diferentes, detrás de HTTPS. Consulte el manual de administración.

En modo desarrollo Java, instale Java 21, Maven 3.9+ y PostgreSQL; configure las variables antes de ejecutar `mvn spring-boot:run` desde `backend`. En otra terminal, desde `frontend`, ejecute `npm install` y `npm run dev`; Vite redirige `/api` a localhost:8080. Genere y versione el `package-lock.json` después de la primera instalación verificada. El Dockerfile utiliza npm install porque el lockfile no pudo generarse sin acceso a paquetes.

## 7. API REST y seguridad

Las rutas Java están bajo `/api`. La demo mantiene las rutas originales sin prefijo. Las operaciones principales utilizan GET (consulta), POST (creación o registro de actuación) y PATCH (actualización parcial). Los documentos se cargan como multipart/form-data. Los reportes se descargan como archivos binarios. El contrato detallado está en `Contrato_API.md`.

La autenticación usa JWT HS256 con expiración de ocho horas y clave aleatoria de servidor; PBKDF2-HMAC-SHA256 con salt y 600.000 iteraciones; contraseñas de 10–128 caracteres con complejidad; validación de roles en el servidor, bloqueo temporal por intentos reiterados y revocación de sesiones al cambiar credenciales/rol/estado. La interfaz mantiene el token en memoria, no en localStorage. Los cambios de estado se registran como evidencia de una actuación externa. Las autorizaciones son por módulo y acciones críticas; no se ha definido autorización por propietario individual del registro.

La gestión documental acepta PDF, PNG, JPEG, DOCX y XLSX hasta 10 MB; comprueba extensión, firma básica y estructura OOXML cuando corresponde. No se realiza análisis antimalware ni certificación de firmas; se debe aplicar revisión institucional antes de usar archivos reales. No se almacenan contraseñas ni contenido íntegro de peticiones en logs de auditoría de cambios.

## 8. Reglas de negocio relevantes

Peticiones: radicado único, responsable obligatorio cuando está distribuida o en trámite, coherencia entre fechas/estado. Vencimiento explícito o cálculo orientativo en días hábiles (festivos nacionales de referencia). El funcionario confirma el término real.

Caja: apertura, compras, relación de gastos, revisión jurídica, firma, Control Interno, reintegro y cierre. El fondo disponible es fondo inicial + reintegros efectivamente recibidos – gastos acumulados – sobrante consignado. Se exige saldo suficiente, revisión aprobada antes de firma, cierre a cero y se bloquean cambios a cajas y ciclos cerrados. Un nuevo ciclo permite continuar compras durante la vigencia. El sistema registra las actuaciones, no las sustituye.

Presupuesto: tipos de conveniencia, disponibilidad, compromiso, orden de pago, informe de ejecución, informe de pago y modificación. Los descuentos se asocian a órdenes, no a otros tipos; su suma no excede el valor registrado de la orden si está informado. Convenios: contrato asociado antes de remisión, acta antes de liquidación y registro diferenciado de remisión de acta. No se hacen pagos ni transferencias.

## 9. Pruebas, calidad y mantenimiento

En esta entrega se ejecutaron seis pruebas Pytest y una prueba de interfaz con Chromium, usando un puente en memoria hacia el backend FastAPI. No fue posible navegar directamente a localhost desde el navegador del entorno de elaboración. Se incluyen capturas de la interfaz renderizada. El código Java fue analizado sintácticamente por JDK 21 y se ejecutaron tres comprobaciones del calendario Java sin Maven.

Para validar la versión acordada: `cd frontend; npm install; npm run build`; después `cd backend; mvn clean test`. El test Java `FlujoPostgresTest` necesita Docker y PostgreSQL Testcontainers; verifique que no se haya omitido. Luego levante staging y repita la lista de `Pruebas_aceptacion.md` en Chrome, Firefox, Edge, Safari y dispositivos móviles. No se certifican build Maven/Vite, PostgreSQL, HTTPS, navegadores restantes ni pruebas de seguridad de producción desde este paquete.

## 10. Versionamiento y cierre

El historial Git local se entrega mediante `historial-git.bundle`. El equipo debe publicarlo en un repositorio GitHub autorizado, proteger ramas, agregar cambios mediante pull requests y ejecutar CI. La plantilla `.github/workflows/ci.yml` aún no se ejecutó en GitHub. Mantenga dependencias y lockfile revisados; valide migraciones, restauración y seguridad en staging antes de promover a producción. Consulte la matriz CAR y los pendientes explícitos. No se deben declarar cumplidos los criterios de aceptación hasta obtener evidencias de la arquitectura objetivo.
