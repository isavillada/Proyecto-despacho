"""Calendario de referencia para el seguimiento; el usuario puede registrar el plazo real.
No sustituye la verificación de términos por el responsable del trámite.
"""
import datetime as dt
from functools import lru_cache
from zoneinfo import ZoneInfo


def hoy():
    return dt.datetime.now(ZoneInfo("America/Bogota")).date()


def pascua(y):
    a=y%19; b=y//100; c=y%100; d=b//4; e=b%4; f=(b+8)//25
    g=(b-f+1)//3; h=(19*a+b-d-g+15)%30; i=c//4; k=c%4
    l=(32+2*e+2*i-h-k)%7; m=(a+11*h+22*l)//451
    return dt.date(y,(h+l-7*m+114)//31,(h+l-7*m+114)%31+1)


def lunes(d):
    return d+dt.timedelta(days=(-d.weekday())%7)


@lru_cache(maxsize=32)
def festivos(y):
    f={dt.date(y,m,d) for m,d in [(1,1),(5,1),(7,20),(8,7),(12,8),(12,25)]}
    f.update(lunes(dt.date(y,m,d)) for m,d in [(1,6),(3,19),(6,29),(8,15),(10,12),(11,1),(11,11)])
    p=pascua(y)
    f.update(p+dt.timedelta(days=n) for n in [-3,-2])
    f.update(lunes(p+dt.timedelta(days=n)) for n in [39,60,68])
    return f


def dias_habiles(inicio, n):
    d=inicio
    while n>0:
        d+=dt.timedelta(days=1)
        if d.weekday()<5 and d not in festivos(d.year): n-=1
    return d
