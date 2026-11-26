package co.pereira.cultura;

public class ApiFailure extends RuntimeException {
    public final int status;
    public ApiFailure(int status,String message) { super(message); this.status=status; }
    static ApiFailure bad(String message) { return new ApiFailure(422,message); }
    static ApiFailure conflict(String message) { return new ApiFailure(409,message); }
    static ApiFailure forbidden() { return new ApiFailure(403,"Su rol no tiene permiso para esta operación"); }
    static ApiFailure missing() { return new ApiFailure(404,"Registro no encontrado"); }
    static ApiFailure unauthorized(String message) { return new ApiFailure(401,message); }
}
