"""Hata değerinin Türkçe açıklaması (T8; tasarım `t8_tasarim.md`). Qt yok.

Hesap yoluna dokunmaz: kullanıcı hatalı hücreye bakınca formül **yeniden** değerlendirilir ve hatanın
doğduğu yer aranır. Her düğümde "sonucu bu hatayı taşıyan ilk çocuk"a inilir; hiçbir çocuk taşımıyorsa
hata o düğümde doğmuştur. Düğüm başka bir hücreyi gösteriyorsa (başvuru, ad, aralık) o hücreye geçilir
ve aynı arama orada sürer (zincir). Excel de nedeni saklamaz; "Hatayı İzle" istenince hesaplar.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ..metin_tr import kucuk
from ..model.adres import Aralik, hucre_yaz
from ..model.deger import Hata
from ..model.gosterim import HATA_TR, goster
from . import adlar, fonksiyonlar
from .agac import KESISIM, Ad, Cagri, Ikili, Ref, Sabit, Tekli, Yuzde
from .degerler import AralikDeger, Bekle, Dizi
from .degerlendir import Baglam, ad_agaci, ad_coz, degerlendir
from .donustur import sayiya
from .sozcuk import sayfa_oneki

ZINCIR_SINIRI = 2_000           # en çok halka: halka başına ≈ 45 µs → ≈ 0,1 sn (çok uzun zincirde arama durur)


UZUN = "Zincir çok uzun; kaynak bulunamadı."


@dataclass(frozen=True)
class Halka:
    """Zincirin bir hücresi. `neden` yalnız son halkada (hatanın doğduğu hücre) doludur."""
    sayfa: object
    satir: int
    sutun: int
    kod: str
    neden: Optional[str] = None


# --- işlevin kendi ürettiği hatalar (argümanında o hata yok); ezbere değil, işlevin davranışından ---
_ARAMA = ("VLOOKUP", "HLOOKUP", "MATCH", "XLOOKUP", "XMATCH")
_ISLEV_NEDENI: Dict[Tuple[str, str], str] = {
    **{(f, "#N/A"): "{ad} aranan değeri ({ilk}) bulamadı." for f in _ARAMA},
    ("INDEX", "#REF!"): "{ad}: satır ya da sütun numarası aralığın dışında.",
    ("SQRT", "#NUM!"): "{ad} negatif sayı aldı ({ilk}).",
    ("LN", "#NUM!"): "{ad} sıfır ya da negatif sayı aldı ({ilk}).",
    ("LOG", "#NUM!"): "{ad} sıfır ya da negatif sayı aldı ({ilk}).",
    ("LOG10", "#NUM!"): "{ad} sıfır ya da negatif sayı aldı ({ilk}).",
    ("AVERAGE", "#DIV/0!"): "{ad}: ortalaması alınacak sayı yok.",
    ("AVERAGEIF", "#DIV/0!"): "{ad}: koşula uyan sayı yok.",
    ("AVERAGEIFS", "#DIV/0!"): "{ad}: koşullara uyan sayı yok.",
    ("MOD", "#DIV/0!"): "{ad}: bölen sıfır.",
    ("NA", "#N/A"): "{ad} işlevi bilerek {tr} üretir.",
    ("INDIRECT", "#REF!"): "{ad}: verilen metin geçerli bir başvuru değil.",
    ("OFFSET", "#REF!"): "{ad}: sonuç sayfanın dışına taşıyor.",
}
# argümanındaki aralığın içinde aynı hata olsa bile hatayı kendisi üretebilen işlevler: aralık suçlanmaz
_KENDI_HATASI = {(f, "#N/A") for f in _ARAMA} | {("INDEX", "#REF!")}

_GENEL = {
    "#DIV/0!": "Sıfıra bölme.",
    "#N/A": "Değer bulunamadı ya da yok.",
    "#NAME?": "Formülde tanınmayan bir ad var.",
    "#NULL!": "Aralıklar kesişmiyor.",
    "#NUM!": "Geçersiz sayısal değer ya da sonuç (çok büyük sayı, negatif sayının kökü vb.).",
    "#REF!": "Geçersiz hücre başvurusu (silinmiş hücre ya da sayfa).",
    "#VALUE!": "Değerin türü uygun değil (ör. sayı yerine metin).",
    "#SPILL!": "Dizi sonucunun yayılacağı hücrelerden biri dolu ya da birleşik (veya sayfa sınırı aşılıyor).",
    "#CALC!": "Dizi sonucu boş (ör. FİLTRE koşula uyan satır bulamadı).",
}


class _Arayici:
    def __init__(self, hedef_sayfa):
        self.hedef = hedef_sayfa
        self._tarama: Dict[tuple, Optional[Tuple[int, int]]] = {}
        self._hatalar: Dict[int, List[Tuple[int, int, str]]] = {}     # sayfa → hata hücreleri (sıralı)

    # --- yardımcılar ---
    def adres(self, sayfa, r: int, c: int) -> str:
        a = hucre_yaz(r, c)
        return a if sayfa is self.hedef else sayfa_oneki(sayfa.ad) + a

    def _hata_hucreleri(self, s) -> List[Tuple[int, int, str]]:
        """Sayfadaki hata değerli hücreler (satır, sütun sırasıyla); çağrı başına sayfada bir geçiş."""
        liste = self._hatalar.get(id(s))
        if liste is None:
            liste = [(k[0], k[1], v.kod) for k, v in s._sonuc.items() if type(v) is Hata]   # formül sonuçları
            liste += [(k[0], k[1], h.deger.kod) for k, h in s._hucreler.items()             # elle yazılmış hatalar
                      if type(h.deger) is Hata and h.formul is None]
            liste.sort()
            self._hatalar[id(s)] = liste
        return liste

    def aralik_hatasi(self, ar: AralikDeger, kod: str) -> Optional[Tuple[int, int]]:
        """Aralıkta `kod` hatasını taşıyan ilk (satır, sütun sırasıyla) hücre."""
        s = ar.sayfa
        if ar.r1 == ar.r2 and ar.c1 == ar.c2:                # tek hücre: doğrudan bak
            h = s._hucreler.get((ar.r1, ar.c1))
            if h is None:
                return None
            v = h.deger if h.formul is None else s._sonuc.get((ar.r1, ar.c1))
            return (ar.r1, ar.c1) if type(v) is Hata and v.kod == kod else None
        anahtar = (id(s), ar.r1, ar.c1, ar.r2, ar.c2, kod)
        if anahtar not in self._tarama:
            self._tarama[anahtar] = next(
                ((r, c) for r, c, k in self._hata_hucreleri(s)
                 if k == kod and ar.r1 <= r <= ar.r2 and ar.c1 <= c <= ar.c2), None)
        return self._tarama[anahtar]

    def tasir(self, v, kod: str):
        """`v` bu hatayı taşıyor mu: 'deger' (skaler/dizi), ('hucre', sayfa, r, c) (aralık) ya da None."""
        if isinstance(v, Hata):
            return "deger" if v.kod == kod else None
        if isinstance(v, Dizi):
            return "deger" if any(isinstance(x, Hata) and x.kod == kod for s in v.satirlar for x in s) else None
        if isinstance(v, AralikDeger):
            h = self.aralik_hatasi(v, kod)
            return None if h is None else ("hucre", v.sayfa, h[0], h[1])
        return None

    # --- arama ---
    def izle(self, d, b: Baglam, kod: str):
        """('hucre', sayfa, r, c) — hata o hücreden geliyor; ('neden', metin) — burada doğdu;
        ('belirsiz',) — yeniden değerlendirme bu hatayı vermedi (değişken işlev)."""
        if type(d) is Ad:
            return self._ad(d, b, kod)
        cocuklar = _cocuklar(d)
        degerler = [degerlendir(x, b) for x in cocuklar]
        sonra = []                                           # aralıkla taşıyanlar (ikinci öncelik)
        kendi = type(d) is Cagri and (d.ad.upper(), kod) in _KENDI_HATASI
        for x, v in zip(cocuklar, degerler):
            t = self.tasir(v, kod)
            if t == "deger":
                return self.izle(x, b, kod)
            if t is not None and not kendi:
                sonra.append(x)
        if sonra:
            return self.izle(sonra[0], b, kod)
        v = degerlendir(d, b)                                # yalnız hiçbir çocuk taşımıyorsa
        t = self.tasir(v, kod)
        if t is None:
            return ("belirsiz",)
        if isinstance(t, tuple):
            return t
        return ("neden", self.neden(d, b, kod, degerler))

    def _ad(self, d: Ad, b: Baglam, kod: str):
        agac, tanim = ad_coz(d.ad, b)
        if tanim is None:
            return ("neden", f"'{d.ad}' adı tanımlı değil.")
        if agac is None:
            return ("neden", f"'{d.ad}' adının formülü çözümlenemedi.")
        anahtar = tanim.anahtar()
        if anahtar in b.ad_yigini:
            return ("neden", f"'{d.ad}' adı kendine başvuruyor.")
        return self.izle(agac, Baglam(b.sayfa, b.satir, b.sutun, b.kitap, b.ad_yigini + (anahtar,)), kod)

    def neden(self, d, b: Baglam, kod: str, degerler: list) -> str:
        t = type(d)
        tr = HATA_TR.get(kod, kod)
        if t is Sabit:
            return "Başvurulan hücreler silinmiş." if kod == "#REF!" else f"Formüle {tr} değeri yazılmış."
        if t is Ref:
            return "Başvurulan sayfa silinmiş." if kod == "#REF!" else _GENEL.get(kod, "")
        if t in (Ikili, Tekli, Yuzde):
            islec = d.islec if t is not Yuzde else "%"
            if t is Ikili and islec == KESISIM:
                return "İki aralığın ortak hücresi yok."
            if t is Ikili and islec == ":":
                return "Aralık işleci (:) iki ucunda da hücre başvurusu ister."
            isl = [d.a, d.b] if t is Ikili else [d.x]
            if kod == "#VALUE!":
                for x, v in zip(isl, degerler):
                    yer = self._metin_yeri(x, v, b)
                    if yer:
                        return yer
            if kod == "#DIV/0!" and t is Ikili and islec == "/":
                bolen = "Bölen"
                if type(d.b) is Ref and d.b.basvuru.r1 == d.b.basvuru.r2 and d.b.basvuru.c1 == d.b.basvuru.c2:
                    s = b.sayfa_bul(d.b.basvuru.sayfa)
                    if s is not None:
                        bolen += f" ({self.adres(s, d.b.basvuru.r1, d.b.basvuru.c1)})"
                return f"{bolen} sıfır ya da boş."
            if t is Ikili and islec == "^":
                if kod == "#DIV/0!":
                    return "Sıfırın negatif kuvveti tanımsız."
                if kod == "#NUM!":
                    return "Üs alma tanımsız ya da sonuç çok büyük (ör. 0^0, negatif sayının kesirli kuvveti)."
            if kod == "#NUM!":
                return "Sonuç hesaplanamayacak kadar büyük."
            return _GENEL.get(kod, "")
        if t is Cagri:
            return self._islev(d, b, kod, degerler)
        return _GENEL.get(kod, "")

    def _metin_yeri(self, x, v, b: Baglam) -> Optional[str]:
        """İşlenen sayıya çevrilemeyen metinse nerede olduğunu söyler."""
        if isinstance(v, AralikDeger):
            if v.r1 == v.r2 and v.c1 == v.c2:
                h = v.hucre_degeri(v.r1, v.c1)
                if isinstance(h, str) and isinstance(sayiya(h), Hata):
                    return f"{self.adres(v.sayfa, v.r1, v.c1)} hücresinde sayı yerine metin var ({_kisa(h)})."
                return None
            for r, c, hc in v.sayfa.aralikta(Aralik(v.r1, v.c1, v.r2, v.c2)):
                h = hc.deger if hc.formul is None else v.sayfa._sonuc.get((r, c))
                if isinstance(h, str) and isinstance(sayiya(h), Hata):
                    return f"{self.adres(v.sayfa, r, c)} hücresinde sayı yerine metin var ({_kisa(h)})."
            return None
        if isinstance(v, str) and isinstance(sayiya(v), Hata):
            return f"Formülde sayı yerine metin var ({_kisa(v)})."
        return None

    def _islev(self, d: Cagri, b: Baglam, kod: str, degerler: list) -> str:
        ad_en = d.ad.upper()
        ad = adlar.turkcesi(ad_en)
        tanim = fonksiyonlar.bul(ad_en)
        if tanim is None:
            return f"'{ad}' adlı bir işlev yok."
        n = len(d.argumanlar)
        if n < tanim.en_az or (tanim.en_cok is not None and n > tanim.en_cok):
            if tanim.en_cok == tanim.en_az:
                beklenen = f"{tanim.en_az}"
            elif tanim.en_cok is None:
                beklenen = f"en az {tanim.en_az}"
            else:
                beklenen = f"{tanim.en_az}–{tanim.en_cok}"
            return f"{ad} {beklenen} bağımsız değişken ister; {n} verildi."
        sablon = _ISLEV_NEDENI.get((ad_en, kod))
        if sablon:
            ilk = _kisa(_skaler(degerler[0])) if degerler else ""
            return sablon.format(ad=ad, ilk=ilk, tr=HATA_TR.get(kod, kod))
        if kod == "#VALUE!" and not tanim.uygula.__module__.endswith(".metin"):
            for x, v in zip(d.argumanlar, degerler):
                yer = self._metin_yeri(x, v, b)
                if yer:
                    return f"{ad}: {_kucuk_bas(yer) if yer.startswith('Formülde') else yer}"
        return f"{ad}: {_kucuk_bas(_GENEL.get(kod, ''))}"


def _kucuk_bas(m: str) -> str:
    """Cümlenin ilk harfi küçük (işlev adından sonra gelince). Yalnız kendi cümlelerimizde kullanılır
    (hücre adresi/sayfa adıyla başlayanlarda değil)."""
    return kucuk(m[:1]) + m[1:]


def _cocuklar(d) -> list:
    t = type(d)
    if t is Ikili:
        return [d.a, d.b]
    if t in (Tekli, Yuzde):
        return [d.x]
    if t is Cagri:
        return list(d.argumanlar)
    return []


def _skaler(v):
    if isinstance(v, AralikDeger):
        try:
            return v.hucre_degeri(v.r1, v.c1)
        except Bekle:
            return None
    if isinstance(v, Dizi):
        return v.satirlar[0][0] if v.satirlar and v.satirlar[0] else None
    return v


def _kisa(v) -> str:
    m = goster(v) if not isinstance(v, str) else v
    if len(m) > 30:
        m = m[:29] + "…"
    return f'"{m}"' if isinstance(v, str) else m


# ---------------------------------------------------------------- dış arayüz
def acikla(sayfa, satir: int, sutun: int, sinir: int = ZINCIR_SINIRI, motor=None) -> Optional[List[Halka]]:
    """Hücre hata değeri taşıyorsa zincir (ilk halka bu hücre, son halka hatanın doğduğu hücre);
    hata yoksa None. `motor` verilirse onun ayrıştırılmış ağaçları kullanılır (uzun zincirde hızlı).
    Hiçbir koşulda istisna atmaz (arayüz ipucu bozulmasın)."""
    try:
        return _acikla(sayfa, satir, sutun, sinir, motor)
    except (Bekle, RecursionError):
        return None
    except Exception:                       # tanı asla programı düşürmesin
        return None


def _tasma_nedeni(sayfa, satir: int, sutun: int, motor, ara) -> str:
    kutu = motor._tasma_alan.get((sayfa.kimlik, satir, sutun)) if motor is not None else None
    if kutu is None:
        return _GENEL["#SPILL!"]
    r1, c1, r2, c2 = kutu
    if r2 > 1_048_576 or c2 > 16_384:
        return "Dizi sonucu sayfa sınırını aşıyor."
    sayac = 0
    for r in range(r1, r2 + 1):
        for c in range(c1, c2 + 1):
            if (r, c) == (satir, sutun):
                continue
            sayac += 1
            if sayac > 20_000:
                return _GENEL["#SPILL!"]
            h = sayfa.hucre(r, c)
            if h is not None and getattr(h, "sahip", None) != (satir, sutun):
                return f"Dizi sonucu yayılamıyor: {ara.adres(sayfa, r, c)} hücresi dolu."
            if (r, c) in sayfa._birlesim_idx:
                return f"Dizi sonucu yayılamıyor: {ara.adres(sayfa, r, c)} birleşik bir hücre."
    return _GENEL["#SPILL!"]


def _deger(sayfa, r, c):
    h = sayfa.hucre(r, c)
    if h is None:
        return None, None
    return h, (h.deger if h.formul is None else sayfa.sonuc(r, c))


def _acikla(sayfa, satir, sutun, sinir, motor):
    h, v = _deger(sayfa, satir, sutun)
    if not isinstance(v, Hata):
        return None
    kod = v.kod
    ara = _Arayici(sayfa)
    if kod == "#SPILL!" and h is not None and h.formul is not None:          # taşma engeli: yayılacak alandaki ilk dolu hücre
        return [Halka(sayfa, satir, sutun, kod, _tasma_nedeni(sayfa, satir, sutun, motor, ara))]
    zincir: List[Halka] = []
    gorulen = set()
    s, r, c = sayfa, satir, sutun
    while True:
        if len(zincir) >= sinir:
            zincir.append(Halka(s, r, c, kod, UZUN))
            return zincir
        gorulen.add((id(s), r, c))
        h, v = _deger(s, r, c)
        if h is None or not isinstance(v, Hata) or v.kod != kod:
            zincir.append(Halka(s, r, c, kod, "Nedeni belirlenemedi."))
            return zincir
        if h.formul is None:
            zincir.append(Halka(s, r, c, kod, f"Hücreye {HATA_TR.get(kod, kod)} değeri yazılmış."))
            return zincir
        agac = motor.agac((s.kimlik, r, c), h.formul) if motor is not None else ad_agaci(h.formul)
        if agac is None:
            zincir.append(Halka(s, r, c, kod, "Formül çözümlenemedi."))
            return zincir
        sonuc = ara.izle(agac, Baglam(s, r, c, s.kitap), kod)
        if sonuc[0] == "belirsiz":                       # değişken işlev (ör. S_SAYI_ÜRET) başka sonuç verdi
            zincir.append(Halka(s, r, c, kod, "Nedeni belirlenemedi (sonuç her hesapta değişebilir)."))
            return zincir
        if sonuc[0] == "neden":
            zincir.append(Halka(s, r, c, kod, sonuc[1] or _GENEL.get(kod, "")))
            return zincir
        zincir.append(Halka(s, r, c, kod))
        _, s, r, c = sonuc
        if (id(s), r, c) in gorulen:
            zincir.append(Halka(s, r, c, kod, "Döngüsel zincir; kaynak bulunamadı."))
            return zincir


def metin(zincir: Optional[List[Halka]], hedef_sayfa=None) -> str:
    """İpucu/durum çubuğu metni: `#DEĞER!: B3 hücresinde sayı yerine metin var.`; başka hücreden
    geliyorsa `#DEĞER!: A1 hücresinden geliyor (C5 → B3 → A1). A1: …`."""
    if not zincir:
        return ""
    ilk, son = zincir[0], zincir[-1]
    hedef = hedef_sayfa if hedef_sayfa is not None else ilk.sayfa
    ara = _Arayici(hedef)
    tr = HATA_TR.get(son.kod, son.kod)
    if len(zincir) == 1:
        return f"{tr}: {son.neden}"
    kaynak = ara.adres(son.sayfa, son.satir, son.sutun)
    if son.neden == UZUN:
        return (f"{tr}: başka hücrelerden geliyor; zincir çok uzun ({len(zincir) - 1} hücre izlendi, "
                f"son izlenen: {kaynak}), kaynak bulunamadı.")
    if len(zincir) <= 6:
        yol = " → ".join(ara.adres(h.sayfa, h.satir, h.sutun) for h in zincir)
    else:
        bas = [ara.adres(h.sayfa, h.satir, h.sutun) for h in zincir[:2]]
        yol = " → ".join(bas + ["…", kaynak])
    return f"{tr}: {kaynak} hücresinden geliyor ({yol}). {kaynak}: {son.neden}"
