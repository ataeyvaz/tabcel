"""Şablon tanım şeması (surum 1) ve doğrulayıcı. Qt yok.

Doğrulayıcı hiçbir zaman istisna fırlatmaz: hatalar `Hata` listesine (`yol`, `mesaj`) yazılır; hatası olan tanım
`None` döner. Bilinmeyen alanlar hata değil uyarıdır (ileri uyum). Formüller burada yalnız yer tutucu düzeyinde
denetlenir (genişletme 10b'de).
"""
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

SURUM = 1                                   # bu uygulamanın anladığı en yeni şema sürümü
KIMLIK_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
EGER_RE = re.compile(r"^!?[a-z][a-z0-9_]{0,39}$")
TURLER = ("metin", "tam_sayi", "ondalik", "para", "yuzde", "tarih", "evet_hayir", "liste", "baglanti", "hesaplanan",
          "tc_kimlik", "vergi_no", "iban", "telefon", "eposta")
BICIMLER = ("tam_sayi", "ondalik", "para", "yuzde", "tarih")      # hesaplanan sütunun sayı biçimi
AYAR_TURLERI = ("metin", "tam_sayi", "ondalik", "para", "yuzde", "tarih", "evet_hayir")
SIDDETLER = ("durdur", "uyar")
EN_COK_SORU = 7
SAYFA_ADI_YASAK = set("[]:*?/\\")
EN_COK_FORMUL_SATIRI = 20_000
YER_TUTUCU_RE = re.compile(r"\[([^\[\]]*)\]|\bAYAR\.([A-Za-z_][A-Za-z0-9_]*)")


@dataclass
class Hata:
    yol: str
    mesaj: str
    uyari: bool = False

    def __str__(self):
        return f"{self.yol}: {self.mesaj}" if self.yol else self.mesaj


@dataclass
class Sutun:
    kimlik: str
    ad: str
    tur: str
    zorunlu: bool = False
    benzersiz: bool = False
    varsayilan: Any = None
    kisit: Dict[str, Any] = field(default_factory=dict)
    para_birimi: Optional[str] = None
    secenekler: List[str] = field(default_factory=list)
    baglanti: Optional[Tuple[str, str]] = None          # (modül, alan)
    formul: Optional[str] = None
    eger: Optional[str] = None
    barkod: bool = False
    aciklama: str = ""
    bicim: Optional[str] = None                # yalnız hesaplanan: sonucun sayı biçimi (BICIMLER)


@dataclass
class Kural:
    kimlik: str
    ad: str
    formul: str
    ileti: str
    siddet: str = "durdur"
    ne_zaman: Optional[str] = None


@dataclass
class Ayar:
    kimlik: str
    ad: str
    tur: str
    varsayilan: Any = None
    aciklama: str = ""
    eger: Optional[str] = None                 # bayrak ifadesi; yanlışsa ayar hiç üretilmez


@dataclass
class Modul:
    surum: int
    kimlik: str
    ad: str
    tekil_ad: str
    aciklama: str
    sayfa_adi: str
    sutunlar: List[Sutun]
    gorunen: List[str] = field(default_factory=list)
    kurallar: List[Kural] = field(default_factory=list)
    form_gruplari: List[Tuple[str, List[str]]] = field(default_factory=list)
    matris: Optional[Dict[str, str]] = None
    ornek_veri: List[Dict[str, Any]] = field(default_factory=list)
    ham: dict = field(default_factory=dict, repr=False, compare=False)      # göçü yapılmış kaynak JSON sözlüğü (kitapta saklanır)
    formul_satiri: Optional[int] = None        # hesaplanan sütunların formülle doldurulacağı satır sayısı (None = üreticinin varsayılanı)

    def sutun(self, kimlik: str) -> Optional[Sutun]:
        return next((s for s in self.sutunlar if s.kimlik == kimlik), None)


