package co.pereira.cultura;

import jakarta.servlet.http.HttpServletRequest;
import java.io.IOException;
import java.util.*;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api")
public class ApiController {
    private final AuthService auth;private final RecordsService records;private final DocumentService docs;private final ReportService reports;private final JdbcTemplate db;
    public ApiController(AuthService auth,RecordsService records,DocumentService docs,ReportService reports,JdbcTemplate db){this.auth=auth;this.records=records;this.docs=docs;this.reports=reports;this.db=db;}
    private AuthService.User u(HttpServletRequest req){return auth.current(req);}
    private RecordsService.Resource resource(HttpServletRequest req,boolean hasId){String path=req.getRequestURI().substring(req.getContextPath().length()+4);if(hasId)path=path.substring(0,path.lastIndexOf('/'));return RecordsService.resource(path);}
    @GetMapping("/salud") Map<String,Object> health(){db.queryForObject("SELECT 1",Integer.class);return Map.of("estado","ok");}
    @PostMapping(value="/auth/login",consumes=MediaType.APPLICATION_FORM_URLENCODED_VALUE) Map<String,Object> login(@RequestParam String username,@RequestParam String password){return auth.login(username,password);}
    @GetMapping("/auth/yo") Map<String,Object> me(HttpServletRequest req){return auth.me(u(req));}
    @GetMapping("/auth/permisos") Map<String,Object> permissions(HttpServletRequest req){return auth.permisos(u(req));}
    @GetMapping("/auth/usuarios") List<Map<String,Object>> users(HttpServletRequest req){return auth.users(u(req));}
    @PostMapping("/auth/usuarios") @ResponseStatus(HttpStatus.CREATED) Map<String,Object> userCreate(HttpServletRequest req,@RequestBody Map<String,Object> body){return auth.create(u(req),body);}
    @PatchMapping("/auth/usuarios/{id}") Map<String,Object> userUpdate(HttpServletRequest req,@PathVariable long id,@RequestBody Map<String,Object> body){return auth.update(u(req),id,body);}
    @PostMapping("/auth/cambiar-clave") Map<String,Object> password(HttpServletRequest req,@RequestBody Map<String,Object> body){return auth.changePassword(u(req),body);}
    @GetMapping("/auditoria") List<Map<String,Object>> audit(HttpServletRequest req,@RequestParam(required=false) String usuario,@RequestParam(required=false) String entidad,@RequestParam(defaultValue="200") int limit){return auth.auditList(u(req),usuario,entidad,limit);}
    @GetMapping({"/peticiones","/cajas-menores","/gastos-caja-menor","/reintegros-caja-menor","/presupuesto/solicitudes","/presupuesto/descuentos","/convenios"}) List<Map<String,Object>> list(HttpServletRequest req,@RequestParam Map<String,String> params){return records.list(resource(req,false),params,u(req));}
    @GetMapping({"/peticiones/{id}","/cajas-menores/{id}","/gastos-caja-menor/{id}","/reintegros-caja-menor/{id}","/presupuesto/solicitudes/{id}","/presupuesto/descuentos/{id}","/convenios/{id}"}) Map<String,Object> get(HttpServletRequest req,@PathVariable long id){return records.get(resource(req,true),id,u(req));}
    @PostMapping({"/peticiones","/cajas-menores","/gastos-caja-menor","/reintegros-caja-menor","/presupuesto/solicitudes","/presupuesto/descuentos","/convenios"}) @ResponseStatus(HttpStatus.CREATED) Map<String,Object> create(HttpServletRequest req,@RequestBody Map<String,Object> body){return records.create(resource(req,false),body,u(req));}
    @PatchMapping({"/peticiones/{id}","/cajas-menores/{id}","/gastos-caja-menor/{id}","/reintegros-caja-menor/{id}","/presupuesto/solicitudes/{id}","/presupuesto/descuentos/{id}","/convenios/{id}"}) Map<String,Object> update(HttpServletRequest req,@PathVariable long id,@RequestBody Map<String,Object> body){return records.update(resource(req,true),id,body,u(req));}
    @GetMapping("/peticiones/seguimiento") List<Map<String,Object>> pending(HttpServletRequest req){return records.seguimiento(u(req));}
    @GetMapping("/cajas-menores/{id}/resumen") Map<String,Object> cashSummary(HttpServletRequest req,@PathVariable long id){return records.cajaResumen(id,u(req));}
    @GetMapping("/cajas-menores/{id}/historial") List<Map<String,Object>> cashHistory(HttpServletRequest req,@PathVariable long id){return records.cajaHistorial(id,u(req));}
    @PostMapping("/cajas-menores/{id}/{action:avanzar|nuevo-ciclo}") Map<String,Object> cashAction(HttpServletRequest req,@PathVariable long id,@PathVariable String action,@RequestBody(required=false) Map<String,Object> body){return records.cajaAction(id,action,body,u(req));}
    @PostMapping("/convenios/{id}/{action:enviar-contaduria|liquidar|enviar-liquidacion}") Map<String,Object> agreementAction(HttpServletRequest req,@PathVariable long id,@PathVariable String action,@RequestBody(required=false) Map<String,Object> body){return records.convenioAction(id,action,body,u(req));}
    @GetMapping("/panel/resumen") Map<String,Object> panel(HttpServletRequest req){return records.panel(u(req));}
    @GetMapping("/documentos") List<Map<String,Object>> documents(HttpServletRequest req,@RequestParam String entidad,@RequestParam long entidad_id){return docs.list(entidad,entidad_id,u(req));}
    @PostMapping(value="/documentos",consumes=MediaType.MULTIPART_FORM_DATA_VALUE) @ResponseStatus(HttpStatus.CREATED) Map<String,Object> upload(HttpServletRequest req,@RequestParam String entidad,@RequestParam long entidad_id,@RequestParam(defaultValue="soporte") String tipo,@RequestPart("archivo") MultipartFile archivo) throws IOException{return docs.upload(entidad,entidad_id,tipo,archivo,u(req));}
    @GetMapping("/documentos/{id}/descargar") ResponseEntity<FileSystemResource> download(HttpServletRequest req,@PathVariable long id){return docs.download(id,u(req));}
    @GetMapping("/reportes/{entidad}") ResponseEntity<byte[]> report(HttpServletRequest req,@PathVariable String entidad,@RequestParam(defaultValue="xlsx") String formato) throws IOException{return reports.export(entidad,formato,u(req));}
}
