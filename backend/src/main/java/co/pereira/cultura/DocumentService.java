package co.pereira.cultura;

import java.io.IOException;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.zip.ZipFile;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.web.multipart.MultipartFile;

@Service
public class DocumentService {
    private static final long MAX=10L*1024*1024;
    private static final Set<String> EXT=Set.of("pdf","png","jpg","jpeg","docx","xlsx");
    private static final String PUBLIC="id,entidad,entidad_id,tipo,nombre_original,subido_por,subido_en";
    private final JdbcTemplate db;private final RecordsService records;private final AuthService auth;private final Path root;
    public DocumentService(JdbcTemplate db,RecordsService records,AuthService auth,@Value("${app.upload-dir}") String dir){this.db=db;this.records=records;this.auth=auth;this.root=Path.of(dir).toAbsolutePath().normalize();}
    List<Map<String,Object>> list(String entity,long id,AuthService.User u){RecordsService.Resource r=RecordsService.byDocument(entity);AuthService.require(u,r.module(),false);records.find(r,id,false);return db.queryForList("SELECT "+PUBLIC+" FROM documentos WHERE entidad=? AND entidad_id=? ORDER BY id DESC",entity,id);}
    private static boolean starts(byte[] data,int... signature){if(data.length<signature.length)return false;for(int i=0;i<signature.length;i++)if(Byte.toUnsignedInt(data[i])!=signature[i])return false;return true;}
    private static void validateSignature(String ext,byte[] data,Path temp) throws IOException {
        boolean ok=switch(ext){case "pdf"->starts(data,37,80,68,70,45);case "png"->starts(data,137,80,78,71,13,10,26,10);case "jpg","jpeg"->starts(data,255,216,255);case "docx","xlsx"->starts(data,80,75);default->false;};
        if(!ok)throw new ApiFailure(415,"El contenido no corresponde a la extensión declarada");
        if(ext.equals("docx")||ext.equals("xlsx")){try(ZipFile z=new ZipFile(temp.toFile())){if(z.getEntry(ext.equals("docx")?"word/document.xml":"xl/workbook.xml")==null)throw new ApiFailure(415,"Contenido Office inválido");}catch(java.util.zip.ZipException e){throw new ApiFailure(415,"Contenido Office inválido");}}
    }
    @Transactional(rollbackFor=Exception.class) public Map<String,Object> upload(String entity,long id,String type,MultipartFile file,AuthService.User u) throws IOException {
        RecordsService.Resource r=RecordsService.byDocument(entity);AuthService.require(u,r.module(),true);Map<String,Object> parent=records.find(r,id,true);
        if(entity.equals("caja_menor")&&parent.get("estado").equals("cierre"))throw ApiFailure.conflict("Caja cerrada");
        if(Set.of("gasto","reintegro").contains(entity)){Map<String,Object> c=records.find(RecordsService.resource("/cajas-menores"),RecordsService.id(parent.get("caja_id")),true);if(c.get("estado").equals("cierre"))throw ApiFailure.conflict("Caja cerrada");}
        if(entity.equals("convenio")&&parent.get("estado").equals("liquidado")&&Set.of("contrato","acta_liquidacion").contains(type))throw ApiFailure.conflict("Convenio liquidado; los soportes principales no se modifican");
        if(type==null||type.isBlank()||type.length()>40)throw ApiFailure.bad("Tipo documental inválido");
        if(file.isEmpty())throw ApiFailure.bad("Archivo vacío");if(file.getSize()>MAX)throw new ApiFailure(413,"Archivo superior a 10 MB");
        String original=Objects.requireNonNullElse(file.getOriginalFilename(),"archivo").replace('\\','/');original=original.substring(original.lastIndexOf('/')+1).replaceAll("[\\p{Cntrl}]","");if(original.length()>255||original.isBlank())throw ApiFailure.bad("Nombre de archivo inválido");int dot=original.lastIndexOf('.');String ext=dot<0?"":original.substring(dot+1).toLowerCase(Locale.ROOT);if(!EXT.contains(ext))throw new ApiFailure(415,"Extensión no permitida");
        Files.createDirectories(root);String name=UUID.randomUUID()+"."+ext;Path path=root.resolve(name);byte[] data=file.getBytes();if(data.length>MAX)throw new ApiFailure(413,"Archivo superior a 10 MB");
        try{Files.write(path,data,StandardOpenOption.CREATE_NEW);validateSignature(ext,data,path);
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization(){@Override public void afterCompletion(int status){if(status!=STATUS_COMMITTED)try{Files.deleteIfExists(path);}catch(IOException ignored){}}});
            Map<String,Object> row=db.queryForMap("INSERT INTO documentos(entidad,entidad_id,tipo,nombre_original,ruta,subido_por) VALUES (?,?,?,?,?,?) RETURNING "+PUBLIC,entity,id,type.strip(),original,name,u.username());auth.audit(u.username(),"SUBIR_DOCUMENTO","documentos",RecordsService.id(row.get("id")),entity+":"+id+" "+type);return row;
        }catch(IOException|RuntimeException e){Files.deleteIfExists(path);throw e;}
    }
    ResponseEntity<FileSystemResource> download(long id,AuthService.User u){Map<String,Object> d=db.queryForList("SELECT * FROM documentos WHERE id=?",id).stream().findFirst().orElseThrow(ApiFailure::missing);RecordsService.Resource r=RecordsService.byDocument((String)d.get("entidad"));AuthService.require(u,r.module(),false);Path path=root.resolve((String)d.get("ruta")).normalize();if(!path.startsWith(root)||!Files.isRegularFile(path))throw ApiFailure.missing();auth.audit(u.username(),"DESCARGAR_DOCUMENTO","documentos",id,null);return ResponseEntity.ok().header(HttpHeaders.CONTENT_DISPOSITION,ContentDisposition.attachment().filename((String)d.get("nombre_original"),StandardCharsets.UTF_8).build().toString()).contentType(MediaType.APPLICATION_OCTET_STREAM).body(new FileSystemResource(path));}
}
