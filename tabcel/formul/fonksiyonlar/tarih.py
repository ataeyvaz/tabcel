"""Tarih/saat fonksiyonları: 1900 tarih sistemi, Excel'in 1900 artık yıl hatasıyla (seri 60 =
29.2.1900, seri 0 = 0.1.1900). Qt yok. Metin tarihleri (`"1.1.2026"`) Faz 3'te çözülür; şimdilik
yalnız seri numaraları kabul edilir.
"""
import datetime as dt
import math

from ...model import deger as D
from ...model.deger import Hata
# seri ⇄ tarih yardımcıları model/ altında ortak (sayı biçimi de kullanır); adlar burada da geçerli
from ...model.tarihseri import (MAKS_SERI, TEMEL as _TEMEL, ay_gun_sayisi, ayin_ilki,  # noqa: F401
                                haftanin_gunu0, seri_ymd, ymd_seri)
from . import fonksiyon
from .ortak import duz, skaler


def _tarih_nesnesi(n: int) -> dt.date:
    """Tarih aritmetiği için gerçek takvim tarihi (seri 0 ve 60 komşu güne yuvarlanır)."""
    if n <= 0:
        return dt.date(1899, 12, 31)
    if n == 60:
        return dt.date(1900, 3, 1)
    return (dt.date(1899, 12, 31) + dt.timedelta(n)) if n < 60 else _TEMEL + dt.timedelta(n)


def _seri_kontrol(x: float):
    """Tarih kısmı (int) ya da #SAYI!."""
    if x < 0 or x >= MAKS_SERI + 1:
        return D.SAYI
    return int(math.floor(x))


@fonksiyon("TODAY", en_az=0, en_cok=0, degisken=True)
def _today(b):
    return float((dt.date.today() - _TEMEL).days)


@fonksiyon("NOW", en_az=0, en_cok=0, degisken=True)
def _now(b):
    simdi = dt.datetime.now()
    gun = (simdi.date() - _TEMEL).days
    saniye = simdi.hour * 3600 + simdi.minute * 60 + simdi.second + simdi.microsecond / 1e6
    return gun + saniye / 86400


@skaler("DATE", "sss")
def _date(b, y, m, g):
    y, m, g = math.trunc(y), math.trunc(m), math.trunc(g)
    if 0 <= y < 1900:
        y += 1900
    if y < 0 or y > 9999:
        return D.SAYI
    yy, mm = divmod(y * 12 + (m - 1), 12)
    if yy < 1900 or yy > 9999:
        return D.SAYI
    seri = ymd_seri(yy, mm + 1, 1) + (g - 1)
    if seri < 0 or seri > MAKS_SERI:
        return D.SAYI
    return float(seri)


@skaler("TIME", "sss")
def _time(b, h, m, s):
    h, m, s = math.trunc(h), math.trunc(m), math.trunc(s)
    if abs(h) > 32767 or abs(m) > 32767 or abs(s) > 32767:
        return D.SAYI
    toplam = h * 3600 + m * 60 + s
    if toplam < 0:                           # Excel (COM, 2026-10-15): TIME(1;-30;0) = 0:30; toplam eksiyse #SAYI!
        return D.SAYI
    return (toplam % 86400) / 86400


def _ymd_al(x):
    n = _seri_kontrol(x)
    return n if isinstance(n, Hata) else seri_ymd(n)


@skaler("YEAR", "s")
def _year(b, x):
    r = _ymd_al(x)
    return r if isinstance(r, Hata) else float(r[0])


@skaler("MONTH", "s")
def _month(b, x):
    r = _ymd_al(x)
    return r if isinstance(r, Hata) else float(r[1])


@skaler("DAY", "s")
def _day(b, x):
    r = _ymd_al(x)
    return r if isinstance(r, Hata) else float(r[2])


def _saniyeler(x: float):
    if x < 0 or x >= MAKS_SERI + 1:
        return D.SAYI
    kesir = x - math.floor(x)
    return int(round(kesir * 86400)) % 86400


