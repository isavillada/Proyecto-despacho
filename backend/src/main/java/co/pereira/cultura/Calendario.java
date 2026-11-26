package co.pereira.cultura;

import java.time.*;
import java.time.temporal.TemporalAdjusters;
import java.util.HashSet;
import java.util.Set;

final class Calendario {
    private Calendario() {}
    static LocalDate hoy() { return LocalDate.now(ZoneId.of("America/Bogota")); }
    static LocalDate pascua(int y) {
        int a=y%19,b=y/100,c=y%100,d=b/4,e=b%4,f=(b+8)/25,g=(b-f+1)/3,h=(19*a+b-d-g+15)%30,i=c/4,k=c%4,l=(32+2*e+2*i-h-k)%7,m=(a+11*h+22*l)/451;
        return LocalDate.of(y,(h+l-7*m+114)/31,(h+l-7*m+114)%31+1);
    }
    static Set<LocalDate> festivos(int y) {
        Set<LocalDate> result=new HashSet<>();
        for(int[] x:new int[][]{{1,1},{5,1},{7,20},{8,7},{12,8},{12,25}}) result.add(LocalDate.of(y,x[0],x[1]));
        for(int[] x:new int[][]{{1,6},{3,19},{6,29},{8,15},{10,12},{11,1},{11,11}}) result.add(LocalDate.of(y,x[0],x[1]).with(TemporalAdjusters.nextOrSame(DayOfWeek.MONDAY)));
        LocalDate p=pascua(y); result.add(p.minusDays(3));result.add(p.minusDays(2));
        for(int n:new int[]{39,60,68}) result.add(p.plusDays(n).with(TemporalAdjusters.nextOrSame(DayOfWeek.MONDAY)));
        return result;
    }
    static LocalDate diasHabiles(LocalDate inicio,int n) {
        LocalDate d=inicio; Set<LocalDate> f=festivos(d.getYear()); int y=d.getYear();
        while(n>0){d=d.plusDays(1);if(d.getYear()!=y){y=d.getYear();f=festivos(y);}if(d.getDayOfWeek().getValue()<6&&!f.contains(d))n--;}
        return d;
    }
}
