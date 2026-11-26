from decimal import Decimal
import io
import datetime as dt
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from app.main import app
from app.calendario import dias_habiles,festivos
from test_flujo import hdr


def crear(c,h,path,body):
    r=c.post(path,headers=h,json=body)
    assert r.status_code==201,r.text
    return r.json()


def test_calendario_referencia():
    assert dt.date(2026,12,8) in festivos(2026)
    assert dias_habiles(dt.date(2026,11,23),15)==dt.date(2026,12,15)
    assert dias_habiles(dt.date(2026,12,7),1)==dt.date(2026,12,9)
    assert dias_habiles(dt.date(2026,12,31),1)==dt.date(2027,1,4)


def test_peticiones_consistencia_y_modalidades():
    with TestClient(app) as c:
        h=hdr(c)
        body={'fecha_ingreso':'2026-11-23','numero_radicado':'PET-X','peticionario':'Demo','solicitud':'Consulta extensa','tipo_peticion':'informacion_documentos'}
        p=crear(c,h,'/peticiones',body); assert p['fecha_vencimiento']=='2026-12-07'
        url=f"/peticiones/{p['id']}"
        assert c.patch(url,headers=h,json={'estado':'respondida'}).status_code==422
        assert c.patch(url,headers=h,json={'estado':'distribuida'}).status_code==422
        r=c.patch(url,headers=h,json={'estado':'distribuida','asignado_a':'Responsable'}); assert r.status_code==200,r.text
        r=c.patch(url,headers=h,json={'fecha_ingreso':'2026-12-10'}); assert r.status_code==200,r.text
        assert r.json()['fecha_vencimiento']=='2026-12-24'
        assert c.patch(url,headers=h,json={'estado':'respondida','fecha_respuesta':'2026-12-01'}).status_code==422
        assert c.patch(url,headers=h,json={'estado':'respondida','fecha_respuesta':'2026-12-15'}).status_code==200
        assert c.patch(url,headers=h,json={'solicitud':None}).status_code==422
        body.update(numero_radicado='PET-Y',tipo_peticion='otro'); assert c.post('/peticiones',headers=h,json=body).status_code==422
        body.update(fecha_vencimiento='2026-12-01'); assert c.post('/peticiones',headers=h,json=body).status_code==201


def test_caja_reintegro_ciclos_y_cierre():
    with TestClient(app) as c:
        h=hdr(c);caja=crear(c,h,'/cajas-menores',{'vigencia':2027,'resolucion':'RES-2027','valor_fondo':'1000.00'});cid=caja['id'];path=f'/cajas-menores/{cid}'
        gasto=crear(c,h,'/gastos-caja-menor',{'caja_id':cid,'fecha':'2027-01-15','concepto':'Compra','valor':'400.00'});gid=gasto['id'];gpath=f'/gastos-caja-menor/{gid}'
        assert c.patch(gpath,headers=h,json={'valor':'1001'}).status_code==422
        assert c.patch(gpath,headers=h,json={'valor':'-1'}).status_code==422
        assert c.patch(path,headers=h,json={'valor_fondo':'100'}).status_code==409
        def avanzar(): return c.post(path+'/avanzar',headers=h,json={'fecha':'2027-01-15','referencia':'Actuación externa ficticia'})
        for _ in range(3): assert avanzar().status_code==200
        assert avanzar().status_code==409
        assert c.patch(gpath,headers=h,json={'estado_revision':'aprobado'}).status_code==200
        for _ in range(3): assert avanzar().status_code==200
        body={'caja_id':cid,'fecha':'2027-01-15','valor':'500','referencia':'REC-1','responsable':'Financiero'}
        assert c.post('/reintegros-caja-menor',headers=h,json=body).status_code==422
        body['valor']='400';rr=crear(c,h,'/reintegros-caja-menor',body)
        assert c.patch(f"/reintegros-caja-menor/{rr['id']}",headers=h,json={'valor':'300'}).status_code==405
        assert Decimal(c.get(path+'/resumen',headers=h).json()['saldo'])==1000
        assert c.post(path+'/nuevo-ciclo',headers=h,json={'fecha':'2027-01-16'}).status_code==200
        assert c.patch(gpath,headers=h,json={'valor':'300'}).status_code==409
        g2=crear(c,h,'/gastos-caja-menor',{'caja_id':cid,'fecha':'2027-01-16','concepto':'Segundo ciclo','valor':'200.00'});assert g2['ciclo']==2
        for _ in range(2): assert avanzar().status_code==200
        assert c.patch(f"/gastos-caja-menor/{g2['id']}",headers=h,json={'estado_revision':'aprobado'}).status_code==200
        for _ in range(3): assert avanzar().status_code==200
        assert c.patch(path,headers=h,json={'sobrante_consignado':'799'}).status_code==200
        assert avanzar().status_code==409
        assert c.patch(path,headers=h,json={'sobrante_consignado':'800'}).status_code==200
        assert avanzar().json()['estado']=='cierre'
        assert Decimal(c.get(path+'/resumen',headers=h).json()['saldo'])==0
        assert c.patch(gpath,headers=h,json={'valor':'1'}).status_code==409
        assert c.patch(path,headers=h,json={'resolucion':'CAMBIO'}).status_code==409
        assert c.get(path+'/historial',headers=h).json()


