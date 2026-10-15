"""ÇEVİR (CONVERT): ölçü birimi dönüştürme (işlev kitaplığı genişletmesi, 2026-10-15). Qt yok.
Tablo Excel'in en sık kullanılan birimlerini kapsar; olmayan birim `#YOK` verir (Excel gibi). Küçük/büyük harf duyarlıdır."""
from ...model import deger as D
from ...model.deger import Hata
from . import fonksiyon
from ..donustur import sayi_metninden
from .ortak import skaler

# birim: (grup, taban birime çarpan, SI öneki alabilir mi)
_B = {}


def _ekle(grup, tablo, onek=False):
    for ad, k in tablo.items():
        _B[ad] = (grup, k, onek)


_ekle("kütle", {"g": 1.0, "sg": 14593.90293720636, "lbm": 453.59237, "u": 1.660538782e-24, "ozm": 28.349523125,
                "grain": 0.06479891, "cwt": 45359.237, "shweight": 45359.237, "uk_cwt": 50802.34544, "lcwt": 50802.34544,
                "hweight": 50802.34544, "stone": 6350.29318, "ton": 907184.74, "uk_ton": 1016046.9088, "LTON": 1016046.9088,
                "brton": 1016046.9088}, True)
_ekle("uzunluk", {"m": 1.0, "mi": 1609.344, "Nmi": 1852.0, "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "ang": 1e-10,
                  "ell": 1.143, "ly": 9.46073047258e15, "parsec": 3.08567758146719e16, "pc": 3.0856775812815532e16,
                  "Pica": 0.0254 / 72, "pica": 0.0254 / 6, "survey_mi": 1609.3472186944373}, True)
_ekle("zaman", {"yr": 31557600.0, "day": 86400.0, "d": 86400.0, "hr": 3600.0, "mn": 60.0, "min": 60.0})
_ekle("zaman", {"sec": 1.0, "s": 1.0}, True)
_ekle("basınç", {"Pa": 1.0, "p": 1.0, "atm": 101325.0, "at": 101325.0, "mmHg": 133.322, "Torr": 133.322368421053,
                 "psi": 6894.757293168361}, True)
_ekle("kuvvet", {"N": 1.0, "dyn": 1e-5, "dy": 1e-5, "lbf": 4.4482216152605, "pond": 0.00980665}, True)
_ekle("enerji", {"J": 1.0, "e": 1e-7, "c": 4.184, "cal": 4.1868, "eV": 1.602176487e-19, "ev": 1.602176487e-19,
                 "HPh": 2684519.537696172, "hh": 2684519.537696172, "Wh": 3600.0, "wh": 3600.0, "flb": 1.3558179483314,
                 "BTU": 1055.05585262, "btu": 1055.05585262}, True)
_ekle("güç", {"W": 1.0, "w": 1.0, "HP": 745.69987158227, "h": 745.69987158227, "PS": 735.49875}, True)
_ekle("manyetik", {"T": 1.0, "ga": 1e-4}, True)
_ekle("hacim", {"l": 0.001, "L": 0.001, "lt": 0.001, "tsp": 4.92892159375e-6, "tspm": 5e-6, "tbs": 1.478676478125e-5,
                "oz": 2.95735295625e-5, "cup": 2.365882365e-4, "pt": 4.73176473e-4, "us_pt": 4.73176473e-4,
                "uk_pt": 5.6826125e-4, "qt": 9.46352946e-4, "uk_qt": 1.1365225e-3, "gal": 3.785411784e-3,
                "uk_gal": 4.54609e-3, "m3": 1.0, "ang3": 1e-30, "ly3": 8.46786664623715e47, "in3": 1.6387064e-5,
                "ft3": 0.028316846592, "yd3": 0.764554857984, "mi3": 4168181825.44058, "Nmi3": 6352182208.0,
                "barrel": 0.158987294928, "bushel": 0.03523907016688, "regton": 2.8316846592, "GRT": 2.8316846592,
                "MTON": 1.13267386368}, True)
