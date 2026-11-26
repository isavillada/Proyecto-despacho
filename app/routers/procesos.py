import datetime as dt
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from pydantic import BaseModel, Field
from ..calendario import dias_habiles, hoy as fecha_local
from ..models import AuditLog, ReintegroCaja
from ..schemas import ReintegroIn
from sqlalchemy.orm import Session
from ..crud import audit, crud_router
from ..db import get_db
from ..models import (CajaMenor, Convenio, Descuento, Documento, GastoCajaMenor,
                      Peticion, SolicitudPresupuestal, User)
from ..schemas import (CajaIn, ConvenioIn, DescuentoIn, GastoIn, PeticionIn, SolicitudIn)
from ..security import get_current_user, has_access, require

# ============ Release 1.0: Derechos de petición ============
PLAZOS = {"general": 15, "informacion_documentos": 10, "consulta": 30}


def peticion_antes_crear(db, data):
    if not data.get("fecha_vencimiento"):
        n = data.get("plazo_habil") or PLAZOS.get(data["tipo_peticion"])
        if n is None:
            raise HTTPException(422, "Para otro tipo de petición indique plazo o vencimiento")
        data["fecha_vencimiento"] = dias_habiles(data["fecha_ingreso"], n)


def peticion_preparar(obj,data):
    if "fecha_vencimiento" not in data and any(k in data and data[k] != getattr(obj,k) for k in ("fecha_ingreso","tipo_peticion","plazo_habil")):
        data["fecha_vencimiento"]=None


def peticion_antes_actualizar(db, obj, data, user):
    if "fecha_vencimiento" in data and data["fecha_vencimiento"] is None:
        nuevo = {k: getattr(obj,k) for k in PeticionIn.model_fields}
        nuevo.update(data)
        peticion_antes_crear(db,nuevo)
        data["fecha_vencimiento"] = nuevo["fecha_vencimiento"]


peticiones_seg = APIRouter(prefix="/peticiones", tags=["1.0 Derechos de petición"])


@peticiones_seg.get("/seguimiento")
def seguimiento(db: Session = Depends(get_db), user: User = Depends(require("peticiones"))):
    """Peticiones pendientes con días restantes (seguimiento semanal)."""
    hoy = fecha_local()
    pend = db.scalars(select(Peticion).where(Peticion.estado != "respondida")
                      .order_by(Peticion.fecha_vencimiento)).all()
    return [{"id": p.id, "radicado": p.numero_radicado, "peticionario": p.peticionario,
             "asignado_a": p.asignado_a, "estado": p.estado, "vence": p.fecha_vencimiento,
             "dias_restantes": (p.fecha_vencimiento - hoy).days if p.fecha_vencimiento else None,
             "vencida": bool(p.fecha_vencimiento and p.fecha_vencimiento < hoy)} for p in pend]


peticiones = crud_router("/peticiones", "1.0 Derechos de petición", "peticiones", Peticion, PeticionIn,
                         filtros=("estado", "asignado_a"), antes_crear=peticion_antes_crear, antes_actualizar=peticion_antes_actualizar, preparar_actualizacion=peticion_preparar)

# ============ Release 2.0: Caja menor ============
ETAPAS = ["apertura", "compras", "relacion_gastos", "revision_juridica",
          "firma", "control_interno", "reintegro", "cierre"]

cajas_flujo = APIRouter(prefix="/cajas-menores", tags=["2.0 Caja menor"])


class EventoIn(BaseModel):
    fecha: dt.date = Field(default_factory=fecha_local)
    responsable: str | None = Field(default=None, max_length=150)
    referencia: str | None = Field(default=None, max_length=300)


def rol(user, *roles):
    if user.role not in ("admin", *roles):
        raise HTTPException(403, "Su rol no puede registrar esta actividad")


def caja_lock(db, caja_id):
    c = db.get(CajaMenor, caja_id, with_for_update=True)
    if not c:
        raise HTTPException(404, "La caja menor no existe")
    return c


def _gastado(db, caja_id, excluir=None):
    q=select(func.coalesce(func.sum(GastoCajaMenor.valor), 0)).where(GastoCajaMenor.caja_id == caja_id)
    if excluir is not None: q=q.where(GastoCajaMenor.id != excluir)
    return Decimal(db.scalar(q))