@dataclass
class Soru:
    kimlik: str
    metin: str
    tur: str = "evet_hayir"
    varsayilan: bool = False
    emin_degilim: bool = False
    eger: Optional[str] = None
    aciklama: str = ""


@dataclass
class Akis:
    surum: int
    kimlik: str
    ad: str
    kategori: str
    aciklama: str
    kokler: List[str]
    es_anlamlilar: List[str]
    agirlik: float
    sorular: List[Soru]
    moduller: List[Tuple[str, Optional[str]]]           # (modül kimliği, eger)
    bayraklar: Dict[str, str]
    ayarlar: List[Ayar]
    nasil_kullanilir: List[Tuple[str, str]]
    ornek_veri: bool = False
    ham: dict = field(default_factory=dict, repr=False, compare=False)


# ---------------------------------------------------------------- yardımcılar
class _Denetci:
    def __init__(self):
        self.hatalar: List[Hata] = []

    def hata(self, yol, mesaj):
        self.hatalar.append(Hata(yol, mesaj))

    def uyari(self, yol, mesaj):
        self.hatalar.append(Hata(yol, mesaj, True))

    def ciddi(self) -> bool:
        return any(not h.uyari for h in self.hatalar)

    def sozluk(self, yol, d):
        if not isinstance(d, dict):
            self.hata(yol, "nesne ({…}) olmalı")
            return False
        return True

    @staticmethod
    def _yol(yol, ad):
        return f"{yol}.{ad}" if yol else ad

    def metin(self, yol, d, ad, zorunlu=True):
        v = d.get(ad)
        if v is None:
            if zorunlu:
                self.hata(self._yol(yol, ad), "zorunlu alan eksik")
            return None
        if not isinstance(v, str) or not v.strip():
            self.hata(self._yol(yol, ad), "boş olmayan metin olmalı")
            return None
        return v

    def kimlik(self, yol, d, ad="kimlik"):
        v = self.metin(yol, d, ad)
        if v is not None and not KIMLIK_RE.match(v):
            self.hata(self._yol(yol, ad),
                      f'geçersiz kimlik "{v}" (küçük harf ASCII, rakam ve alt çizgi; harfle başlar; en çok 40 karakter)')
            return None
        return v

    def bool_(self, yol, d, ad, varsayilan=False):
        v = d.get(ad, varsayilan)
        if not isinstance(v, bool):
            self.hata(self._yol(yol, ad), "doğru/yanlış (true/false) olmalı")
            return varsayilan
        return v

    def liste(self, yol, d, ad, zorunlu=True, bos_olamaz=False):
        v = d.get(ad)
        if v is None:
            if zorunlu:
                self.hata(self._yol(yol, ad), "zorunlu alan eksik")
            return []
        if not isinstance(v, list):
            self.hata(self._yol(yol, ad), "liste ([…]) olmalı")
            return []
        if bos_olamaz and not v:
            self.hata(self._yol(yol, ad), "boş olamaz")
        return v

    def bilinmeyen(self, yol, d, bilinen):
        for k in d:
            if k not in bilinen:
                self.uyari(self._yol(yol, k), "bilinmeyen alan (yok sayıldı)")

    def eger(self, yol, d):
        e = d.get("eger")
        if e is None:
            return None
        if isinstance(e, str) and EGER_RE.match(e):
            return e
        self.hata(self._yol(yol, "eger"), "bayrak adı olmalı (başına ! konabilir)")
        return None


def _surum_denetle(c: _Denetci, d: dict, beklenen_tur: str) -> Optional[int]:
    s = d.get("surum")
    ok = not isinstance(s, bool) and isinstance(s, int) and s >= 1
    if not ok:
        c.hata("surum", "zorunlu: 1 ya da daha büyük tam sayı")
        s = None
    t = d.get("tur")
    if t != beklenen_tur:
        c.hata("tur", f'"{beklenen_tur}" olmalı' + (f' ("{t}" bulundu)' if t else ""))
    return s


