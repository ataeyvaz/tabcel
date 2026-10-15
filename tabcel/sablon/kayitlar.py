"""Şablon kayıtları ve kural motoru (Faz 10f). Qt yok. Tasarım: `sablon_tasarim.md` §3.4, §6, §7.

**Tek kural kaynağı (CLAUDE.md kural 21):** form ayrı kural yazmaz.
- *Alan kuralları* (zorunlu, benzersiz, tür/aralık, kimlik doğrulayıcıları, açılır liste) tablodaki hücre doğrulamasıdır
  (`Dogrulama`); form onu `formul.kosul.dogrula` ile **aynı değerlendirici** üzerinden sınar.
- *Satır kuralları* (`Modul.kurallar`) tanımdaki tek `formul`dur; yer tutucuları `uretici.genislet` ile çevrilir ve formül motorunda
  değerlendirilir. Form taslağında `[@x]` değer sabitine, kayıtlı satırda (Sağlık Kontrolü) hücre başvurusuna dönüşür.
- Yapıştırmayla tabloya girip doğrulamayı atlayan hatalı kayıtlar `tablo_ihlalleri` ile bulunur.

Sınır: başka modüllerin toplamlarına bakan kurallar (`[modül.alan]`, ör. stok eksiye düşmesin) **giriş anı kuralıdır** — kayıt zaten
toplamlara dâhil olduktan sonra değerlendirilemez; `tablo_ihlalleri` bunları atlar (`giris_ani_mi`).
"""
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..metin_tr import esit_mi, kucuk
from ..model.gosterim import goster
from ..model.sayfa import Hucre
from . import saklama
from .sema import Kural, Modul, Sutun, yer_tutucular
from .uretici import ModulYeri, UretimHatasi, genislet

_NE_ZAMAN = re.compile(r"^\s*([a-z][a-z0-9_]*)\s*(!=|=)\s*(.*?)\s*$")
_SAYISAL = ("tam_sayi", "ondalik", "para", "yuzde", "tarih", "hesaplanan")
DURDUR, UYAR = "durdur", "uyar"


@dataclass
class Ihlal:
    kural: str                         # kural kimliği, alan kuralı için "alan:<sütun>"
    alan: Optional[str]                # ilgili sütun kimliği (satır kuralında None olabilir)
    ileti: str
    siddet: str = DURDUR
    satir: Optional[int] = None


@dataclass
class ModulGorunumu:
    """Bir modülün kitaptaki güncel yeri: sayfa, sütun numaraları, veri bölgesi."""
    modul: Modul
    sayfa: Any
    sutunlar: Dict[str, int]
    ilk_satir: int
    kapasite: int
    formul_satiri: int

    @property
    def son_satir(self) -> int:
        return self.ilk_satir + self.kapasite - 1

    def alanlar(self) -> List[Sutun]:
        """Formda gösterilen (etkin) alanlar, sütun sırasıyla."""
        return [s for s in self.modul.sutunlar if s.kimlik in self.sutunlar]

    def girdi_alanlari(self) -> List[Sutun]:
        return [s for s in self.alanlar() if s.tur != "hesaplanan"]

    def sutun_no(self, kimlik: str) -> int:
        return self.sutunlar[kimlik]