def _reintegrado(db, caja_id):
    return Decimal(db.scalar(select(func.coalesce(func.sum(ReintegroCaja.valor), 0)).where(ReintegroCaja.caja_id == caja_id)))


def _saldo(db, caja):
    return caja.valor_fondo + _reintegrado(db, caja.id) - _gastado(db,caja.id)


def caja_editar(db, obj, data, user):
    if obj.estado == "cierre": raise HTTPException(409,"La caja menor está cerrada")
    if "vigencia" in data and data["vigencia"] != obj.vigencia: raise HTTPException(422,"No se puede cambiar la vigencia")
    if "valor_fondo" in data and data["valor_fondo"] != obj.valor_fondo:
        if obj.estado != "apertura" or _gastado(db,obj.id): raise HTTPException(409,"El fondo solo se modifica antes de registrar gastos")
    if "sobrante_consignado" in data and data["sobrante_consignado"] != obj.sobrante_consignado:
        rol(user,"auxiliar_administrativo","apoyo_financiero")
        if obj.estado != "reintegro": raise HTTPException(409,"Registre la consignación en la etapa de reintegro/cierre")


def caja_crear(user,data):
    rol(user,"auxiliar_administrativo","abogado_delegado","secretario")
    if data.get("sobrante_consignado") is not None: raise HTTPException(422,"El sobrante se registra al cierre")


cajas_extra = crud_router("/cajas-menores", "2.0 Caja menor", "caja_menor", CajaMenor, CajaIn,
                          filtros=("estado", "vigencia"), extra_out={"estado": (str, ...), "ciclo": (int, ...)},
                          antes_actualizar=caja_editar, autorizar_crear=caja_crear)


def gasto_antes_crear(db, data):
    c=caja_lock(db,data["caja_id"])
    if c.estado not in ("apertura","compras","relacion_gastos"): raise HTTPException(409,"No se pueden crear gastos en esta etapa")
    if data["fecha"].year != c.vigencia: raise HTTPException(422,"La fecha debe corresponder a la vigencia")
    if data["valor"] > _saldo(db,c): raise HTTPException(422,"El gasto excede el saldo de caja menor")
    data["ciclo"] = c.ciclo


def gasto_autorizar(user,data):
    rol(user,"auxiliar_administrativo","secretario")
    if data.get("estado_revision") != "pendiente": raise HTTPException(422,"Un gasto nuevo debe quedar pendiente de revisión")


def gasto_editar(db,obj,data,user):
    c=caja_lock(db,obj.caja_id)
    if c.ciclo != obj.ciclo: raise HTTPException(409,"El gasto pertenece a un ciclo anterior")
    if c.estado not in ("apertura","compras","relacion_gastos","revision_juridica"): raise HTTPException(409,"No se pueden modificar gastos en esta etapa")
    if "caja_id" in data and data["caja_id"] != obj.caja_id: raise HTTPException(422,"No se puede trasladar un gasto a otra caja")
    revision={"estado_revision","observacion_revision"}
    cambios={k for k,v in data.items() if v != getattr(obj,k)}
    if cambios & revision:
        rol(user,"abogado_delegado")
        if c.estado != "revision_juridica": raise HTTPException(409,"La revisión se registra en su etapa")
    if cambios - revision:
        rol(user,"auxiliar_administrativo","secretario")
        data["estado_revision"]="pendiente"
        data["observacion_revision"]=None
    if data.get("fecha",obj.fecha).year != c.vigencia: raise HTTPException(422,"La fecha debe corresponder a la vigencia")
    if _gastado(db,c.id,obj.id)+data.get("valor",obj.valor)>c.valor_fondo+_reintegrado(db,c.id):
        raise HTTPException(422,"El gasto excede el saldo de caja menor")


gastos = crud_router("/gastos-caja-menor", "2.0 Caja menor", "caja_menor", GastoCajaMenor, GastoIn,
                     filtros=("caja_id", "estado_revision"), antes_crear=gasto_antes_crear,
                     antes_actualizar=gasto_editar, autorizar_crear=gasto_autorizar, extra_out={"ciclo": (int, ...)})