def sayfa_adi_hatasi(ad: str) -> Optional[str]:
    if len(ad) > 31:
        return "en çok 31 karakter olabilir"
    if any(ch in SAYFA_ADI_YASAK for ch in ad):
        return "şu karakterleri içeremez: [ ] : * ? / \\"
    if ad.startswith("'") or ad.endswith("'"):
        return "kesme işaretiyle başlayıp bitemez"
    return None


def yer_tutucular(formul: str):
    """Formüldeki yer tutucular: [('sutun', kimlik, opsiyonel) | ('modul', modül, alan|None, opsiyonel) | ('ayar', kimlik)] ve söz dizimi hataları."""
    sonuc, hatalar = [], []
    if formul.count('"') % 2:
        hatalar.append("kapanmamış tırnak")
    govde = re.sub(r'"[^"]*"', '""', formul)                 # metin sabitlerini boşalt
    sade = YER_TUTUCU_RE.sub("", govde)
    if sade.count("(") != sade.count(")"):
        hatalar.append("parantezler dengeli değil")
    if "[" in sade or "]" in sade:
        hatalar.append("köşeli parantez eşleşmiyor")
    for m in YER_TUTUCU_RE.finditer(govde):
        if m.group(2):
            sonuc.append(("ayar", m.group(2)))
            continue
        ic = m.group(1)
        opsiyonel = ic.endswith("?")               # [@x?] / [m.x?]: sütun kapalıysa 0 (kapalı isteğe bağlı sütuna dayanan formül)
        govde_ic = ic[:-1] if opsiyonel else ic
        if govde_ic.startswith("@"):
            if KIMLIK_RE.match(govde_ic[1:]):
                sonuc.append(("sutun", govde_ic[1:], opsiyonel))
            else:
                hatalar.append(f"geçersiz yer tutucu [{ic}]")
        else:
            parca = govde_ic.split(".")
            if len(parca) in (1, 2) and all(KIMLIK_RE.match(p) for p in parca) and not (opsiyonel and len(parca) == 1):
                sonuc.append(("modul", parca[0], parca[1] if len(parca) == 2 else None, opsiyonel))
            else:
                hatalar.append(f"geçersiz yer tutucu [{ic}]")
    return sonuc, hatalar


# ---------------------------------------------------------------- modül
def _kisit(c: _Denetci, yol: str, d: dict) -> Dict[str, Any]:
    kisit = d.get("kisit")
    if kisit is None:
        return {}
    if not c.sozluk(f"{yol}.kisit", kisit):
        return {}
    for k in ("min", "max"):
        v = kisit.get(k)
        if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float))):
            c.hata(f"{yol}.kisit.{k}", "sayı olmalı")
    u = kisit.get("uzunluk")
    if u is not None and (isinstance(u, bool) or not isinstance(u, int) or u < 1):
        c.hata(f"{yol}.kisit.uzunluk", "1 ya da daha büyük tam sayı olmalı")
    a, z = kisit.get("min"), kisit.get("max")
    if all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (a, z)) and a > z:
        c.hata(f"{yol}.kisit", "min, max'tan büyük olamaz")
    return dict(kisit)


