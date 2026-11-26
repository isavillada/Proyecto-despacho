import json
import datetime as dt
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import create_model, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .db import get_db
from .models import AuditLog
from .security import require


def audit(db: Session, usuario, accion, entidad=None, entidad_id=None, detalle=None):
    db.add(AuditLog(usuario=usuario, accion=accion, entidad=entidad,
                    entidad_id=entidad_id, detalle=detalle))


def variants(name, base, extra=None):
    upd = create_model(f"{name}Update",
                       __config__={"extra": "forbid"}, **{k: (Optional[f.annotation], None) for k, f in base.model_fields.items()})
    out = create_model(
        f"{name}Out", __base__=base,
        id=(int, ...), created_at=(dt.datetime, ...), created_by=(Optional[str], None),
        updated_at=(Optional[dt.datetime], None), updated_by=(Optional[str], None),
        **(extra or {}),
    )
    return upd, out


def crud_router(prefix, tag, modulo, Model, In, filtros=(), antes_crear=None,
                antes_actualizar=None, extra_out=None, permitir_actualizar=True, autorizar_crear=None, preparar_actualizacion=None):
    Upd, Out = variants(Model.__name__, In, extra_out)
    r = APIRouter(prefix=prefix, tags=[tag])

    @r.get("", response_model=list[Out])
    def listar(request: Request, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500),
               db: Session = Depends(get_db), user=Depends(require(modulo))):
        q = select(Model)
        for f in filtros:
            v = request.query_params.get(f)
            if v:
                try:
                    v = Model.__table__.c[f].type.python_type(v)
                except (ValueError, NotImplementedError):
                    raise HTTPException(422, f"Filtro inválido: {f}")
                q = q.where(getattr(Model, f) == v)
        return db.scalars(q.order_by(Model.id.desc()).offset(skip).limit(limit)).all()

    @r.get("/{item_id}", response_model=Out)
    def obtener(item_id: int, db: Session = Depends(get_db), user=Depends(require(modulo))):
        obj = db.get(Model, item_id)
        if not obj:
            raise HTTPException(404, "No encontrado")
        return obj

    @r.post("", response_model=Out, status_code=201)
    def crear(body: In, db: Session = Depends(get_db), user=Depends(require(modulo, True))):
        data = body.model_dump()
        if autorizar_crear:
            autorizar_crear(user, data)
        if antes_crear:
            antes_crear(db, data)
        obj = Model(**data, created_by=user.username)
        db.add(obj)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Registro duplicado")
        audit(db, user.username, "CREAR", Model.__tablename__, obj.id, json.dumps({"campos": list(data)}, ensure_ascii=False))
        db.commit()
        return obj

    @r.patch("/{item_id}", response_model=Out)
    def actualizar(item_id: int, body: Upd, db: Session = Depends(get_db),
                   user=Depends(require(modulo, True))):
        if not permitir_actualizar:
            raise HTTPException(405, "Este registro no admite modificación")
        obj = db.get(Model, item_id, with_for_update=True)
        if not obj:
            raise HTTPException(404, "No encontrado")
        data = body.model_dump(exclude_unset=True)
        if preparar_actualizacion:
            preparar_actualizacion(obj,data)
        previo = {k: getattr(obj,k) for k in In.model_fields}
        try:
            validado = In.model_validate({**previo, **data}).model_dump()
        except ValidationError as e:
            raise HTTPException(422, e.errors(include_context=False, include_url=False, include_input=False))
        data = {k: validado[k] for k in data}
        if antes_actualizar:
            antes_actualizar(db, obj, data, user)
        for k, v in data.items():
            setattr(obj, k, v)
        obj.updated_by = user.username
        audit(db, user.username, "MODIFICAR", Model.__tablename__, obj.id, json.dumps({"campos": list(data)}, ensure_ascii=False))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Registro duplicado")
        db.refresh(obj)
        return obj

    return r
