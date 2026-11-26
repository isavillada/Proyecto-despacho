import os, uuid
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..crud import audit
from ..db import get_db
from ..models import CajaMenor, Convenio, Documento, GastoCajaMenor, Peticion, SolicitudPresupuestal, User, ReintegroCaja
from ..schemas import DocumentoOut
from ..security import get_current_user, has_access

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
EXT = {".pdf", ".png", ".jpg", ".jpeg", ".docx", ".xlsx"}
MAX = 10 * 1024 * 1024
Entidad = Literal["peticion", "caja_menor", "gasto", "presupuesto", "convenio", "reintegro"]
MAPA = {"peticion": ("peticiones", Peticion), "caja_menor": ("caja_menor", CajaMenor),
        "gasto": ("caja_menor", GastoCajaMenor), "presupuesto": ("presupuesto", SolicitudPresupuestal),
        "convenio": ("convenios", Convenio), "reintegro": ("caja_menor", ReintegroCaja)}

router = APIRouter(prefix="/documentos", tags=["Documentos y soportes"])


@router.post("", response_model=DocumentoOut, status_code=201)
async def subir(entidad: Entidad, entidad_id: int, tipo: str = "soporte", archivo: UploadFile = File(...),
                db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    modulo, Model = MAPA[entidad]
    if not has_access(user, modulo, True):
        raise HTTPException(403, "Sin permiso")
    obj=db.get(Model,entidad_id)
    if not obj: raise HTTPException(404,"El registro asociado no existe")
    if entidad=="caja_menor" and obj.estado=="cierre": raise HTTPException(409,"Caja cerrada")
    if entidad in ("gasto","reintegro") and db.get(CajaMenor,obj.caja_id).estado=="cierre": raise HTTPException(409,"Caja cerrada")
    if entidad=="convenio" and obj.estado=="liquidado" and tipo in ("contrato","acta_liquidacion"): raise HTTPException(409,"No modifique los soportes principales de un convenio liquidado")
    if not tipo.strip() or len(tipo)>40: raise HTTPException(422,"Tipo documental inválido")
    ext = Path(archivo.filename or "").suffix.lower()
    if ext not in EXT:
        raise HTTPException(415, f"Extensiones permitidas: {sorted(EXT)}")
    data = await archivo.read(MAX + 1)
    if len(data) > MAX:
        raise HTTPException(413, "Archivo mayor a 10 MB")
    if not data: raise HTTPException(422,"Archivo vacío")
    if ext==".pdf" and not data.startswith(b"%PDF-"): raise HTTPException(415,"Contenido PDF inválido")
    if ext==".png" and not data.startswith(b"\x89PNG\r\n\x1a\n"): raise HTTPException(415,"Contenido PNG inválido")
    if ext in (".jpg",".jpeg") and not data.startswith(b"\xff\xd8\xff"): raise HTTPException(415,"Contenido JPEG inválido")
    if ext in (".docx",".xlsx"):
        import io,zipfile
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                required="word/document.xml" if ext==".docx" else "xl/workbook.xml"
                if required not in z.namelist(): raise ValueError()
        except (ValueError,zipfile.BadZipFile): raise HTTPException(415,"Contenido Office inválido")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    nombre = f"{uuid.uuid4().hex}{ext}"
    (UPLOAD_DIR / nombre).write_bytes(data)
    d = Documento(entidad=entidad, entidad_id=entidad_id, tipo=tipo[:40], ruta=nombre,
                  nombre_original=(archivo.filename or nombre)[:255], subido_por=user.username)
    db.add(d)
    db.flush()
    audit(db, user.username, "SUBIR_DOCUMENTO", "documentos", d.id, f"{entidad}:{entidad_id} {tipo}")
    try:
        db.commit()
    except Exception:
        (UPLOAD_DIR / nombre).unlink(missing_ok=True)
        raise
    return d


@router.get("", response_model=list[DocumentoOut])
def listar(entidad: Entidad, entidad_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not has_access(user, MAPA[entidad][0]):
        raise HTTPException(403, "Sin permiso")
    if not db.get(MAPA[entidad][1],entidad_id): raise HTTPException(404,"Registro no encontrado")
    return db.scalars(select(Documento).where(Documento.entidad == entidad,
                                              Documento.entidad_id == entidad_id)).all()


@router.get("/{doc_id}/descargar")
def descargar(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    d = db.get(Documento, doc_id)
    if not d:
        raise HTTPException(404, "No encontrado")
    if not has_access(user, MAPA[d.entidad][0]):
        raise HTTPException(403, "Sin permiso")
    audit(db, user.username, "DESCARGAR_DOCUMENTO", "documentos", d.id)
    db.commit()
    path=UPLOAD_DIR / d.ruta
    if not path.is_file(): raise HTTPException(404,"Archivo no disponible")
    return FileResponse(path, filename=d.nombre_original, media_type="application/octet-stream", headers={"X-Content-Type-Options":"nosniff"})