def _sutun(c: _Denetci, yol: str, d: Any) -> Optional[Sutun]:
    if not c.sozluk(yol, d):
        return None
    c.bilinmeyen(yol, d, {"kimlik", "ad", "tur", "zorunlu", "benzersiz", "varsayilan", "kisit", "para_birimi",
                          "secenekler", "baglanti", "formul", "eger", "barkod", "aciklama", "bicim"})
    kimlik, ad = c.kimlik(yol, d), c.metin(yol, d, "ad")
    tur = d.get("tur")
    if tur not in TURLER:
        c.hata(f"{yol}.tur", f'bilinmeyen tür "{tur}" (geçerli: {", ".join(TURLER)})' if tur else "zorunlu alan eksik")
        tur = None
    s = Sutun(kimlik or "", ad or "", tur or "", aciklama=d.get("aciklama") or "")
    s.zorunlu, s.benzersiz, s.barkod = (c.bool_(yol, d, "zorunlu"), c.bool_(yol, d, "benzersiz"), c.bool_(yol, d, "barkod"))
    s.varsayilan = d.get("varsayilan")
    s.kisit = _kisit(c, yol, d)
    s.eger = c.eger(yol, d)
    bic = d.get("bicim")
    if bic is not None:
        if tur != "hesaplanan":
            c.hata(f"{yol}.bicim", 'yalnız "hesaplanan" türünde kullanılır')
        elif bic not in BICIMLER:
            c.hata(f"{yol}.bicim", f'geçersiz biçim "{bic}" (geçerli: {", ".join(BICIMLER)})')
        else:
            s.bicim = bic
    pb = d.get("para_birimi")
    if pb is not None:
        if tur != "para" and not (tur == "hesaplanan" and bic == "para"):
            c.hata(f"{yol}.para_birimi", 'yalnız "para" türünde (ya da bicim "para" olan hesaplanan sütunda) kullanılır')
        elif not isinstance(pb, str) or not (re.fullmatch(r"[A-Z]{3}", pb) or re.fullmatch(r"ayar:[a-z][a-z0-9_]*", pb)):
            c.hata(f"{yol}.para_birimi", 'üç harfli kod (TRY) ya da "ayar:<kimlik>" olmalı')
        else:
            s.para_birimi = pb
    sec = d.get("secenekler")
    if tur == "liste":
        if not isinstance(sec, list) or not sec or not all(isinstance(x, str) and x.strip() for x in sec):
            c.hata(f"{yol}.secenekler", '"liste" türünde boş olmayan metin listesi gerekir')
        elif len(set(sec)) != len(sec):
            c.hata(f"{yol}.secenekler", "yinelenen seçenek var")
        else:
            s.secenekler = list(sec)
    elif sec is not None:
        c.hata(f"{yol}.secenekler", 'yalnız "liste" türünde kullanılır')
    b = d.get("baglanti")
    if tur == "baglanti":
        if not isinstance(b, dict):
            c.hata(f"{yol}.baglanti", '"baglanti" türünde {"modul": …, "alan": …} gerekir')
        else:
            m, a = b.get("modul"), b.get("alan")
            if isinstance(m, str) and KIMLIK_RE.match(m) and isinstance(a, str) and KIMLIK_RE.match(a):
                s.baglanti = (m, a)
            else:
                c.hata(f"{yol}.baglanti", "modul ve alan kimlik olmalı")
    elif b is not None:
        c.hata(f"{yol}.baglanti", 'yalnız "baglanti" türünde kullanılır')
    f = d.get("formul")
    if tur == "hesaplanan":
        if not isinstance(f, str) or not f.startswith("="):
            c.hata(f"{yol}.formul", '"hesaplanan" türünde "=" ile başlayan formül gerekir')
        else:
            s.formul = f
    elif f is not None:
        c.hata(f"{yol}.formul", 'yalnız "hesaplanan" türünde kullanılır')
    return s


def _kural(c: _Denetci, yol: str, kd: Any) -> Optional[Kural]:
    if not c.sozluk(yol, kd):
        return None
    c.bilinmeyen(yol, kd, {"kimlik", "ad", "formul", "ne_zaman", "ileti", "siddet", "aciklama"})
    kk, ka, kf, ki = c.kimlik(yol, kd), c.metin(yol, kd, "ad"), c.metin(yol, kd, "formul"), c.metin(yol, kd, "ileti")
    if kf is not None and not kf.startswith("="):
        c.hata(f"{yol}.formul", '"=" ile başlamalı')
        kf = None
    siddet = kd.get("siddet", "durdur")
    if siddet not in SIDDETLER:
        c.hata(f"{yol}.siddet", '"durdur" ya da "uyar" olmalı')
        siddet = "durdur"
    nz = kd.get("ne_zaman")
    if nz is not None and not isinstance(nz, str):
        c.hata(f"{yol}.ne_zaman", "metin olmalı")
        nz = None
    if kk and ka and kf and ki:
        return Kural(kk, ka, kf, ki, siddet, nz)
    return None