class Baglam:
    """Kitaptaki şablon bilgisi + güncel yerleşim. `kur(kitap)` şablon yoksa ya da denetim başarısızsa (form kapalı) None döner."""

    def __init__(self, kitap, kayit, moduller: Dict[str, Modul], denetim):
        self.kitap, self.kayit, self.moduller, self.denetim = kitap, kayit, moduller, denetim
        self._yerler: Optional[Dict[str, ModulYeri]] = None

    @staticmethod
    def kur(kitap) -> Optional["Baglam"]:
        kayit = getattr(kitap, "sablon", None)
        if kayit is None:
            return None
        denetim = getattr(kitap, "sablon_denetim", None)
        if denetim is None:
            denetim = saklama.denetle(kitap, kayit)
        if not denetim.aktif:
            return None
        akis, moduller, hatalar = saklama.tanimlari_ayristir(kayit)
        if akis is None:
            return None
        return Baglam(kitap, kayit, moduller, denetim)

    def modul_kimlikleri(self) -> List[str]:
        return [m for m in self.kayit.baglar if m in self.denetim.esleme and m in self.moduller]

    def gorunum(self, modul: str) -> Optional[ModulGorunumu]:
        if modul not in self.denetim.esleme or modul not in self.moduller:
            return None
        bag = self.kayit.baglar[modul]
        sayfa = self.kitap.sayfa_kimlikle(self.denetim.sayfalar[modul])
        if sayfa is None:
            return None
        return ModulGorunumu(self.moduller[modul], sayfa, dict(self.denetim.esleme[modul]), bag.ilk_satir,
                             bag.kapasite or 20_000, bag.formul_satiri)

    def gorunum_sayfadan(self, sayfa) -> Optional[ModulGorunumu]:
        for mk in self.modul_kimlikleri():
            g = self.gorunum(mk)
            if g is not None and g.sayfa is sayfa:
                return g
        return None

    def yerler(self) -> Dict[str, ModulYeri]:
        if self._yerler is None:
            y = {}
            for mk in self.modul_kimlikleri():
                g = self.gorunum(mk)
                y[mk] = ModulYeri(g.modul, g.sayfa.kimlik, dict(g.sutunlar), g.ilk_satir, g.kapasite, g.formul_satiri)
            self._yerler = y
        return self._yerler

    def ayar_adlari(self) -> set:
        return set(self.kayit.ayarlar)


# ---------------------------------------------------------------- kayıt satırları
def _bos(h: Optional[Hucre]) -> bool:
    return h is None or h.formul is None and (h.deger is None or h.deger == "")


def kayit_mi(g: ModulGorunumu, satir: int) -> bool:
    """Satırın en az bir girdi alanı dolu mu (hesaplanan sütunlar sayılmaz)."""
    return any(not _bos(g.sayfa.hucre(satir, g.sutunlar[s.kimlik])) for s in g.girdi_alanlari())


def kayit_satirlari(g: ModulGorunumu) -> List[int]:
    kul = g.sayfa.kullanilan_aralik()
    if kul is None:
        return []
    son = min(kul[2], g.son_satir)
    sutlar = [g.sutunlar[s.kimlik] for s in g.girdi_alanlari()]
    cikti = []
    for r in range(g.ilk_satir, son + 1):
        if any(not _bos(g.sayfa.hucre(r, c)) for c in sutlar):
            cikti.append(r)
    return cikti


def yeni_satir(g: ModulGorunumu) -> Optional[int]:
    """Veri bölgesindeki ilk tamamen boş satır (son kayıttan sonraki); bölge dolduysa None."""
    kayitlar = kayit_satirlari(g)
    r = (kayitlar[-1] + 1) if kayitlar else g.ilk_satir
    return r if r <= g.son_satir else None


def oku(g: ModulGorunumu, satir: int) -> Dict[str, Any]:
    """{sütun kimliği: değer} (hesaplanan sütunlar dâhil; formül sonuçları)."""
    return {k: g.sayfa.deger(satir, c) for k, c in g.sutunlar.items()}


def gorunen(g: ModulGorunumu, satir: int, kimlik: str) -> str:
    from ..model.bul import gorunen_metin
    return gorunen_metin(g.sayfa, satir, g.sutunlar[kimlik]) or ""


def duzenleme_metni(g: ModulGorunumu, satir: int, kimlik: str) -> str:
    """Form kutusuna konan metin: hücreyi düzenlerken görülen metin (tarih `gg.aa.yyyy`, sayı virgüllü…)."""
    from ..formul.ceviri import hucre_metni
    c = g.sutunlar[kimlik]
    h = g.sayfa.hucre(satir, c)
    if h is None:
        return ""
    s = next(x for x in g.modul.sutunlar if x.kimlik == kimlik)
    if s.tur in ("tarih", "yuzde", "para", "tam_sayi", "ondalik") and isinstance(h.deger, float):
        return gorunen(g, satir, kimlik)
    return hucre_metni(h, g.sayfa.kitap, g.sayfa.stil(satir, c).sayi_bicimi)


