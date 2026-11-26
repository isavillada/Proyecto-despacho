package co.pereira.cultura;

import org.junit.jupiter.api.Test;
import java.time.LocalDate;
import static org.junit.jupiter.api.Assertions.*;

class CalendarioTest {
    @Test void calendarioReferencia(){
        assertEquals(LocalDate.of(2026,12,15),Calendario.diasHabiles(LocalDate.of(2026,11,23),15));
        assertEquals(LocalDate.of(2026,12,9),Calendario.diasHabiles(LocalDate.of(2026,12,7),1));
        assertEquals(LocalDate.of(2027,1,4),Calendario.diasHabiles(LocalDate.of(2026,12,31),1));
    }
}
