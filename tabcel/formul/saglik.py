"""Tablo Sağlık Kontrolü (Faz 9c): tüm çalışma kitabını tarayıp yaygın hataları bulan denetçi. Qt yok.

**Kesin kural (CLAUDE.md kural 17):** denetçi hiçbir hücreyi değiştirmez; yalnız `Bulgu` üretir. Düzeltme önerisi (`Duzeltme`) ancak
kullanıcı onayladığında `duzeltme_komutu` ile geri alınabilir bir komuta çevrilir.

Tarama bir **üreteçtir** (`Tarayici.calistir`): işi küçük dilimlere böler ve ilerleme bildirir; arayüz onu zamanlayıcıyla sürerek
donmadan çalıştırır, istediği an bırakarak iptal eder. Yanlış alarm düşük tutulur (kullanıcı gürültülü denetçiyi kapatır): her
kontrolün neyi bilerek saymadığı kendi bölümünde yazılıdır; belirsizlikte bulgu verilmez ya da `bilgi` düzeyinde verilir.

Kontroller (önem sırasıyla): eksik_aralik, hata, gecersiz_kimlik (kritik); tutarsiz_formul, metin_sayi (uyarı); sabit_sayi,
bos_basvuru, yinelenen_satir (bilgi)."""
import json
import re
import time
from dataclasses import dataclass, field, replace
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

from .. import veri_klasoru
from ..io import csv_io
from ..metin_tr import kucuk
from ..model import deger as D
from ..model import girdi, kimlik
from ..model.adres import hucre_yaz, sutun_harfe
from ..model.deger import Hata
from ..model.gosterim import goster
from ..model.komutlar import Grup, HucrelerDegis
from ..model.sayfa import Hucre, TasmaHucre
from . import ceviri, hata_neden
from .agac import Ad, Bos, Cagri, Dugum, Ikili, Ref, Sabit, Tekli, Yuzde
from .kaydir import _donustur, kopyala
from .sozcuk import BASVURU, FormulHatasi, sozcukle
from .yerel import SAKLI

KRITIK, UYARI, BILGI = "kritik", "uyari", "bilgi"
ONEM_ADLARI = {KRITIK: "Kritik", UYARI: "Uyarı", BILGI: "Bilgi"}

# (kimlik, ad, önem, kısa açıklama) — ayarlar penceresi ve rapor bu listeden okur
KONTROLLER = (
    ("eksik_aralik", "Eksik aralık", KRITIK, "TOPLA/ORTALAMA/SAY… aralığının hemen bitişiğindeki veri toplamaya katılmıyor"),
    ("hata", "Hata değerleri", KRITIK, "#DEĞER!, #BAŞV!, #SAYI/0! gibi hata veren hücreler ve hatanın kaynağı"),
    ("gecersiz_kimlik", "Geçersiz kimlik verisi", KRITIK, "T.C. kimlik no, vergi no ve IBAN sütunlarında algoritmaya uymayan değerler"),
    ("tutarsiz_formul", "Tutarsız formül", UYARI, "Komşu formüllerle aynı desende olması gereken ama farklı olan formül"),
    ("metin_sayi", "Metin olarak saklanan sayı", UYARI, "Sayıya benzeyen ama metin olan değerler (IBAN, T.C. no, telefon hariç)"),
    ("sabit_sayi", "Formül içinde sabit sayı", BILGI, "Formüle elle yazılmış sayılar (ör. =B5*1,18)"),
    ("bos_basvuru", "Boş hücreye başvuru", BILGI, "Formülün veri arasındaki boş bir hücreyi kullanması"),
    ("yinelenen_satir", "Yinelenen satırlar", BILGI, "Tamamen aynı olan satırlar"),
)
KONTROL_ADI = {k: a for k, a, _, _ in KONTROLLER}
KONTROL_ONEMI = {k: o for k, _, o, _ in KONTROLLER}

VARSAYILAN_SABITLER = (-1.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0, 12.0, 24.0, 30.0, 60.0, 100.0, 1000.0, 0.5, 365.0)
_TOPLAMA = {"SUM", "AVERAGE", "COUNT", "COUNTA", "MAX", "MIN"}
_KIMLIK_BASLIK = {"tc": ("tc", "t.c", "tckn", "tc kimlik", "kimlik no", "kimlik numarasi", "t c"), "vkn": ("vergi no", "vergi kimlik", "vkn", "vergi numarasi"),
                  "iban": ("iban",)}
_KIMLIK_METIN_BASLIK = ("tel", "telefon", "gsm", "cep", "kod", "posta", "barkod", "sicil", "hesap no", "seri no", "sira no", "no")


# ------------------------------------------------------------------ ayarlar
@dataclass
class Ayarlar:
    acik: Dict[str, bool] = field(default_factory=lambda: {k: True for k, *_ in KONTROLLER})
    sabit_yoksay: Tuple[float, ...] = VARSAYILAN_SABITLER

    def acik_mi(self, kontrol: str) -> bool:
        return self.acik.get(kontrol, True)