def _formul_yerel_denetle(c: _Denetci, yol: str, formul: str, sutun_kimlikleri: Set[str]):
    tut, hatalar = yer_tutucular(formul)
    for h in hatalar:
        c.hata(yol, h)
    for t in tut:
        if t[0] == "sutun" and t[1] not in sutun_kimlikleri:
            c.hata(yol, f'[@{t[1]}]: bu modülde "{t[1]}" sütunu yok')


def modul_ayristir(d: Any) -> Tuple[Optional[Modul], List[Hata]]:
    c = _Denetci()
    if not isinstance(d, dict):
        return None, [Hata("", "dosyanın en dışı nesne ({…}) olmalı")]
    c.bilinmeyen("", d, {"surum", "tur", "kimlik", "ad", "tekil_ad", "aciklama", "sayfa_adi", "gorunen", "sutunlar",
                         "kurallar", "form", "matris", "ornek_veri", "formul_satiri"})
    surum = _surum_denetle(c, d, "modul")
    kimlik, ad, tekil, aciklama = c.kimlik("", d), c.metin("", d, "ad"), c.metin("", d, "tekil_ad"), c.metin("", d, "aciklama")
    sayfa_adi = c.metin("", d, "sayfa_adi")
    if sayfa_adi:
        h = sayfa_adi_hatasi(sayfa_adi)
        if h:
            c.hata("sayfa_adi", h)
    fs = d.get("formul_satiri")
    if fs is not None and (isinstance(fs, bool) or not isinstance(fs, int) or not 1 <= fs <= EN_COK_FORMUL_SATIRI):
        c.hata("formul_satiri", f"1 ile {EN_COK_FORMUL_SATIRI} arasında tam sayı olmalı")
        fs = None
    sutunlar: List[Sutun] = []
    gorulen: Set[str] = set()
    for i, sd in enumerate(c.liste("", d, "sutunlar", bos_olamaz=True)):
        s = _sutun(c, f"sutunlar[{i}]", sd)
        if s is None:
            continue
        if s.kimlik in gorulen:
            c.hata(f"sutunlar[{i}].kimlik", f'"{s.kimlik}" kimliği yinelendi')
        gorulen.add(s.kimlik)
        sutunlar.append(s)
    basliklar = [s.ad for s in sutunlar if s.ad]
    for a in sorted({x for x in basliklar if basliklar.count(x) > 1}):
        c.hata("sutunlar", f'"{a}" sütun adı yinelendi (başlıklar benzersiz olmalı)')
    gorunen = c.liste("", d, "gorunen", zorunlu=False)
    for x in gorunen:
        if x not in gorulen:
            c.hata("gorunen", f'"{x}" adlı sütun yok')
    kurallar: List[Kural] = []
    for i, kd in enumerate(c.liste("", d, "kurallar", zorunlu=False)):
        k = _kural(c, f"kurallar[{i}]", kd)
        if k is None:
            continue
        if any(x.kimlik == k.kimlik for x in kurallar):
            c.hata(f"kurallar[{i}].kimlik", f'"{k.kimlik}" kimliği yinelendi')
        kurallar.append(k)
    gruplar: List[Tuple[str, List[str]]] = []
    form = d.get("form")
    if form is not None and c.sozluk("form", form):
        for i, g in enumerate(c.liste("form", form, "gruplar")):
            yol = f"form.gruplar[{i}]"
            if not c.sozluk(yol, g):
                continue
            gad, alanlar = c.metin(yol, g, "ad"), c.liste(yol, g, "alanlar", bos_olamaz=True)
            for x in alanlar:
                if x not in gorulen:
                    c.hata(f"{yol}.alanlar", f'"{x}" adlı sütun yok')
            if gad:
                gruplar.append((gad, [x for x in alanlar if x in gorulen]))
    matris = d.get("matris")
    if matris is not None and c.sozluk("matris", matris):
        for k in ("satir", "sutun", "deger"):
            if matris.get(k) not in gorulen:
                c.hata(f"matris.{k}", f'"{matris.get(k)}" adlı sütun yok')
    ornekler = []
    for i, od in enumerate(c.liste("", d, "ornek_veri", zorunlu=False)):
        if not c.sozluk(f"ornek_veri[{i}]", od):
            continue
        for k, v in od.items():
            if k not in gorulen:
                c.hata(f"ornek_veri[{i}].{k}", "böyle bir sütun yok")
            elif not (v is None or isinstance(v, (str, int, float, bool))):
                c.hata(f"ornek_veri[{i}].{k}", "değer metin, sayı, doğru/yanlış ya da boş olmalı")
        ornekler.append(od)
    for i, s in enumerate(sutunlar):
        if s.formul:
            _formul_yerel_denetle(c, f"sutunlar[{i}].formul", s.formul, gorulen)
    for i, k in enumerate(kurallar):
        _formul_yerel_denetle(c, f"kurallar[{i}].formul", k.formul, gorulen)
    if c.ciddi() or surum is None or not (kimlik and ad and tekil and aciklama and sayfa_adi):
        return None, c.hatalar
    return Modul(surum, kimlik, ad, tekil, aciklama, sayfa_adi, sutunlar, list(gorunen), kurallar, gruplar, matris,
                 ornekler, formul_satiri=fs), c.hatalar


