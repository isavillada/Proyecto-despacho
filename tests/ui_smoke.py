import os, tempfile, base64
from pathlib import Path
from io import BytesIO
from reportlab.pdfgen import canvas
buf=BytesIO(); pdf=canvas.Canvas(buf); pdf.drawString(40,700,"Contrato ficticio para pruebas"); pdf.save(); valid_pdf=buf.getvalue()
from playwright.sync_api import sync_playwright, expect
root=Path(__file__).resolve().parent.parent if Path(__file__).parent.name=='tests' else Path.cwd()
tmp=tempfile.TemporaryDirectory(); folder=Path(tmp.name)
os.environ.update(DATABASE_URL=f'sqlite:///{folder}/qa.db',UPLOAD_DIR=str(folder/'uploads'),ADMIN_PASSWORD='Prueba#Cultura2026',SECRET_KEY='qa-only-local-secret-not-for-production-123456789')
from fastapi.testclient import TestClient
from app.main import app
(root/'evidencia').mkdir(exist_ok=True)
with TestClient(app) as client, sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=os.getenv('CHROMIUM_PATH') or None,headless=True,args=['--no-sandbox'])
    ctx=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
    page=ctx.new_page();page.set_default_timeout(5000);errors=[];page.on('pageerror',lambda e: errors.append(str(e)))
    # Exercise the real API without a browser network connection. All data remains local.
    def bridge(req):
        headers=req['headers'];kwargs={'headers':headers}
        if req.get('form') is not None:
            kwargs['files']={k:(v['name'],base64.b64decode(v['data']),v['type']) for k,v in req['form'].items()}
        elif req.get('body') is not None: kwargs['content']=req['body']
        result=client.request(req['method'],req['path'],**kwargs)
        return {'status':result.status_code,'headers':{'content-type':result.headers.get('content-type','application/octet-stream')},'data':base64.b64encode(result.content).decode()}
    page.expose_function('apiBridge',bridge)
    page.set_content('<!doctype html><html lang="es"><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="root"></div></body></html>')
    page.add_style_tag(path=str(root/'frontend/style.css'))
    page.evaluate("""() => { window.fetch=async(path,opts={})=>{const headers={...(opts.headers||{})};let body=opts.body||null,form=null;if(body instanceof URLSearchParams){headers['Content-Type']='application/x-www-form-urlencoded';body=body.toString();}else if(body instanceof FormData){form={};for(const [k,v] of body.entries()){const bytes=new Uint8Array(await v.arrayBuffer());let binary='';for(let i=0;i<bytes.length;i++)binary+=String.fromCharCode(bytes[i]);form[k]={name:v.name,type:v.type,data:btoa(binary)};}body=null;}const r=await window.apiBridge({path,method:opts.method||'GET',headers,body,form});const bytes=Uint8Array.from(atob(r.data),c=>c.charCodeAt(0));return new Response(bytes,{status:r.status,headers:r.headers});}; }""")
    for script in ['frontend/preview/vendor/react.js','frontend/preview/vendor/react-dom.js','frontend/ui.js','frontend/preview/start.js']:
        page.add_script_tag(path=str(root/script))
    expect(page.get_by_role('heading',name='Iniciar sesión')).to_be_visible(timeout=10000)
    page.screenshot(path=str(root/'evidencia/01_acceso.png'))
    page.get_by_label('Usuario',exact=True).fill('admin');page.get_by_label('Contraseña',exact=True).fill('Prueba#Cultura2026');page.get_by_role('button',name='Ingresar',exact=True).click();expect(page.get_by_role('heading',name='Panel general')).to_be_visible()
    page.get_by_role('button',name='Peticiones',exact=True).click();expect(page.get_by_role('heading',name='Derechos de petición y correspondencia')).to_be_visible();page.get_by_role('button',name='+ Nuevo registro').click()
    page.locator('#field-fecha_ingreso').fill('2026-11-23');page.locator('#field-numero_radicado').fill('DEMO-001');page.locator('#field-peticionario').fill('Ciudadana de prueba');page.locator('#field-solicitud').fill('Solicitud ficticia de información sobre actividades culturales.');page.locator('#field-tipo_peticion').select_option('informacion_documentos');page.locator('#field-asignado_a').fill('Jefe de oficina');page.locator('#field-estado').select_option('distribuida');page.get_by_role('button',name='Guardar registro').click();expect(page.get_by_text('DEMO-001',exact=True)).to_be_visible();page.screenshot(path=str(root/'evidencia/02_peticiones.png'))
    page.get_by_role('button',name='Editar registro 1').click();page.locator('#field-estado').select_option('respondida');page.locator('#field-fecha_respuesta').fill('2026-11-24');page.get_by_role('button',name='Guardar registro').click();expect(page.locator('td .status.respondida')).to_be_visible()
    page.get_by_role('button',name='Caja menor',exact=True).click();page.get_by_role('button',name='+ Nuevo registro').click();page.locator('#field-vigencia').fill('2026');page.locator('#field-resolucion').fill('RES-DEMO-01');page.locator('#field-valor_fondo').fill('1000000');page.get_by_role('button',name='Guardar registro').click();expect(page.get_by_text('RES-DEMO-01',exact=True)).to_be_visible()
    page.get_by_role('button',name='Gastos y revisión').click();page.get_by_role('button',name='+ Nuevo registro').click();page.locator('#field-caja_id').select_option('1');page.locator('#field-fecha').fill('2026-11-24');page.locator('#field-concepto').fill('Papelería demostración');page.locator('#field-valor').fill('150000');page.locator('#field-numero_recibo').fill('REC-DEMO');page.get_by_role('button',name='Guardar registro').click();expect(page.get_by_text('Papelería demostración',exact=True)).to_be_visible();page.screenshot(path=str(root/'evidencia/03_caja_menor.png'))
    page.get_by_role('button',name='Presupuesto y pagos',exact=True).click();page.get_by_role('button',name='+ Nuevo registro').click();page.locator('#field-tipo').select_option('certificado_conveniencia');page.locator('#field-numero').fill('CERT-DEMO');page.locator('#field-descripcion').fill('Certificado de conveniencia de demostración');page.locator('#field-fecha').fill('2026-11-24');page.get_by_role('button',name='Guardar registro').click();expect(page.get_by_text('CERT-DEMO',exact=True)).to_be_visible();page.screenshot(path=str(root/'evidencia/04_presupuesto.png'))
    page.get_by_role('button',name='Convenios',exact=True).click();page.get_by_role('button',name='+ Nuevo registro').click();page.locator('#field-numero').fill('CONV-DEMO');page.locator('#field-fecha_inicio').fill('2026-02-01');page.locator('#field-nit').fill('900000001');page.locator('#field-entidad').fill('Entidad ficticia');page.locator('#field-valor_total').fill('8000000');page.get_by_role('button',name='Guardar registro').click();expect(page.get_by_text('CONV-DEMO',exact=True)).to_be_visible();page.get_by_role('button',name='Ver registro 1').click();page.locator('#doc-type').select_option('contrato');page.locator('#doc-file').set_input_files({'name':'contrato-demo.pdf','mimeType':'application/pdf','buffer':valid_pdf});page.get_by_role('button',name='Adjuntar',exact=True).click();expect(page.get_by_text('contrato-demo.pdf',exact=True)).to_be_visible();page.get_by_role('button',name='Registrar remisión a Contaduría').click();page.locator('#field-fecha').fill('2026-11-24');page.get_by_role('button',name='Confirmar registro').click();expect(page.locator('td .status.enviado_contaduria')).to_be_visible();page.screenshot(path=str(root/'evidencia/05_convenio.png'));page.get_by_role('button',name='Cerrar ventana').click()
    page.get_by_role('button',name='Reportes',exact=True).click();page.locator('#report-entity').select_option('convenios');
    with page.expect_download() as d: page.get_by_role('button',name='Descargar Excel (.xlsx)').click()
    assert d.value.suggested_filename=='convenios.xlsx'
    page.get_by_role('button',name='Panel general',exact=True).click();expect(page.get_by_role('heading',name='Panel general')).to_be_visible();page.wait_for_timeout(350);page.screenshot(path=str(root/'evidencia/06_panel.png'))
    page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(150);assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth');page.screenshot(path=str(root/'evidencia/07_panel_movil.png'));page.get_by_role('button',name='☰ Menú').click();page.get_by_role('button',name='Peticiones',exact=True).click();expect(page.get_by_role('heading',name='Derechos de petición y correspondencia')).to_be_visible();assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth');page.screenshot(path=str(root/'evidencia/08_peticiones_movil.png'))
    assert not errors,errors
    browser.close()
    print('UI: acceso, peticiones, caja/gastos, presupuesto, convenios/documentos, Excel y diseño móvil aprobados.')
