-- PostgreSQL schema for CAR-01 to CAR-20. Versioned by Flyway.
CREATE TABLE usuarios (
  id BIGSERIAL PRIMARY KEY, username VARCHAR(80) NOT NULL UNIQUE, full_name VARCHAR(150) NOT NULL,
  role VARCHAR(40) NOT NULL CHECK(role IN ('admin','secretario','secretaria_ejecutiva','auxiliar_administrativo','abogado_delegado','profesional_presupuesto','profesional_universitario','tecnico_administrativo','apoyo_financiero')),
  password_hash VARCHAR(300) NOT NULL, activo BOOLEAN NOT NULL DEFAULT TRUE, token_version INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE auditoria (
  id BIGSERIAL PRIMARY KEY, ts TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, usuario VARCHAR(80),
  accion VARCHAR(40) NOT NULL, entidad VARCHAR(40), entidad_id BIGINT, detalle TEXT
);
CREATE INDEX audit_ts_idx ON auditoria(ts DESC);
CREATE INDEX audit_login_idx ON auditoria(usuario,accion,ts);
CREATE INDEX audit_entidad_idx ON auditoria(entidad,entidad_id);
CREATE TABLE peticiones (
  id BIGSERIAL PRIMARY KEY, fecha_ingreso DATE NOT NULL, numero_radicado VARCHAR(50) NOT NULL UNIQUE,
  peticionario VARCHAR(200) NOT NULL, solicitud TEXT NOT NULL, asignado_a VARCHAR(150),
  tipo_peticion VARCHAR(25) NOT NULL DEFAULT 'general' CHECK(tipo_peticion IN ('general','informacion_documentos','consulta','otro')),
  plazo_habil INTEGER CHECK(plazo_habil BETWEEN 1 AND 365), fecha_vencimiento DATE NOT NULL,
  fecha_respuesta DATE, estado VARCHAR(20) NOT NULL DEFAULT 'recibida' CHECK(estado IN ('recibida','distribuida','en_tramite','respondida')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, created_by VARCHAR(80), updated_at TIMESTAMPTZ, updated_by VARCHAR(80),
  CHECK(fecha_vencimiento>=fecha_ingreso), CHECK(fecha_respuesta IS NULL OR fecha_respuesta>=fecha_ingreso),
  CHECK((estado='respondida')=(fecha_respuesta IS NOT NULL))
);
CREATE INDEX peticiones_seguimiento_idx ON peticiones(estado,fecha_vencimiento);
CREATE TABLE cajas_menores (
  id BIGSERIAL PRIMARY KEY, vigencia INTEGER NOT NULL UNIQUE CHECK(vigencia BETWEEN 2000 AND 2100),
  resolucion VARCHAR(100), valor_fondo NUMERIC(15,2) NOT NULL CHECK(valor_fondo>0),
  sobrante_consignado NUMERIC(15,2) CHECK(sobrante_consignado>=0), ciclo INTEGER NOT NULL DEFAULT 1 CHECK(ciclo>0),
  estado VARCHAR(25) NOT NULL DEFAULT 'apertura' CHECK(estado IN ('apertura','compras','relacion_gastos','revision_juridica','firma','control_interno','reintegro','cierre')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, created_by VARCHAR(80), updated_at TIMESTAMPTZ, updated_by VARCHAR(80)
);
CREATE TABLE gastos_caja_menor (
  id BIGSERIAL PRIMARY KEY, caja_id BIGINT NOT NULL REFERENCES cajas_menores(id), ciclo INTEGER NOT NULL DEFAULT 1 CHECK(ciclo>0),
  fecha DATE NOT NULL, concepto VARCHAR(300) NOT NULL, valor NUMERIC(15,2) NOT NULL CHECK(valor>0),
  numero_recibo VARCHAR(50), autorizado_por VARCHAR(150), estado_revision VARCHAR(15) NOT NULL DEFAULT 'pendiente' CHECK(estado_revision IN ('pendiente','aprobado','rechazado')),
  observacion_revision TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, created_by VARCHAR(80), updated_at TIMESTAMPTZ, updated_by VARCHAR(80)
);
CREATE INDEX gastos_caja_idx ON gastos_caja_menor(caja_id,ciclo);
CREATE TABLE reintegros_caja_menor (
  id BIGSERIAL PRIMARY KEY, caja_id BIGINT NOT NULL REFERENCES cajas_menores(id), ciclo INTEGER NOT NULL DEFAULT 1 CHECK(ciclo>0),
  fecha DATE NOT NULL, valor NUMERIC(15,2) NOT NULL CHECK(valor>0), referencia VARCHAR(150) NOT NULL, responsable VARCHAR(150) NOT NULL,
  observaciones TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, created_by VARCHAR(80), updated_at TIMESTAMPTZ, updated_by VARCHAR(80)
);
CREATE INDEX reintegros_caja_idx ON reintegros_caja_menor(caja_id);
CREATE TABLE solicitudes_presupuestales (
  id BIGSERIAL PRIMARY KEY, tipo VARCHAR(30) NOT NULL CHECK(tipo IN ('certificado_conveniencia','certificado_disponibilidad','compromiso','orden_pago','informe_ejecucion','informe_pago','modificacion_presupuestal')),
  numero VARCHAR(50), descripcion TEXT NOT NULL, valor NUMERIC(15,2) CHECK(valor>=0), fecha DATE NOT NULL,
  estado VARCHAR(15) NOT NULL DEFAULT 'solicitada' CHECK(estado IN ('solicitada','aprobada','rechazada','tramitada')),
  referencia_siif VARCHAR(100), responsable VARCHAR(150), observaciones TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, created_by VARCHAR(80), updated_at TIMESTAMPTZ, updated_by VARCHAR(80)
);
CREATE INDEX solicitudes_tipo_idx ON solicitudes_presupuestales(tipo,estado);
CREATE TABLE descuentos (
  id BIGSERIAL PRIMARY KEY, orden_id BIGINT NOT NULL REFERENCES solicitudes_presupuestales(id),
  tipo VARCHAR(30) NOT NULL CHECK(tipo IN ('retencion_fuente','sobretasa_deporte','estampilla_procultura','industria_comercio','estampilla_prodesarrollo')),
  valor NUMERIC(15,2) NOT NULL CHECK(valor>0), created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, created_by VARCHAR(80), updated_at TIMESTAMPTZ, updated_by VARCHAR(80)
);
CREATE INDEX descuentos_orden_idx ON descuentos(orden_id);
CREATE TABLE convenios (
  id BIGSERIAL PRIMARY KEY, numero VARCHAR(50) NOT NULL UNIQUE, fecha_inicio DATE NOT NULL, nit VARCHAR(30) NOT NULL,
  entidad VARCHAR(200) NOT NULL, valor_total NUMERIC(15,2) NOT NULL CHECK(valor_total>0), secretaria_responsable VARCHAR(150) NOT NULL,
  estado VARCHAR(25) NOT NULL DEFAULT 'registrado' CHECK(estado IN ('registrado','enviado_contaduria','liquidado')),
  fecha_envio_contaduria DATE, fecha_liquidacion DATE, fecha_envio_liquidacion DATE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, created_by VARCHAR(80), updated_at TIMESTAMPTZ, updated_by VARCHAR(80),
  CHECK(fecha_envio_contaduria IS NULL OR fecha_envio_contaduria>=fecha_inicio),
  CHECK(fecha_liquidacion IS NULL OR (fecha_envio_contaduria IS NOT NULL AND fecha_liquidacion>=fecha_envio_contaduria)),
  CHECK(fecha_envio_liquidacion IS NULL OR (fecha_liquidacion IS NOT NULL AND fecha_envio_liquidacion>=fecha_liquidacion))
);
CREATE INDEX convenios_estado_idx ON convenios(estado);
CREATE TABLE documentos (
  id BIGSERIAL PRIMARY KEY, entidad VARCHAR(20) NOT NULL CHECK(entidad IN ('peticion','caja_menor','gasto','reintegro','presupuesto','convenio')),
  entidad_id BIGINT NOT NULL, tipo VARCHAR(40) NOT NULL, nombre_original VARCHAR(255) NOT NULL, ruta VARCHAR(255) NOT NULL UNIQUE,
  subido_por VARCHAR(80) NOT NULL, subido_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX documentos_entidad_idx ON documentos(entidad,entidad_id);