def _ayar_yolu():
    return veri_klasoru() / "saglik_ayarlari.json"


def ayarlari_oku() -> Ayarlar:
    a = Ayarlar()
    try:
        d = json.loads(_ayar_yolu().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return a
    if isinstance(d, dict):
        for k, v in (d.get("acik") or {}).items():
            if k in a.acik and isinstance(v, bool):
                a.acik[k] = v
        s = d.get("sabit_yoksay")
        if isinstance(s, list) and all(isinstance(x, (int, float)) for x in s):
            a.sabit_yoksay = tuple(float(x) for x in s)
    return a


def ayarlari_yaz(a: Ayarlar) -> None:
    try:
        yol = _ayar_yolu()
        yol.parent.mkdir(parents=True, exist_ok=True)
        gecici = yol.with_suffix(".tmp")
        gecici.write_text(json.dumps({"acik": a.acik, "sabit_yoksay": list(a.sabit_yoksay)}, ensure_ascii=False, indent=1),
                          encoding="utf-8")
        gecici.replace(yol)
    except OSError:
        pass


# ------------------------------------------------------------------ bulgu
@dataclass
class Duzeltme:
    tur: str                                  # "metni_sayiya" | "aralik_genislet" | "formul_esitle"
    aciklama: str                             # kullanıcıya gösterilen tam değişiklik
    veri: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Bulgu:
    kontrol: str
    onem: str
    sayfa_kimlik: int
    sayfa_ad: str
    hucreler: List[Tuple[int, int]]           # ilk hücre = konum; gruplanan bulgularda üyeler
    baslik: str
    aciklama: str                             # ne bulundu
    neden: str                                # neden sorun olabilir (sade Türkçe)
    duzeltme: Optional[Duzeltme] = None
    anahtar: str = ""                         # yoksayma anahtarı (kontrol|sayfa|ilk hücre|ek)

    @property
    def konum(self) -> Tuple[int, int]:
        return self.hucreler[0]

    @property
    def adet(self) -> int:
        return len(self.hucreler)

    @property
    def adres(self) -> str:
        return f"{self.sayfa_ad}!{hucre_yaz(*self.konum)}"


def _anahtar(kontrol: str, sayfa_ad: str, hucre: Tuple[int, int], ek: str = "") -> str:
    return f"{kontrol}|{sayfa_ad}|{hucre_yaz(*hucre)}" + (f"|{ek}" if ek else "")


# ------------------------------------------------------------------ yardımcılar
def _gez(d: Dugum):
    """(düğüm, ebeveyn) çiftleri; ebeveyn kökte None."""
    yigin = [(d, None)]
    while yigin:
        x, p = yigin.pop()
        yield x, p
        if isinstance(x, Cagri):
            yigin.extend((a, x) for a in x.argumanlar)
        elif isinstance(x, Ikili):
            yigin.append((x.b, x))
            yigin.append((x.a, x))
        elif isinstance(x, (Tekli, Yuzde)):
            yigin.append((x.x, x))


_ASCII = str.maketrans("ıçğöşüâîû", "icgosuaiu")


def _sade(metin: str) -> str:
    """Başlık eşlemesi için: Türkçe küçük harf + aksansız (`IBAN` → `iban`, `Şehir` → `sehir`)."""
    return kucuk(metin).translate(_ASCII)


def _sayi_mi(v) -> bool:
    return isinstance(v, float) and not isinstance(v, bool)


def _desen(formul: str, r: int, c: int) -> Optional[Tuple[str, str]]:
    """(tam desen, iskelet): başvurular konuma göre GÖRELİ yazılır (R[-1]C[0] gibi; mutlak olanlar sabit). İskelet: başvurular `#`."""
    if not formul.startswith("="):
        return None
    try:
        soz = sozcukle(formul[1:], SAKLI)
    except FormulHatasi:
        return None
    tam, iskelet = [], []
    for s in soz:
        if s.tur == BASVURU:
            b = s.deger

            def kordinat(n, mutlak, merkez):
                return f"${n}" if mutlak else f"[{n - merkez}]"
            kisa = f"{b.sayfa if b.sayfa is not None else ''}!R{kordinat(b.r1, b.r1m, r)}C{kordinat(b.c1, b.c1m, c)}"
            if b.tur in ("aralik", "sutun", "satir"):
                kisa += f":R{kordinat(b.r2, b.r2m, r)}C{kordinat(b.c2, b.c2m, c)}"
            tam.append(kisa)
            iskelet.append("#")
        else:
            tam.append(s.metin)
            iskelet.append(s.metin)
    return "".join(tam), "".join(iskelet)


def _ust_baslik_mi(sayfa, r: int, c: int) -> bool:
    """(r, c) bir başlık satırında mı: aynı satırda başka metin hücreleri var ve üstü boş (sayı gibi görünen başlıklar: yıl vb.)."""
    for cc in (c - 2, c - 1, c + 1, c + 2):
        v = sayfa.deger(r, cc) if cc >= 1 else None
        if isinstance(v, str) and v.strip():
            return sayfa.deger(r - 1, c) in (None, "") if r > 1 else True
    return False


# ------------------------------------------------------------------ tarayıcı
class Tarayici:
    """Kitabı tarar; `calistir()` bir üreteçtir: `("ilerleme", 0..1, "metin")` ve `("bulgu", Bulgu)` demetleri verir."""

    def __init__(self, kitap, motor, ayarlar: Optional[Ayarlar] = None, yoksay: Optional[Set[str]] = None):
        self.kitap, self.motor = kitap, motor
        self.ayarlar = ayarlar or Ayarlar()
        self.yoksay = yoksay if yoksay is not None else set()
        self.yoksayilan = 0
        self._son = time.perf_counter()
        self._toplama = None                               # eksik_aralik: tüm kitabın toplama aralıkları (bir kez kurulur)
        self._kapsam = None

    def _ritim(self) -> bool:
        """Son nabızdan beri ≥ 10 ms geçtiyse True: kontrol `yield None` ile arayüze döner (donma yok, iptal mümkün)."""
        t = time.perf_counter()
        if t - self._son >= 0.010:
            self._son = t
            return True
        return False

    # --- genel akış
    def calistir(self) -> Iterator[tuple]:
        sayfalar = list(self.kitap.sayfalar)
        adimlar = [(s, k) for s in sayfalar for k, *_ in KONTROLLER if self.ayarlar.acik_mi(k)]
        toplam = max(1, len(adimlar))
        for i, (sayfa, kontrol) in enumerate(adimlar):
            yield ("ilerleme", i / toplam, f"{sayfa.ad}: {KONTROL_ADI[kontrol]}")
            for b in getattr(self, "_k_" + kontrol)(sayfa):
                if b is None:
                    yield ("ritim",)
                    continue
                if b.anahtar in self.yoksay:
                    self.yoksayilan += 1
                    continue
                yield ("bulgu", b)
        yield ("ilerleme", 1.0, "Bitti")

    def tara(self) -> List[Bulgu]:
        """Hepsini bir seferde (testler ve küçük kitaplar için)."""
        return [x[1] for x in self.calistir() if x[0] == "bulgu"]

    # --- ortak veri
    def _formuller(self, sayfa):
        for (r, c), h in sayfa._hucreler.items():
            if h.formul is not None:
                yield r, c, h, self.motor.agac((sayfa.kimlik, r, c), h.formul)

    def _sayfa_ve_hedef(self, sayfa, b):
        if b.sayfa is None:
            return sayfa
        if isinstance(b.sayfa, int):
            return self.kitap.sayfa_kimlikle(b.sayfa)
        ad = kucuk(str(b.sayfa))
        return next((x for x in self.kitap.sayfalar if kucuk(x.ad) == ad), None)

    def _bulgu(self, kontrol, sayfa, hucreler, baslik, aciklama, neden, duzeltme=None, ek="") -> Bulgu:
        return Bulgu(kontrol, KONTROL_ONEMI[kontrol], sayfa.kimlik, sayfa.ad, list(hucreler), baslik, aciklama, neden, duzeltme,
                     _anahtar(kontrol, sayfa.ad, hucreler[0], ek))

    # =========================================================== 1. eksik aralık
    def _toplama_araliklari(self, sayfa, sonuc):
        """Bu sayfadaki formüllerin toplama türü işlevlere verdiği aralıkları `sonuc` listesine ekler:
        (hedef sayfa, ana hücre, işlev, başvuru, ana sayfa). Üreteçtir (nabız verir)."""
        for r, c, h, agac in self._formuller(sayfa):
            if self._ritim():
                yield None
            if agac is None:
                continue
            for x, _ in _gez(agac):
                if isinstance(x, Cagri) and x.ad in _TOPLAMA:
                    for a in x.argumanlar:
                        if isinstance(a, Ref) and a.basvuru.tur == "aralik":
                            hedef = self._sayfa_ve_hedef(sayfa, a.basvuru)
                            if hedef is not None:
                                sonuc.append((hedef, (r, c), x.ad, a.basvuru, sayfa))

    def _k_eksik_aralik(self, sayfa) -> Iterator[Bulgu]:
        if self._toplama is None:                                # kapsama dizini tüm sayfalardan (başka sayfadan toplama da sayılır); bir kez
            tum = []
            for s in self.kitap.sayfalar:
                yield from self._toplama_araliklari(s, tum)
            kapsam: Dict[Tuple[int, int], List[Tuple[int, int, tuple]]] = {}      # (sayfa kimliği, sütun) → [(r1, r2, ana)]
            for hedef, ana, _fn, b, ana_sayfa in tum:
                for cc in range(b.c1, min(b.c2, b.c1 + 60) + 1):
                    kapsam.setdefault((hedef.kimlik, cc), []).append((b.r1, b.r2, (ana_sayfa.kimlik, ana)))
            self._toplama, self._kapsam = tum, kapsam
        tum, kapsam = self._toplama, self._kapsam
        for hedef, ana, fn, b, ana_sayfa in tum:
            if self._ritim():
                yield None
            if ana_sayfa is not sayfa:
                continue
            tek_sutun, tek_satir = b.c1 == b.c2 and b.r2 > b.r1, b.r1 == b.r2 and b.c2 > b.c1
            if not (tek_sutun or tek_satir):
                continue
            ana_k = (ana_sayfa.kimlik, ana)
            adaylar = ([(b.r2 + 1, b.c1, 1, 0), (b.r1 - 1, b.c1, -1, 0)] if tek_sutun
                       else [(b.r1, b.c2 + 1, 0, 1), (b.r1, b.c1 - 1, 0, -1)])
            for r, c, dr, dc in adaylar:
                if r < 1 or c < 1 or not self._veri_hucresi(hedef, r, c, ana_k, kapsam):
                    continue
                if (dr == -1 or dc == -1) and _ust_baslik_mi(hedef, r, c):
                    continue
                # bitişik veri bloğunun sonu
                n, rr, cc = 0, r, c
                while n < 5000 and rr >= 1 and cc >= 1 and self._veri_hucresi(hedef, rr, cc, ana_k, kapsam):
                    n += 1
                    rr, cc = rr + dr, cc + dc
                son_r, son_c = rr - dr, cc - dc
                yeni = self._aralik_genislet(sayfa.kimlik, ana, b, son_r, son_c, dr, dc)
                ilk = hucre_yaz(r, c)
                bitis = hucre_yaz(son_r, son_c)
                aralik_eski = f"{hucre_yaz(b.r1, b.c1)}:{hucre_yaz(b.r2, b.c2)}"
                yon = "altında" if dr == 1 else "üstünde" if dr == -1 else "sağında" if dc == 1 else "solunda"
                fonk = ceviri.gosterime("=" + fn + "(A1)", self.kitap)[1:].split("(")[0]
                duz = None
                if yeni is not None:
                    duz = Duzeltme("aralik_genislet",
                                   f"{hucre_yaz(*ana)} formülündeki {aralik_eski} aralığı {self._yeni_aralik_metni(b, son_r, son_c, dr, dc)} olacak.",
                                   {"hucre": ana, "yeni_formul": yeni})
                yield self._bulgu(
                    "eksik_aralik", sayfa, [ana],
                    f"{fonk}({aralik_eski}) aralığının {yon} veri var",
                    f"{hucre_yaz(*ana)} hücresindeki {fonk} işlevi {aralik_eski} aralığını topluyor; aralığın hemen {yon}ki "
                    f"{ilk if n == 1 else ilk + ':' + bitis} hücre{'si' if n == 1 else 'leri'}nde de sayı var ama işleve katılmıyor.",
                    "Yeni eklenen satır/sütunlar toplama dahil edilmemiş olabilir; sonuç eksik çıkar.", duz)
                break

    def _veri_hucresi(self, hedef, r: int, c: int, ana_k, kapsam) -> bool:
        """Bitişik hücre toplanması beklenen bir veri mi: sayı olmalı; formül hücresinin kendisi, başka bir toplama formülü ya da
        başka bir toplama aralığının kapsadığı hücre DEĞİL (bilerek bölünmüş tablo)."""
        h = hedef._hucreler.get((r, c))
        if h is None or (hedef.kimlik, (r, c)) == ana_k:
            return False
        if type(h) is TasmaHucre:
            return False
        v = hedef.deger(r, c)
        if not _sayi_mi(v):
            return False
        if h.formul is not None:
            agac = self.motor.agac((hedef.kimlik, r, c), h.formul)
            if agac is None or isinstance(agac, Cagri) and agac.ad in _TOPLAMA | {"SUBTOTAL", "SUMPRODUCT", "SUMIF", "SUMIFS"}:
                return False
        for r1, r2, ana in kapsam.get((hedef.kimlik, c), ()):
            if r1 <= r <= r2 and ana != ana_k:
                return False
        return True

    def _yeni_aralik_metni(self, b, son_r, son_c, dr, dc) -> str:
        r1, c1, r2, c2 = b.r1, b.c1, b.r2, b.c2
        if dr == 1:
            r2 = son_r
        elif dr == -1:
            r1 = son_r
        elif dc == 1:
            c2 = son_c
        else:
            c1 = son_c
        return f"{hucre_yaz(r1, c1)}:{hucre_yaz(r2, c2)}"

    def _aralik_genislet(self, sayfa_kimlik: int, ana, b, son_r, son_c, dr, dc) -> Optional[str]:
        sayfa = self.kitap.sayfa_kimlikle(sayfa_kimlik)
        h = sayfa.hucre(*ana)
        yeni_r1, yeni_c1, yeni_r2, yeni_c2 = b.r1, b.c1, b.r2, b.c2
        if dr == 1:
            yeni_r2 = son_r
        elif dr == -1:
            yeni_r1 = son_r
        elif dc == 1:
            yeni_c2 = son_c
        else:
            yeni_c1 = son_c

        def f(x):
            if (x.tur, x.r1, x.c1, x.r2, x.c2, x.sayfa) == (b.tur, b.r1, b.c1, b.r2, b.c2, b.sayfa):
                return replace(x, r1=yeni_r1, c1=yeni_c1, r2=yeni_r2, c2=yeni_c2)
            return x
        return _donustur(h.formul, f)

    # =========================================================== 2. tutarsız formül
    def _k_tutarsiz_formul(self, sayfa) -> Iterator[Bulgu]:
        """Excel'in kuralı: iki yanı (üst-alt ya da sol-sağ) aynı desende olan bir formül kendisi farklıysa. Uç hücrede yalnız,
        önceki ≥ 3 hücre aynı desendeyse ve bu hücre aynı iskelette (aynı işlem yapısı) farklı başvuruysa. Toplam satırı gibi yapısı
        başka olan formüller (iskelet farklı) bilerek sayılmaz."""
        desen: Dict[Tuple[int, int], Tuple[str, str]] = {}
        for (r, c), h in sayfa._hucreler.items():
            if h.formul is not None:
                d = _desen(h.formul, r, c)
                if d is not None:
                    desen[(r, c)] = d
                if self._ritim():
                    yield None
        goruldu = set()
        for (r, c), (tam, iskelet) in sorted(desen.items()):
            if self._ritim():
                yield None
            for dr, dc in ((1, 0), (0, 1)):
                once, sonra = desen.get((r - dr, c - dc)), desen.get((r + dr, c + dc))
                komsu = None
                if once is not None and sonra is not None and once[0] == sonra[0] and tam != once[0]:
                    komsu = (r - dr, c - dc)                           # iki yanı aynı, bu farklı
                elif (once is not None and sonra is None and tam != once[0] and iskelet == once[1]
                      and all(desen.get((r - k * dr, c - k * dc), ("",))[0] == once[0] for k in (1, 2, 3))):
                    komsu = (r - dr, c - dc)                           # uç hücre
                if komsu is None or (r, c) in goruldu:
                    continue
                if (desen.get((r - 2 * dr, c - 2 * dc), ("",))[0] == tam or desen.get((r + 2 * dr, c + 2 * dc), ("",))[0] == tam):
                    continue                                          # dönüşümlü (periyodik) desen: kasıtlı
                goruldu.add((r, c))
                yeni = kopyala(sayfa.hucre(*komsu).formul, r - komsu[0], c - komsu[1])
                eski_g = ceviri.gosterime(sayfa.hucre(r, c).formul, self.kitap)
                yeni_g = ceviri.gosterime(yeni, self.kitap)
                yon = "sütundaki" if dc == 0 else "satırdaki"
                yield self._bulgu(
                    "tutarsiz_formul", sayfa, [(r, c)], f"{hucre_yaz(r, c)} formülü komşularından farklı",
                    f"{hucre_yaz(r, c)} hücresinde {eski_g} yazılı; aynı {yon} komşu formüller aynı desende ({yeni_g} olurdu).",
                    "Kopyalanırken ya da düzenlenirken kayan bir başvuru olabilir; sonuç yanlış çıkar.",
                    Duzeltme("formul_esitle", f"{hucre_yaz(r, c)} formülü {yeni_g} olacak (komşu formülün aynı deseni).",
                             {"hucre": (r, c), "yeni_formul": yeni}))

    # =========================================================== 3. metin olarak saklanan sayı
    def _k_metin_sayi(self, sayfa) -> Iterator[Bulgu]:
        sutunlar: Dict[int, List[Tuple[int, Hucre]]] = {}
        sayi_say: Dict[int, int] = {}
        for (r, c), h in sayfa._hucreler.items():
            if self._ritim():
                yield None
            if type(h) is TasmaHucre:
                continue
            if h.formul is None and isinstance(h.deger, str):
                sutunlar.setdefault(c, []).append((r, h))
            elif h.formul is None and _sayi_mi(h.deger):
                sayi_say[c] = sayi_say.get(c, 0) + 1
        for c, liste in sorted(sutunlar.items()):
            adaylar = []
            for r, h in sorted(liste):
                if self._ritim():
                    yield None
                m = h.deger.strip()
                if not m or csv_io.korunmali_mi(m) or kimlik.telefon_gecerli(m) or kimlik.tara_metin(m):
                    continue
                if sayfa.stil(r, c).sayi_bicimi == "@":                       # bilerek Metin biçimli
                    continue
                if not re.fullmatch(r"[-+]?[\d.,]+\s*(?:%|₺|TL|\$|€)?|%\s*[\d.,]+|[₺$€]\s*[\d.,]+", m):
                    continue
                hh, kod = girdi.akilli_coz(m)
                if hh is None or not _sayi_mi(hh.deger) or (kod and re.search(r"[dmyhs]", kod.replace("General", ""))):
                    continue
                adaylar.append((r, hh, kod))
            if not adaylar:
                continue
            baslik = self._sutun_basligi(sayfa, c, adaylar[0][0])
            kimlik_sutunu = any(a in _sade(baslik or "") for a in _KIMLIK_METIN_BASLIK) if baslik else False
            karisik = sayi_say.get(c, 0) >= 1 and sayi_say.get(c, 0) >= len(adaylar) // 3
            if kimlik_sutunu and not karisik:
                continue
            if not karisik and len(adaylar) < 3:
                continue
            ilk = adaylar[0][0]
            onem_bilgi = not karisik                                          # tüm sütun metinse genelde kod/numara: bilgi
            ornek = sayfa.hucre(ilk, c).deger.strip()
            b = self._bulgu(
                "metin_sayi", sayfa, [(r, c) for r, _, _ in adaylar],
                f"{sutun_harfe(c)} sütununda metin olarak saklanan {len(adaylar)} sayı",
                f"{hucre_yaz(ilk, c)} hücresi gibi {len(adaylar)} hücrede sayıya benzeyen değer metin olarak duruyor (örn. “{ornek}”).",
                "Metin olan sayılar toplama/ortalama gibi hesaplara katılmaz ve sıralamada yanlış yerde durur.",
                Duzeltme("metni_sayiya", f"{len(adaylar)} hücredeki metin sayıya çevrilecek (görünüm değişmez, hesaplamaya katılır).",
                         {"hucreler": [(r, c, hh.deger, kod) for r, hh, kod in adaylar]}))
            if onem_bilgi:
                b.onem = BILGI
            yield b

    def _sutun_basligi(self, sayfa, c: int, ilk_satir: int) -> Optional[str]:
        for r in range(ilk_satir - 1, max(0, ilk_satir - 60), -1):
            v = sayfa.deger(r, c)
            if isinstance(v, str) and v.strip():
                return v
        return None

    # =========================================================== 4. formül içinde sabit sayı
    def _k_sabit_sayi(self, sayfa) -> Iterator[Bulgu]:
        yok = set(self.ayarlar.sabit_yoksay)
        gruplar: Dict[Tuple[int, float], List[Tuple[int, int]]] = {}
        for r, c, h, agac in self._formuller(sayfa):
            if self._ritim():
                yield None
            if agac is None:
                continue
            bulunan = set()
            for x, p in _gez(agac):
                if not isinstance(x, Sabit) or not _sayi_mi(x.deger) or x.deger in yok:
                    continue
                if not isinstance(p, Ikili) or p.islec not in "+-*/^":
                    continue                                                  # yalnız işlem işleneni (işlev argümanı: sütun no, ondalık vb. değil)
                diger = p.b if p.a is x else p.a
                if any(isinstance(y, (Ref, Ad, Cagri)) for y, _ in _gez(diger)):
                    bulunan.add(x.deger)
            for v in bulunan:
                gruplar.setdefault((c, v), []).append((r, c))
        for (c, v), hucreler in sorted(gruplar.items()):
            hucreler.sort()
            r, _ = hucreler[0]
            sayi = goster(v)
            yield self._bulgu(
                "sabit_sayi", sayfa, hucreler, f"Formülde sabit sayı: {sayi}",
                f"{hucre_yaz(r, c)} formülünde elle yazılmış {sayi} sayısı var" + (f" ({len(hucreler)} hücrede)." if len(hucreler) > 1 else "."),
                "Oran/katsayı değişince (ör. KDV oranı) her formülü tek tek düzeltmeniz gerekir; ayrı bir hücreye yazıp başvurmak daha güvenlidir.",
                None, ek=sayi)

    # =========================================================== 5. hata değerleri
    def _k_hata(self, sayfa) -> Iterator[Bulgu]:
        """Kitap düzeyinde TEK sefer (ilk sayfada çalışır): her hata için KAYNAK hücre bulunur (`hata_neden`), aynı kaynaktan doğan
        hatalar tek bulguda toplanır (kaç hücreyi etkilediği yazılır); bulgu kaynak hücrenin sayfasına ve adresine bağlanır."""
        if sayfa is not self.kitap.sayfalar[0]:
            return
        gruplar: Dict[Tuple[int, int, int], dict] = {}
        say = 0
        for s in self.kitap.sayfalar:
            for r, c in sorted(s._hucreler):                                    # yalnız anahtarlar sıralanır (hızlı)
                h = s._hucreler[(r, c)]
                if self._ritim():
                    yield None
                v = s.deger(r, c)
                if not isinstance(v, Hata) or type(h) is TasmaHucre:
                    continue
                say += 1
                if say > 3000:                                                      # çok büyük hata yığını: ilk 3000'i çözümlenir
                    break
                if h.formul is None:
                    kaynak, neden = (s.kimlik, r, c), f"Hücreye {goster(v)} değeri elle yazılmış."
                else:
                    zincir = hata_neden.acikla(s, r, c, motor=self.motor)
                    if not zincir:
                        continue
                    son = zincir[-1]
                    kaynak = (son.sayfa.kimlik, son.satir, son.sutun)
                    neden = son.neden or hata_neden._GENEL.get(son.kod, "")
                g = gruplar.setdefault(kaynak, {"etkilenen": 0, "neden": neden, "kod": v})
                g["etkilenen"] += 1
        for (k, r, c), g in gruplar.items():
            ks = self.kitap.sayfa_kimlikle(k)
            if ks is None:
                continue
            adres = f"{ks.ad}!{hucre_yaz(r, c)}"
            sonuc = goster(g["kod"])
            yield self._bulgu(
                "hata", ks, [(r, c)], f"{sonuc} hatası: {hucre_yaz(r, c)}",
                f"{sonuc}: {g['neden']} Kaynak hücre {adres}; bu hata toplam {g['etkilenen']} hücreyi etkiliyor.",
                "Hata değerleri tablodaki hesapları (toplam, ortalama, grafik) bozar; kaynak düzelince bağlı hücreler de düzelir.", None)

    # =========================================================== 6. boş hücreye başvuru
    def _k_bos_basvuru(self, sayfa) -> Iterator[Bulgu]:
        for r, c, h, agac in self._formuller(sayfa):
            if self._ritim():
                yield None
            if agac is None:
                continue
            bos = []
            for x, p in _gez(agac):
                if not (isinstance(x, Ref) and x.basvuru.tur == "hucre"):
                    continue
                if p is not None and not (isinstance(p, (Ikili, Tekli, Yuzde)) and (not isinstance(p, Ikili) or p.islec in "+-*/^")):
                    continue                                                  # işlev argümanı (EĞER, EBOŞSA, DÜŞEYARA…) sayılmaz
                b = x.basvuru
                hedef = self._sayfa_ve_hedef(sayfa, b)
                if hedef is None or (hedef.kimlik, b.r1, b.c1) == (sayfa.kimlik, r, c):
                    continue
                if hedef._hucreler.get((b.r1, b.c1)) is None and self._delik_mi(hedef, b.r1, b.c1):
                    bos.append(f"{hedef.ad + '!' if hedef is not sayfa else ''}{hucre_yaz(b.r1, b.c1)}")
            if bos:
                yield self._bulgu(
                    "bos_basvuru", sayfa, [(r, c)], f"{hucre_yaz(r, c)} boş hücreyi kullanıyor",
                    f"{hucre_yaz(r, c)} formülü veri arasında boş duran {', '.join(sorted(set(bos)))} hücresine başvuruyor (boş hücre 0 sayılır).",
                    "Veri girilmeyi unutulmuş olabilir; boş hücre sonucu sessizce değiştirir.", None, ek=",".join(sorted(set(bos))))

    def _delik_mi(self, sayfa, r: int, c: int) -> bool:
        """Boş hücre, iki yanında (sol-sağ ya da üst-alt) dolu hücre olan bir “delik” mi."""
        def dolu(rr, cc):
            return rr >= 1 and cc >= 1 and sayfa._hucreler.get((rr, cc)) is not None
        return (dolu(r, c - 1) and dolu(r, c + 1)) or (dolu(r - 1, c) and dolu(r + 1, c))

    # =========================================================== 7. yinelenen satırlar
    def _k_yinelenen_satir(self, sayfa) -> Iterator[Bulgu]:
        satirlar: Dict[int, Dict[int, Any]] = {}
        for (r, c), h in sayfa._hucreler.items():
            if self._ritim():
                yield None
            if type(h) is not TasmaHucre and h.formul is None and h.deger not in (None, ""):
                satirlar.setdefault(r, {})[c] = h.deger
        bloklar, mevcut = [], []
        for r in sorted(satirlar):
            if len(satirlar[r]) >= 3 and (not mevcut or r == mevcut[-1] + 1):
                mevcut.append(r)
            else:
                if len(mevcut) >= 5:
                    bloklar.append(mevcut)
                mevcut = [r] if len(satirlar[r]) >= 3 else []
        if len(mevcut) >= 5:
            bloklar.append(mevcut)

        def norm(v):
            return kucuk(v.strip()) if isinstance(v, str) else v
        for blok in bloklar:
            gorulen: Dict[tuple, int] = {}
            tekrar: Dict[int, List[int]] = {}
            for r in blok[1:]:                                                # ilk satır başlık sayılır
                if self._ritim():
                    yield None
                imza = tuple(sorted((c, norm(v)) for c, v in satirlar[r].items()))
                if imza in gorulen:
                    tekrar.setdefault(gorulen[imza], []).append(r)
                else:
                    gorulen[imza] = r
            for ilk, digerleri in tekrar.items():
                kol = min(satirlar[ilk])
                yield self._bulgu(
                    "yinelenen_satir", sayfa, [(r, kol) for r in [ilk] + digerleri],
                    f"{ilk}. satır {len(digerleri)} kez daha tekrarlanıyor",
                    f"{ilk}. satırdaki değerlerin aynısı {', '.join(str(x) for x in digerleri[:6])}. satırlarda da var"
                    + ("…" if len(digerleri) > 6 else "."),
                    "Aynı kayıt iki kez girilmiş olabilir; toplamlar ve sayımlar şişer.", None)

    # =========================================================== 8. geçersiz kimlik verileri
    def _k_gecersiz_kimlik(self, sayfa) -> Iterator[Bulgu]:
        sutunlar: Dict[int, List[Tuple[int, str]]] = {}
        for (r, c), h in sayfa._hucreler.items():
            if self._ritim():
                yield None
            if type(h) is TasmaHucre or h.formul is not None:
                continue
            v = h.deger
            if isinstance(v, float) and v == int(v) and 1e8 <= abs(v) < 1e12:
                v = str(int(v))                                               # sayı olarak yazılmış TC/vergi no
            if isinstance(v, str) and v.strip():
                sutunlar.setdefault(c, []).append((r, v.strip()))
        dogrulayici = {"tc": kimlik.tc_gecerli, "vkn": kimlik.vkn_gecerli, "iban": kimlik.iban_gecerli}
        benzer = {"tc": re.compile(r"\d{9,12}"), "vkn": re.compile(r"\d{9,11}"),
                  "iban": re.compile(r"[A-Za-z]{2}\d{2}[\w\s\-]{10,}")}                  # türüne benzeyen değerler (başlık/not metni sayılmaz)
        adlar = {"tc": "T.C. kimlik no", "vkn": "Vergi kimlik no", "iban": "IBAN"}
        for c, liste in sorted(sutunlar.items()):
            liste.sort()
            for tur, anahtarlar in _KIMLIK_BASLIK.items():
                uygun = []                                                            # türüne benzeyen değerler
                for r, v in liste:
                    if benzer[tur].fullmatch(v):
                        uygun.append((r, v))
                    if self._ritim():
                        yield None
                if not uygun:
                    continue
                baslik = _sade(self._sutun_basligi(sayfa, c, uygun[0][0]) or "")
                basliktan = bool(baslik) and any(a in baslik for a in anahtarlar)
                dv = dogrulayici[tur]
                gecerli = 0
                for _, v in uygun:
                    gecerli += bool(dv(v))
                    if self._ritim():
                        yield None
                icerikten = len(uygun) >= 5 and gecerli / len(uygun) >= 0.7
                if not (basliktan or icerikten):
                    continue
                gecersiz = []
                for r, v in uygun:
                    if not dv(v):
                        gecersiz.append((r, v))
                    if self._ritim():
                        yield None
                if not gecersiz:
                    break
                b = self._bulgu(
                    "gecersiz_kimlik", sayfa, [(r, c) for r, _ in gecersiz],
                    f"{sutun_harfe(c)} sütununda {len(gecersiz)} geçersiz {adlar[tur]}",
                    f"{hucre_yaz(gecersiz[0][0], c)} hücresi gibi {len(gecersiz)} değer {adlar[tur]} sağlama kuralına uymuyor.",
                    "Yazım hatası olabilir; yanlış kimlik/IBAN ile yapılan işlemler (ödeme, bildirim) reddedilir ya da yanlış kişiye gider.",
                    None, ek=tur)
                if not basliktan:
                    b.onem = UYARI                                           # yalnız içerikten anlaşıldıysa daha temkinli
                yield b
                break


# ------------------------------------------------------------------ düzeltme (yalnız kullanıcı onayıyla)
def duzeltme_komutu(kitap, bulgu: Bulgu):
    """Önerilen düzeltmenin geri alınabilir komutu (çağıran `yigin.calistir` ile çalıştırır = kullanıcı onayı)."""
    d = bulgu.duzeltme
    sayfa = kitap.sayfa_kimlikle(bulgu.sayfa_kimlik)
    if d is None or sayfa is None:
        raise ValueError("Bu bulgu için otomatik düzeltme yok.")
    if d.tur in ("aralik_genislet", "formul_esitle"):
        return HucrelerDegis(sayfa, {tuple(d.veri["hucre"]): Hucre(None, d.veri["yeni_formul"])})
    if d.tur == "metni_sayiya":
        from ..model.komutlar import bicim_komutu
        from ..model.stil import StilYama
        yeni, komutlar = {}, []
        for r, c, deger, kod in d.veri["hucreler"]:
            yeni[(r, c)] = Hucre(deger)
            if kod and sayfa.stil(r, c).sayi_bicimi == "General":
                from ..model.adres import Aralik
                komutlar.append(bicim_komutu(sayfa, [Aralik(r, c, r, c)], StilYama(sayi_bicimi=kod)))
        return Grup([HucrelerDegis(sayfa, yeni)] + komutlar)
    raise ValueError(f"Bilinmeyen düzeltme: {d.tur}")
