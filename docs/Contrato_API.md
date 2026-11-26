# Contrato API REST

Base de la arquitectura objetivo: `/api`. En la modalidad de compatibilidad se omite ese prefijo. JSON en altas y modificaciones salvo login (application/x-www-form-urlencoded) y documentos (multipart/form-data). Todas las rutas requieren `Authorization: Bearer TOKEN` excepto inicio de sesión y salud. No existe DELETE de registros administrativos.

| Método y ruta (sin prefijo) | Función |
|---|---|
| GET /salud | Estado del servicio; Java consulta la base |
| POST /auth/login | username y password; devuelve access_token, token_type, role |
| GET /auth/yo | Identidad y rol de la sesión |
| GET /auth/permisos | Permisos de lectura/escritura por módulo |
| GET, POST /auth/usuarios | Listar/crear cuentas (admin) |
| PATCH /auth/usuarios/{id} | Editar nombre, rol, activo, contraseña opcional |
| POST /auth/cambiar-clave | actual y nueva; revoca tokens |
| GET, POST /peticiones | Consultar/crear peticiones |
| GET, PATCH /peticiones/{id} | Consultar/actualizar petición |
| GET /peticiones/seguimiento | Peticiones no respondidas, vencimiento y días calendario restantes |
| GET, POST /cajas-menores | Consultar/abrir caja |
| GET, PATCH /cajas-menores/{id} | Consultar/actualizar caja |
| GET /cajas-menores/{id}/resumen | Fondo, gastos, reintegros, sobrante, saldo |
| GET /cajas-menores/{id}/historial | Actividades de caja |
| POST /cajas-menores/{id}/avanzar | Registrar siguiente etapa |
| POST /cajas-menores/{id}/nuevo-ciclo | Abrir ciclo desde reintegro |
| GET, POST /gastos-caja-menor | Consultar/registrar gastos |
| GET, PATCH /gastos-caja-menor/{id} | Detalle, corrección/revisión según rol y etapa |
| GET, POST /reintegros-caja-menor | Consultar/registrar reintegros |
| GET /reintegros-caja-menor/{id} | Consultar reintegro; modificación no permitida |
| GET, POST /presupuesto/solicitudes | Consultar/registrar solicitudes y seguimiento |
| GET, PATCH /presupuesto/solicitudes/{id} | Consultar/actualizar solicitud |
| GET, POST /presupuesto/descuentos | Consultar/registrar descuentos |
| GET, PATCH /presupuesto/descuentos/{id} | Consultar/actualizar descuento |
| GET, POST /convenios | Consultar/registrar convenio |
| GET, PATCH /convenios/{id} | Detalle/actualización antes de liquidar |
| POST /convenios/{id}/enviar-contaduria | Registrar remisión de contrato |
| POST /convenios/{id}/liquidar | Registrar liquidación con acta y remisión previa |
| POST /convenios/{id}/enviar-liquidacion | Registrar remisión del acta |
| GET /documentos?entidad=...&entidad_id=... | Listar soportes asociados |
| POST /documentos?entidad=...&entidad_id=...&tipo=... | Cargar campo multipart archivo |
| GET /documentos/{id}/descargar | Descargar soporte autorizado |
| GET /reportes/{entidad}?formato=xlsx o pdf | Exportar entidad completa autorizada |
| GET /panel/resumen | Conteos y seguimiento por permiso |
| GET /auditoria?usuario=...&entidad=...&limit=200 | Consultar eventos (admin/secretario) |

Listados generales: `skip` (desplazamiento >=0), `limit` (1–500, por defecto 100). Filtros: peticiones (estado, asignado_a), cajas (estado, vigencia), gastos (caja_id, estado_revision), reintegros (caja_id), solicitudes (tipo, estado), descuentos (orden_id, tipo), convenios (estado, nit). Entidades documentales: peticion, caja_menor, gasto, reintegro, presupuesto, convenio. Entidades de reportes: peticiones, cajas-menores, gastos-caja-menor, reintegros-caja-menor, solicitudes-presupuestales, descuentos, convenios.

Ejemplo de petición:

```json
{"fecha_ingreso":"2026-11-23","numero_radicado":"DEMO-001","peticionario":"Persona de prueba","solicitud":"Información sobre actividades culturales","tipo_peticion":"general","estado":"recibida"}
```

Ejemplo de actuación de caja o convenio (fecha del trámite efectivamente realizado, no de envío automático):

```json
{"fecha":"2026-11-24","responsable":"Funcionario de prueba","referencia":"Soporte externo DEMO"}
```

Errores usuales: 401 autenticación; 403 rol; 404 no encontrado; 409 estado/duplicado/restricción; 413 tamaño; 415 formato; 422 validación; 429 intentos de acceso; 405 modificación de reintegro. Los mensajes controlados se devuelven como `detail`. El frontend maneja los mensajes y revocación de sesión. El contrato se implementó en las dos bases de código; su paridad debe probarse con la versión Java en staging.
