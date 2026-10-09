"""Excel sayı biçimi kodları: çözümleme, biçimleme, kanonik ⇄ yerel çeviri. Qt yok.

Kod iki dilde yazılabilir (CLAUDE.md kural 3'ün sayı biçimi karşılığı):
- **kanonik** (.xlsx'te ve modelde saklanan, en-US ayırıcılı): ``#,##0.00``, ``dd.mm.yyyy``, ``[Red]``
- **yerel** (Türkçe kullanıcıya gösterilen/yazdırılan): ``#.##0,00``, ``gg.aa.yyyy``, ``[Kırmızı]``

Ekrandaki sonuç her zaman Türkçe yerel ayarla üretilir (ondalık ``,``, binlik ``.``, Türkçe ay/gün adları).

Belirsizlikler (surec.md §8b'ye aktarılacak, kodda varsayım):
- Türkçe tarih kodu harfleri: gün ``g``, ay ``a`` Microsoft tr-tr kılavuzunda ("Bir sayı biçimini
  özelleştirmeyle ilgili kuralları inceleme") geçiyor; ama aynı sayfa saat/dakika/saniye için çelişkili
  (``s``/``ss`` saat, ``a``/``d`` dakika, ``sn`` saniye). Bu yüzden yerel kodda saat ``h``, dakika ``m``,
  saniye ``s`` (kanonik harfler) kullanılır; ``d`` gün olarak da kabul edilir (sayfa "g veya d" diyor).
- ``AM/PM`` ekranda ``ÖÖ``/``ÖS`` (Windows tr-TR belirteçleri); Excel'in Türkçe sürümündeki çıktı doğrulanmadı.
- Ay/gün kısaltmaları Windows tr-TR yerel ayarından (bu makinede ``strftime`` ile okundu: Oca, Şub…;
  Pzt, Sal…); Excel'in aynısını kullandığı doğrulanmadı.
- Negatif değerin sıfıra yuvarlandığı durum (``-0,4`` → ``0`` kodunda ``-0``), koşullu bölümlerde eksi
  işareti, hiçbir koşula uymayan değer (``####``), metne ilk bölümün rengi uygulanır mı.
"""
import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from functools import lru_cache
from typing import List, NamedTuple, Optional, Tuple

from .deger import Hata
from .gosterim import goster, sayiyi_sigdir
from .tarihseri import MAKS_SERI, haftanin_gunu0, seri_ymd


class BicimHatasi(ValueError):
    """Geçersiz sayı biçimi kodu (Excel "kullanılamaz sayı biçimi" uyarısının karşılığı)."""


SOL, SAG, ORTA = "sol", "sag", "orta"

# ------------------------------------------------------------------ yerel ayar (Türkçe)
ONDALIK, BINLIK = ",", "."
# Kesin (Türkçe takvim adları)
AYLAR = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül",
         "Ekim", "Kasım", "Aralık")
GUNLER = ("Pazar", "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi")  # 0 = Pazar
# BELİRSİZ (§8b): Windows tr-TR kısaltmaları (GetLocaleInfo/strftime); Excel'deki çıktı doğrulanmadı
AY_KISA = ("Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara")
GUN_KISA = ("Paz", "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt")
OO, OS = "ÖÖ", "ÖS"           # BELİRSİZ (§8b): Windows tr-TR AM/PM belirteçleri

# Renkler: İngilizce adlar Excel'in kanonik adları; Türkçe adlar Microsoft tr-tr kılavuzunda
# ("Bir sayı biçimini özelleştirmeyle ilgili kuralları inceleme") geçen sekiz ad — doğrulandı.
_RENKLER = (  # (kanonik, Türkçe, #rrggbb)
    ("Black", "Siyah", "#000000"), ("Green", "Yeşil", "#00FF00"), ("White", "Beyaz", "#FFFFFF"),
    ("Blue", "Mavi", "#0000FF"), ("Magenta", "Eflatun", "#FF00FF"), ("Yellow", "Sarı", "#FFFF00"),
    ("Cyan", "Camgöbeği", "#00FFFF"), ("Red", "Kırmızı", "#FF0000"),
)


def _tr_kucuk(s: str) -> str:
    return s.replace("I", "ı").replace("İ", "i").lower()


_RENK_ADI = {}
for _en, _tr, _hex in _RENKLER:
    _RENK_ADI[_en.lower()] = (_en, _tr, _hex)
    _RENK_ADI[_tr_kucuk(_tr)] = (_en, _tr, _hex)

# [ColorN] (N = 1..56): Excel'in varsayılan 56 renklik paleti (BIFF dizin 8..63; openpyxl COLOR_INDEX
# ile testte karşılaştırılır). Türkçe "[Renk N]" yazımı doğrulanmadı → yalnız kanonik kabul edilir.
PALET56 = (
    "000000", "FFFFFF", "FF0000", "00FF00", "0000FF", "FFFF00", "FF00FF", "00FFFF",
    "800000", "008000", "000080", "808000", "800080", "008080", "C0C0C0", "808080",
    "9999FF", "993366", "FFFFCC", "CCFFFF", "660066", "FF8080", "0066CC", "CCCCFF",
    "000080", "FF00FF", "FFFF00", "00FFFF", "800080", "800000", "008080", "0000FF",
    "00CCFF", "CCFFFF", "CCFFCC", "FFFF99", "99CCFF", "FF99CC", "CC99FF", "FFCC99",
    "3366FF", "33CCCC", "99CC00", "FFCC00", "FF9900", "FF6600", "666699", "969696",
    "003366", "339966", "003300", "333300", "993300", "993366", "333399", "333333",
)

# Tırnaksız yazılabilen sabit karakterler (Microsoft: $ + ( : ^ ' { < = - / ) ! & ~ } > ve boşluk)
_SABIT = set("$+(:^'{<=-/)!&~}> ")

# ------------------------------------------------------------------ sonuç
class BicimSonucu(NamedTuple):            # NamedTuple: sıcak yolda dataclass'tan ~3 kat hızlı kurulur
    metin: str
    renk: Optional[str] = None                 # '#RRGGBB' (biçim kodundaki [Renk]) ya da None
    hizalama: str = SAG                        # hücre "Genel" hizalıysa kullanılacak yön
    dolgu: Optional[Tuple[int, str]] = None    # `*x`: (metindeki konum, x) — sütunu doldurmak için
    diyez: bool = False                        # bu biçimle gösterilemez (negatif tarih…) → `####`


