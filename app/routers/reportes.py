import io
from decimal import Decimal
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from xml.sax.saxutils import escape
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..crud import audit
from ..db import get_db
from ..models import (CajaMenor, Convenio, Descuento, GastoCajaMenor, Peticion,
                      SolicitudPresupuestal, User, ReintegroCaja)
from ..security import get_current_user, has_access

ENTIDADES = {
    "peticiones": (Peticion, "peticiones"), "cajas-menores": (CajaMenor, "caja_menor"),
    "gastos-caja-menor": (GastoCajaMenor, "caja_menor"),
    "solicitudes-presupuestales": (SolicitudPresupuestal, "presupuesto"),
    "descuentos": (Descuento, "presupuesto"), "convenios": (Convenio, "convenios"),
    "reintegros-caja-menor": (ReintegroCaja, "caja_menor"),
}
OCULTAS = {"created_at", "created_by", "updated_at", "updated_by"}
router = APIRouter(prefix="/reportes", tags=["Reportes"])


def _v(x):
    if isinstance(x, Decimal):
        return float(x)
    return x


@router.get("/{entidad}")
def reporte(entidad: Literal[tuple(ENTIDADES)], formato: Literal["xlsx", "pdf"] = "xlsx",
            db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    Model, modulo = ENTIDADES[entidad]
    if not has_access(user, modulo):
        raise HTTPException(403, "Sin permiso")
    cols = [c.name for c in Model.__table__.columns if c.name not in OCULTAS]
    filas = [[_v(getattr(r, c)) for c in cols] for r in db.scalars(select(Model).order_by(Model.id))]
    buf = io.BytesIO()
    if formato == "xlsx":
        wb = Workbook()
        ws = wb.active
        ws.title = entidad[:31]
        ws.append(cols)
        for f in filas:
            ws.append(f)
            for cell in ws[ws.max_row]:
                if isinstance(cell.value,str): cell.data_type="s"  # no ejecutar fórmulas provenientes de registros
        for cell in ws[1]:
            cell.font=Font(bold=True,color="FFFFFF"); cell.fill=PatternFill("solid",fgColor="173A51")
        ws.freeze_panes="A2"; ws.auto_filter.ref=ws.dimensions
        for i,col in enumerate(cols,1):
            ws.column_dimensions[get_column_letter(i)].width=min(45,max(16,len(col)+4))
        for row in ws.iter_rows(min_row=2):
            for c in row: c.alignment=Alignment(vertical="top",wrap_text=True)
        wb.save(buf)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        st = getSampleStyleSheet()
        story=[Paragraph(f"Reporte administrativo: {escape(entidad)}",st["Title"]),Paragraph(f"Registros: {len(filas)}",st["Normal"]),Spacer(1,10)]
        def para(v): return Paragraph(escape("" if v is None else str(v)).replace("\n","<br/>"),st["BodyText"])
        if not filas: story.append(Paragraph("No hay registros para este reporte.",st["Normal"]))
        for f in filas:
            story.append(Paragraph(f"Registro {f[0]}",st["Heading2"]))
            tabla=Table([[para(c.replace("_"," ")),para(v)] for c,v in zip(cols,f)],colWidths=[145,365],splitByRow=1,splitInRow=1)
            tabla.setStyle(TableStyle([("BACKGROUND",(0,0),(0,-1),colors.HexColor("#E7EFF4")),("GRID",(0,0),(-1,-1),0.25,colors.lightgrey),("VALIGN",(0,0),(-1,-1),"TOP")]))
            story.extend([tabla,Spacer(1,12)])
        SimpleDocTemplate(buf,pagesize=A4,leftMargin=42,rightMargin=42).build(story)
        media = "application/pdf"
    audit(db, user.username, "EXPORTAR", entidad, None, formato)
    db.commit()
    buf.seek(0)
    return StreamingResponse(buf, media_type=media,
                             headers={"Content-Disposition": f'attachment; filename="{entidad}.{formato}"'})
