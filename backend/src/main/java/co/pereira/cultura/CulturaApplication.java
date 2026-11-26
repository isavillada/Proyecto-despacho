package co.pereira.cultura;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Bean;

@SpringBootApplication
public class CulturaApplication {
    public static void main(String[] args) { SpringApplication.run(CulturaApplication.class,args); }
    @Bean ApplicationRunner inicializar(AuthService auth) { return args -> auth.seed(); }
}