# ------------------------------------------------------------------ sözcükler
# Sözcük demetleri: (tür, ...). Türler:
#  ('sabit', metin, ham)  ham: yazıldığı gibi (tırnak/ters bölü dahil) — çeviride korunur
#  ('ph', '0'|'#'|'?')  ('nokta', ham)  ('binlik', ham)  ('yuzde',)  ('us', '+'|'-', 'E'|'e')
#  ('bolu',)  ('rakam', '1'..'9')  ('metin',)  ('genel',)  ('bosluk', x)  ('dolgu', x)
#  ('t', 'Y'|'M'|'D'|'H'|'N'|'S'|'m?', adet)   N = dakika, 'm?' = ay/dakika henüz çözülmedi
#  ('gecen', 'H'|'N'|'S', adet)  ('ampm', ham)  ('ssk', adet)  saniye kesri (ss.00)
#  ('renk', kanonik_ad | 'ColorN', '#hex')  ('kosul', op, sayı)  ('yerel', ham)  [$…] / [DBNum…]

_KOSUL_OP = ("<=", ">=", "<>", "<", ">", "=")


def _sayi_metni_coz(s: str, yerel: bool) -> float:
    t = s.strip()
    if yerel:
        t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        raise BicimHatasi(f"Koşuldaki sayı geçersiz: {s}") from None


def _koseli(icerik: str, yerel: bool):
    k = icerik.strip()
    kk = _tr_kucuk(k)
    renk = _RENK_ADI.get(kk) or _RENK_ADI.get(k.lower())    # Türkçe I/ı ve İngilizce I/i
    if renk is not None:
        return ("renk", renk[0], renk[2])
    kk = k.lower()
    if kk.startswith("color") and kk[5:].isdigit():
        n = int(kk[5:])
        if 1 <= n <= 56:
            return ("renk", f"Color{n}", "#" + PALET56[n - 1])
        raise BicimHatasi(f"Renk numarası 1–56 olmalı: {icerik}")
    for op in _KOSUL_OP:
        if k.startswith(op):
            return ("kosul", op, _sayi_metni_coz(k[len(op):], yerel))
    if k and set(kk) <= set("hms") and len(set(kk)) == 1:
        return ("gecen", {"h": "H", "m": "N", "s": "S"}[kk[0]], len(kk))
    if k.startswith("$") or kk.startswith("dbnum") or kk.startswith("natnum"):
        return ("yerel", icerik)
    raise BicimHatasi(f"Tanınmayan köşeli ayraç: [{icerik}]")


def _sozcukle(s: str, yerel: bool) -> List[tuple]:
    ondalik, binlik = (",", ".") if yerel else (".", ",")
    out: List[tuple] = []
    i, n = 0, len(s)
    while i < n:
        ch = s[i]
        if ch == '"':
            j = s.find('"', i + 1)
            if j < 0:
                raise BicimHatasi("Kapanmamış tırnak")
            out.append(("sabit", s[i + 1:j], s[i:j + 1]))
            i = j + 1
            continue
        if ch in "\\_*":
            if i + 1 >= n:
                raise BicimHatasi(f"'{ch}' sonrasında karakter yok")
            x = s[i + 1]
            out.append(("sabit", x, s[i:i + 2]) if ch == "\\" else
                       ("bosluk", x) if ch == "_" else ("dolgu", x))
            i += 2
            continue
        if ch == "[":
            j = s.find("]", i + 1)
            if j < 0:
                raise BicimHatasi("Kapanmamış köşeli ayraç")
            out.append(_koseli(s[i + 1:j], yerel))
            i = j + 1
            continue
        if ch in "0#?":
            out.append(("ph", ch))
        elif ch == ondalik:
            out.append(("nokta", ch))
        elif ch == binlik:
            out.append(("binlik", ch))
        elif ch == "%":
            out.append(("yuzde",))
        elif ch in "Ee" and i + 1 < n and s[i + 1] in "+-":
            out.append(("us", s[i + 1], ch))
            i += 2
            continue
        elif ch == "/":
            out.append(("bolu",))
        elif ch in "123456789":
            out.append(("rakam", ch))
        elif ch == "@":
            out.append(("metin",))
        else:
            kalan = s[i:]
            ku = kalan.upper()
            if ku.startswith("GENERAL"):
                out.append(("genel",))
                i += 7
                continue
            if yerel and _tr_kucuk(kalan[:5]) == "genel":
                out.append(("genel",))
                i += 5
                continue
            if ku.startswith("AM/PM"):
                out.append(("ampm", kalan[:5]))
                i += 5
                continue
            if ku.startswith("A/P"):
                out.append(("ampm", kalan[:3]))
                i += 3
                continue
            if yerel and kalan.startswith("ÖÖ/ÖS"):
                out.append(("ampm", "AM/PM"))
                i += 5
                continue
            harf = ch.lower()
            harfler = "ymdhsga" if yerel else "ymdhs"
            if harf in harfler:
                j = i
                while j < n and s[j].lower() == harf:
                    j += 1
                adet = j - i
                tur = {"y": "Y", "d": "D", "g": "D", "h": "H", "s": "S", "a": "M", "m": "m?"}[harf]
                out.append(("t", tur, adet))
                i = j
                continue
            if ch in _SABIT or ord(ch) > 127:
                out.append(("sabit", ch, ch))
            else:
                raise BicimHatasi(f"Biçim kodunda geçersiz karakter: {ch}")
        i += 1
    return out


def _bolumlere_ayir(kod: str) -> List[str]:
    """Kodu tırnak/ters bölü/köşeli ayraç dışındaki ';' ile böler."""
    parcalar, bas, i, n = [], 0, 0, len(kod)
    while i < n:
        ch = kod[i]
        if ch == '"':
            j = kod.find('"', i + 1)
            i = n if j < 0 else j + 1
            continue
        if ch in "\\_*":
            i += 2
            continue
        if ch == "[":
            j = kod.find("]", i + 1)
            i = n if j < 0 else j + 1
            continue
        if ch == ";":
            parcalar.append(kod[bas:i])
            bas = i + 1
        i += 1
    parcalar.append(kod[bas:])
    if len(parcalar) > 4:
        raise BicimHatasi("Biçim kodu en çok dört bölüm içerebilir")
    return parcalar


# ------------------------------------------------------------------ bölüm
_TARIH = ("t", "gecen", "ampm", "ssk")