# ---------------------------------------------------------------- akış
def _anahtar_kelimeler(c: _Denetci, d: dict):
    ak = d.get("anahtar_kelimeler")
    if ak is None:
        c.hata("anahtar_kelimeler", "zorunlu alan eksik")
        return [], [], 1.0
    if not c.sozluk("anahtar_kelimeler", ak):
        return [], [], 1.0
    c.bilinmeyen("anahtar_kelimeler", ak, {"kokler", "es_anlamlilar", "agirlik"})
    kokler = c.liste("anahtar_kelimeler", ak, "kokler", bos_olamaz=True)
    es = c.liste("anahtar_kelimeler", ak, "es_anlamlilar", zorunlu=False)
    for ad, liste in (("kokler", kokler), ("es_anlamlilar", es)):
        for j, x in enumerate(liste):
            if not isinstance(x, str) or not x.strip():
                c.hata(f"anahtar_kelimeler.{ad}[{j}]", "boş olmayan metin olmalı")
            elif ad == "kokler" and len(x.strip()) < 3:
                c.hata(f"anahtar_kelimeler.{ad}[{j}]", "kök en az 3 harf olmalı")
    agirlik = ak.get("agirlik", 1.0)
    if isinstance(agirlik, bool) or not isinstance(agirlik, (int, float)) or agirlik <= 0:
        c.hata("anahtar_kelimeler.agirlik", "sıfırdan büyük sayı olmalı")
        agirlik = 1.0
    temiz = lambda l: [x.strip() for x in l if isinstance(x, str) and x.strip()]  # noqa: E731
    return temiz(kokler), temiz(es), float(agirlik)