def reintegro_crear(db,data):
    c=caja_lock(db,data["caja_id"])
    if c.estado != "reintegro": raise HTTPException(409,"Registre el reintegro después de Control Interno")
    if c.sobrante_consignado is not None: raise HTTPException(409,"Ya se registró el sobrante de cierre")
    if data["fecha"].year != c.vigencia: raise HTTPException(422,"La fecha debe corresponder a la vigencia")
    if data["valor"] > _gastado(db,c.id)-_reintegrado(db,c.id): raise HTTPException(422,"El reintegro excede el gasto neto")
    data["ciclo"] = c.ciclo


def reintegro_autorizar(user,data): rol(user,"auxiliar_administrativo","apoyo_financiero")


reintegros = crud_router("/reintegros-caja-menor", "2.0 Caja menor", "caja_menor", ReintegroCaja, ReintegroIn,
                       filtros=("caja_id",), antes_crear=reintegro_crear, autorizar_crear=reintegro_autorizar,
                       permitir_actualizar=False, extra_out={"ciclo": (int, ...)})


@cajas_flujo.get("/{caja_id}/resumen")
def caja_resumen(caja_id: int, db: Session = Depends(get_db), user: User = Depends(require("caja_menor"))):
    c=db.get(CajaMenor,caja_id)
    if not c: raise HTTPException(404,"No encontrada")
    g, r = _gastado(db,c.id), _reintegrado(db,c.id)
    return {"id":c.id,"vigencia":c.vigencia,"estado":c.estado,"ciclo":c.ciclo,"fondo":c.valor_fondo,"gastado":g,
            "reintegrado":r,"sobrante_consignado":c.sobrante_consignado,
            "saldo":c.valor_fondo+r-g-(c.sobrante_consignado or 0)}


def evento_detalle(anterior,sig,evento,user):
    return f"{anterior} -> {sig} | fecha informada: {evento.fecha} | responsable: {evento.responsable or user.full_name} | referencia: {evento.referencia or 'Sin referencia'}"


@cajas_flujo.get("/{caja_id}/historial")
def caja_historial(caja_id: int, db: Session = Depends(get_db), user: User = Depends(require("caja_menor"))):
    if not db.get(CajaMenor,caja_id): raise HTTPException(404,"No encontrada")
    q=select(AuditLog).where(AuditLog.entidad=="cajas_menores",AuditLog.entidad_id==caja_id).order_by(AuditLog.id.desc())
    return [{"ts":a.ts,"usuario":a.usuario,"accion":a.accion,"detalle":a.detalle} for a in db.scalars(q)]


@cajas_flujo.post("/{caja_id}/avanzar")
def caja_avanzar(caja_id: int, evento: EventoIn | None = None, db: Session = Depends(get_db), user: User = Depends(require("caja_menor", True))):
    c=caja_lock(db,caja_id)
    i=ETAPAS.index(c.estado)
    if i==len(ETAPAS)-1: raise HTTPException(409,"La caja menor ya está cerrada")
    sig=ETAPAS[i+1]
    roles={"compras":("auxiliar_administrativo","abogado_delegado","secretario"),
           "relacion_gastos":("auxiliar_administrativo",),"revision_juridica":("auxiliar_administrativo","abogado_delegado"),
           "firma":("abogado_delegado",),"control_interno":("secretario",),
           "reintegro":("auxiliar_administrativo","apoyo_financiero"),"cierre":("auxiliar_administrativo","apoyo_financiero")}
    rol(user,*roles[sig])
    evento=evento or EventoIn()
    if evento.fecha.year != c.vigencia: raise HTTPException(422,"La fecha informada debe corresponder a la vigencia")
    if sig=="compras" and not c.resolucion: raise HTTPException(409,"Registre la resolución de apertura")
    if sig=="firma":
        n=db.scalar(select(func.count()).select_from(GastoCajaMenor).where(GastoCajaMenor.caja_id==c.id,GastoCajaMenor.estado_revision!="aprobado"))
        if n: raise HTTPException(409,f"Hay {n} gasto(s) sin revisión aprobada")
    if sig=="cierre" and (c.sobrante_consignado is None or c.sobrante_consignado != _saldo(db,c)):
        raise HTTPException(409,"El sobrante consignado debe dejar el fondo en $0,00")
    anterior,c.estado,c.updated_by=c.estado,sig,user.username
    audit(db,user.username,"CAMBIO_ESTADO","cajas_menores",c.id,evento_detalle(anterior,sig,evento,user))
    db.commit()
    return {"id":c.id,"estado":c.estado}


