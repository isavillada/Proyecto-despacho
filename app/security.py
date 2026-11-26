import os, re, hmac, hashlib, secrets, datetime as dt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .db import get_db
from .models import User

SECRET = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)  # defina SECRET_KEY en producción
ITER = 600_000
oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")

ROLES = {
    "admin", "secretario", "secretaria_ejecutiva", "auxiliar_administrativo",
    "abogado_delegado", "profesional_presupuesto", "profesional_universitario",
    "tecnico_administrativo", "apoyo_financiero",
}
# Roles con escritura por módulo. Lectura = escritura + secretario. 'admin' accede a todo.
ESCRITURA = {
    "peticiones": {"secretaria_ejecutiva", "secretario", "abogado_delegado"},
    "caja_menor": {"auxiliar_administrativo", "abogado_delegado", "secretario", "apoyo_financiero"},
    "presupuesto": {"profesional_presupuesto", "auxiliar_administrativo",
                    "profesional_universitario", "tecnico_administrativo"},
    "convenios": {"secretario"},
}


def hash_password(p: str) -> str:
    salt = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", p.encode(), salt, ITER)
    return f"pbkdf2${ITER}${salt.hex()}${h.hex()}"


def verify_password(p: str, stored: str) -> bool:
    if len(p)>128: return False
    try:
        _, it, salt, h = stored.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", p.encode(), bytes.fromhex(salt), int(it))
        return hmac.compare_digest(calc.hex(), h)
    except ValueError:
        return False


def validar_clave(p: str):
    if not (10 <= len(p) <= 128 and re.search(r"[A-Z]", p) and re.search(r"[a-z]", p)
            and re.search(r"\d", p) and re.search(r"[^\w\s]", p)):
        raise HTTPException(422, "La clave debe tener mínimo 10 caracteres, mayúscula, minúscula, número y carácter especial")


def crear_token(user: User) -> str:
    exp = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=8)
    return jwt.encode({"sub": user.username, "role": user.role, "ver": user.token_version, "exp": exp}, SECRET, algorithm="HS256")


def get_current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    try:
        claims = jwt.decode(token, SECRET, algorithms=["HS256"], options={"require":["exp","sub","ver"]})
        username = claims["sub"]
    except jwt.PyJWTError:
        raise HTTPException(401, "Token inválido o expirado")
    user = db.query(User).filter_by(username=username, activo=True).first()
    if not user or claims["ver"] != user.token_version:
        raise HTTPException(401, "Usuario no válido o sesión revocada")
    return user


def has_access(user: User, modulo: str, escribir: bool = False) -> bool:
    if user.role == "admin":
        return True
    w = ESCRITURA[modulo]
    return user.role in w if escribir else (user.role in w or user.role == "secretario")


def require(modulo: str, escribir: bool = False):
    def dep(user: User = Depends(get_current_user)) -> User:
        if not has_access(user, modulo, escribir):
            raise HTTPException(403, "Su rol no tiene permiso para esta operación")
        return user
    return dep
