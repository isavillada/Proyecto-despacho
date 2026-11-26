package co.pereira.cultura;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.core.type.TypeReference;
import jakarta.servlet.http.HttpServletRequest;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.*;
import javax.crypto.Mac;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AuthService {
    static final Set<String> ROLES=Set.of("admin","secretario","secretaria_ejecutiva","auxiliar_administrativo","abogado_delegado","profesional_presupuesto","profesional_universitario","tecnico_administrativo","apoyo_financiero");
    static final Map<String,Set<String>> WRITE=Map.of(
        "peticiones",Set.of("secretaria_ejecutiva","secretario","abogado_delegado"),
        "caja_menor",Set.of("auxiliar_administrativo","abogado_delegado","secretario","apoyo_financiero"),
        "presupuesto",Set.of("profesional_presupuesto","auxiliar_administrativo","profesional_universitario","tecnico_administrativo"),
        "convenios",Set.of("secretario"));
    static final String PUBLIC_COLS="id,username,full_name,role,activo";
    static final int ITER=600000;
    private final JdbcTemplate db;
    private final ObjectMapper json;
    private final byte[] secret;
    private final String adminPassword;
    private final SecureRandom random=new SecureRandom();
    record User(long id,String username,String fullName,String role,boolean active,int version) {}
    public AuthService(JdbcTemplate db,ObjectMapper json,@Value("${app.secret}") String secret,@Value("${app.admin-password}") String adminPassword) {
        this.db=db;this.json=json;this.secret=secret.getBytes(StandardCharsets.UTF_8);this.adminPassword=adminPassword;
        if(this.secret.length<32) throw new IllegalStateException("Configure APP_SECRET con al menos 32 bytes aleatorios");
    }
    @Transactional public void seed() {
        if(db.queryForObject("SELECT count(*) FROM usuarios",Long.class)==0){
            validatePassword(adminPassword);
            db.update("INSERT INTO usuarios(username,full_name,role,password_hash) VALUES (?,?,?,?)","admin","Administrador","admin",hash(adminPassword));
            audit("admin","CREAR","usuarios",null,"Cuenta inicial");
        }
    }
    static void validatePassword(String p) {
        if(p==null||p.length()<10||p.length()>128||!p.matches("(?s).*[A-Z].*")||!p.matches("(?s).*[a-z].*")||!p.matches("(?s).*\\d.*")||!p.matches("(?s).*[\\p{Punct}].*"))
            throw ApiFailure.bad("La contraseña requiere 10–128 caracteres, mayúscula, minúscula, número y símbolo");
    }
    private byte[] derive(String p,byte[] salt,int n) {
        PBEKeySpec spec=new PBEKeySpec(p.toCharArray(),salt,n,256);
        try {return SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).getEncoded();}
        catch(Exception e){throw new IllegalStateException("Error de seguridad",e);}finally{spec.clearPassword();}
    }
    private String hash(String p) {byte[] salt=new byte[16];random.nextBytes(salt);return "pbkdf2$"+ITER+"$"+HexFormat.of().formatHex(salt)+"$"+HexFormat.of().formatHex(derive(p,salt,ITER));}
    private boolean verify(String p,String encoded) {
        if(p==null||p.length()>128)return false;
        try{String[] v=encoded.split("\\$");int n=Integer.parseInt(v[1]);if(!v[0].equals("pbkdf2")||n<100000||n>2000000)return false;return MessageDigest.isEqual(derive(p,HexFormat.of().parseHex(v[2]),n),HexFormat.of().parseHex(v[3]));}catch(RuntimeException e){return false;}
    }
    private String b64(byte[] b){return Base64.getUrlEncoder().withoutPadding().encodeToString(b);}
    private byte[] sign(String data){try{Mac m=Mac.getInstance("HmacSHA256");m.init(new SecretKeySpec(secret,"HmacSHA256"));return m.doFinal(data.getBytes(StandardCharsets.US_ASCII));}catch(Exception e){throw new IllegalStateException(e);}}
    private String token(User u){try{String header=b64("{\"alg\":\"HS256\",\"typ\":\"JWT\"}".getBytes(StandardCharsets.UTF_8));String payload=b64(json.writeValueAsBytes(Map.of("sub",u.username,"ver",u.version,"exp",Instant.now().plusSeconds(8*3600).getEpochSecond())));String body=header+"."+payload;return body+"."+b64(sign(body));}catch(Exception e){throw new IllegalStateException(e);}}
    private User toUser(Map<String,Object> row){return new User(((Number)row.get("id")).longValue(),(String)row.get("username"),(String)row.get("full_name"),(String)row.get("role"),Boolean.TRUE.equals(row.get("activo")),((Number)row.get("token_version")).intValue());}
    private Map<String,Object> find(String username){return db.queryForList("SELECT * FROM usuarios WHERE username=?",username).stream().findFirst().orElse(null);}
    User current(HttpServletRequest request){
        String auth=request.getHeader("Authorization"); if(auth==null||!auth.startsWith("Bearer "))throw ApiFailure.unauthorized("Debe iniciar sesión");
        String raw=auth.substring(7);if(raw.length()>4096)throw ApiFailure.unauthorized("Token inválido");
        try{String[] p=raw.split("\\.");if(p.length!=3||!MessageDigest.isEqual(sign(p[0]+"."+p[1]),Base64.getUrlDecoder().decode(p[2])))throw new IllegalArgumentException();
            Map<String,Object> c=json.readValue(Base64.getUrlDecoder().decode(p[1]),new TypeReference<Map<String,Object>>(){});
            if(((Number)c.get("exp")).longValue()<=Instant.now().getEpochSecond())throw new IllegalArgumentException();
            Map<String,Object> row=find((String)c.get("sub"));if(row==null)throw new IllegalArgumentException();User u=toUser(row);
            if(!u.active||u.version!=((Number)c.get("ver")).intValue())throw new IllegalArgumentException();return u;
        }catch(Exception e){throw ApiFailure.unauthorized("Token inválido o expirado");}
    }
    // Login audit is committed independently of a failed authentication.
    public Map<String,Object> login(String username,String password){
        String safe=username==null?"":username.substring(0,Math.min(username.length(),80));
        if(db.queryForObject("SELECT count(*) FROM auditoria WHERE usuario=? AND accion='LOGIN_FALLIDO' AND ts>=CURRENT_TIMESTAMP-INTERVAL '10 minutes'",Long.class,safe)>=10)throw new ApiFailure(429,"Demasiados intentos. Intente nuevamente en unos minutos.");
        Map<String,Object> row=find(safe);
        if(row==null||!Boolean.TRUE.equals(row.get("activo"))||!verify(password,(String)row.get("password_hash"))){audit(safe,"LOGIN_FALLIDO",null,null,null);throw ApiFailure.unauthorized("Credenciales incorrectas");}
        User u=toUser(row);audit(u.username,"LOGIN_EXITOSO",null,null,null);return Map.of("access_token",token(u),"token_type","bearer","role",u.role);
    }
    void audit(String user,String action,String entity,Long id,String detail){db.update("INSERT INTO auditoria(usuario,accion,entidad,entidad_id,detalle) VALUES (?,?,?,?,?)",user,action,entity,id,detail);}
    static boolean allowed(User u,String module,boolean write){if(u.role.equals("admin"))return true;Set<String> r=WRITE.getOrDefault(module,Set.of());return r.contains(u.role)||(!write&&u.role.equals("secretario"));}
    static void require(User u,String module,boolean write){if(!allowed(u,module,write))throw ApiFailure.forbidden();}
    static void role(User u,String... roles){if(!u.role.equals("admin")&&!Arrays.asList(roles).contains(u.role))throw ApiFailure.forbidden();}
    Map<String,Object> permisos(User u){Map<String,Object> p=new LinkedHashMap<>();for(String m:WRITE.keySet())p.put(m,Map.of("leer",allowed(u,m,false),"escribir",allowed(u,m,true)));return p;}
    Map<String,Object> me(User u){return Map.of("id",u.id,"username",u.username,"full_name",u.fullName,"role",u.role,"activo",u.active);}
    List<Map<String,Object>> users(User u){role(u);return db.queryForList("SELECT "+PUBLIC_COLS+" FROM usuarios ORDER BY id");}
    static String string(Map<String,Object> data,String field,int max,boolean required){Object v=data.get(field);if(v==null){if(required)throw ApiFailure.bad("Indique "+field);return null;}if(!(v instanceof String s))throw ApiFailure.bad("Valor inválido: "+field);s=s.strip();if(s.isEmpty()&&required)throw ApiFailure.bad("Indique "+field);if(s.length()>max)throw ApiFailure.bad("Valor demasiado largo: "+field);return s.isEmpty()?null:s;}
    static void fields(Map<String,Object> data,Set<String> valid){if(!valid.containsAll(data.keySet()))throw ApiFailure.bad("Campos no admitidos en la solicitud");}
    @Transactional public Map<String,Object> create(User u,Map<String,Object> data){role(u);fields(data,Set.of("username","full_name","role","password"));String name=string(data,"username",80,true),full=string(data,"full_name",150,true),role=string(data,"role",40,true),p=data.get("password") instanceof String v?v:null;
        if(name.length()<3||!ROLES.contains(role))throw ApiFailure.bad("Usuario o rol inválido");validatePassword(p);Map<String,Object> row=db.queryForMap("INSERT INTO usuarios(username,full_name,role,password_hash) VALUES(?,?,?,?) RETURNING "+PUBLIC_COLS,name,full,role,hash(p));audit(u.username,"CREAR","usuarios",((Number)row.get("id")).longValue(),"Cuenta creada: "+name+" ("+role+")");return row;
    }
    @Transactional public Map<String,Object> update(User u,long id,Map<String,Object> data){role(u);fields(data,Set.of("full_name","role","activo","password"));Map<String,Object> row=db.queryForList("SELECT * FROM usuarios WHERE id=? FOR UPDATE",id).stream().findFirst().orElseThrow(ApiFailure::missing);
        String name=data.containsKey("full_name")?string(data,"full_name",150,true):(String)row.get("full_name");String role=data.containsKey("role")?string(data,"role",40,true):(String)row.get("role");Object active=data.getOrDefault("activo",row.get("activo"));if(!ROLES.contains(role)||!(active instanceof Boolean))throw ApiFailure.bad("Rol o estado inválido");if(id==u.id&&(!role.equals("admin")||!Boolean.TRUE.equals(active)))throw ApiFailure.conflict("No puede retirar sus propios permisos de administración");
        String hashed=(String)row.get("password_hash");boolean revoke=!Objects.equals(role,row.get("role"))||!Objects.equals(active,row.get("activo"));if(data.containsKey("password")){String p=data.get("password") instanceof String s?s:null;validatePassword(p);hashed=hash(p);revoke=true;}
        Map<String,Object> out=db.queryForMap("UPDATE usuarios SET full_name=?,role=?,activo=?,password_hash=?,token_version=token_version+? WHERE id=? RETURNING "+PUBLIC_COLS,name,role,active,hashed,revoke?1:0,id);audit(u.username,"MODIFICAR","usuarios",id,"Actualización de cuenta");return out;
    }
    @Transactional public Map<String,Object> changePassword(User u,Map<String,Object> data){fields(data,Set.of("actual","nueva"));String current=data.get("actual") instanceof String p?p:null;String next=data.get("nueva") instanceof String p?p:null;Map<String,Object> row=db.queryForMap("SELECT * FROM usuarios WHERE id=? FOR UPDATE",u.id);if(!verify(current,(String)row.get("password_hash")))throw ApiFailure.bad("Contraseña actual incorrecta");validatePassword(next);db.update("UPDATE usuarios SET password_hash=?,token_version=token_version+1 WHERE id=?",hash(next),u.id);audit(u.username,"CAMBIO_CLAVE","usuarios",u.id,null);return Map.of("ok",true);}
    List<Map<String,Object>> auditList(User u,String user,String entity,int limit){role(u,"secretario");if(limit<1||limit>1000)throw ApiFailure.bad("Límite inválido");String sql="SELECT ts,usuario,accion,entidad,entidad_id,detalle FROM auditoria WHERE 1=1";List<Object> args=new ArrayList<>();if(user!=null&&!user.isBlank()){sql+=" AND usuario=?";args.add(user);}if(entity!=null&&!entity.isBlank()){sql+=" AND entidad=?";args.add(entity);}sql+=" ORDER BY id DESC LIMIT ?";args.add(limit);return db.queryForList(sql,args.toArray());}
}