@dataclass(frozen=True)
class Bolum:
    tur: str                          # 'genel' | 'sayi' | 'tarih' | 'metin' | 'sabit'
    ogeler: tuple                     # sözcükler (renk/koşul hariç, sırayla)
    renk: Optional[str] = None        # '#RRGGBB'
    renk_adi: Optional[str] = None    # kanonik ad ('Red', 'Color10')
    kosul: Optional[Tuple[str, float]] = None
    duzen: Optional[object] = None    # sayı/tarih için önceden hesaplanmış düzen

    def kosul_uyar(self, x: float) -> bool:
        op, d = self.kosul
        return {"<": x < d, "<=": x <= d, ">": x > d, ">=": x >= d, "=": x == d,
                "<>": x != d}[op]


def _tarih_coz(ogeler: list) -> list:
    """'m?' sözcüklerini ay/dakika olarak çözer; tarih bölümünde nokta/rakamları düzeltir."""
    og = list(ogeler)
    zaman = [i for i, t in enumerate(og) if t[0] in ("t", "gecen")]

    def tur(i):
        t = og[i]
        return t[1] if t[0] == "t" else "g" + t[1]

    for k, i in enumerate(zaman):
        t = og[i]
        if t[0] == "t" and t[1] == "m?":
            dakika = False
            if t[2] <= 2:
                if k > 0 and tur(zaman[k - 1]) in ("H", "gH"):
                    dakika = True
                elif k + 1 < len(zaman) and tur(zaman[k + 1]) in ("S", "gS"):
                    dakika = True
            og[i] = ("t", "N" if dakika else "M", t[2])
    # 'ss.00': saniyeden sonra nokta + '0'lar saniye kesridir; diğer nokta/virgül/rakam sabittir
    sonuc, i = [], 0
    while i < len(og):
        t = og[i]
        if t[0] == "nokta":
            j = i + 1
            while j < len(og) and og[j] == ("ph", "0"):
                j += 1
            onceki = next((x for x in reversed(sonuc) if x[0] in ("t", "gecen")), None)
            if j > i + 1 and onceki is not None and onceki[1] == "S":
                sonuc.append(("ssk", j - i - 1))
                i = j
                continue
            sonuc.append(("sabit", t[1], t[1]))
        elif t[0] == "binlik":
            sonuc.append(("sabit", t[1], t[1]))
        elif t[0] == "ph":
            sonuc.append(("sabit", t[1], t[1]))
        elif t[0] == "rakam":
            sonuc.append(("sabit", t[1], t[1]))
        elif t[0] == "bolu":
            sonuc.append(("sabit", "/", "/"))
        elif t[0] == "yuzde":
            sonuc.append(("sabit", "%", "%"))
        else:
            sonuc.append(t)
        i += 1
    return sonuc


@dataclass(frozen=True)
class _SayiDuzeni:
    tam: tuple            # tam kısım sözcükleri (ph/sabit/bosluk/dolgu) — en az bir ph
    ondalik: tuple        # ondalık nokta sonrası (nokta yoksa boş)
    nokta: bool
    us: Optional[tuple]   # (işaret, harf, üs sözcükleri)
    kesir: Optional[tuple]  # (pay sözcükleri, payda: int | ph listesi, sonrası)
    binlik: bool
    olcek: int            # 1000'e bölme sayısı
    yuzde: int
    ondalik_basamak: int
    hizli: Optional[tuple] = None   # sık kalıplar için hazır parçalar (bkz. `_hizli_duzen`)


def _hizli_duzen(tam: list, ond: list, nokta: bool, binlik: bool):
    """`[sabitler] #,##0[.00] [sabitler]` biçimindeki (en sık) kalıplar için önceden hazırlanmış
    (önek, önek dolgusu, en az tam basamak, binlik, ondalık basamak, nokta, sonek, sonek dolgusu).
    Uymayan kalıpta None → genel (yavaş ama tam) yol."""
    i = 0
    while i < len(tam) and tam[i][0] != "ph":
        i += 1
    onek_og, tam_ph = tam[:i], tam[i:]
    desen = "".join(t[1] for t in tam_ph if t[0] == "ph")
    if any(t[0] != "ph" for t in tam_ph) or desen.lstrip("#").strip("0") or "?" in desen:
        return None
    en_az = desen.count("0")
    if binlik and en_az > 1:
        return None
    j = 0
    while j < len(ond) and ond[j] == ("ph", "0"):
        j += 1
    son_og = ond[j:]
    if any(t[0] == "ph" for t in son_og) or any(t[0] == "nokta" for t in onek_og + son_og):
        return None
    on, on_d, son, son_d = [], [], [], []
    for t in onek_og:
        _sabit_ekle(t, on, on_d)
    for t in son_og:
        _sabit_ekle(t, son, son_d)
    if on_d and son_d:
        return None
    return ("".join(on), on_d[0] if on_d else None, en_az, binlik, j, nokta, "".join(son),
            son_d[0] if son_d else None)


def _sayi_duzeni(ogeler: list) -> _SayiDuzeni:
    yuzde = sum(1 for t in ogeler if t[0] == "yuzde")
    us_i = next((i for i, t in enumerate(ogeler) if t[0] == "us"), None)
    bolu_i = next((i for i, t in enumerate(ogeler) if t[0] == "bolu"), None)
    govde = ogeler if us_i is None else ogeler[:us_i]
    if bolu_i is not None and us_i is None:
        return _kesir_duzeni(ogeler, bolu_i, yuzde)
    # binlik / ölçek virgülleri
    phler = [i for i, t in enumerate(govde) if t[0] == "ph"]
    nokta_i = next((i for i, t in enumerate(govde) if t[0] == "nokta"), None)
    tam_son = nokta_i if nokta_i is not None else len(govde)
    binlik, olcek = False, 0
    temiz = []
    for i, t in enumerate(govde):
        if t[0] == "binlik":
            once = any(p < i for p in phler)
            sonra_tam = any(i < p < tam_son for p in phler)
            sonra = any(p > i for p in phler)
            if once and sonra_tam:
                binlik = True
            elif once and not sonra:
                olcek += 1
            elif not once:
                temiz.append(("sabit", t[1], t[1]))
            continue
        if t[0] == "yuzde":
            temiz.append(("sabit", "%", "%"))
            continue
        if t[0] in ("rakam", "bolu"):
            temiz.append(("sabit", t[1] if t[0] == "rakam" else "/", t[1] if t[0] == "rakam" else "/"))
            continue
        temiz.append(t)
    nokta_i = next((i for i, t in enumerate(temiz) if t[0] == "nokta"), None)
    if nokta_i is None:
        tam, ond = temiz, []
    else:
        tam = temiz[:nokta_i]
        ond = [t if t[0] != "nokta" else ("sabit", t[1], t[1]) for t in temiz[nokta_i + 1:]]
    if not any(t[0] == "ph" for t in tam):
        # tam kısım yer tutucusu yoksa rakamlar ondalık noktadan hemen önce yazılır ('.00' → '12,50')
        tam = list(tam) + [("ph", "#")]
    us = None
    if us_i is not None:
        us_og = [t if t[0] in ("ph", "sabit", "bosluk", "dolgu") else
                 ("sabit", t[1], t[1]) if t[0] in ("binlik", "nokta", "rakam") else
                 ("sabit", "%", "%") if t[0] == "yuzde" else ("sabit", "/", "/")
                 for t in ogeler[us_i + 1:]]
        us = (ogeler[us_i][1], ogeler[us_i][2], tuple(us_og))
    hizli = None if us is not None else _hizli_duzen(tam, ond, nokta_i is not None, binlik)
    return _SayiDuzeni(tuple(tam), tuple(ond), nokta_i is not None, us, None, binlik, olcek,
                       yuzde, sum(1 for t in ond if t[0] == "ph"), hizli)