# ---------------------------------------------------------------- metin → hücre
def metinden_hucre(g: ModulGorunumu, satir: int, kimlik: str, metin: str) -> Optional[Hucre]:
    """Form kutusuna yazılan metin → hücre değeri; tabloya aynı metni yazmakla aynı kurallar (`grid.hucre_gir`):
    metin biçimli sütunlarda (`@`) her şey metin kalır. Formül girişi alanlarda kabul edilmez (düz metin olur)."""
    metin = metin.strip() if metin is not None else ""
    if metin == "":
        return None
    s = next(x for x in g.modul.sutunlar if x.kimlik == kimlik)
    c = g.sutunlar[kimlik]
    if s.tur == "evet_hayir":
        k = kucuk(metin)
        if k in ("e", "evet", "1", "true", "doğru", "dogru"):
            return Hucre("Evet")
        if k in ("h", "hayır", "hayir", "0", "false", "yanlış", "yanlis"):
            return Hucre("Hayır")
        return Hucre(metin)
    if g.sayfa.stil(satir, c).sayi_bicimi == "@" or s.tur in ("metin", "liste", "baglanti"):
        if s.tur in ("liste", "baglanti"):
            return Hucre(metin)
        return Hucre(metin[1:] if metin.startswith("'") else metin)
    from ..formul.ceviri import hucre_girdisi_akilli
    from ..formul.sozcuk import FormulHatasi
    try:
        h, _ = hucre_girdisi_akilli(metin, g.sayfa.kitap)
    except FormulHatasi:
        return Hucre(metin)
    if h is not None and h.formul is not None:                 # alanlara formül yazılmaz: düz metin
        return Hucre(metin)
    return h


# ---------------------------------------------------------------- alan denetimi (tablo doğrulamasıyla aynı değerlendirici)
def alan_denetle(b: Baglam, g: ModulGorunumu, satir: int, kimlik: str, hucre: Optional[Hucre]) -> Optional[Ihlal]:
    from ..formul import kosul
    s = next(x for x in g.modul.sutunlar if x.kimlik == kimlik)
    if s.tur == "hesaplanan":
        return None
    c = g.sutunlar[kimlik]
    deger = None if hucre is None else hucre.deger
    if deger == "":
        deger = None
    dv = g.sayfa.dogrulama(satir, c)
    if deger is None:
        if s.zorunlu:
            return Ihlal(f"alan:{kimlik}", kimlik, f"“{s.ad}” boş bırakılamaz.")
        return None
    if dv is None or dv.tur == "her_deger":
        return None
    if kosul.dogrula(g.sayfa, satir, c, deger, b.kitap, dv):
        return None
    ileti = dv.hata[3] or f"“{s.ad}” alanına geçerli bir değer girin."
    return Ihlal(f"alan:{kimlik}", kimlik, ileti, dv.hata[1] if dv.hata[1] in (DURDUR, UYAR) else DURDUR)


# ---------------------------------------------------------------- satır kuralları
def _sabit(s: Sutun, deger: Any) -> str:
    if deger is None:
        return "0" if s.tur in _SAYISAL else '""'
    if isinstance(deger, bool):
        return "TRUE" if deger else "FALSE"
    if isinstance(deger, float):
        return f"{deger:.15g}"
    return '"' + str(deger).replace('"', '""') + '"'


def ne_zaman_saglanir(kural: Kural, g: ModulGorunumu, degerler: Dict[str, Any]) -> bool:
    """`ne_zaman`: `sütun=Değer` ya da `sütun!=Değer` (Türkçe harf duyarsız). Çözülemezse kural uygulanır."""
    if not kural.ne_zaman:
        return True
    m = _NE_ZAMAN.match(kural.ne_zaman)
    if m is None or m.group(1) not in g.sutunlar:
        return True
    v = degerler.get(m.group(1))
    metin = "" if v is None else goster(v)
    esit = esit_mi(metin, m.group(3))
    return esit if m.group(2) == "=" else not esit