def test_presupuesto_descuentos_reportes():
    with TestClient(app) as c:
        h=hdr(c);base={'fecha':'2026-11-25','descripcion':'Seguimiento administrativo'};url='/presupuesto/solicitudes'
        for tipo in ['certificado_conveniencia','certificado_disponibilidad','compromiso','informe_ejecucion','informe_pago','modificacion_presupuestal']:
            crear(c,h,url,{**base,'tipo':tipo,'responsable':'Funcionario'})
        assert len(c.get(url+'?tipo=informe_pago',headers=h).json())==1
        o=crear(c,h,url,{**base,'tipo':'orden_pago','valor':'1000','numero':'=1+1'});oid=o['id'];d=crear(c,h,'/presupuesto/descuentos',{'orden_id':oid,'tipo':'retencion_fuente','valor':'100'})
        assert c.post('/presupuesto/descuentos',headers=h,json={'orden_id':oid,'tipo':'industria_comercio','valor':'901'}).status_code==422
        assert c.patch(f"/presupuesto/descuentos/{d['id']}",headers=h,json={'valor':'1200'}).status_code==422
        assert c.patch(f'{url}/{oid}',headers=h,json={'tipo':'informe_pago'}).status_code==409
        assert c.patch(f'{url}/{oid}',headers=h,json={'valor':'50'}).status_code==422
        invalid=crear(c,h,url,{**base,'tipo':'compromiso'});assert c.post('/presupuesto/descuentos',headers=h,json={'orden_id':invalid['id'],'tipo':'retencion_fuente','valor':'10'}).status_code==422
        b=c.get('/reportes/solicitudes-presupuestales?formato=xlsx',headers=h);assert b.status_code==200
        sh=load_workbook(io.BytesIO(b.content),data_only=False).active
        assert any(cell.value=='=1+1' and cell.data_type=='s' for row in sh for cell in row)
        pdf=c.get('/reportes/solicitudes-presupuestales?formato=pdf',headers=h);assert pdf.status_code==200 and pdf.content.startswith(b'%PDF-')


def test_documentos_permisos_y_revocacion():
    with TestClient(app) as c:
        h=hdr(c)
        u=crear(c,h,'/auth/usuarios',{'username':'secretaria','full_name':'Secretaria de prueba','role':'secretaria_ejecutiva','password':'Clave#Prueba123'})
        sec=hdr(c,'secretaria','Clave#Prueba123')
        assert c.get('/convenios',headers=sec).status_code==403
        assert c.get('/reportes/convenios',headers=sec).status_code==403
        assert 'convenios' not in c.get('/panel/resumen',headers=sec).json()
        assert c.get('/auditoria',headers=sec).status_code==403
        p=crear(c,sec,'/peticiones',{'fecha_ingreso':'2026-11-23','numero_radicado':'DOC-P','peticionario':'Demo','solicitud':'Documento'})
        q={'entidad':'peticion','entidad_id':p['id'],'tipo':'soporte'}
        assert c.post('/documentos',headers=sec,params=q,files={'archivo':('fake.pdf',b'no pdf','application/pdf')}).status_code==415
        from reportlab.pdfgen import canvas
        b=io.BytesIO();pdf=canvas.Canvas(b);pdf.drawString(40,700,'Soporte ficticio');pdf.save();data=b.getvalue()
        r=c.post('/documentos',headers=sec,params=q,files={'archivo':('soporte.pdf',data,'application/pdf')});assert r.status_code==201,r.text
        doc=r.json();assert c.get(f"/documentos/{doc['id']}/descargar",headers=sec).content==data
        assert c.patch(f"/auth/usuarios/{u['id']}",headers=h,json={'activo':False}).status_code==200
        assert c.get('/peticiones',headers=sec).status_code==401
        assert c.patch(f"/auth/usuarios/{u['id']}",headers=h,json={'activo':True}).status_code==200
        assert c.get('/peticiones',headers=sec).status_code==401  # la sesión anterior no revive
        new=hdr(c,'secretaria','Clave#Prueba123');assert c.post('/auth/cambiar-clave',headers=new,json={'actual':'Clave#Prueba123','nueva':'Nueva#Prueba123'}).status_code==200
        assert c.get('/peticiones',headers=new).status_code==401
        assert c.get('/peticiones',headers=hdr(c,'secretaria','Nueva#Prueba123')).status_code==200
