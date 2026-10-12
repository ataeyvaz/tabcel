"""Türkiye'ye özel işlevler (T7). Qt yok.

⚠ Bu işlevler Microsoft Excel'de YOKTUR: Tabcel'e özgüdür, Türkçe adları Microsoft listesinden doğrulanmış değildir
(`adlar.py` → "Tabcel'e özel"). `.xlsx`e kaydedilince başka programlarda `#AD?` verirler; kaydederken kullanıcıya
uyarı gösterilir (`xlsx_io.TABCEL_OZEL`).

- `YAZIYLA(sayı)`: sayıyı Türkçe yazıya çevirir. 125 → "yüz yirmi beş"; −3 → "eksi üç"; 2,05 → "iki virgül sıfır beş".
  |sayı| < 10^15 (katrilyon altı); ondalık basamaklar tek tek okunur (en çok 10 basamak).
- `TRNETWORKDAYS`/`TRWORKDAY` (`TRTAMİŞGÜNÜ`/`TRİŞGÜNÜ`): `TAMİŞGÜNÜ`/`İŞGÜNÜ` gibi, ama Türkiye resmî tatillerini
  (`tabcel/veri/resmi_tatiller.json`) kendiliğinden eler; ek tatil listesi isteğe bağlı. Arife yarım gün tam iş günü sayılır.
  Veri kapsamı dışındaki yıllar `#SAYI!`. Excel'in `TAMİŞGÜNÜ`/`İŞGÜNÜ` davranışı (kural 7) değişmez.
- `TCKIMLIKDOGRULA(no)`: 11 haneli T.C. kimlik numarası algoritmasına uyuyorsa DOĞRU (yalnızca biçim/sağlama: kişi
  gerçekten var mı denetlenmez). Sayı ya da metin kabul eder (baştaki sıfır korunmuş metin).
"""
from ...model import deger as D
from ...model.deger import Hata
from ...model import kimlik, tatiller as _tatil_verisi
from ...model.tarihseri import MAKS_SERI, seri_ymd
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


@skaler("TR_NUMBERTOWORDS", "s")
def _yaziyla(b, x):
    if abs(x) >= MAKS_YAZI:
        return D.SAYI
    return sayi_yazi(x)


tc_kimlik_gecerli_mi = kimlik.tc_gecerli                  # algoritma tek kaynakta (kural 18); eski ad korunur


@skaler("TR_VALIDATE_TCKN", "m")
def _tc_dogrula(b, no):
    return tc_kimlik_gecerli_mi(no.strip())


@skaler("TR_VALIDATE_VKN", "m")
def _vkn_dogrula(b, no):
    """Vergi kimlik no sağlaması (10 hane; sayı olarak yazılmış baştaki sıfırı kaybetmiş değerler de zorlanmaz)."""
    return kimlik.vkn_gecerli(no.strip())


@skaler("TR_VALIDATE_IBAN", "m")
def _iban_dogrula(b, iban):
    """TR IBAN: 26 karakter, mod-97; boşluklu/tireli yazım kabul."""
    return kimlik.iban_gecerli(iban)


@skaler("TR_VALIDATE_PHONE", "m")
def _telefon_dogrula(b, tel):
    """Türkiye telefonu: +90/0090/0 ön ekli ya da 10 haneli; cep (5xx), sabit (2xx/3xx/4xx), 850."""
    return kimlik.telefon_gecerli(tel)


@skaler("TR_VALIDATE_EMAIL", "m")
def _eposta_dogrula(b, adres):
    """E-posta adresi biçimi (adresin var olup olmadığı denetlenmez)."""
    return kimlik.eposta_gecerli(adres)


def _ek_tatiller(ek):
    """Resmî tatiller + isteğe bağlı ek liste (küme) ya da hata."""
    from .tarih import _tatiller
    t = _tatiller(ek) if ek is not None else set()
    if isinstance(t, Hata):
        return t
    return t | _tatil_verisi.tatiller()


@fonksiyon("TR_NETWORKDAYS", en_az=2, en_cok=3)
def _tr_networkdays(b, bas, son, ek=None):
    from .ortak import ham
    from ..donustur import sayiya
    from .tarih import _is_gunu, _seri_kontrol
    n1, n2 = sayiya(ham(bas)), sayiya(ham(son))
    for x in (n1, n2):
        if isinstance(x, Hata):
            return x
    n1, n2 = _seri_kontrol(n1), _seri_kontrol(n2)
    for n in (n1, n2):
        if isinstance(n, Hata):
            return n
    t = _ek_tatiller(ek)
    if isinstance(t, Hata):
        return t
    if not _tatil_verisi.kapsiyor_mu(n1, n2):
        return D.SAYI                                   # tatil verisi olmayan yılda sessizce yanlış sayma
    isaret, a, z = (1, n1, n2) if n1 <= n2 else (-1, n2, n1)
    return float(isaret * sum(1 for n in range(a, z + 1) if _is_gunu(n, t)))


@fonksiyon("TR_WORKDAY", en_az=2, en_cok=3)
def _tr_workday(b, bas, gun, ek=None):
    import math
    from .ortak import ham
    from ..donustur import sayiya
    from .tarih import _is_gunu, _seri_kontrol
    n1, k = sayiya(ham(bas)), sayiya(ham(gun))
    for x in (n1, k):
        if isinstance(x, Hata):
            return x
    n = _seri_kontrol(n1)
    if isinstance(n, Hata):
        return n
    t = _ek_tatiller(ek)
    if isinstance(t, Hata):
        return t
    ilk, son = _tatil_verisi.yil_araligi()
    k = math.trunc(k)
    adim = 1 if k >= 0 else -1
    kalan = abs(k)
    if not ilk <= seri_ymd(n)[0] <= son:
        return D.SAYI
    while kalan:
        n += adim
        if n < 0 or n > MAKS_SERI or not ilk <= seri_ymd(n)[0] <= son:
            return D.SAYI
        if _is_gunu(n, t):
            kalan -= 1
    return float(n)
