import datetime as dt
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Text, Date, DateTime, Numeric, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

Dinero = Numeric(15, 2)


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


class Trazable:
    """Fecha/hora y usuario de creación y modificación (requisito de trazabilidad)."""
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)
    created_by: Mapped[Optional[str]] = mapped_column(String(80))
    updated_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, onupdate=now)
    updated_by: Mapped[Optional[str]] = mapped_column(String(80))


class User(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    role: Mapped[str] = mapped_column(String(40))
    password_hash: Mapped[str] = mapped_column(String(300))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    token_version: Mapped[int] = mapped_column(Integer, default=0)


class AuditLog(Base):
    __tablename__ = "auditoria"
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[dt.datetime] = mapped_column(DateTime, default=now, index=True)
    usuario: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    accion: Mapped[str] = mapped_column(String(40))
    entidad: Mapped[Optional[str]] = mapped_column(String(40))
    entidad_id: Mapped[Optional[int]] = mapped_column(Integer)
    detalle: Mapped[Optional[str]] = mapped_column(Text)


# ---- Release 1.0: derechos de petición y correspondencia ----
class Peticion(Trazable, Base):
    __tablename__ = "peticiones"
    id: Mapped[int] = mapped_column(primary_key=True)
    fecha_ingreso: Mapped[dt.date] = mapped_column(Date)
    tipo_peticion: Mapped[str] = mapped_column(String(25), default="general")
    plazo_habil: Mapped[Optional[int]] = mapped_column(Integer)
    numero_radicado: Mapped[str] = mapped_column(String(50), unique=True)
    peticionario: Mapped[str] = mapped_column(String(200))
    solicitud: Mapped[str] = mapped_column(Text)
    asignado_a: Mapped[Optional[str]] = mapped_column(String(150))  # jefe de oficina / abogado
    fecha_vencimiento: Mapped[Optional[dt.date]] = mapped_column(Date)
    fecha_respuesta: Mapped[Optional[dt.date]] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(20), default="recibida")


# ---- Release 2.0: caja menor ----
class CajaMenor(Trazable, Base):
    __tablename__ = "cajas_menores"
    id: Mapped[int] = mapped_column(primary_key=True)
    vigencia: Mapped[int] = mapped_column(Integer, unique=True)
    ciclo: Mapped[int] = mapped_column(Integer, default=1)
    resolucion: Mapped[Optional[str]] = mapped_column(String(100))
    valor_fondo: Mapped[Decimal] = mapped_column(Dinero)
    sobrante_consignado: Mapped[Optional[Decimal]] = mapped_column(Dinero)
    estado: Mapped[str] = mapped_column(String(25), default="apertura")


class GastoCajaMenor(Trazable, Base):
    __tablename__ = "gastos_caja_menor"
    id: Mapped[int] = mapped_column(primary_key=True)
    caja_id: Mapped[int] = mapped_column(ForeignKey("cajas_menores.id"), index=True)
    ciclo: Mapped[int] = mapped_column(Integer, default=1)
    fecha: Mapped[dt.date] = mapped_column(Date)
    concepto: Mapped[str] = mapped_column(String(300))
    valor: Mapped[Decimal] = mapped_column(Dinero)
    numero_recibo: Mapped[Optional[str]] = mapped_column(String(50))
    autorizado_por: Mapped[Optional[str]] = mapped_column(String(150))
    estado_revision: Mapped[str] = mapped_column(String(15), default="pendiente")
    observacion_revision: Mapped[Optional[str]] = mapped_column(Text)


class ReintegroCaja(Trazable, Base):
    __tablename__ = "reintegros_caja_menor"
    id: Mapped[int] = mapped_column(primary_key=True)
    caja_id: Mapped[int] = mapped_column(ForeignKey("cajas_menores.id"), index=True)
    ciclo: Mapped[int] = mapped_column(Integer, default=1)
    fecha: Mapped[dt.date] = mapped_column(Date)
    valor: Mapped[Decimal] = mapped_column(Dinero)
    referencia: Mapped[str] = mapped_column(String(150))
    responsable: Mapped[str] = mapped_column(String(150))
    observaciones: Mapped[Optional[str]] = mapped_column(Text)


# ---- Release 3.0: gestión presupuestal y pagos ----
class SolicitudPresupuestal(Trazable, Base):
    __tablename__ = "solicitudes_presupuestales"
    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(30))
    numero: Mapped[Optional[str]] = mapped_column(String(50))
    descripcion: Mapped[str] = mapped_column(Text)
    valor: Mapped[Optional[Decimal]] = mapped_column(Dinero)
    fecha: Mapped[dt.date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(15), default="solicitada")
    responsable: Mapped[Optional[str]] = mapped_column(String(150))
    observaciones: Mapped[Optional[str]] = mapped_column(Text)
    referencia_siif: Mapped[Optional[str]] = mapped_column(String(100))  # el trámite sigue en SIIF


class Descuento(Trazable, Base):
    __tablename__ = "descuentos"
    id: Mapped[int] = mapped_column(primary_key=True)
    orden_id: Mapped[int] = mapped_column(ForeignKey("solicitudes_presupuestales.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(30))
    valor: Mapped[Decimal] = mapped_column(Dinero)


# ---- Release 4.0: convenios ----
class Convenio(Trazable, Base):
    __tablename__ = "convenios"
    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(50), unique=True)
    fecha_inicio: Mapped[dt.date] = mapped_column(Date)
    nit: Mapped[str] = mapped_column(String(30))
    entidad: Mapped[str] = mapped_column(String(200))
    valor_total: Mapped[Decimal] = mapped_column(Dinero)
    secretaria_responsable: Mapped[str] = mapped_column(String(150))
    estado: Mapped[str] = mapped_column(String(25), default="registrado")
    fecha_envio_contaduria: Mapped[Optional[dt.date]] = mapped_column(Date)
    fecha_liquidacion: Mapped[Optional[dt.date]] = mapped_column(Date)
    fecha_envio_liquidacion: Mapped[Optional[dt.date]] = mapped_column(Date)


class Documento(Base):
    __tablename__ = "documentos"
    id: Mapped[int] = mapped_column(primary_key=True)
    entidad: Mapped[str] = mapped_column(String(20), index=True)
    entidad_id: Mapped[int] = mapped_column(Integer, index=True)
    tipo: Mapped[str] = mapped_column(String(40))
    nombre_original: Mapped[str] = mapped_column(String(255))
    ruta: Mapped[str] = mapped_column(String(255))
    subido_por: Mapped[str] = mapped_column(String(80))
    subido_en: Mapped[dt.datetime] = mapped_column(DateTime, default=now)
