import os, secrets
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from .db import Base, SessionLocal, engine
from .models import User
from .routers import auth, documentos, procesos, reportes
from .security import hash_password, validar_clave


def seed_admin():
    with SessionLocal() as db:
        if db.query(User).count():
            return
        pwd = os.getenv("ADMIN_PASSWORD") or secrets.token_urlsafe(14) + "!aA1"
        validar_clave(pwd)
        db.add(User(username="admin", full_name="Administrador", role="admin",
                    password_hash=hash_password(pwd)))
        db.commit()
        if not os.getenv("ADMIN_PASSWORD"):
            print(f"\n>>> Usuario inicial: admin / {pwd}  (cámbiela de inmediato)\n")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    seed_admin()
    yield


app = FastAPI(title="Plataforma de Gestión del Despacho - Secretaría de Cultura de Pereira",
              version="1.0", lifespan=lifespan)

for r in (auth.router, procesos.peticiones_seg, procesos.peticiones, procesos.cajas_extra,
          procesos.cajas_flujo, procesos.gastos, procesos.reintegros, procesos.solicitudes, procesos.descuentos,
          procesos.convenios_crud, procesos.convenios_flujo, procesos.panel,
          documentos.router, reportes.router):
    app.include_router(r)

from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

UI = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/ui", StaticFiles(directory=UI), name="frontend-demo")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def inicio():
    return FileResponse(UI / "preview" / "index.html", media_type="text/html")


@app.get("/salud", include_in_schema=False)
def salud():
    return {"estado":"ok","modo":"compatibilidad FastAPI"}