_ekle("alan", {"m2": 1.0, "ha": 1e4, "ar": 100.0, "in2": 6.4516e-4, "ft2": 0.09290304, "yd2": 0.83612736,
               "mi2": 2589988.110336, "Nmi2": 3429904.0, "ang2": 1e-20, "uk_acre": 4046.8564224, "us_acre": 4046.872609874252,
               "Morgen": 2500.0, "Picapt2": (0.0254 / 72) ** 2}, True)
_ekle("hız", {"m/s": 1.0, "m/sec": 1.0, "m/h": 1 / 3600, "m/hr": 1 / 3600, "mph": 0.44704, "kn": 1852 / 3600,
              "admkn": 1852.0 / 3600, "ang/s": 1e-10}, True)
_ekle("bilgi", {"bit": 1.0, "byte": 8.0}, True)

_ONEK = {"Y": 1e24, "Z": 1e21, "E": 1e18, "P": 1e15, "T": 1e12, "G": 1e9, "M": 1e6, "k": 1e3, "h": 1e2, "da": 1e1,
         "e": 1e1, "d": 1e-1, "c": 1e-2, "m": 1e-3, "u": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15, "a": 1e-18,
         "z": 1e-21, "y": 1e-24}
_IKILI = {"Yi": 2.0 ** 80, "Zi": 2.0 ** 70, "Ei": 2.0 ** 60, "Pi": 2.0 ** 50, "Ti": 2.0 ** 40, "Gi": 2.0 ** 30,
          "Mi": 2.0 ** 20, "ki": 2.0 ** 10}
_SICAKLIK = {"C": "C", "cel": "C", "F": "F", "fah": "F", "K": "K", "kel": "K", "Rank": "Rank", "Reau": "Reau"}


def _coz(ad):
    if ad in _B:
        g, k, _ = _B[ad]
        return g, k
    # güç/uzunluk ... önekleri
    for n in (2, 1):
        if len(ad) > n:
            on, kalan = ad[:n], ad[n:]
            if kalan in _B and _B[kalan][2]:
                g, k, _ = _B[kalan]
                if g == "bilgi" and on in _IKILI:
                    return g, k * _IKILI[on]
                if on in _ONEK:
                    kat = _ONEK[on]
                    if g == "alan":
                        kat = kat ** 2
                    elif g == "hacim" and kalan == "m3":
                        kat = kat ** 3
                    elif g == "hacim" and kalan == "ang3":
                        kat = kat ** 3
                    return g, k * kat
    return None, None


def _sicaklik_c(x, b):
    return {"C": x, "F": (x - 32) * 5 / 9, "K": x - 273.15, "Rank": (x - 491.67) * 5 / 9,
            "Reau": x * 5 / 4}[b]


def _sicaklik_den(c, b):
    return {"C": c, "F": c * 9 / 5 + 32, "K": c + 273.15, "Rank": (c + 273.15) * 9 / 5,
            "Reau": c * 4 / 5}[b]


@skaler("CONVERT", "hmm")
def _convert(b, sayi, kaynak, hedef):
    if isinstance(sayi, Hata):
        return sayi
    if isinstance(sayi, bool) or isinstance(sayi, str):
        return D.DEGER_HATASI if isinstance(sayi, bool) else (D.DEGER_HATASI if sayi_metninden(sayi) is None
                                                              else _convert(b, sayi_metninden(sayi), kaynak, hedef))
    sayi = 0.0 if sayi is None else sayi
    if kaynak in _SICAKLIK and hedef in _SICAKLIK:
        return _sicaklik_den(_sicaklik_c(sayi, _SICAKLIK[kaynak]), _SICAKLIK[hedef])
    g1, k1 = _coz(kaynak)
    g2, k2 = _coz(hedef)
    if g1 is None or g2 is None or g1 != g2:
        return D.YOK
    return sayi * k1 / k2
