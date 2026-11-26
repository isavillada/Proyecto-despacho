import datetime as dt
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class S(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True, extra="forbid")


class PeticionIn(S):
    fecha_ingreso: dt.date
    tipo_peticion: Literal["general", "informacion_documentos", "consulta", "otro"] = "general"
    plazo_habil: Optional[int] = Field(default=None, ge=1, le=365)
    numero_radicado: str = Field(min_length=1, max_length=50)
    peticionario: str = Field(min_length=1, max_length=200)
    solicitud: str = Field(min_length=1, max_length=20000)
    asignado_a: Optional[str] = Field(default=None, max_length=150)
    fecha_vencimiento: Optional[dt.date] = None  # si se omite: 15 días hábiles
    fecha_respuesta: Optional[dt.date] = None
    estado: Literal["recibida", "distribuida", "en_tramite", "respondida"] = "recibida"

    @model_validator(mode="after")
    def coherencia(self):
        if self.estado in ("distribuida", "en_tramite") and not self.asignado_a:
            raise ValueError("Indique el responsable de la petición")
        if self.estado == "respondida" and not self.fecha_respuesta:
            raise ValueError("Indique la fecha de respuesta")
        if self.fecha_respuesta and self.estado != "respondida":
            raise ValueError("La fecha de respuesta requiere estado respondida")
        for fecha in (self.fecha_respuesta, self.fecha_vencimiento):
            if fecha and fecha < self.fecha_ingreso:
                raise ValueError("Las fechas no pueden ser anteriores al ingreso")
        return self


class CajaIn(S):
    vigencia: int = Field(ge=2000, le=2100)
    resolucion: Optional[str] = Field(default=None,max_length=100)
    valor_fondo: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    sobrante_consignado: Optional[Decimal] = Field(default=None, ge=0, max_digits=15, decimal_places=2)


class GastoIn(S):
    caja_id: int
    fecha: dt.date
    concepto: str = Field(min_length=1, max_length=300)
    valor: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    numero_recibo: Optional[str] = Field(default=None,max_length=50)
    autorizado_por: Optional[str] = Field(default=None,max_length=150)
    estado_revision: Literal["pendiente", "aprobado", "rechazado"] = "pendiente"
    observacion_revision: Optional[str] = Field(default=None,max_length=20000)


class ReintegroIn(S):
    caja_id: int
    fecha: dt.date
    valor: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    referencia: str = Field(min_length=1, max_length=150)
    responsable: str = Field(min_length=1, max_length=150)
    observaciones: Optional[str] = Field(default=None,max_length=20000)


class SolicitudIn(S):
    tipo: Literal["certificado_disponibilidad", "compromiso", "orden_pago",
                  "informe_ejecucion", "modificacion_presupuestal", "certificado_conveniencia", "informe_pago"]
    numero: Optional[str] = Field(default=None,max_length=50)
    descripcion: str = Field(min_length=1,max_length=20000)
    valor: Optional[Decimal] = Field(default=None, ge=0, max_digits=15, decimal_places=2)
    fecha: dt.date
    estado: Literal["solicitada", "aprobada", "rechazada", "tramitada"] = "solicitada"
    responsable: Optional[str] = Field(default=None, max_length=150)
    observaciones: Optional[str] = Field(default=None,max_length=20000)
    referencia_siif: Optional[str] = Field(default=None, max_length=100)


class DescuentoIn(S):
    orden_id: int
    tipo: Literal["retencion_fuente", "sobretasa_deporte", "estampilla_procultura",
                  "industria_comercio", "estampilla_prodesarrollo"]
    valor: Decimal = Field(gt=0, max_digits=15, decimal_places=2)


class ConvenioIn(S):
    numero: str = Field(min_length=1, max_length=50)
    fecha_inicio: dt.date
    nit: str = Field(min_length=5, max_length=30)
    entidad: str = Field(min_length=1, max_length=200)
    valor_total: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    secretaria_responsable: str = Field(default="Secretaría de Cultura",min_length=1,max_length=150)


class UsuarioIn(S):
    username: str = Field(min_length=3, max_length=80)
    full_name: str = Field(min_length=1,max_length=150)
    role: str
    password: str


class UsuarioUpdate(S):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    role: Optional[str] = None
    activo: Optional[bool] = None
    password: Optional[str] = None


class UsuarioOut(S):
    id: int
    username: str
    full_name: str
    role: str
    activo: bool


class DocumentoOut(S):
    id: int
    entidad: str
    entidad_id: int
    tipo: str
    nombre_original: str
    subido_por: str
    subido_en: dt.datetime