def giris_ani_mi(kural: Kural) -> bool:
    """Başka modülün toplamlarına bakan kural (kayıt eklendikten sonra yeniden değerlendirilemez)."""
    tut, _ = yer_tutucular(kural.formul)
    return any(t[0] == "modul" for t in tut)


def _ileti(kural: Kural, degerler: Dict[str, Any]) -> str:
    return re.sub(r"\{([a-z][a-z0-9_]*)\}", lambda m: goster(degerler[m.group(1)]) if m.group(1) in degerler else m.group(0),
                  kural.ileti)


def _degerlendir(b: Baglam, g: ModulGorunumu, formul: str):
    from ..formul.agac import formul_ayristir
    from ..formul.degerlendir import Baglam as FBaglam, hucre_sonucu
    from ..formul.yerel import EN
    return hucre_sonucu(formul_ayristir(formul, EN), FBaglam(g.sayfa, g.ilk_satir, 1, b.kitap))


def kural_denetle(b: Baglam, g: ModulGorunumu, kural: Kural, degerler: Dict[str, Any],
                  satir: Optional[int] = None) -> Optional[Ihlal]:
    """Kural geçerliyse None; ihlalse `Ihlal`. `satir` verilirse `[@x]` hücre başvurusu olur (kayıtlı satır),
    verilmezse `degerler` sabitleri kullanılır (form taslağı). Değerlendirilemeyen kural (kapalı sütun, hata) ihlal sayılmaz."""
    from ..model.deger import Hata
    if not ne_zaman_saglanir(kural, g, degerler):
        return None
    yerler = b.yerler()
    try:
        if satir is None:
            sabitler = {s.kimlik: _sabit(s, degerler.get(s.kimlik)) for s in g.modul.sutunlar if s.kimlik in g.sutunlar}
            formul = genislet(kural.formul, None, yerler[g.modul.kimlik], yerler, kural.kimlik, b.ayar_adlari(), sabitler)
        else:
            formul = genislet(kural.formul, satir, yerler[g.modul.kimlik], yerler, kural.kimlik, b.ayar_adlari())
        sonuc = _degerlendir(b, g, formul)
    except (UretimHatasi, KeyError, ValueError, ArithmeticError, RecursionError):
        return None
    if isinstance(sonuc, Hata):
        return None
    ok = sonuc if isinstance(sonuc, bool) else (isinstance(sonuc, float) and sonuc != 0)
    if ok:
        return None
    return Ihlal(kural.kimlik, None, _ileti(kural, degerler), kural.siddet, satir)


def taslak_degerleri(g: ModulGorunumu, taslak: Dict[str, Optional[Hucre]]) -> Dict[str, Any]:
    return {k: (None if h is None else h.deger) for k, h in taslak.items()}


def kayit_denetle(b: Baglam, g: ModulGorunumu, satir: int, taslak: Dict[str, Optional[Hucre]]) -> List[Ihlal]:
    """Form taslağının tüm ihlalleri: önce alan kuralları, sonra satır kuralları (alanlarda `durdur` ihlali varsa
    satır kuralları da yine de raporlanır — kullanıcı hepsini görsün)."""
    cikti: List[Ihlal] = []
    for s in g.girdi_alanlari():
        i = alan_denetle(b, g, satir, s.kimlik, taslak.get(s.kimlik))
        if i is not None:
            i.satir = satir
            cikti.append(i)
    degerler = taslak_degerleri(g, taslak)
    for hesap in (s for s in g.alanlar() if s.tur == "hesaplanan"):
        degerler.setdefault(hesap.kimlik, None)
    for k in g.modul.kurallar:
        i = kural_denetle(b, g, k, degerler)
        if i is not None:
            i.satir = satir
            cikti.append(i)
    return cikti


