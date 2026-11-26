# Pruebas y criterios de aceptación

## Evidencia ejecutada en esta elaboración

- `python -m pytest -q`: seis pruebas pasaron (test_flujo + cinco pruebas específicas). Resultado en `../evidencia/pruebas_api.txt`. Cobertura: calendario, datos de peticiones, roles y autenticación, caja menor con reintegros/ciclos, validación de descuentos, convenios/remisiones, documentos y exportaciones, revocación de sesión, panel y auditoría. No equivale a cobertura exhaustiva ni prueba de carga.
- `tests/ui_smoke.py`: prueba de interfaz React con Chromium a 1440×1000 y 390×844, usando puente local a FastAPI TestClient. Verificó ingreso, alta y edición de petición, alta de caja/gasto, alta de certificado, alta de convenio, carga de contrato, remisión, descarga Excel y menú móvil. Capturas reales en `../evidencia/`. No fue una prueba HTTP real ni con Spring Boot.
- Análisis sintáctico de 12 archivos Java con JDK 21, y tres comprobaciones ejecutadas del calendario Java aislado. No se ejecutó Maven, Testcontainers ni Vite por falta de dependencias/herramientas disponibles. La evidencia se limita a lo que indican los archivos de resultados.

## Pruebas que deben ejecutarse en staging objetivo

Utilice solo datos ficticios. Para cada caso registre: responsable, fecha, versión Git, navegador/dispositivo, entradas, resultado esperado, resultado obtenido, evidencia y estado (aprobado/fallido/no ejecutado). No marque aprobado por inspección de código.

| Caso | CAR | Procedimiento y resultado esperado | Estado objetivo |
|---|---|---|---|
| PA-01 | 01–03 | Secretaria ejecutiva registra petición, radicado único, asignación, cambio a respondida con fecha. Crear duplicado y fecha inválida debe fallar. Revisar vencimiento y responsable. | No ejecutado |
| PA-02 | 03 | Crear modalidades y plazo explícito, comprobar festivos de referencia y fechas; validar el término real con responsable. | No ejecutado |
| PA-03 | 04–06 | Crear caja con resolución, gastos y soportes; exceder fondo al crear/editar debe fallar. Auxiliar no puede aprobar revisión jurídica. | No ejecutado |
| PA-04 | 06 | Registrar revisión, firma, Control Interno, reintegro, nuevo ciclo y cierre. Intentar saltar etapa, cerrar sin saldo cero o modificar ciclo cerrado debe fallar. | No ejecutado |
| PA-05 | 07–11 | Crear y consultar cada uno de los siete tipos presupuestales; actualizar estado y responsable. Asociar descuentos a orden válida, rechazar otros tipos y monto excedido. | No ejecutado |
| PA-06 | 12–14 | Registrar convenio, adjuntar contrato, remitir, adjuntar acta, liquidar y registrar remisión de acta. Rechazar liquidación sin acta y remisión previa; comprobar fechas. | No ejecutado |
| PA-07 | 13, 04 | Asociar y descargar PDF, JPEG/PNG, DOCX y XLSX válidos; rechazar archivos mayores a 10 MB y extensión/contenido inválidos. Probar acceso de rol no autorizado. | No ejecutado |
| PA-08 | 15–16 | Exportar las siete entidades en Excel/PDF, abrir archivos, verificar textos largos, montos, caracteres y cantidad de registros. Probar entidad vacía. | No ejecutado |
| PA-09 | 17 | Probar los nueve roles, login correcto/incorrecto, acceso sin token, token alterado/expirado, cambio de contraseña, desactivación/reactivación, bloqueo por intentos. | No ejecutado |
| PA-10 | 18 | Confirmar usuario, fecha/hora y acción de creación, actualización, etapa, documentos, exportación e inicio de sesión. Probar que rol no autorizado no consulta auditoría. | No ejecutado |
| PA-11 | 19 | Probar Chrome, Firefox, Edge y Safari recientes. Windows, macOS, Linux, iOS y Android; tamaños escritorio, tablet y móvil. Revisar navegación, formularios, tablas, teclado, foco y descarga. | No ejecutado |
| PA-12 | 20 | Verificar que panel coincide con los registros de cada proceso y solo muestra módulos autorizados. Acceder al detalle y seguimiento de pendientes. | No ejecutado |
| PA-13 | 5.3/6 | Compilar Maven, Vite, ejecutar Flyway en PostgreSQL y `FlujoPostgresTest` (confirmar no omitido). | No ejecutado |
| PA-14 | 5.3/6 | Instalar staging y producción en redes/volúmenes independientes; crear un registro ficticio en staging y comprobar que no existe en producción. | No ejecutado |
| PA-15 | 5.3/6 | Comprobar certificado TLS válido, redirección HTTPS, acceso a dominios, DB no expuesta, persistencia tras reinicio y copia/restauración de documentos y DB. | No ejecutado |
| PA-16 | 6 | Publicar GitHub, verificar commits y CI. Presentar manuales y realizar revisión con usuarios responsables. | No ejecutado |

## Comandos de comprobación

En raíz: `python -m pytest -q`; para interfaz: instalar playwright, `python -m playwright install chromium`, configurar `PYTHONPATH=.` y ejecutar `python tests/ui_smoke.py`. En frontend: `npm install` y `npm run build`. En backend: `mvn clean test` (con Docker activo para PostgreSQL Testcontainers). Inspeccione el resumen Maven y `target/surefire-reports`; si el test integrado fue omitido, no cuenta como aprobado. Luego instale staging y ejecute PA-01 a PA-16 en la versión acordada.