@skaler("HOUR", "s")
def _hour(b, x):
    s = _saniyeler(x)
    return s if isinstance(s, Hata) else float(s // 3600)


@skaler("MINUTE", "s")
def _minute(b, x):
    s = _saniyeler(x)
    return s if isinstance(s, Hata) else float(s % 3600 // 60)


@skaler("SECOND", "s")
def _second(b, x):
    s = _saniyeler(x)
    return s if isinstance(s, Hata) else float(s % 60)


# hafta başlangıcı (0 = Pazar) türe göre
_HAFTA_BASI = {1: 0, 2: 1, 11: 1, 12: 2, 13: 3, 14: 4, 15: 5, 16: 6, 17: 0}


@skaler("WEEKDAY", "ss", en_az=1)
def _weekday(b, x, tur=1.0):
    n = _seri_kontrol(x)
    if isinstance(n, Hata):
        return n
    tur = math.trunc(tur)
    g = haftanin_gunu0(n)
    if tur == 3:
        return float((g - 1) % 7)
    if tur not in _HAFTA_BASI:
        return D.SAYI
    return float((g - _HAFTA_BASI[tur]) % 7 + 1)


@skaler("WEEKNUM", "ss", en_az=1)
def _weeknum(b, x, tur=1.0):
    n = _seri_kontrol(x)
    if isinstance(n, Hata):
        return n
    tur = math.trunc(tur)
    if tur == 21:
        return float(_tarih_nesnesi(n).isocalendar()[1])
    if tur not in _HAFTA_BASI:
        return D.SAYI
    y = seri_ymd(n)[0]
    bas = ayin_ilki(y, 1)
    kayma = (haftanin_gunu0(bas) - _HAFTA_BASI[tur]) % 7
    return float((n - bas + kayma) // 7 + 1)


def _gercek_ay_gun(y: int, m: int) -> int:
    """Gerçek takvimdeki ay uzunluğu (Şubat 1900 = 28): Excel'in EDATE/EOMONTH'u ay sonuna kırparken sahte
    29 Şubat 1900'ü saymaz (COM ile doğrulandı: EOMONTH(40;0) = 59)."""
    return 28 if (y == 1900 and m == 2) else ay_gun_sayisi(y, m)


def ay_ekle(n: int, aylar: int):
    """n tarihine `aylar` ay ekler (gün ay sonunu aşarsa kırpılır) → seri ya da #SAYI!."""
    y, m, g = seri_ymd(n)
    yy, mm = divmod(y * 12 + (m - 1) + aylar, 12)
    if yy < 1900 or yy > 9999:
        return D.SAYI
    mm += 1
    if n == 0:                               # 0 = "0 Ocak 1900": gün 0 korunur (EDATE(0;1) = 31)
        seri = ymd_seri(yy, mm, 1) - 1
    else:
        seri = ymd_seri(yy, mm, min(max(g, 1), _gercek_ay_gun(yy, mm)))
    return float(seri) if 0 <= seri <= MAKS_SERI else D.SAYI


@skaler("EDATE", "ss")
def _edate(b, x, aylar):
    n = _seri_kontrol(x)
    return n if isinstance(n, Hata) else ay_ekle(n, math.trunc(aylar))


@skaler("EOMONTH", "ss")
def _eomonth(b, x, aylar):
    n = _seri_kontrol(x)
    if isinstance(n, Hata):
        return n
    y, m, _ = seri_ymd(n)
    yy, mm = divmod(y * 12 + (m - 1) + math.trunc(aylar), 12)
    if yy < 1900 or yy > 9999:
        return D.SAYI
    mm += 1
    seri = ymd_seri(yy, mm, _gercek_ay_gun(yy, mm))
    return float(seri) if 0 <= seri <= MAKS_SERI else D.SAYI


@skaler("DATEDIF", "ssm")
def _datedif(b, bas, son, birim):
    n1, n2 = _seri_kontrol(bas), _seri_kontrol(son)
    for n in (n1, n2):
        if isinstance(n, Hata):
            return n
    if n2 < n1:
        return D.SAYI
    y1, m1, g1 = seri_ymd(n1)
    y2, m2, g2 = seri_ymd(n2)
    # Türkçe belge örnekleri birimi "G" (gün) ve "YG" (yıl yok sayılarak gün) yazıyor
    # (support.microsoft.com/tr-tr/excel/functions/datedif-function); "AG" (MD) doğrulanmadı → §8b-23
    birim = {"G": "D", "YG": "YD"}.get(birim.upper(), birim.upper())
    ay_farki = (y2 - y1) * 12 + (m2 - m1) - (1 if g2 < g1 else 0)
    if birim == "Y":
        return float(ay_farki // 12)
    if birim == "M":
        return float(ay_farki)
    if birim == "D":
        return float(n2 - n1)
    if birim == "YM":
        return float(ay_farki % 12)
    if birim == "MD":
        if g2 >= g1:
            return float(g2 - g1)
        yo, mo = (y2, m2 - 1) if m2 > 1 else (y2 - 1, 12)
        return float(g2 - g1 + ay_gun_sayisi(yo, mo))
    if birim == "YD":
        def yil_donumu(yil):                 # Excel (COM): 29 Şubat'ın artık olmayan yıldaki dönümü 1 Mart
            if m1 == 2 and g1 == 29 and ay_gun_sayisi(yil, 2) < 29:
                return ymd_seri(yil, 3, 1)
            return ymd_seri(yil, m1, min(g1, ay_gun_sayisi(yil, m1)))
        yil = y2
        if yil_donumu(yil) > n2:
            yil -= 1
        return float(n2 - yil_donumu(yil))
    return D.SAYI


@skaler("DAYS", "ss")
def _days(b, son, bas):
    n2, n1 = _seri_kontrol(son), _seri_kontrol(bas)
    for n in (n1, n2):
        if isinstance(n, Hata):
            return n
    return float(n2 - n1)


def _tatiller(v):
    """Tatil listesi (küme) ya da hata."""
    cikti = set()
    for x in duz(v):
        if isinstance(x, Hata):
            return x
        if isinstance(x, float) and not isinstance(x, bool):
            cikti.add(int(math.floor(x)))
        elif x is not None:
            return D.DEGER_HATASI
    return cikti


def _is_gunu(n: int, tatil) -> bool:
    return haftanin_gunu0(n) not in (0, 6) and n not in tatil


@fonksiyon("NETWORKDAYS", en_az=2, en_cok=3)
def _networkdays(b, bas, son, tatil=None):
    from .ortak import ham
    from ..donustur import sayiya
    n1, n2 = sayiya(ham(bas)), sayiya(ham(son))
    for x in (n1, n2):
        if isinstance(x, Hata):
            return x
    n1, n2 = _seri_kontrol(n1), _seri_kontrol(n2)
    for n in (n1, n2):
        if isinstance(n, Hata):
            return n
    t = _tatiller(tatil) if tatil is not None else set()
    if isinstance(t, Hata):
        return t
    isaret, a, z = (1, n1, n2) if n1 <= n2 else (-1, n2, n1)
    return float(isaret * sum(1 for n in range(a, z + 1) if _is_gunu(n, t)))


@fonksiyon("WORKDAY", en_az=2, en_cok=3)
def _workday(b, bas, gun, tatil=None):
    from .ortak import ham
    from ..donustur import sayiya
    n1, k = sayiya(ham(bas)), sayiya(ham(gun))
    for x in (n1, k):
        if isinstance(x, Hata):
            return x
    n = _seri_kontrol(n1)
    if isinstance(n, Hata):
        return n
    t = _tatiller(tatil) if tatil is not None else set()
    if isinstance(t, Hata):
        return t
    k = math.trunc(k)
    adim = 1 if k >= 0 else -1
    kalan = abs(k)
    while kalan:
        n += adim
        if n < 0 or n > MAKS_SERI:
            return D.SAYI
        if _is_gunu(n, t):
            kalan -= 1
    return float(n)