# ---------------------------------------------------------------- kaydetme
def yazim_haritasi(b: Baglam, g: ModulGorunumu, satir: int, taslak: Dict[str, Optional[Hucre]]) -> Dict[Tuple[int, int], Optional[Hucre]]:
    """Kaydedilecek hücreler `{(satır, sütun): Hucre|None}` (tek `HucrelerDegis` = tek geri al adımı). Yeni satırda eksik kalan
    hesaplanan sütun formülleri de yazılır (şablonun ilk `formul_satiri` satırı dışına taşan kayıtlar için)."""
    yeni: Dict[Tuple[int, int], Optional[Hucre]] = {}
    for s in g.girdi_alanlari():
        yeni[(satir, g.sutunlar[s.kimlik])] = taslak.get(s.kimlik)
    yerler = b.yerler()
    for s in g.alanlar():
        if s.tur != "hesaplanan" or not s.formul:
            continue
        c = g.sutunlar[s.kimlik]
        h = g.sayfa.hucre(satir, c)
        if h is None or h.formul is None:
            try:
                f = genislet(s.formul, satir, yerler[g.modul.kimlik], yerler, f"{g.modul.sayfa_adi}/{s.ad}", b.ayar_adlari())
            except UretimHatasi:
                continue
            yeni[(satir, c)] = Hucre(formul=f)
    return yeni


def formul_eksik_mi(g: ModulGorunumu, satir: int) -> bool:
    """Hesaplanan sütunlar bu satırda formülsüz mü (şablonun hazır formül satırlarının dışında)."""
    return satir >= g.ilk_satir + max(g.formul_satiri, 0) and any(s.tur == "hesaplanan" for s in g.alanlar())


# ---------------------------------------------------------------- tablo taraması (Sağlık Kontrolü)
def tablo_ihlalleri(b: Baglam, modul: Optional[str] = None):
    """Kayıtlı satırların ihlalleri: `[(modül kimliği, satır, Ihlal)]`. Alan kuralları tablodaki doğrulamayla; satır kuralları yalnız
    kendi satırına bakanlar (giriş anı kuralları atlanır)."""
    cikti = []
    for mk in ([modul] if modul else b.modul_kimlikleri()):
        g = b.gorunum(mk)
        if g is None:
            continue
        for r in kayit_satirlari(g):
            for s in g.girdi_alanlari():
                h = g.sayfa.hucre(r, g.sutunlar[s.kimlik])
                i = alan_denetle(b, g, r, s.kimlik, None if _bos(h) else h)
                if i is not None:
                    i.satir = r
                    cikti.append((mk, r, i))
            degerler = oku(g, r)
            for k in g.modul.kurallar:
                if giris_ani_mi(k):
                    continue
                i = kural_denetle(b, g, k, degerler, satir=r)
                if i is not None:
                    cikti.append((mk, r, i))
    return cikti


# ---------------------------------------------------------------- örnek veriyi temizleme
def ornek_satirlari(b: Baglam) -> Dict[str, List[int]]:
    """Hâlâ üretimdeki örnek veriyle aynı duran satırlar: {modül: [satır]} (kullanıcı değiştirdiği satıra dokunulmaz)."""
    from .uretici import _ornek_hucre
    cikti: Dict[str, List[int]] = {}
    for mk, satirlar in b.kayit.ornek_satirlar.items():
        g = b.gorunum(mk)
        if g is None:
            continue
        for i, r in enumerate(satirlar):
            if i >= len(g.modul.ornek_veri):
                continue
            ornek = g.modul.ornek_veri[i]
            ayni = True
            for s in g.girdi_alanlari():
                try:
                    beklenen = _ornek_hucre(s, ornek.get(s.kimlik))
                except UretimHatasi:
                    beklenen = None
                h = g.sayfa.hucre(r, g.sutunlar[s.kimlik])
                if (None if _bos(h) else h.deger) != (None if beklenen is None else beklenen.deger):
                    ayni = False
                    break
            if ayni:
                cikti.setdefault(mk, []).append(r)
    return cikti


def ornek_temizleme_haritasi(b: Baglam):
    """Örnek satırların girdi hücrelerini boşaltan yazım haritaları: `[(sayfa, {(satır, sütun): None})]` (sayfa başına bir
    `HucrelerDegis`; hepsi bir `Grup` içinde tek geri al adımı)."""
    cikti = []
    for mk, satirlar in ornek_satirlari(b).items():
        g = b.gorunum(mk)
        harita = {(r, g.sutunlar[s.kimlik]): None for r in satirlar for s in g.girdi_alanlari()}
        if harita:
            cikti.append((g.sayfa, harita))
    return cikti