@cajas_flujo.post("/{caja_id}/nuevo-ciclo")
def nuevo_ciclo(caja_id:int, evento: EventoIn | None=None, db:Session=Depends(get_db),user:User=Depends(require("caja_menor",True))):
    rol(user,"auxiliar_administrativo","apoyo_financiero")
    c=caja_lock(db,caja_id)
    evento=evento or EventoIn()
    if evento.fecha.year != c.vigencia: raise HTTPException(422,"La fecha informada debe corresponder a la vigencia")
    if c.estado != "reintegro" or c.sobrante_consignado is not None: raise HTTPException(409,"Solo se abre un ciclo desde reintegro, antes de consignar el sobrante")
    c.estado,c.updated_by="compras",user.username
    c.ciclo += 1
    audit(db,user.username,"CAMBIO_ESTADO","cajas_menores",c.id,evento_detalle("reintegro","compras",evento,user))
    db.commit()
    return {"id":c.id,"estado":c.estado}


# ============ Release 3.0: Presupuesto y pagos ============
def validar_descuento(db,data,excluir=None):
    o=db.get(SolicitudPresupuestal,data["orden_id"],with_for_update=True)
    if not o or o.tipo!="orden_pago": raise HTTPException(422,"Seleccione una orden de pago válida")
    q=select(func.coalesce(func.sum(Descuento.valor),0)).where(Descuento.orden_id==o.id)
    if excluir is not None: q=q.where(Descuento.id!=excluir)
    if o.valor is not None and Decimal(db.scalar(q))+data["valor"]>o.valor:
        raise HTTPException(422,"Los descuentos superan el valor de la orden")


def descuento_antes_crear(db,data): validar_descuento(db,data)


def descuento_editar(db,obj,data,user):
    validar_descuento(db,{"orden_id":data.get("orden_id",obj.orden_id),"valor":data.get("valor",obj.valor)},obj.id)


def solicitud_editar(db,obj,data,user):
    total=db.scalar(select(func.coalesce(func.sum(Descuento.valor),0)).where(Descuento.orden_id==obj.id))
    if total and data.get("tipo",obj.tipo)!="orden_pago": raise HTTPException(409,"La orden tiene descuentos asociados")
    if total and data.get("valor",obj.valor) is not None and Decimal(total)>data.get("valor",obj.valor): raise HTTPException(422,"Los descuentos superan el nuevo valor")


solicitudes=crud_router("/presupuesto/solicitudes","3.0 Presupuesto y pagos","presupuesto",SolicitudPresupuestal,SolicitudIn,
                       filtros=("tipo","estado"),antes_actualizar=solicitud_editar)
descuentos=crud_router("/presupuesto/descuentos","3.0 Presupuesto y pagos","presupuesto",Descuento,DescuentoIn,
                       filtros=("orden_id","tipo"),antes_crear=descuento_antes_crear,antes_actualizar=descuento_editar)

# ============ Release 4.0: Convenios ============
def convenio_editar(db,obj,data,user):
    if obj.estado=="liquidado": raise HTTPException(409,"El convenio ya está liquidado")
    if obj.fecha_envio_contaduria and data.get("fecha_inicio",obj.fecha_inicio)>obj.fecha_envio_contaduria:
        raise HTTPException(422,"La fecha de inicio no puede ser posterior a la remisión registrada")


convenios_crud=crud_router("/convenios","4.0 Convenios","convenios",Convenio,ConvenioIn,filtros=("estado","nit"),
    extra_out={"estado":(str,...),"fecha_envio_contaduria":(dt.date|None,None),"fecha_liquidacion":(dt.date|None,None),
               "fecha_envio_liquidacion":(dt.date|None,None)},antes_actualizar=convenio_editar)
convenios_flujo=APIRouter(prefix="/convenios",tags=["4.0 Convenios"])


def hay_doc(db,cid,tipo):
    return db.scalar(select(func.count()).select_from(Documento).where(Documento.entidad=="convenio",Documento.entidad_id==cid,Documento.tipo==tipo))


