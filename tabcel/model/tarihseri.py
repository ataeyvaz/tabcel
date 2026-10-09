"""Excel 1900 tarih sistemi: seri numarası ⇄ (yıl, ay, gün). Qt yok, `formul/`'a bağımlılık yok.

Excel'in 1900 artık yıl hatası bilerek korunur: seri 60 = 29.2.1900 (var olmayan gün),
seri 0 = 0.1.1900. Hem formül fonksiyonları (`formul/fonksiyonlar/tarih.py`) hem sayı biçimi
(`model/sayi_bicimi.py`) hem de akıllı giriş buradan kullanır (CLAUDE.md kural 2: `model/`
`formul/`'u içe aktarmasın diye ortak yardımcılar burada durur).
"""
import calendar
import datetime as dt

TEMEL = dt.date(1899, 12, 30)       # seri 61 ve sonrası için gerçek takvim kayması
MAKS_SERI = 2958465                 # 31.12.9999


def ay_gun_sayisi(y: int, m: int) -> int:
    if y == 1900 and m == 2:
        return 29                   # Excel'in hatası
    return calendar.monthrange(y, m)[1]


def ayin_ilki(y: int, m: int) -> int:
    """y/m/1 seri numarası (y ≥ 1900)."""
    if y == 1900 and m == 1:
        return 1
    if y == 1900 and m == 2:
        return 32
    return (dt.date(y, m, 1) - TEMEL).days


def seri_ymd(n: int):
    """Seri numarası → (yıl, ay, gün)."""
    if n == 0:
        return 1900, 1, 0
    if n == 60:
        return 1900, 2, 29
    d = (dt.date(1899, 12, 31) + dt.timedelta(n)) if n < 60 else TEMEL + dt.timedelta(n)
    return d.year, d.month, d.day


def ymd_seri(y: int, m: int, g: int) -> int:
    return ayin_ilki(y, m) + g - 1


def haftanin_gunu0(n: int) -> int:
    """0 = Pazar … 6 = Cumartesi (Excel'in seri→gün eşlemesi; seri 1 = Pazar)."""
    return (n - 1) % 7