def ornek_kaydini_sifirla(b: Baglam) -> None:
    """Temizlemeden sonra: sonradan aynı satırlara yazılan gerçek veriye bir daha dokunulmasın."""
    b.kayit.ornek_satirlar = {}


# ---------------------------------------------------------------- barkod (Faz 10g)
def _metin(h: Optional[Hucre]) -> str:
    if _bos(h):
        return ""
    v = h.deger
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v).strip()


def barkod_sutunlari(g: ModulGorunumu) -> List[Sutun]:
    """Modülün barkod alanları (`barkod: true`)."""
    return [s for s in g.girdi_alanlari() if s.barkod]


def barkod_ara(g: ModulGorunumu, kod: str, haric: Optional[int] = None) -> Optional[int]:
    """Barkod sütunlarında `kod` ile **tam** eşleşen ilk kaydın satırı (başta sıfırlar önemlidir; boşluk kırpılır)."""
    kod = (kod or "").strip()
    sutlar = [g.sutunlar[s.kimlik] for s in barkod_sutunlari(g)]
    if not kod or not sutlar:
        return None
    for r in kayit_satirlari(g):
        if r != haric and any(_metin(g.sayfa.hucre(r, c)) == kod for c in sutlar):
            return r
    return None


def barkodlu_baglantilar(b: Baglam, g: ModulGorunumu) -> List[Sutun]:
    """Bu modüldeki, hedef modülünde barkod alanı olan bağlantı alanları (ör. Stok hareketi → Ürün kodu)."""
    cikti = []
    for s in g.girdi_alanlari():
        if s.tur == "baglanti" and s.baglanti:
            h = b.gorunum(s.baglanti[0])
            if h is not None and barkod_sutunlari(h):
                cikti.append(s)
    return cikti


def baglanti_degeri(b: Baglam, sutun: Sutun, kod: str) -> Optional[str]:
    """Okunan barkod → bağlantı alanının değeri (hedef modülde barkodu eşleşen kaydın bağlanılan alanı). Okunan metin zaten
    bağlanılan alanın değeriyse (ör. ürün kodu) o döner. Bulunamazsa None."""
    modul, alan = sutun.baglanti
    h = b.gorunum(modul)
    if h is None or alan not in h.sutunlar:
        return None
    r = barkod_ara(h, kod)
    if r is not None:
        v = _metin(h.sayfa.hucre(r, h.sutunlar[alan]))
        return v or None
    kod = (kod or "").strip()
    for r in kayit_satirlari(h):
        v = _metin(h.sayfa.hucre(r, h.sutunlar[alan]))
        if v and esit_mi(v, kod):
            return v
    return None


# ---------------------------------------------------------------- varyant matrisi (Faz 10h)
@dataclass
class MatrisPlani:
    """`matris_plani` sonucu: yazılacak hücreler + ihlaller. İhlal varsa hiçbir şey yazılmaz (hepsi ya da hiçbiri)."""
    yazimlar: Dict[Tuple[int, int], Optional[Hucre]] = field(default_factory=dict)
    ihlaller: List[Tuple[str, Ihlal]] = field(default_factory=list)       # (“Beden M / Renk Mavi”, ihlal)
    yeni: int = 0
    guncellenen: int = 0
    degismeyen: int = 0

    @property
    def tamam(self) -> bool:
        return not any(i.siddet == DURDUR for _, i in self.ihlaller)


def matris_tanimi(g: ModulGorunumu) -> Optional[Tuple[Sutun, Sutun, Sutun]]:
    """Modülün `matris` tanımı: (satır alanı, sütun alanı, değer alanı); tanım yoksa ya da bir sütun kapalıysa None."""
    m = g.modul.matris
    if not m:
        return None
    s = [g.modul.sutun(m.get(k)) for k in ("satir", "sutun", "deger")]
    if any(x is None or x.kimlik not in g.sutunlar for x in s):
        return None
    return s[0], s[1], s[2]


