from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select, func
import datetime as dt
from sqlalchemy.orm import Session
from ..crud import audit
from ..db import get_db
from ..models import AuditLog, User
from ..schemas import UsuarioIn, UsuarioOut, UsuarioUpdate
from ..security import (ROLES, crear_token, get_current_user, hash_password,
                        validar_clave, verify_password, has_access, ESCRITURA)

router = APIRouter(tags=["Autenticación y auditoría"])


@router.post("/auth/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    safe=form.username[:80]
    attempts=db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.usuario==safe,AuditLog.accion=="LOGIN_FALLIDO",AuditLog.ts>=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)-dt.timedelta(minutes=10)))
    if attempts>=10: raise HTTPException(429,"Demasiados intentos. Intente nuevamente en unos minutos.")
    user = db.query(User).filter_by(username=safe, activo=True).first()
    if not user or not verify_password(form.password, user.password_hash):
        audit(db, safe, "LOGIN_FALLIDO")
        db.commit()
        raise HTTPException(401, "Credenciales incorrectas")
    audit(db, user.username, "LOGIN_EXITOSO")
    db.commit()
    return {"access_token": crear_token(user), "token_type": "bearer", "role": user.role}


@router.get("/auth/yo", response_model=UsuarioOut)
def yo(user: User = Depends(get_current_user)):
    return user


class CambioClave(BaseModel):
    actual: str
    nueva: str


@router.post("/auth/cambiar-clave")
def cambiar_clave(body: CambioClave, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(body.actual, user.password_hash):
        raise HTTPException(422, "Clave actual incorrecta")
    validar_clave(body.nueva)
    user.password_hash = hash_password(body.nueva)
    user.token_version += 1
    audit(db, user.username, "CAMBIO_CLAVE")
    db.commit()
    return {"ok": True}


@router.post("/auth/usuarios", response_model=UsuarioOut, status_code=201)
def crear_usuario(body: UsuarioIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "admin":
        raise HTTPException(403, "Solo el administrador puede crear usuarios")
    if body.role not in ROLES:
        raise HTTPException(422, f"Rol inválido. Opciones: {sorted(ROLES)}")
    validar_clave(body.password)
    if db.query(User).filter_by(username=body.username).first():
        raise HTTPException(409, "El usuario ya existe")
    u = User(username=body.username, full_name=body.full_name, role=body.role,
             password_hash=hash_password(body.password))
    db.add(u)
    db.flush()
    audit(db, user.username, "CREAR", "usuarios", u.id, f"{u.username} ({u.role})")
    db.commit()
    return u


@router.get("/auth/usuarios", response_model=list[UsuarioOut])
def listar_usuarios(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "admin":
        raise HTTPException(403, "Solo el administrador")
    return db.scalars(select(User).order_by(User.id)).all()


@router.get("/auditoria")
def ver_auditoria(usuario: str | None = None, entidad: str | None = None, limit: int = 200,
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in ("admin", "secretario"):
        raise HTTPException(403, "Sin permiso")
    q = select(AuditLog).order_by(AuditLog.id.desc()).limit(min(limit, 1000))
    if usuario:
        q = q.where(AuditLog.usuario == usuario)
    if entidad:
        q = q.where(AuditLog.entidad == entidad)
    return [{"ts": a.ts, "usuario": a.usuario, "accion": a.accion, "entidad": a.entidad,
             "entidad_id": a.entidad_id, "detalle": a.detalle} for a in db.scalars(q)]


@router.get("/auth/permisos")
def permisos(user: User = Depends(get_current_user)):
    return {m:{"leer":has_access(user,m),"escribir":has_access(user,m,True)} for m in ESCRITURA}


@router.patch("/auth/usuarios/{uid}",response_model=UsuarioOut)
def actualizar_usuario(uid:int,body:UsuarioUpdate,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    if user.role!="admin": raise HTTPException(403,"Solo el administrador")
    u=db.get(User,uid)
    if not u: raise HTTPException(404,"Usuario no encontrado")
    data=body.model_dump(exclude_unset=True)
    if any(v is None for v in data.values()): raise HTTPException(422,"No se permiten valores nulos")
    if data.get("role",u.role) not in ROLES: raise HTTPException(422,"Rol inválido")
    if u.id==user.id and (data.get("activo",True) is False or data.get("role",u.role)!="admin"):
        raise HTTPException(409,"No puede retirar sus propios permisos de administración")
    if any(k in data and data[k] != getattr(u,k) for k in ("role","activo")) or "password" in data:
        u.token_version += 1
    if "password" in data:
        validar_clave(data["password"])
        u.password_hash=hash_password(data.pop("password"))
    for k,v in data.items(): setattr(u,k,v)
    audit(db,user.username,"MODIFICAR","usuarios",u.id,"Actualización de cuenta")
    db.commit()
    return u