def akis_ayristir(d: Any) -> Tuple[Optional[Akis], List[Hata]]:
    c = _Denetci()
    if not isinstance(d, dict):
        return None, [Hata("", "dosyanın en dışı nesne ({…}) olmalı")]
    c.bilinmeyen("", d, {"surum", "tur", "kimlik", "ad", "kategori", "aciklama", "anahtar_kelimeler", "sorular", "moduller",
                         "bayraklar", "ayarlar", "nasil_kullanilir", "ornek_veri"})
    surum = _surum_denetle(c, d, "akis")
    kimlik, ad, kategori, aciklama = c.kimlik("", d), c.metin("", d, "ad"), c.metin("", d, "kategori"), c.metin("", d, "aciklama")
    kokler, es, agirlik = _anahtar_kelimeler(c, d)
    sorular: List[Soru] = []
    sl = c.liste("", d, "sorular", zorunlu=False)
    if len(sl) > EN_COK_SORU:
        c.hata("sorular", f"en çok {EN_COK_SORU} soru olabilir ({len(sl)} bulundu)")
    for i, sd in enumerate(sl):
        yol = f"sorular[{i}]"
        if not c.sozluk(yol, sd):
            continue
        c.bilinmeyen(yol, sd, {"kimlik", "metin", "tur", "varsayilan", "emin_degilim", "eger", "aciklama"})
        sk, sm = c.kimlik(yol, sd), c.metin(yol, sd, "metin")
        if sd.get("tur", "evet_hayir") != "evet_hayir":
            c.hata(f"{yol}.tur", 'şimdilik yalnız "evet_hayir" soruları desteklenir')
        vs, em, eg = c.bool_(yol, sd, "varsayilan"), c.bool_(yol, sd, "emin_degilim"), c.eger(yol, sd)
        if sk and any(x.kimlik == sk for x in sorular):
            c.hata(f"{yol}.kimlik", f'"{sk}" kimliği yinelendi')
        if sk and sm:
            sorular.append(Soru(sk, sm, "evet_hayir", vs, em, eg, sd.get("aciklama") or ""))
    soru_k = {s.kimlik for s in sorular}
    bayraklar: Dict[str, str] = {}
    bd = d.get("bayraklar")
    if bd is not None and c.sozluk("bayraklar", bd):
        for k, v in bd.items():
            if not KIMLIK_RE.match(k):
                c.hata(f"bayraklar.{k}", "geçersiz bayrak adı")
            elif k in soru_k:
                c.hata(f"bayraklar.{k}", "bayrak adı bir soru kimliğiyle aynı olamaz")
            elif v not in soru_k:
                c.hata(f"bayraklar.{k}", f'"{v}" adlı soru yok')
            else:
                bayraklar[k] = v
    gecerli = soru_k | set(bayraklar)
    for i, s in enumerate(sorular):
        if s.eger and s.eger.lstrip("!") not in gecerli:
            c.hata(f"sorular[{i}].eger", f'"{s.eger}" bilinmeyen bayrak')
    moduller: List[Tuple[str, Optional[str]]] = []
    for i, md in enumerate(c.liste("", d, "moduller", bos_olamaz=True)):
        yol = f"moduller[{i}]"
        if not c.sozluk(yol, md):
            continue
        c.bilinmeyen(yol, md, {"modul", "eger"})
        mk, eg = c.kimlik(yol, md, "modul"), c.eger(yol, md)
        if eg and eg.lstrip("!") not in gecerli:
            c.hata(f"{yol}.eger", f'"{eg}" bilinmeyen bayrak')
        if mk:
            if any(m == mk for m, _ in moduller):
                c.hata(f"{yol}.modul", f'"{mk}" modülü yinelendi')
            moduller.append((mk, eg))
    ayarlar: List[Ayar] = []
    for i, a in enumerate(c.liste("", d, "ayarlar", zorunlu=False)):
        yol = f"ayarlar[{i}]"
        if not c.sozluk(yol, a):
            continue
        c.bilinmeyen(yol, a, {"kimlik", "ad", "tur", "varsayilan", "aciklama", "eger"})
        ak_, aa, at, aeg = c.kimlik(yol, a), c.metin(yol, a, "ad"), a.get("tur"), c.eger(yol, a)
        if aeg and aeg.lstrip("!") not in gecerli:
            c.hata(f"{yol}.eger", f'"{aeg}" bilinmeyen bayrak')
        if at not in AYAR_TURLERI:
            c.hata(f"{yol}.tur", f'bilinmeyen ayar türü "{at}"')
        if ak_ and any(x.kimlik == ak_ for x in ayarlar):
            c.hata(f"{yol}.kimlik", f'"{ak_}" kimliği yinelendi')
        if ak_ and aa and at in AYAR_TURLERI:
            ayarlar.append(Ayar(ak_, aa, at, a.get("varsayilan"), a.get("aciklama") or "", aeg))
    nasil: List[Tuple[str, str]] = []
    for i, n in enumerate(c.liste("", d, "nasil_kullanilir", zorunlu=False)):
        if c.sozluk(f"nasil_kullanilir[{i}]", n):
            b, m = c.metin(f"nasil_kullanilir[{i}]", n, "baslik"), c.metin(f"nasil_kullanilir[{i}]", n, "metin")
            if b and m:
                nasil.append((b, m))
    ornek = c.bool_("", d, "ornek_veri", False)
    if c.ciddi() or surum is None or not (kimlik and ad and kategori and aciklama):
        return None, c.hatalar
    return Akis(surum, kimlik, ad, kategori, aciklama, kokler, es, agirlik, sorular, moduller, bayraklar, ayarlar, nasil,
                ornek), c.hatalar


