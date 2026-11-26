# Matriz de trazabilidad CAR-01 a CAR-20

Base: Documento de Visión y Alcance del 17/09/2026, sección 3.2 (págs. 7–8), releases (pág. 8) y criterios de aceptación (pág. 11). El manual institucional fundamenta los flujos de las secciones 2.4.1–2.4.4 (págs. 4–7 de Visión y Alcance). El proyecto académico Lucy Tejada es un alcance distinto y no se incorpora.

**Lectura de estados:** P = prueba ejecutada de la modalidad de compatibilidad FastAPI/SQLite; S = fuente de implementación Spring Boot disponible, sin build/ejecución integrales verificados; I = interfaz React demostrada con prueba Chromium de puente local (no HTTP real); R = revisión de código, no prueba individual ejecutada. La presencia de código fuente no equivale a aceptación de la arquitectura objetivo. No se declara un porcentaje de cumplimiento final.

| CAR | Release(s) | Compromiso exacto resumido | Implementación y evidencia | Verificación |
|---|---|---|---|---|
| 01 | 1.0 | Registrar/consultar derechos de petición y correspondencia: ingreso, radicado, peticionario, solicitud, respuesta | Peticiones, formulario/tabla/edición; `/peticiones`. `test_flujo`, `test_peticiones_consistencia_y_modalidades`, captura 02. | P, I, S |
| 02 | 1.0 | Registrar distribución a jefe de oficina y/o abogado | `asignado_a` y estado; requisito de responsable; formulario. Prueba de consistencia y UI. | P, I, S |
| 03 | 1.0 | Seguimiento de estado y vencimiento | `/peticiones/seguimiento`; vencimiento explícito o orientativo, calendario, panel y estados. | P, I, S |
| 04 | 2.0 | Registrar información y soportes de operaciones de caja menor | Cajas, gastos, recibos, documentos polimórficos y formulario; captura 03. Prueba gastos/documentos. | P, I, S |
| 05 | 2.0 | Registrar relación de gastos y revisión | Gastos, estado y observaciones, filtro, revisión por abogado. Prueba autorización/revisión. | P, I (registro/listado), S |
| 06 | 2.0 | Registrar apertura, revisión, firma, aprobación, reintegro y cierre | Flujo ocho etapas, roles, historial, reintegros, nuevos ciclos, saldo cero y bloqueo. `test_caja_reintegro_ciclos_y_cierre`. | P, S; UI de todas las etapas pendiente validación exhaustiva |
| 07 | 3.0 | Solicitudes de certificados de conveniencia y disponibilidad | Tipos separados y soporte, referencia SIIF, responsable; captura 04 y prueba presupuesto. | P, I (conveniencia), S |
| 08 | 3.0 | Registrar/consultar compromisos y órdenes de pago | Tipos compromiso y orden_pago, formulario y filtro. Prueba presupuesto. | P, S; R UI |
| 09 | 3.0 | Descuentos asociados a órdenes de pago | Cinco tipos, FK, total no superior al valor informado. Prueba presupuesto. | P, S; R UI |
| 10 | 3.0 | Informes de ejecución y seguimiento a informes de pago | Tipos informe_ejecucion e informe_pago diferenciados, estado, responsable y soporte. Prueba presupuesto. | P, S; R UI |
| 11 | 3.0 | Registrar/seguir modificaciones presupuestales | Tipo modificacion_presupuestal, referencia y estado. Prueba presupuesto. | P, S; R UI |
| 12 | 4.0 | Registrar convenio/contrato con número, inicio, NIT, entidad, valor, Secretaría | Formulario y consulta convenios. Prueba integrada y captura 05. | P, I, S |
| 13 | 4.0 | Asociar contrato, acta y soportes al convenio | Gestión documental por tipo, carga/descarga; verificación de contrato y acta. Prueba integrada y UI contrato. | P, I, S |
| 14 | 4.0 | Consultar estado y seguimiento de liquidación | Remisión del contrato, liquidación con acta, remisión de acta; fechas y bloqueo. Prueba integrada; UI remisión. | P, I (remisión), S |
| 15 | 3.0, 4.0 | Generar reportes de procesos registrados | Reportes de siete entidades, acceso por módulo. Pruebas de reportes. | P, I, S |
| 16 | 3.0, 4.0 | Exportar Excel (.xlsx) y PDF | OpenPyXL/ReportLab en demo; Apache POI/OpenPDF en Java; botones. Prueba ambos formatos; descarga UI Excel. | P, I (Excel), S |
| 17 | 1.0, 2.0; transversal | Autenticación segura por roles | JWT, PBKDF2, cuentas, permisos servidor, revocación. Pruebas login, rol, revocación. | P, I (login admin), S |
| 18 | 1.0, 2.0; transversal | Trazabilidad con usuario, fecha y hora | Metadatos y auditoría de cambios, login, documentos, exportación; pantalla auditoría. | P, S; R UI |
| 19 | 1.0; transversal | Diseño responsivo en computador, tablet y móvil | CSS responsivo, navegación móvil, tablas desplazables, captura 07/08 y prueba 1440/390 px. | I parcial: Chromium; tablets, Safari, Firefox, Edge pendientes |
| 20 | 4.0 | Panel de consulta y seguimiento administrativo | Resumen por módulo/estado, vencidas, gastos pendientes, valor convenios y acceso al detalle. Capturas 06/07. | P, I, S |

## Criterios de aceptación (sección 6, pág. 11)

| Criterio del documento | Evidencia incluida | Estado de cierre |
|---|---|---|
| Plataforma instalada y funcionando | Demo local; Dockerfile y Compose para objetivo | Pendiente instalación y validación Spring/PostgreSQL |
| Cuatro procesos con funciones correspondientes | CAR-01–14, interfaz, pruebas demo | Pendiente ejecución/aceptación objetivo |
| Consulta y seguimiento de estados, actividades y responsables | UI, API, reglas y auditoría | Pendiente aceptación por funcionarios |
| Documentos y soportes asociados | API, UI, pruebas de carga/descarga | Demo verificada; objetivo pendiente |
| Acceso solo a datos y funciones autorizadas | RBAC y pruebas negativas | Demo verificada; objetivo y matriz de roles institucional pendientes |
| Trazabilidad | Metadatos, eventos y pruebas | Demo verificada; objetivo pendiente |
| Reportes y Excel/PDF | Exportaciones verificadas en demo | Objetivo pendiente |
| Responsividad y staging independiente | CSS, captura móvil, dos configuraciones Compose | Prueba parcial Chromium; staging real y demás dispositivos pendientes |
| Git versionado | Historial local en bundle y commits | Git local incluido; publicación en GitHub pendiente |
| Manual técnico, de administración y de usuario | Markdown y PDF en docs | Elaborados; actualizar con evidencias de versión objetivo tras validación |
