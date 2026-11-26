package co.pereira.cultura;

import java.util.Map;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.multipart.support.MissingServletRequestPartException;

@RestControllerAdvice
class ApiErrors {
    @ExceptionHandler(ApiFailure.class) ResponseEntity<Map<String,String>> api(ApiFailure e) {
        return ResponseEntity.status(e.status).body(Map.of("detail",e.getMessage()));
    }
    @ExceptionHandler(DataIntegrityViolationException.class) ResponseEntity<Map<String,String>> integrity() {
        return ResponseEntity.status(409).body(Map.of("detail","Registro duplicado o restricción de integridad incumplida"));
    }
    @ExceptionHandler({HttpMessageNotReadableException.class,MissingServletRequestParameterException.class,MethodArgumentTypeMismatchException.class,MissingServletRequestPartException.class})
    ResponseEntity<Map<String,String>> invalid() { return ResponseEntity.status(422).body(Map.of("detail","Datos de solicitud inválidos o incompletos")); }
    @ExceptionHandler(MaxUploadSizeExceededException.class) ResponseEntity<Map<String,String>> tooLarge() {
        return ResponseEntity.status(413).body(Map.of("detail","El archivo supera los 10 MB"));
    }
}