def akis_modul_denetle(akis: Akis, moduller: Dict[str, Modul]) -> List[Hata]:
    """Akış ile modüllerin uyumu: modül var mı, bağlantılar, modüller arası yer tutucular, bayraklar, ayarlar."""
    c = _Denetci()
    kullanilan = {m for m, _ in akis.moduller}
    bayrak = {s.kimlik for s in akis.sorular} | set(akis.bayraklar)
    ayar = {a.kimlik for a in akis.ayarlar}
    for i, (mk, _) in enumerate(akis.moduller):
        if mk not in moduller:
            c.hata(f"moduller[{i}].modul", f'"{mk}" modülü bulunamadı')
    for mk in sorted(kullanilan & set(moduller)):
        m = moduller[mk]
        for si, s in enumerate(m.sutunlar):
            yol = f"modül {mk}: sutunlar[{si}]"
            if s.eger and s.eger.lstrip("!") not in bayrak:
                c.hata(f"{yol}.eger", f'"{s.eger}" bilinmeyen bayrak')
            if s.baglanti:
                hedef = moduller.get(s.baglanti[0])
                if s.baglanti[0] not in kullanilan or hedef is None:
                    c.hata(f"{yol}.baglanti", f'"{s.baglanti[0]}" modülü bu akışta yok')
                elif hedef.sutun(s.baglanti[1]) is None:
                    c.hata(f"{yol}.baglanti", f'"{s.baglanti[0]}" modülünde "{s.baglanti[1]}" sütunu yok')
            if s.para_birimi and s.para_birimi.startswith("ayar:") and s.para_birimi[5:] not in ayar:
                c.hata(f"{yol}.para_birimi", f'"{s.para_birimi[5:]}" adlı ayar yok')
        formuller = [(f"modül {mk}: sutunlar[{si}].formul", s.formul) for si, s in enumerate(m.sutunlar) if s.formul] + \
                    [(f"modül {mk}: kurallar[{ki}].formul", k.formul) for ki, k in enumerate(m.kurallar)]
        for yol, f in formuller:
            for t in yer_tutucular(f)[0]:
                if t[0] == "ayar" and t[1] not in ayar:
                    c.hata(yol, f'AYAR.{t[1]}: bu akışta "{t[1]}" ayarı yok')
                elif t[0] == "modul":
                    hedef = moduller.get(t[1])
                    if t[1] not in kullanilan or hedef is None:
                        c.hata(yol, f'[{t[1]}…]: "{t[1]}" modülü bu akışta yok')
                    elif t[2] is not None and hedef.sutun(t[2]) is None:
                        c.hata(yol, f'[{t[1]}.{t[2]}]: "{t[1]}" modülünde "{t[2]}" sütunu yok')
    return c.hatalar
