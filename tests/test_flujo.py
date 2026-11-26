from fastapi.testclient import TestClient
from app.main import app


def hdr(c, u="admin", p="Admin#12345!"):
    r = c.post("/auth/login", data={"username": u, "password": p})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_flujo_completo():
    with TestClient(app) as c:
        h = hdr(c)
        assert c.post("/auth/login", data={"username": "admin", "password": "mala"}).status_code == 401
        r = c.post("/auth/usuarios", headers=h, json={"username": "aux", "full_name": "Aux",
                   "role": "auxiliar_administrativo", "password": "Aux#123456!"})
        assert r.status_code == 201
        ha = hdr(c, "aux", "Aux#123456!")

        # Peticiones: vencimiento automático (15 días hábiles) y control de rol
        p = {"fecha_ingreso": "2026-11-23", "numero_radicado": "R-1", "peticionario": "Ana", "solicitud": "Info"}
        assert c.post("/peticiones", headers=ha, json=p).status_code == 403
        r = c.post("/peticiones", headers=h, json=p)
        assert r.status_code == 201 and r.json()["fecha_vencimiento"] == "2026-12-15"
        assert c.post("/peticiones", headers=h, json=p).status_code == 409
        assert len(c.get("/peticiones/seguimiento", headers=h).json()) == 1

        # Caja menor
        caja = c.post("/cajas-menores", headers=ha, json={"vigencia": 2026, "valor_fondo": "1000000", "resolucion":"RES-2026-001"}).json()
        cid = caja["id"]
        assert caja["estado"] == "apertura"
        g = c.post("/gastos-caja-menor", headers=ha, json={"caja_id": cid, "fecha": "2026-11-24",
                   "concepto": "Papelería", "valor": "200000"}).json()
        assert c.post("/gastos-caja-menor", headers=ha, json={"caja_id": cid, "fecha": "2026-11-24",
                      "concepto": "Exceso", "valor": "900000"}).status_code == 422
        for _ in range(3):
            assert c.post(f"/cajas-menores/{cid}/avanzar", headers=h, json={"fecha":"2026-11-24"}).status_code == 200
        assert c.post(f"/cajas-menores/{cid}/avanzar", headers=h, json={"fecha":"2026-11-24"}).status_code == 409  # gasto sin revisar
        assert c.patch(f"/gastos-caja-menor/{g['id']}", headers=ha, json={"estado_revision": "aprobado"}).status_code == 403
        assert c.patch(f"/gastos-caja-menor/{g['id']}", headers=h, json={"estado_revision": "aprobado"}).status_code == 200
        for _ in range(3):
            assert c.post(f"/cajas-menores/{cid}/avanzar", headers=h, json={"fecha":"2026-11-24"}).status_code == 200
        assert c.post(f"/cajas-menores/{cid}/avanzar", headers=h, json={"fecha":"2026-11-24"}).status_code == 409  # sin sobrante
        c.patch(f"/cajas-menores/{cid}", headers=ha, json={"sobrante_consignado": "800000"})
        r = c.post(f"/cajas-menores/{cid}/avanzar", headers=h, json={"fecha":"2026-11-24"})
        assert r.json()["estado"] == "cierre"

        # Convenios: no se liquida sin acta
        cv = c.post("/convenios", headers=h, json={"numero": "C-1", "fecha_inicio": "2026-02-01",
                    "nit": "800123456", "entidad": "Min Cultura", "valor_total": "5000000"}).json()
        assert c.post(f"/convenios/{cv['id']}/liquidar", headers=h).status_code == 409
        up = c.post("/documentos", headers=h, params={"entidad": "convenio", "entidad_id": cv["id"],
                    "tipo": "acta_liquidacion"}, files={"archivo": ("acta.pdf", b"%PDF-1.4", "application/pdf")})
        assert up.status_code == 201
        assert c.post(f"/convenios/{cv['id']}/liquidar", headers=h).status_code == 409
        assert c.post("/documentos", headers=h, params={"entidad":"convenio", "entidad_id":cv["id"],"tipo":"contrato"}, files={"archivo":("contrato.pdf",b"%PDF-1.4","application/pdf")}).status_code==201
        assert c.post(f"/convenios/{cv['id']}/enviar-contaduria", headers=h).status_code==200
        assert c.post(f"/convenios/{cv['id']}/liquidar", headers=h).json()["estado"] == "liquidado"
        assert c.post(f"/convenios/{cv['id']}/enviar-liquidacion",headers=h).status_code==200

        # Reportes, panel y auditoría
        assert c.get("/reportes/convenios?formato=xlsx", headers=h).status_code == 200
        assert c.get("/reportes/peticiones?formato=pdf", headers=h).status_code == 200
        assert "peticiones" in c.get("/panel/resumen", headers=h).json()
        acciones = {a["accion"] for a in c.get("/auditoria", headers=h).json()}
        assert {"LOGIN_FALLIDO", "LOGIN_EXITOSO", "CREAR", "CAMBIO_ESTADO", "EXPORTAR"} <= acciones
