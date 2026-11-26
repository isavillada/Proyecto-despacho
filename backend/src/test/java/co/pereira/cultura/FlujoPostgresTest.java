package co.pereira.cultura;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.junit.jupiter.api.Assertions.*;

/** Contract/acceptance test against real PostgreSQL. Requires Docker. */
@Testcontainers(disabledWithoutDocker=true)
@SpringBootTest
@AutoConfigureMockMvc
class FlujoPostgresTest {
    @Container static PostgreSQLContainer<?> postgres=new PostgreSQLContainer<>("postgres:16-alpine");
    static final Path UPLOADS;
    static {try{UPLOADS=Files.createTempDirectory("cultura-java-test-");}catch(Exception e){throw new ExceptionInInitializerError(e);}}
    @DynamicPropertySource static void properties(DynamicPropertyRegistry p){p.add("spring.datasource.url",postgres::getJdbcUrl);p.add("spring.datasource.username",postgres::getUsername);p.add("spring.datasource.password",postgres::getPassword);p.add("app.secret",()->"only-testing-java-secret-not-for-production-123456789");p.add("app.admin-password",()->"Admin#12345!");p.add("app.upload-dir",UPLOADS::toString);}
    @Autowired MockMvc mvc;@Autowired ObjectMapper mapper;
    String login(String user,String password)throws Exception{String s=mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_FORM_URLENCODED).param("username",user).param("password",password)).andExpect(status().isOk()).andReturn().getResponse().getContentAsString();return "Bearer "+mapper.readTree(s).get("access_token").asText();}
    ResultActions create(String path,String token,Map<String,Object> data)throws Exception{return mvc.perform(post("/api"+path).header("Authorization",token).contentType(MediaType.APPLICATION_JSON).content(mapper.writeValueAsBytes(data)));}
    ResultActions update(String path,String token,Map<String,Object> data)throws Exception{return mvc.perform(patch("/api"+path).header("Authorization",token).contentType(MediaType.APPLICATION_JSON).content(mapper.writeValueAsBytes(data)));}
    long created(ResultActions r)throws Exception{return mapper.readTree(r.andExpect(status().isCreated()).andReturn().getResponse().getContentAsString()).get("id").asLong();}
    @Test void cuatroProcesosYSeguridad()throws Exception{
        String h=login("admin","Admin#12345!");
        created(create("/auth/usuarios",h,Map.of("username","aux","full_name","Auxiliar","role","auxiliar_administrativo","password","Aux#123456!")));String aux=login("aux","Aux#123456!");
        Map<String,Object> pet=Map.of("fecha_ingreso","2026-11-23","numero_radicado","R-JAVA-1","peticionario","Persona de prueba","solicitud","Información");
        create("/peticiones",aux,pet).andExpect(status().isForbidden());
        long pid=created(create("/peticiones",h,pet).andExpect(jsonPath("$.fecha_vencimiento").value("2026-12-15")));
        create("/peticiones",h,pet).andExpect(status().isConflict());
        update("/peticiones/"+pid,h,Map.of("estado","respondida")).andExpect(status().isUnprocessableEntity());
        update("/peticiones/"+pid,h,Map.of("estado","respondida","fecha_respuesta","2026-11-24")).andExpect(status().isOk());
        long cid=created(create("/cajas-menores",aux,Map.of("vigencia",2026,"resolucion","RES-JAVA","valor_fondo","1000")));
        long gid=created(create("/gastos-caja-menor",aux,Map.of("caja_id",cid,"fecha","2026-11-24","concepto","Papelería","valor","200")));
        update("/gastos-caja-menor/"+gid,aux,Map.of("valor","1200")).andExpect(status().isUnprocessableEntity());
        String cp="/cajas-menores/"+cid;Map<String,Object> event=Map.of("fecha","2026-11-24","responsable","Funcionario de prueba");
        for(int i=0;i<3;i++)create(cp+"/avanzar",h,event).andExpect(status().isOk());
        create(cp+"/avanzar",h,event).andExpect(status().isConflict());
        update("/gastos-caja-menor/"+gid,aux,Map.of("estado_revision","aprobado")).andExpect(status().isForbidden());
        update("/gastos-caja-menor/"+gid,h,Map.of("estado_revision","aprobado")).andExpect(status().isOk());
        for(int i=0;i<3;i++)create(cp+"/avanzar",h,event).andExpect(status().isOk());
        created(create("/reintegros-caja-menor",h,Map.of("caja_id",cid,"fecha","2026-11-24","valor","200","referencia","REC-JAVA","responsable","Apoyo financiero")));
        update(cp,h,Map.of("sobrante_consignado","1000")).andExpect(status().isOk());
        create(cp+"/avanzar",h,event).andExpect(status().isOk()).andExpect(jsonPath("$.estado").value("cierre"));
        mvc.perform(get("/api"+cp+"/resumen").header("Authorization",h)).andExpect(status().isOk()).andExpect(jsonPath("$.saldo").value(0));
        update("/gastos-caja-menor/"+gid,aux,Map.of("valor","10")).andExpect(status().isConflict());
        for(String tipo:List.of("certificado_conveniencia","certificado_disponibilidad","compromiso","informe_ejecucion","informe_pago","modificacion_presupuestal"))created(create("/presupuesto/solicitudes",h,Map.of("tipo",tipo,"fecha","2026-11-24","descripcion","Registro de prueba")));
        long oid=created(create("/presupuesto/solicitudes",h,Map.of("tipo","orden_pago","fecha","2026-11-24","descripcion","Orden de pago","valor","1000")));
        created(create("/presupuesto/descuentos",h,Map.of("orden_id",oid,"tipo","retencion_fuente","valor","100")));
        create("/presupuesto/descuentos",h,Map.of("orden_id",oid,"tipo","industria_comercio","valor","950")).andExpect(status().isUnprocessableEntity());
        long cv=created(create("/convenios",h,Map.of("numero","CV-JAVA","fecha_inicio","2026-02-01","nit","900000001","entidad","Entidad ficticia","valor_total","1000000")));
        String vp="/convenios/"+cv;create(vp+"/liquidar",h,event).andExpect(status().isConflict());
        for(String tipo:List.of("contrato","acta_liquidacion")){MockMultipartFile doc=new MockMultipartFile("archivo",tipo+".pdf","application/pdf","%PDF-1.4\n%%EOF".getBytes());mvc.perform(multipart("/api/documentos").file(doc).param("entidad","convenio").param("entidad_id",String.valueOf(cv)).param("tipo",tipo).header("Authorization",h)).andExpect(status().isCreated());}
        create(vp+"/enviar-contaduria",h,event).andExpect(status().isOk());create(vp+"/liquidar",h,event).andExpect(status().isOk());create(vp+"/enviar-liquidacion",h,event).andExpect(status().isOk());
        mvc.perform(get("/api/reportes/convenios?formato=xlsx").header("Authorization",h)).andExpect(status().isOk());
        byte[] pdf=mvc.perform(get("/api/reportes/peticiones?formato=pdf").header("Authorization",h)).andExpect(status().isOk()).andReturn().getResponse().getContentAsByteArray();assertTrue(new String(Arrays.copyOf(pdf,5)).startsWith("%PDF-"));
        mvc.perform(get("/api/reportes/convenios").header("Authorization",aux)).andExpect(status().isForbidden());
        mvc.perform(get("/api/panel/resumen").header("Authorization",h)).andExpect(status().isOk()).andExpect(jsonPath("$.peticiones").exists());
        mvc.perform(get("/api/auditoria").header("Authorization",h)).andExpect(status().isOk()).andExpect(jsonPath("$[0].usuario").exists());
    }
}