def _kesir_duzeni(ogeler: list, bolu_i: int, yuzde: int) -> _SayiDuzeni:
    once, sonra = ogeler[:bolu_i], ogeler[bolu_i + 1:]

    def sabitle(t):
        if t[0] in ("binlik", "nokta"):
            return ("sabit", t[1], t[1])
        if t[0] == "yuzde":
            return ("sabit", "%", "%")
        if t[0] == "rakam":
            return ("sabit", t[1], t[1])
        return t

    # pay: bölüden önceki son yer tutucu dizisi; ondan önceki yer tutucular tam kısım
    j = len(once)
    while j > 0 and once[j - 1][0] != "ph":
        j -= 1
    pay_son = j
    while j > 0 and once[j - 1][0] == "ph":
        j -= 1
    pay = tuple(once[j:pay_son])
    if not pay:
        raise BicimHatasi("Kesirde pay yer tutucusu yok")
    pay_arasi = tuple(sabitle(t) for t in once[pay_son:])
    tam = [sabitle(t) for t in once[:j]]
    tam_var = any(t[0] == "ph" for t in tam)
    # payda: sabit sayı ya da yer tutucular
    k = 0
    while k < len(sonra) and sonra[k][0] in ("ph", "rakam"):
        k += 1
    payda_og = sonra[:k]
    if not payda_og:
        raise BicimHatasi("Kesirde payda yok")
    if any(t[0] == "rakam" for t in payda_og):
        rakamlar = "".join("0" if t == ("ph", "0") else t[1] for t in payda_og)
        if not rakamlar.isdigit():
            raise BicimHatasi("Kesir paydası geçersiz")
        payda = int(rakamlar)
        if payda == 0:
            raise BicimHatasi("Kesir paydası sıfır olamaz")
    else:
        payda = tuple(t[1] for t in payda_og)
    son = tuple(sabitle(t) for t in sonra[k:])
    return _SayiDuzeni(tuple(tam), (), False, None,
                       (pay, pay_arasi, payda, son, tam_var), False, 0, yuzde, 0)


def _bolum_kur(metin: str, yerel: bool) -> Bolum:
    ogeler = _sozcukle(metin, yerel)
    renk = renk_adi = kosul = None
    kalan = []
    for t in ogeler:
        if t[0] == "renk":
            renk_adi, renk = t[1], t[2]
        elif t[0] == "kosul":
            kosul = (t[1], t[2])
        else:
            kalan.append(t)
    turler = {t[0] for t in kalan}
    if "genel" in turler:
        tur = "genel"
    elif turler & {"t", "gecen", "ampm"}:
        tur = "tarih"
        kalan = _tarih_coz(kalan)
    elif "metin" in turler:
        tur = "metin"
    elif "ph" in turler:
        tur = "sayi"
    elif not kalan and (renk is not None or kosul is not None):
        tur = "genel"            # yalnız renk/koşul ('[Red][<=100]'): sayı Genel biçimde, o renkte
    else:
        tur = "sabit"
    duzen = _sayi_duzeni(kalan) if tur == "sayi" else None
    if tur == "tarih":
        # (saniye kesri basamağı, 12 saatlik mi, geçen süre birimi, takvim gerekli mi)
        duzen = (max((t[1] for t in kalan if t[0] == "ssk"), default=0),
                 any(t[0] == "ampm" for t in kalan),
                 next((t[1] for t in kalan if t[0] == "gecen"), None),
                 any(t[0] == "t" and t[1] in "YMD" for t in kalan))
    return Bolum(tur, tuple(kalan), renk, renk_adi, kosul, duzen)


@dataclass(frozen=True)
class BicimKodu:
    """Ayrıştırılmış biçim kodu. `sayi_bolumleri` sayılara, `metin_bolumu` metinlere uygulanır."""
    bolumler: Tuple[Bolum, ...]
    sayi_bolumleri: Tuple[Bolum, ...]
    metin_bolumu: Optional[Bolum]
    kosullu: bool

    @property
    def genel_mi(self) -> bool:
        return len(self.sayi_bolumleri) <= 1 and (
            not self.sayi_bolumleri or self.sayi_bolumleri[0].tur == "genel"
            and len(self.sayi_bolumleri[0].ogeler) == 1 and self.sayi_bolumleri[0].renk is None)

    @property
    def tarih_mi(self) -> bool:
        """İlk sayı bölümü tarih/saat mi (akıllı giriş, METNEÇEVİR, doldurma için)."""
        return bool(self.sayi_bolumleri) and self.sayi_bolumleri[0].tur == "tarih"

    def yaz(self, yerel: bool) -> str:
        return ";".join(_bolum_yaz(b, yerel) for b in self.bolumler)