def convenio_lock(db,cid):
    c=db.get(Convenio,cid,with_for_update=True)
    if not c: raise HTTPException(404,"No encontrado")
    return c


@convenios_flujo.post("/{cid}/enviar-contaduria")
def enviar_contaduria(cid:int,evento:EventoIn|None=None,db:Session=Depends(get_db),user:User=Depends(require("convenios",True))):
    c=convenio_lock(db,cid); evento=evento or EventoIn()
    if c.estado!="registrado": raise HTTPException(409,f"Estado actual: {c.estado}")
    if evento.fecha<c.fecha_inicio: raise HTTPException(422,"Fecha anterior al inicio")
    if not hay_doc(db,cid,"contrato"): raise HTTPException(409,"Adjunte el contrato o convenio con tipo contrato")
    c.estado,c.fecha_envio_contaduria,c.updated_by="enviado_contaduria",evento.fecha,user.username
    audit(db,user.username,"CAMBIO_ESTADO","convenios",cid,evento_detalle("registrado",c.estado,evento,user)); db.commit()
    return {"id":cid,"estado":c.estado}


@convenios_flujo.post("/{cid}/liquidar")
def liquidar(cid:int,evento:EventoIn|None=None,db:Session=Depends(get_db),user:User=Depends(require("convenios",True))):
    c=convenio_lock(db,cid); evento=evento or EventoIn()
    if c.estado!="enviado_contaduria": raise HTTPException(409,"Registre primero la remisión a Contaduría")
    if evento.fecha<c.fecha_envio_contaduria: raise HTTPException(422,"Fecha anterior a la remisión")
    if not hay_doc(db,cid,"acta_liquidacion"): raise HTTPException(409,"Adjunte el acta de liquidación")
    anterior=c.estado; c.estado,c.fecha_liquidacion,c.updated_by="liquidado",evento.fecha,user.username
    audit(db,user.username,"CAMBIO_ESTADO","convenios",cid,evento_detalle(anterior,c.estado,evento,user)); db.commit()
    return {"id":cid,"estado":c.estado}


@convenios_flujo.post("/{cid}/enviar-liquidacion")
def enviar_liquidacion(cid:int,evento:EventoIn|None=None,db:Session=Depends(get_db),user:User=Depends(require("convenios",True))):
    c=convenio_lock(db,cid); evento=evento or EventoIn()
    if c.estado!="liquidado" or c.fecha_envio_liquidacion: raise HTTPException(409,"Requiere una liquidación aún no remitida")
    if evento.fecha<c.fecha_liquidacion: raise HTTPException(422,"Fecha anterior a la liquidación")
    c.fecha_envio_liquidacion,c.updated_by=evento.fecha,user.username
    audit(db,user.username,"REMISION_LIQUIDACION","convenios",cid,evento_detalle("liquidado","acta remitida",evento,user)); db.commit()
    return {"id":cid,"estado":c.estado,"fecha_envio_liquidacion":evento.fecha}


# ============ Panel (CAR-20) ============
panel = APIRouter(prefix="/panel", tags=["Panel"])


def _por_estado(db, Model):
    return {e: n for e, n in db.execute(select(Model.estado, func.count()).group_by(Model.estado))}


@panel.get("/resumen")
def resumen(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = {}
    if has_access(user, "peticiones"):
        hoy = fecha_local()
        r["peticiones"] = {
            "por_estado": _por_estado(db, Peticion),
            "vencidas": db.scalar(select(func.count()).select_from(Peticion).where(
                Peticion.estado != "respondida", Peticion.fecha_vencimiento < hoy))}
    if has_access(user, "caja_menor"):
        r["cajas_menores"] = _por_estado(db, CajaMenor)
        r["gastos_pendientes_revision"] = db.scalar(select(func.count()).select_from(GastoCajaMenor)
                                                    .where(GastoCajaMenor.estado_revision == "pendiente"))
    if has_access(user, "presupuesto"):
        r["presupuesto"] = _por_estado(db, SolicitudPresupuestal)
    if has_access(user, "convenios"):
        r["convenios"] = _por_estado(db, Convenio)
        r["convenios_valor_total"] = db.scalar(select(func.coalesce(func.sum(Convenio.valor_total), 0)))
    return r
