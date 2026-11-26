# Decisiones de implementación y pendientes de cierre

## Alcance conservado

Visión y Alcance (páginas 8–9 y 11–12) es el compromiso de entrega. Los procedimientos de la Escuela de Formación Cultural, matrículas, estudiantes, docentes, asistencia y evaluaciones del documento Proyecto de Plataforma de Gestión – Centro Cultural Lucy Tejada no son parte de los cuatro procesos del Despacho. Tampoco se añaden pagos reales, firmas digitales, reemplazo de sistemas externos, integración directa con SAIA/SIIF ni automatización de aprobaciones. No se cambió el documento de Visión y Alcance para ocultar una diferencia tecnológica.

## Decisiones de diseño (por confirmar con responsables)

- Dos modalidades explícitas: arquitectura objetivo React/Spring Boot/PostgreSQL y compatibilidad local React/FastAPI/SQLite. La segunda permite demostrar y conservar el avance probado; no sustituye la arquitectura de entrega.
- Se conserva una caja por vigencia, de acuerdo con el modelo original. Los ciclos permiten registrar reintegros y continuar compras. El cierre exige saldo cero y las actuaciones se registran con fecha, responsable y referencia. Las restricciones por roles/etapas se derivan del manual; confirmar con los responsables la distribución exacta.
- El vencimiento de peticiones admite fecha explícita y plazo configurable; por defecto utiliza modalidades generales de referencia 15, 10 y 30 días hábiles, con festivos nacionales habituales. Estos cálculos no fueron auditados jurídicamente ni cubren todos los términos especiales, suspensiones o calendarios locales. El funcionario valida el plazo aplicable; no se pretende sustituir normativa ni procedimiento.
- Se exigen contrato y acta en convenios para registrar remisión y liquidación, respectivamente; la aplicación no autentica jurídicamente el contenido ni prueba que se haya enviado externamente.
- Los reportes exportan toda la entidad autorizada, no solo la página filtrada. La búsqueda de texto se aplica a la página consultada. La interfaz incluye paginación y filtros por estado/tipo en módulos relevantes.
- No se implementa borrado físico de registros administrativos ni edición de reintegros ya registrados. Un error en un reintegro requiere procedimiento correctivo acordado con la entidad; debe definirse una actuación de reversión auditada antes del uso real.
- Los documentos están en un volumen privado con relación polimórfica, validación de tipo/tamaño/firma básica; no se certifica integridad jurídica ni ausencia de malware. Los permisos son por módulo y acción crítica, no por propietario individual.
- Git local creado a partir del ZIP; no se supone que el equipo no tenga un repositorio previo. Si ya existe, integrar los cambios en su historial en lugar de sustituirlo.

## Bloqueos y verificación pendiente

1. No había Maven ni dependencias Spring Boot disponibles ni Docker/PostgreSQL en el entorno de elaboración. Se escribió la implementación Java y las migraciones, se comprobó sintaxis con JDK 21 y se ejecutó la prueba aislada de calendario. No se compiló ni ejecutó el servicio Java completo. Debe ejecutarse Maven con acceso a dependencias y el test PostgreSQL antes de declarar que el stack acordado funciona.
2. No había paquetes React 18/Vite disponibles offline; se probó el código de interfaz compartido con React 16 de vista previa local. El build React 18 real, lockfile, auditoría de dependencias y compatibilidad con el backend Java deben verificarse al instalar. La vista previa offline no se incluye en el Dockerfile de producción.
3. Chromium bloqueó navegación HTTP directa a localhost en el entorno. La prueba de interfaz se hizo con un puente local hacia FastAPI TestClient. Se deben repetir pruebas reales por HTTP/HTTPS y en otros navegadores y tamaños, incluyendo Safari/iOS y Android.
4. No se cuenta con credenciales, dominios, infraestructura ni autorización de despliegue. Configuraciones de staging y producción y proxy HTTPS listas como plantillas; falta instalación real, certificado válido y verificación de aislamiento.
5. El historial Git local se entrega como bundle. Falta repositorio GitHub del equipo, publicación y CI ejecutada. No se publicaron datos ni credenciales externamente.
6. Faltan aceptación con funcionarios, pruebas de seguridad/operación, política de privacidad y retención institucional, copia/restauración real y revisión de dependencias. No se exige añadir el alcance académico Lucy Tejada para cerrar los CAR del Despacho.

## Orden de cierre recomendado

Compilar el backend Java y el frontend React 18; corregir cualquier error de dependencias/compilación; ejecutar pruebas con PostgreSQL y confirmar que no se omitan; levantar staging; realizar la matriz de pruebas de aceptación de los cuatro releases; confirmar roles y reglas con responsables; validar navegadores y dispositivos; publicar GitHub; configurar hosting y SSL/TLS; aprobar y desplegar producción; actualizar manuales con capturas y URLs del entorno real. Hasta entonces, presentar el paquete como entrega candidata, no como software institucional certificado.