@lru_cache(maxsize=4096)
def kod_coz(kod: str, yerel: bool = False) -> BicimKodu:
    """Biçim kodunu ayrıştırır (önbellekli). `yerel=True`: Türkçe yazım (``#.##0,00``,
    ``gg.aa.yyyy``, ``[Kırmızı]``, ``Genel``). Geçersizse `BicimHatasi`."""
    if kod is None or kod.strip() == "" or kod == "General":
        b = Bolum("genel", (("genel",),))
        return BicimKodu((b,), (b,), None, False)
    bolumler = tuple(_bolum_kur(m, yerel) for m in _bolumlere_ayir(kod))
    if len(bolumler) == 4:
        sayi, metin = bolumler[:3], bolumler[3]
    elif bolumler[-1].tur == "metin":
        sayi, metin = bolumler[:-1], bolumler[-1]
    else:
        sayi, metin = bolumler, None
    for b in sayi:
        if b.tur == "metin":
            raise BicimHatasi("'@' yalnızca metin bölümünde kullanılabilir")
    kosullu = any(b.kosul is not None for b in sayi[:2])
    return BicimKodu(bolumler, sayi, metin, kosullu)


# ------------------------------------------------------------------ yazım (kanonik ⇄ yerel)
def _sayi_yaz(x: float, yerel: bool) -> str:
    t = repr(x)
    if t.endswith(".0"):
        t = t[:-2]
    return t.replace(".", ",") if yerel else t


def _bolum_yaz(b: Bolum, yerel: bool) -> str:
    parca = []
    if b.renk_adi is not None:
        ad = b.renk_adi
        if yerel and ad.lower() in _RENK_ADI:
            ad = _RENK_ADI[ad.lower()][1]
        parca.append(f"[{ad}]")
    if b.kosul is not None:
        parca.append(f"[{b.kosul[0]}{_sayi_yaz(b.kosul[1], yerel)}]")
    ondalik, binlik = (",", ".") if yerel else (".", ",")
    harf = {"Y": "y", "D": "g" if yerel else "d", "M": "a" if yerel else "m", "N": "m", "H": "h",
            "S": "s"}
    for t in b.ogeler:
        tur = t[0]
        if tur == "sabit":
            parca.append(_sabit_yaz(t, b.tur == "tarih"))
        elif tur == "ph":
            parca.append(t[1])
        elif tur == "nokta":
            parca.append(ondalik)
        elif tur == "binlik":
            parca.append(binlik)
        elif tur == "yuzde":
            parca.append("%")
        elif tur == "us":
            parca.append(t[2] + t[1])
        elif tur == "bolu":
            parca.append("/")
        elif tur == "rakam":
            parca.append(t[1])
        elif tur == "metin":
            parca.append("@")
        elif tur == "genel":
            parca.append("Genel" if yerel else "General")
        elif tur == "bosluk":
            parca.append("_" + t[1])
        elif tur == "dolgu":
            parca.append("*" + t[1])
        elif tur == "t":
            parca.append(harf[t[1]] * t[2])
        elif tur == "gecen":
            parca.append("[" + {"H": "h", "N": "m", "S": "s"}[t[1]] * t[2] + "]")
        elif tur == "ampm":
            parca.append(t[1])
        elif tur == "ssk":
            parca.append(ondalik + "0" * t[1])
        elif tur == "yerel":
            parca.append(f"[{t[1]}]")
    return "".join(parca)


_TARIHTE_SERBEST = set(",./0#?%123456789")


def _sabit_yaz(t: tuple, tarih: bool) -> str:
    """Sabit metni hedef yazımda güvenle yazar: hedef dilde anlam taşıyacak karakter kaçışlanır.
    Tarih bölümünde `.` `,` `/` ve rakamlar ayırıcı olarak serbesttir (``dd.mm.yyyy``)."""
    metin, ham = t[1], t[2]
    if ham.startswith(('"', "\\")):
        return ham
    if tarih and metin in _TARIHTE_SERBEST:
        return metin
    if metin in _SABIT and metin != "/":
        return metin
    if ord(metin[0]) > 127 and metin != "Ö":
        return metin
    return "\\" + metin


def yerele(kod: str) -> str:
    """Kanonik kod → Türkçe yazım (``#,##0.00`` → ``#.##0,00``)."""
    if kod is None or kod.strip() == "" or kod == "General":
        return "Genel"
    return kod_coz(kod, False).yaz(True)


def kanonige(kod: str) -> str:
    """Türkçe yazım → kanonik kod (``gg.aa.yyyy`` → ``dd.mm.yyyy``)."""
    if kod is None or kod.strip() == "" or _tr_kucuk(kod.strip()) == "genel":
        return "General"
    return kod_coz(kod, True).yaz(False)


# ------------------------------------------------------------------ biçimleme
def _ondalik_dec(x: float) -> Decimal:
    """15 anlamlı basamakla Decimal (Excel'in görünen duyarlığı; 1,005 → 1,01 yuvarlanır)."""
    return Decimal(f"{x:.15g}")


def _yuvarla(d: Decimal, basamak: int) -> Decimal:
    return d.quantize(Decimal(1).scaleb(-basamak), rounding=ROUND_HALF_UP)


def _tam_yaz(ogeler: tuple, rakamlar: str, binlik: bool, cikti: list, dolgu: list) -> None:
    """Tam kısım: rakamlar sağdan yer tutuculara dağıtılır, fazlası en soldakine gider."""
    ph_konum = [i for i, t in enumerate(ogeler) if t[0] == "ph"]
    n = len(ph_konum)
    L = len(rakamlar)
    sahip = {}                       # sözcük indeksi → kapsadığı basamak konumları (sağdan, büyükten)
    for j, idx in enumerate(reversed(ph_konum)):
        if j == n - 1:
            sahip[idx] = list(range(max(L, n) - 1, j - 1, -1))
        else:
            sahip[idx] = [j]

    def basamak(p, ph):
        if p < L:
            return rakamlar[L - 1 - p]
        return "0" if ph == "0" else " " if ph == "?" else ""

    ph_turu = {}
    for j, idx in enumerate(reversed(ph_konum)):
        ph_turu[j] = ogeler[idx][1]
    for i, t in enumerate(ogeler):
        if t[0] == "ph":
            for p in sahip[i]:
                ch = basamak(p, ph_turu.get(p, t[1]))
                cikti.append(ch)
                if binlik and p > 0 and p % 3 == 0 and ch:
                    cikti.append(" " if ch == " " else BINLIK)
        else:
            _sabit_ekle(t, cikti, dolgu)