def matris_ortak_alanlari(g: ModulGorunumu) -> List[Sutun]:
    """Matrisin tüm hücreleri için ortak olan alanlar (ör. Ürün kodu): satır/sütun/değer dışındaki, benzersiz olmayan girdi
    alanları. Benzersiz alanlar (barkod) her çeşide özgüdür; matrisle girilmez."""
    t = matris_tanimi(g)
    ayri = {x.kimlik for x in t} if t else set()
    return [s for s in g.girdi_alanlari() if s.kimlik not in ayri and not s.benzersiz]


def _anahtar_metni(h: Optional[Hucre]) -> str:
    return kucuk(_metin(h))


def matris_mevcut(g: ModulGorunumu, ortak: Dict[str, Optional[Hucre]]):
    """Ortak alanları aynı olan mevcut kayıtlar: `{(satır etiketi, sütun etiketi): (satır no, değer)}` (etiketler kayıtlı yazımıyla)."""
    t = matris_tanimi(g)
    if t is None:
        return {}
    sa, su, de = t
    ort = matris_ortak_alanlari(g)
    cikti = {}
    for r in kayit_satirlari(g):
        if all(_anahtar_metni(g.sayfa.hucre(r, g.sutunlar[s.kimlik])) == _anahtar_metni(ortak.get(s.kimlik)) for s in ort):
            e, c = _metin(g.sayfa.hucre(r, g.sutunlar[sa.kimlik])), _metin(g.sayfa.hucre(r, g.sutunlar[su.kimlik]))
            if e and c:
                cikti[(e, c)] = (r, g.sayfa.hucre(r, g.sutunlar[de.kimlik]))
    return cikti


def matris_plani(b: Baglam, g: ModulGorunumu, ortak: Dict[str, Optional[Hucre]],
                 hucreler: Dict[Tuple[str, str], Optional[Hucre]]) -> MatrisPlani:
    """Matristeki her dolu hücre bir kayıttır: ortak alanlar + satır etiketi + sütun etiketi + değer. Aynı (ortak, satır, sütun)
    kaydı varsa yalnız değeri güncellenir (diğer alanlara — barkod gibi — dokunulmaz), yoksa yeni satır eklenir. Boş hücre yazılmaz.
    Her kayıt form kuralları (alan + satır kuralları) ile denetlenir; tek ihlal bile varsa plan boş kalır. Hepsi tek `HucrelerDegis` yapılır."""
    plan = MatrisPlani()
    t = matris_tanimi(g)
    if t is None:
        return plan
    sa, su, de = t
    mevcut = matris_mevcut(g, ortak)
    mevcut_kucuk = {(kucuk(e), kucuk(c)): (e, c, r, h) for (e, c), (r, h) in mevcut.items()}
    sonraki = yeni_satir(g)
    yazimlar: Dict[Tuple[int, int], Optional[Hucre]] = {}
    for (e, c), deger in hucreler.items():
        if deger is None or _bos(deger):
            continue
        etiket = f"{sa.ad} {e} / {su.ad} {c}"
        var = mevcut_kucuk.get((kucuk(e), kucuk(c)))
        taslak = dict(ortak)
        taslak[sa.kimlik] = Hucre(var[0] if var else e)
        taslak[su.kimlik] = Hucre(var[1] if var else c)
        taslak[de.kimlik] = deger
        if var is not None:
            satir = var[2]
            if var[3] is not None and var[3].deger == deger.deger:
                plan.degismeyen += 1
                continue
        else:
            if sonraki is None:
                plan.ihlaller.append((etiket, Ihlal("matris:dolu", None, "Tablonun veri bölgesi dolu.", DURDUR)))
                continue
            satir = sonraki
        for i in kayit_denetle(b, g, satir, taslak):
            plan.ihlaller.append((etiket, i))
        if var is not None:
            yazimlar[(satir, g.sutunlar[de.kimlik])] = deger
            plan.guncellenen += 1
        else:
            yazimlar.update(yazim_haritasi(b, g, satir, taslak))
            plan.yeni += 1
            sonraki = satir + 1 if satir + 1 <= g.son_satir else None
    if plan.tamam:
        plan.yazimlar = yazimlar
    else:
        plan.yeni = plan.guncellenen = 0
    return plan
