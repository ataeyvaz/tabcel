"""Türkiye'ye özel işlevler (T7). Qt yok.

⚠ Bu işlevler Microsoft Excel'de YOKTUR: Tabcel'e özgüdür, Türkçe adları Microsoft listesinden doğrulanmış değildir
(`adlar.py` → "Tabcel'e özel"). `.xlsx`e kaydedilince başka programlarda `#AD?` verirler; kaydederken kullanıcıya
uyarı gösterilir (`xlsx_io.TABCEL_OZEL`).

- `YAZIYLA(sayı)`: sayıyı Türkçe yazıya çevirir. 125 → "yüz yirmi beş"; −3 → "eksi üç"; 2,05 → "iki virgül sıfır beş".
  |sayı| < 10^15 (katrilyon altı); ondalık basamaklar tek tek okunur (en çok 10 basamak).
- `TCKIMLIKDOGRULA(no)`: 11 haneli T.C. kimlik numarası algoritmasına uyuyorsa DOĞRU (yalnızca biçim/sağlama: kişi
  gerçekten var mı denetlenmez). Sayı ya da metin kabul eder (baştaki sıfır korunmuş metin).
"""
from ...model import deger as D
from . import fonksiyon  # noqa: F401
from .ortak import skaler

_BIRLER = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
_ONLAR = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]
_BASAMAKLAR = ["", "bin", "milyon", "milyar", "trilyon"]
MAKS_YAZI = 10 ** 15


def _uc_hane(n: int) -> str:
    y, o, b = n // 100, (n // 10) % 10, n % 10
    parca = []
    if y:
        parca.append("yüz" if y == 1 else _BIRLER[y] + " yüz")
    if o:
        parca.append(_ONLAR[o])
    if b:
        parca.append(_BIRLER[b])
    return " ".join(parca)


def tam_sayi_yazi(n: int) -> str:
    """0 ≤ n < 10^15 → Türkçe yazı ('bir bin' değil 'bin')."""
    if n == 0:
        return "sıfır"
    gruplar = []
    while n:
        gruplar.append(n % 1000)
        n //= 1000
    parca = []
    for i in range(len(gruplar) - 1, -1, -1):
        g = gruplar[i]
        if not g:
            continue
        if i == 1 and g == 1:
            parca.append("bin")                        # "bir bin" denmez
        else:
            parca.append(_uc_hane(g) + (" " + _BASAMAKLAR[i] if i else ""))
    return " ".join(parca)


def sayi_yazi(x: float) -> str:
    eksi = x < 0
    x = abs(x)
    tam = int(x)
    kesir = f"{x - tam:.10f}"[2:].rstrip("0")           # "0.0500000000" → "05"
    yazi = tam_sayi_yazi(tam)
    if kesir:
        yazi += " virgül " + " ".join("sıfır" if k == "0" else _BIRLER[int(k)] for k in kesir)
    return ("eksi " if eksi else "") + yazi


@skaler("YAZIYLA", "s")
def _yaziyla(b, x):
    if abs(x) >= MAKS_YAZI:
        return D.SAYI
    return sayi_yazi(x)


def tc_kimlik_gecerli_mi(no: str) -> bool:
    if len(no) != 11 or not no.isdigit() or no[0] == "0":
        return False
    d = [int(k) for k in no]
    if (sum(d[0:9:2]) * 7 - sum(d[1:8:2])) % 10 != d[9]:
        return False
    return sum(d[:10]) % 10 == d[10]


@skaler("TCKIMLIKDOGRULA", "m")
def _tc_dogrula(b, no):
    return tc_kimlik_gecerli_mi(no.strip())