def _sabit_ekle(t: tuple, cikti: list, dolgu: list) -> None:
    tur = t[0]
    if tur == "sabit":
        cikti.append(t[1])
    elif tur == "bosluk":
        cikti.append(" ")
    elif tur == "dolgu":
        if not dolgu:
            dolgu.append((sum(len(c) for c in cikti), t[1]))
    elif tur == "yerel":
        ic = t[1]
        if ic.startswith("$"):
            cikti.append(ic[1:].split("-", 1)[0])
    elif tur == "nokta":
        cikti.append(ONDALIK)
    elif tur == "binlik":
        cikti.append(BINLIK)


def _ondalik_yaz(ogeler: tuple, rakamlar: str, cikti: list, dolgu: list) -> None:
    phler = [t[1] for t in ogeler if t[0] == "ph"]
    gor = list(rakamlar)
    for k in range(len(phler) - 1, -1, -1):
        if gor[k] == "0" and phler[k] in "#?":
            gor[k] = "" if phler[k] == "#" else " "
        else:
            break
    k = 0
    for t in ogeler:
        if t[0] == "ph":
            cikti.append(gor[k])
            k += 1
        else:
            _sabit_ekle(t, cikti, dolgu)


def _hizli_sayi(h: tuple, v: float, isaret: bool):
    on, on_d, en_az, binlik, m, nokta, son, son_d = h
    olcek = 10 ** m
    s = v * olcek
    if s >= 1e15:
        return None
    # 15 anlamlı basamağa indirip yarımı yukarı yuvarla (1,005 → 1,01; Excel gibi)
    n = int(math.floor(float(f"{s:.15g}") + 0.5))
    tam, ond = divmod(n, olcek)
    if tam:
        ts = f"{tam:,}".replace(",", ".") if binlik else str(tam).zfill(en_az)
    else:
        ts = "0" * en_az
    isr = "-" if isaret else ""
    metin = isr + on + ts + ((ONDALIK + str(ond).zfill(m)) if nokta else "") + son
    if on_d is not None:
        dolgu = (on_d[0] + len(isr), on_d[1])
    elif son_d is not None:
        dolgu = (len(metin) - len(son) + son_d[0], son_d[1])
    else:
        dolgu = None
    return metin, dolgu


def _sayi_bicimle(b: Bolum, x: float, isaret: bool) -> Tuple[str, Optional[tuple]]:
    d: _SayiDuzeni = b.duzen
    v = abs(x) * (100 ** d.yuzde) / (1000 ** d.olcek)
    if d.hizli is not None:
        r = _hizli_sayi(d.hizli, v, isaret)
        if r is not None:
            return r
    cikti: list = []
    dolgu: list = []
    if isaret:
        cikti.append("-")
    if d.kesir is not None:
        _kesir_yaz(d, v, cikti, dolgu)
    elif d.us is not None:
        _us_yaz(d, v, cikti, dolgu)
    else:
        dec = _yuvarla(_ondalik_dec(v), d.ondalik_basamak)
        s = f"{dec:f}"
        tam, _, ond = s.partition(".")
        tam = tam.lstrip("0")
        _tam_yaz(d.tam, tam, d.binlik, cikti, dolgu)
        if d.nokta:
            cikti.append(ONDALIK)
            _ondalik_yaz(d.ondalik, ond.ljust(d.ondalik_basamak, "0"), cikti, dolgu)
    return "".join(cikti), (dolgu[0] if dolgu else None)


def _us_yaz(d: _SayiDuzeni, v: float, cikti: list, dolgu: list) -> None:
    tam_ph = [t[1] for t in d.tam if t[0] == "ph"]
    n = len(tam_ph)
    muhendis = n > 1 and any(c in "#?" for c in tam_ph)
    m = d.ondalik_basamak
    if v == 0:
        us, mant = 0, Decimal(0)
    else:
        dv = _ondalik_dec(v)
        e10 = dv.adjusted()
        us = (e10 // n) * n if muhendis else e10 - (n - 1)
        mant = _yuvarla(dv.scaleb(-us), m)
        sinir = Decimal(10) ** n
        if mant >= sinir:                     # yuvarlama basamak taşırdı (9,99 → 10,0)
            us += n if muhendis else 1
            mant = _yuvarla(dv.scaleb(-us), m)
    s = f"{mant:f}"
    tam, _, ond = s.partition(".")
    _tam_yaz(d.tam, tam.lstrip("0"), False, cikti, dolgu)
    if d.nokta:
        cikti.append(ONDALIK)
        _ondalik_yaz(d.ondalik, ond.ljust(m, "0"), cikti, dolgu)
    isaret, harf, us_og = d.us
    cikti.append(harf)
    if us < 0:
        cikti.append("-")
    elif isaret == "+":
        cikti.append("+")
    us_ph = [t[1] for t in us_og if t[0] == "ph"]
    rakam = str(abs(us))
    en_az = sum(1 for c in us_ph if c == "0")
    rakam = rakam.rjust(en_az, "0")
    # üs yer tutucuları dışındaki sabitler sona
    cikti.append(rakam)
    for t in us_og:
        if t[0] != "ph":
            _sabit_ekle(t, cikti, dolgu)


def _ph_doldur(sayi: str, phler: tuple, sola: bool) -> str:
    """Pay/paydayı yer tutucu genişliğine doldurur ('?' boşluk, '0' sıfır)."""
    eksik = len(phler) - len(sayi)
    if eksik <= 0:
        return sayi
    dolgu = "".join(" " if c == "?" else "0" if c == "0" else "" for c in phler[:eksik])
    return dolgu + sayi if sola else sayi + dolgu[::-1]


def _kesir_yaz(d: _SayiDuzeni, v: float, cikti: list, dolgu: list) -> None:
    pay_og, pay_arasi, payda_k, son, tam_var = d.kesir
    dec = _ondalik_dec(v)
    if tam_var:
        tam = int(dec)
        kesir = Fraction(str(dec - tam))
    else:
        tam, kesir = 0, Fraction(str(dec))
    if isinstance(payda_k, int):
        payda = payda_k
        pay = int(_yuvarla(Decimal(kesir.numerator) * payda / Decimal(kesir.denominator), 0))
    else:
        en_cok = 10 ** len(payda_k) - 1
        yak = kesir.limit_denominator(en_cok)
        pay, payda = yak.numerator, yak.denominator
    if tam_var and pay == payda:
        tam, pay = tam + 1, 0
    pay_ph = tuple(t[1] for t in pay_og)
    if tam_var:
        _tam_yaz(d.tam, str(tam) if tam else ("0" if pay == 0 else ""), False, cikti, dolgu)
    else:
        for t in d.tam:
            _sabit_ekle(t, cikti, dolgu)
    if tam_var and pay == 0:
        # kesir kısmı boşluk olur (Excel: '2    ')
        payda_gen = len(payda_k) if not isinstance(payda_k, int) else len(str(payda_k))
        for t in pay_arasi:
            _sabit_ekle(t, cikti, dolgu)
        cikti.append(" " * (len(pay_ph) + 1 + payda_gen))
    else:
        cikti.append(_ph_doldur(str(pay), pay_ph, True))
        for t in pay_arasi:
            _sabit_ekle(t, cikti, dolgu)
        cikti.append("/")
        if isinstance(payda_k, int):
            cikti.append(str(payda))
        else:
            cikti.append(_ph_doldur(str(payda), payda_k, False))
    for t in son:
        _sabit_ekle(t, cikti, dolgu)


def _yuvarla_tam(x: float) -> int:
    return int(math.floor(x + 0.5))


def _tarih_bicimle(b: Bolum, x: float) -> Tuple[Optional[str], Optional[tuple]]:
    """Tarih/saat bölümü; gösterilemezse (negatif, 9999 sonrası) None."""
    if x < 0 or x >= MAKS_SERI + 1:
        return None, None
    k, ampm, gecen, takvim = b.duzen
    birim = 10 ** k
    toplam = _yuvarla_tam(x * 86400 * birim)
    gun, kalan = divmod(toplam, 86400 * birim)
    if gun > MAKS_SERI:
        return None, None
    tum_sn = toplam // birim
    ssk = toplam % birim
    sn_gun, _ = divmod(kalan, birim)
    saat, r = divmod(sn_gun, 3600)
    dk, sn = divmod(r, 60)
    y, a, g = seri_ymd(gun) if takvim else (None, None, None)
    ogeler = b.ogeler
    if gecen == "H":
        dk, sn = (tum_sn % 3600) // 60, tum_sn % 60
    elif gecen == "N":
        sn = tum_sn % 60
    cikti: list = []
    dolgu: list = []
    for t in ogeler:
        tur = t[0]
        if tur == "t":
            harf, n = t[1], t[2]
            if harf == "Y":
                cikti.append(f"{y % 100:02d}" if n <= 2 else f"{y:04d}")
            elif harf == "M":
                if n == 1:
                    cikti.append(str(a))
                elif n == 2:
                    cikti.append(f"{a:02d}")
                elif n == 3:
                    cikti.append(AY_KISA[a - 1])
                elif n == 5:
                    cikti.append(AYLAR[a - 1][0])
                else:
                    cikti.append(AYLAR[a - 1])
            elif harf == "D":
                if n == 1:
                    cikti.append(str(g))
                elif n == 2:
                    cikti.append(f"{g:02d}")
                elif n == 3:
                    cikti.append(GUN_KISA[haftanin_gunu0(gun)])
                else:
                    cikti.append(GUNLER[haftanin_gunu0(gun)])
            elif harf == "H":
                h = saat
                if ampm:
                    h = h % 12 or 12
                cikti.append(f"{h:02d}" if n >= 2 else str(h))
            elif harf == "N":
                cikti.append(f"{dk:02d}" if n >= 2 else str(dk))
            elif harf == "S":
                cikti.append(f"{sn:02d}" if n >= 2 else str(sn))
        elif tur == "gecen":
            deger = {"H": tum_sn // 3600, "N": tum_sn // 60, "S": tum_sn}[t[1]]
            cikti.append(str(deger).rjust(t[2], "0"))
        elif tur == "ampm":
            ogle = saat >= 12
            ham = t[1]
            if ham.upper() == "AM/PM":
                cikti.append(OS if ogle else OO)
            else:
                cikti.append(ham[2] if ogle else ham[0])
        elif tur == "ssk":
            cikti.append(ONDALIK + str(ssk).rjust(k, "0")[:t[1]])
        else:
            _sabit_ekle(t, cikti, dolgu)
    return "".join(cikti), (dolgu[0] if dolgu else None)


def _metin_bicimle(b: Bolum, metin: str) -> Tuple[str, Optional[tuple]]:
    cikti: list = []
    dolgu: list = []
    for t in b.ogeler:
        if t[0] == "metin":
            cikti.append(metin)
        else:
            _sabit_ekle(t, cikti, dolgu)
    return "".join(cikti), (dolgu[0] if dolgu else None)


def _bolum_sec(kod: BicimKodu, x: float):
    """(bölüm, eksi işareti yazılsın mı) ya da (None, False) — hiçbir koşula uymadı."""
    sb = kod.sayi_bolumleri
    if kod.kosullu:
        for i, b in enumerate(sb):
            if b.kosul is None or b.kosul_uyar(x):
                ozel_negatif = i == 1 and b.kosul is not None and b.kosul[0] in ("<", "<=") \
                    and b.kosul[1] <= 0
                return b, x < 0 and not ozel_negatif
        return None, False
    if len(sb) == 1:
        return sb[0], x < 0
    if x < 0:
        return sb[1], False
    if x == 0 and len(sb) >= 3:
        return sb[2], False
    return sb[0], False


def bicimle(deger, kod: Optional[str] = "General", yerel: bool = False) -> BicimSonucu:
    """Değeri biçim koduyla Türkçe gösterim metnine çevirir.

    `kod` varsayılan olarak kanonik yazımdadır (`yerel=True` ise Türkçe). Boş hücre (None) → "".
    Mantıksal ve hata değerleri biçimden etkilenmez (ortalanır). Geçersiz kod → `BicimHatasi`.
    """
    if deger is None:
        return BicimSonucu("", None, SOL)
    if isinstance(deger, bool) or isinstance(deger, Hata):
        return BicimSonucu(goster(deger), None, ORTA)
    if (kod is None or kod == "General") and not isinstance(deger, str):   # hızlı yol
        return BicimSonucu(goster(float(deger)), None, SAG)
    k = kod_coz(kod or "General", yerel)
    if isinstance(deger, str):
        b = k.metin_bolumu
        if b is None:
            return BicimSonucu(deger, None, SOL)
        metin, dolgu = _metin_bicimle(b, deger)
        return BicimSonucu(metin, b.renk, SOL, dolgu)
    x = float(deger)
    if not k.sayi_bolumleri:
        return BicimSonucu(goster(x), None, SAG)
    b, isaret = _bolum_sec(k, x)
    if b is None:
        return BicimSonucu("", None, SAG, None, True)
    if b.tur == "genel":
        cikti: list = []
        dolgu: list = []
        ogeler = b.ogeler or (("genel",),)
        for t in ogeler:
            if t[0] == "genel":
                cikti.append(goster(x) if isaret or x >= 0 else goster(abs(x)))
            else:
                _sabit_ekle(t, cikti, dolgu)
        return BicimSonucu("".join(cikti), b.renk, SAG, dolgu[0] if dolgu else None)
    if b.tur == "sayi":
        metin, dolgu = _sayi_bicimle(b, x, isaret)
        return BicimSonucu(metin, b.renk, SAG, dolgu)
    if b.tur == "tarih":
        metin, dolgu = _tarih_bicimle(b, x)
        if metin is None:
            return BicimSonucu("", b.renk, SAG, None, True)
        return BicimSonucu(metin, b.renk, SAG, dolgu)
    # yalnız sabit metinli bölüm ('"Sıfır"', boş bölüm)
    cikti, dolgu = [], []
    for t in b.ogeler:
        _sabit_ekle(t, cikti, dolgu)
    return BicimSonucu("".join(cikti), b.renk, SAG, dolgu[0] if dolgu else None)


# ------------------------------------------------------------------ sütuna sığdırma
def sigdir(deger, kod: Optional[str], sigar, yerel: bool = False) -> Optional[str]:
    """Hücre metnini sütun genişliğine göre verir; `sigar(metin)` metin sığıyorsa True.

    - Genel biçimde sayı: `gosterim.sayiyi_sigdir` (önce ondalık yuvarlama, sonra bilimsel).
    - Diğer sayı/tarih biçimleri kısaltılmaz: sığmazsa None (çağıran `####` çizer).
    - Metin None dönmez (taşar/kırpılır). `*x` dolgusu varsa `doldur` ile genişletilir.
    """
    if deger is None:
        return ""
    if isinstance(deger, (str, bool, Hata)):
        return bicimle(deger, kod, yerel).metin
    if kod is None or kod == "General" or kod_coz(kod, yerel).genel_mi:
        return sayiyi_sigdir(float(deger), sigar)
    s = bicimle(deger, kod, yerel)
    if s.diyez:
        return None
    metin = doldur(s, sigar) if s.dolgu else s.metin
    return metin if sigar(metin) else None


def doldur(sonuc: BicimSonucu, sigar) -> str:
    """`*x` dolgusunu sütun sığdığı kadar tekrarlar (dolgu yoksa metin aynen)."""
    if not sonuc.dolgu:
        return sonuc.metin
    konum, x = sonuc.dolgu
    bas, son = sonuc.metin[:konum], sonuc.metin[konum:]
    if not sigar(bas + son):
        return bas + son
    alt, ust = 0, 1
    while sigar(bas + x * ust + son) and ust < 4096:
        alt, ust = ust, ust * 2
    while ust - alt > 1:
        orta = (alt + ust) // 2
        if sigar(bas + x * orta + son):
            alt = orta
        else:
            ust = orta
    return bas + x * alt + son


# ------------------------------------------------------------------ hazır biçimler
# Kanonik kodlar. BELİRSİZ (§8b): Türkçe Excel'in hazır "Para Birimi", "Muhasebe", kısa/uzun tarih
# kodları Windows tr-TR yerel ayarından türetildi (kısa tarih d.MM.yyyy, uzun d MMMM yyyy dddd,
# saat HH:mm:ss, para ₺ önde) — Excel web'de "Hücreleri Biçimlendir ▸ Özel" ile karşılaştırılacak.
HAZIR = {
    "Genel": "General",
    "Sayı": "0.00",
    "Sayı (binlik ayraçlı)": "#,##0.00",
    "Para Birimi": '"₺"#,##0.00',
    "Para Birimi ($)": '"$"#,##0.00',
    "Para Birimi (€)": '#,##0.00 "€"',
    "Muhasebe": '_-"₺"* #,##0.00_-;-"₺"* #,##0.00_-;_-"₺"* "-"??_-;_-@_-',
    "Kısa Tarih": "d.mm.yyyy",
    "Uzun Tarih": "d mmmm yyyy dddd",
    "Saat": "hh:mm:ss",
    "Yüzde": "0.00%",
    "Kesir": "# ?/?",
    "Bilimsel": "0.00E+00",
    "Metin": "@",
}


def ad_kodu(adi: str) -> str:
    """Hazır biçim adından kanonik kod (`HAZIR`); bilinmeyen ad → KeyError."""
    return HAZIR[adi]


def ondalik_degistir(kod: str, fark: int, deger=None) -> str:
    """Ondalık Artır (+1) / Azalt (−1): kanonik kodun sayı bölümlerinde ondalık basamak sayısını
    değiştirir. Genel biçimde (Excel gibi) değerin şu anki görünen ondalık sayısından başlar."""
    k = kod_coz(kod or "General")
    if k.genel_mi:
        n = 0
        if isinstance(deger, float) and not isinstance(deger, bool):
            g = goster(deger)
            if "E" not in g and "," in g:
                n = len(g.split(",")[1])
        n = max(0, n + fark)
        return "0" if n == 0 else "0." + "0" * n
    yeni = []
    for b in k.bolumler:
        if b.tur != "sayi" or b.duzen.kesir is not None:
            yeni.append(_bolum_yaz(b, False))
            continue
        og = list(b.ogeler)
        nokta_i = next((i for i, t in enumerate(og) if t[0] == "nokta"), None)
        us_i = next((i for i, t in enumerate(og) if t[0] == "us"), len(og))
        if fark > 0:
            if nokta_i is None:
                son_ph = max(i for i, t in enumerate(og[:us_i]) if t[0] == "ph")
                og[son_ph + 1:son_ph + 1] = [("nokta", ".")] + [("ph", "0")] * fark
            else:
                son = max(i for i, t in enumerate(og[:us_i]) if t[0] in ("ph", "nokta"))
                og[son + 1:son + 1] = [("ph", "0")] * fark
        elif nokta_i is not None:
            for _ in range(-fark):
                phs = [i for i in range(nokta_i + 1, us_i) if og[i][0] == "ph"]
                if not phs:
                    break
                del og[phs[-1]]
                us_i -= 1
            if not any(og[i][0] == "ph" for i in range(nokta_i + 1, us_i)):
                del og[nokta_i]
        yeni.append(_bolum_yaz(Bolum(b.tur, tuple(og), b.renk, b.renk_adi, b.kosul), False))
    return ";".join(yeni)
