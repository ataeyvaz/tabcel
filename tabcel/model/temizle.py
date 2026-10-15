"""KVKK Paylaşım Temizleyici çekirdeği (Faz 9d): kitaptaki kişisel verileri bulur, seçilen eyleme (maskele / sil / bırak) göre
**bellekteki derin bir kopyayı** temizler. Özgün kitaba ve dosyaya hiçbir şey yazılmaz (CLAUDE.md kural 17). Qt yok, ağ yok.

“Yardımcı araç”dır; mevzuata uygunluk iddiası yoktur (kural 20). Doğrulayıcılar yalnız `model/kimlik.py`'dedir (kural 18).

Taranan yerler: hücreler (gizli satır/sütun/sayfa dahil), formüllerin içindeki metin sabitleri, notlar (+ not yazarı), tanımlı adlar,
sayfa adları, grafik başlıkları/seri adları, doğrulama listeleri ve iletileri. Resimler taranamaz (`resim_sayisi`). Dosya düzeyi
(meta veri, üst/alt bilgi) için bkz. `io/temiz_dosya.py`.

Akış: `Tarayici(kitap).tara()` → `Kayit` listesi → `temiz_kopya(kitap, kayitlar, plan)` → `TemizKopya` (kopya kitap + formül etkisi)."""
import copy
import dataclasses
import re
from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Set, Tuple

from .. import metin_tr
from . import kimlik
from .adres import hucre_yaz
from .notlar import Not
from .sayfa import CalismaKitabi, Hucre, TasmaHucre, sayfa_adi_dogrula
from .deger import Hata

# --- yer türleri ---
HUCRE, FORMUL, NOT, NOT_YAZAR, AD, SAYFA_ADI, GRAFIK, DOGRULAMA, SABLON = (
    "hucre", "formul", "not", "not_yazar", "ad", "sayfa_adi", "grafik", "dogrulama", "sablon")
YER_ADLARI = {HUCRE: "Hücre", FORMUL: "Formüldeki metin", NOT: "Not", NOT_YAZAR: "Not yazarı", AD: "Tanımlı ad",
              SAYFA_ADI: "Sayfa adı", GRAFIK: "Grafik", DOGRULAMA: "Veri doğrulama", SABLON: "Şablon bilgisi"}

# --- eylemler ---
MASKELE, SIL, BIRAK = "maskele", "sil", "birak"
EYLEM_ADLARI = {MASKELE: "Maskele", SIL: "Sil", BIRAK: "Bırak"}

# ad-soyad: yalnız sütun başlığına göre öneri (metinden algılanmaz)
AD_BASLIKLARI = frozenset({
    "ad", "adı", "soyad", "soyadı", "ad soyad", "adı soyadı", "ad-soyad", "ad / soyad", "adsoyad", "isim", "isim soyisim",
    "ad soyisim", "ad ve soyad", "müşteri", "müşteri adı", "müşteri ad soyad", "personel", "personel adı", "çalışan",
    "çalışan adı", "kişi", "hasta", "hasta adı", "öğrenci", "öğrenci adı", "ad soyadı", "isim soyadı"})
_AD_BOSLUK_SINIRI = 2                       # başlık altında en çok bu kadar boş satır atlanır
_SAYI_HANE = (10, 15)                       # sayı olarak yazılmış kimlik/telefon için hane aralığı (15 üstü duyarlıkla bozulur)
_TIRNAKLI = re.compile(r'"(?:[^"]|"")*"')


@dataclass(frozen=True)
class Yer:
    """Bir bulgunun yeri. `anahtar` uygulamaya yarar (hücre: (satır, sütun); ad: (anahtar, alan); grafik: (kimlik, alan, sıra);
    doğrulama: (sıra, alan)); `gizli` boş değilse veri kullanıcının göremediği bir yerdedir."""
    tur: str
    sayfa_kimlik: Optional[int]
    adres: str
    ayrinti: str
    anahtar: tuple
    gizli: str = ""


@dataclass(frozen=True)
class Kayit:
    """Bir yerdeki bir bulgu. `metin` o yerin TÜM özgün metnidir (`bulgu` bu metnin içindeki konumu gösterir)."""
    yer: Yer
    bulgu: kimlik.Bulgu
    metin: str
    sayfa_ad: str = ""

    @property
    def tur(self) -> str:
        return self.bulgu.tur


@dataclass
class Plan:
    """Tür başına eylem + maske ayarları; `haric` tek tek dışarıda bırakılan kayıt sırası (kayıt listesindeki indeks)."""
    eylem: Dict[str, str] = field(default_factory=lambda: {t: MASKELE for t in kimlik.TURLER})
    maske: Dict[str, kimlik.MaskeAyari] = field(default_factory=dict)
    haric: Set[int] = field(default_factory=set)
    sayfa_adlarini_degistir: bool = True

    def eylem_of(self, tur: str) -> str:
        return self.eylem.get(tur, MASKELE)


# ------------------------------------------------------------------ tarama
def _sayi_metni(deger) -> Optional[str]:
    """Tam sayı olarak yazılmış 10–15 haneli sayı (TC, telefon, vergi no sayı girilmişse) → rakam metni; değilse None."""
    if isinstance(deger, bool) or not isinstance(deger, float):
        return None
    if deger != deger or deger in (float("inf"), float("-inf")) or deger != int(deger) or deger <= 0:
        return None
    s = str(int(deger))
    return s if _SAYI_HANE[0] <= len(s) <= _SAYI_HANE[1] else None


def _ad_gibi(metin: str) -> bool:
    k = metin.strip()
    return 1 < len(k) <= 60 and any(ch.isalpha() for ch in k) and not any(ch.isdigit() for ch in k) and "@" not in k


class Tarayici:
    """Kitabı tarar. `calistir()` üreteçtir: `("ilerleme", oran, metin)`, `("kayit", Kayit)`, `("ritim",)` (arayüz zamanı
    denetlesin diye düzenli aralıkla). Salt okunurdur."""

    RITIM = 400

    def __init__(self, kitap: CalismaKitabi):
        self.kitap = kitap
        self.kayitlar: List[Kayit] = []
        self.resim_sayisi = 0
        self.taranan_hucre = 0

    def tara(self) -> List[Kayit]:
        for olay in self.calistir():
            pass
        return self.kayitlar

    # --- yardımcılar ---
    def _ekle(self, yer: Yer, metin: str, sayfa_ad: str, bulgular, ad_sutunu: bool = False) -> Iterator[tuple]:
        bulgular = list(bulgular)
        if ad_sutunu and not bulgular and _ad_gibi(metin):
            bulgular = [kimlik.Bulgu(kimlik.AD, 0, len(metin), metin, kimlik.BICIM)]
        for b in bulgular:
            k = Kayit(yer, b, metin, sayfa_ad)
            self.kayitlar.append(k)
            yield ("kayit", k)

    @staticmethod
    def _sabitler(formul: str) -> List[Tuple[int, int, str]]:
        """Formüldeki tırnaklı metin sabitleri: (başlangıç, bitiş, içerik)."""
        return [(m.start() + 1, m.end() - 1, m.group(0)[1:-1].replace('""', '"')) for m in _TIRNAKLI.finditer(formul)]

    def _ad_sutunlari(self, sayfa) -> Dict[int, Set[int]]:
        """Başlığı ad-soyad olan sütunların altındaki hücreler (satır kümeleri)."""
        sonuc: Dict[int, Set[int]] = {}
        h = sayfa._hucreler
        for (r, c), hc in h.items():
            if type(hc) is TasmaHucre or not isinstance(hc.deger, str) or hc.formul is not None:
                continue
            if metin_tr.kucuk(hc.deger.strip()) not in AD_BASLIKLARI:
                continue
            satirlar, bos, rr = set(), 0, r + 1
            son = (sayfa.kullanilan_aralik() or (r, c, r, c))[2]
            while rr <= son and bos <= _AD_BOSLUK_SINIRI:
                alt = h.get((rr, c))
                if alt is None or alt.deger is None:
                    bos += 1
                else:
                    bos = 0
                    if isinstance(alt.deger, str) and alt.formul is None:
                        satirlar.add(rr)
                rr += 1
            if satirlar:
                sonuc.setdefault(c, set()).update(satirlar)
        return sonuc

    # --- ana tarama ---
    def calistir(self) -> Iterator[tuple]:
        kitap = self.kitap
        n = max(1, len(kitap.sayfalar))
        sayac = 0
        for i, sayfa in enumerate(kitap.sayfalar):
            yield ("ilerleme", i / n, f"{sayfa.ad} taranıyor…")
            gizli_sayfa = "gizli sayfa" if sayfa.gizli else ""
            yield from self._ekle(Yer(SAYFA_ADI, sayfa.kimlik, "", "Sayfa adı", (), gizli_sayfa), sayfa.ad, sayfa.ad,
                                  kimlik.tara_metin(sayfa.ad))
            ad_set = self._ad_sutunlari(sayfa)
            for (r, c), h in list(sayfa._hucreler.items()):
                sayac += 1
                if sayac % self.RITIM == 0:
                    yield ("ritim",)
                if type(h) is TasmaHucre:
                    continue
                self.taranan_hucre += 1
                gizli = gizli_sayfa or ("gizli satır" if r in sayfa.gizli_satir else
                                        "gizli sütun" if c in sayfa.gizli_sutun else "")
                adres = hucre_yaz(r, c)
                if h.formul is not None:
                    for bas, son, icerik in self._sabitler(h.formul):
                        if len(icerik) < 6:
                            continue
                        yer = Yer(FORMUL, sayfa.kimlik, adres, "Formüldeki metin", (r, c, bas, son), gizli)
                        yield from self._ekle(yer, icerik, sayfa.ad, kimlik.tara_metin(icerik))
                    continue
                v = h.deger
                if isinstance(v, str):
                    metin = v
                    bulgular = kimlik.tara_metin(metin) if len(metin) >= 5 else []
                    adli = r in ad_set.get(c, ())
                else:
                    metin = _sayi_metni(v)
                    if metin is None:
                        continue
                    bulgular, adli = kimlik.tum_hucre(metin), False
                if bulgular or adli:
                    yield from self._ekle(Yer(HUCRE, sayfa.kimlik, adres, "Hücre", (r, c), gizli), metin, sayfa.ad,
                                          bulgular, adli)
            for (r, c), nt in sayfa.notlar.items():
                adres = hucre_yaz(r, c)
                gizli = gizli_sayfa or ("gizli satır" if r in sayfa.gizli_satir else
                                        "gizli sütun" if c in sayfa.gizli_sutun else "")
                yield from self._ekle(Yer(NOT, sayfa.kimlik, adres, "Not metni", (r, c), gizli), nt.metin, sayfa.ad,
                                      kimlik.tara_metin(nt.metin))
                if nt.yazar.strip():
                    yield from self._ekle(
                        Yer(NOT_YAZAR, sayfa.kimlik, adres, "Not yazarı", (r, c), gizli), nt.yazar, sayfa.ad,
                        [kimlik.Bulgu(kimlik.AD, 0, len(nt.yazar), nt.yazar, kimlik.BICIM)])
            for nesne in sayfa.nesneler:
                if type(nesne).__name__ == "Resim":
                    self.resim_sayisi += 1
                    continue
                for alan in ("baslik", "x_baslik", "y_baslik"):
                    t = getattr(nesne, alan, None)
                    if t:
                        yer = Yer(GRAFIK, sayfa.kimlik, "", f"Grafik {_GRAFIK_ALAN[alan]}", (nesne.kimlik, alan, 0), gizli_sayfa)
                        yield from self._ekle(yer, t, sayfa.ad, kimlik.tara_metin(t))
                for k, seri in enumerate(getattr(nesne, "seriler", ())):
                    if seri.ad:
                        yer = Yer(GRAFIK, sayfa.kimlik, "", "Grafik seri adı", (nesne.kimlik, "seri", k), gizli_sayfa)
                        yield from self._ekle(yer, seri.ad, sayfa.ad, kimlik.tara_metin(seri.ad))
            for k, dv in enumerate(sayfa.dogrulamalar):
                alanlar = [("formul1", dv.formul1), ("formul2", dv.formul2), ("giris_baslik", dv.giris[1]),
                           ("giris_ileti", dv.giris[2]), ("hata_baslik", dv.hata[2]), ("hata_ileti", dv.hata[3])]
                for alan, t in alanlar:
                    if t:
                        yer = Yer(DOGRULAMA, sayfa.kimlik, "", f"Doğrulama ({alan.replace('_', ' ')})", (sayfa.kimlik, k, alan),
                                  gizli_sayfa)
                        yield from self._ekle(yer, t, sayfa.ad, kimlik.tara_metin(t))
        for anahtar, tanim in list(kitap.adlar.items()):
            kapsam = kitap.sayfa_kimlikle(tanim.kapsam).ad if tanim.kapsam is not None and kitap.sayfa_kimlikle(tanim.kapsam) else ""
            if tanim.aciklama:
                yield from self._ekle(Yer(AD, tanim.kapsam, "", f"Ad açıklaması ({tanim.ad})", (anahtar, "aciklama"),
                                          "gizli ad" if tanim.gizli else ""), tanim.aciklama, kapsam, kimlik.tara_metin(tanim.aciklama))
            for bas, son, icerik in self._sabitler(tanim.formul):
                yer = Yer(AD, tanim.kapsam, "", f"Ad değeri ({tanim.ad})", (anahtar, "formul", bas, son),
                          "gizli ad" if tanim.gizli else "")
                yield from self._ekle(yer, icerik, kapsam, kimlik.tara_metin(icerik))
        if kitap.sablon is not None:                       # Faz 10c: çok gizli `_tabcel` sayfasının içeriği (örnek veri, açıklamalar…)
            from ..sablon import saklama
            metin = saklama.json_yaz(kitap.sablon)
            yield from self._ekle(Yer(SABLON, None, "", "Şablon bilgisi (_tabcel)", ("json",), "çok gizli sayfa"), metin, "",
                                  kimlik.tara_metin(metin))
        yield ("ilerleme", 1.0, "Tarama bitti")


_GRAFIK_ALAN = {"baslik": "başlığı", "x_baslik": "X ekseni başlığı", "y_baslik": "Y ekseni başlığı"}


# ------------------------------------------------------------------ uygulama
def _yeni_metin(kayitlar: List[Kayit], plan: Plan, maske_karakteri: Optional[str] = None) -> str:
    """Aynı yerdeki kayıtları (örtüşmeyen, soldan sağa) özgün metne uygular."""
    metin = kayitlar[0].metin
    parcalar, konum = [], 0
    for k in sorted(kayitlar, key=lambda x: (x.bulgu.bas, -(x.bulgu.son - x.bulgu.bas))):
        b = k.bulgu
        eylem = plan.eylem_of(b.tur)
        if eylem == BIRAK or b.bas < konum:
            continue
        parcalar.append(metin[konum:b.bas])
        if eylem == MASKELE:
            m = kimlik.maskele(b.tur, b.metin, plan.maske.get(b.tur))
            parcalar.append(m.replace("*", maske_karakteri) if maske_karakteri else m)
        konum = b.son
    parcalar.append(metin[konum:])
    return "".join(parcalar)


def _etkin(kayitlar: List[Kayit], plan: Plan) -> List[Kayit]:
    return [k for i, k in enumerate(kayitlar) if i not in plan.haric and plan.eylem_of(k.tur) != BIRAK]


def yasak_degerler(kayitlar: List[Kayit], plan: Plan) -> Set[str]:
    """Temiz kopyada ve dosyasında **bulunmaması gereken** özgün değerler (maskelenen/silinen). Rakam yalnız biçimleriyle de
    (boşluksuz) eklenir; 6 karakterden kısa değerler yanlış eşleşmeyi önlemek için dışarıda kalır."""
    def degerler(k: Kayit) -> Set[str]:
        m = k.bulgu.metin.strip()
        d = {m, re.sub(r"[\s\-().]", "", m), kimlik.iban_sade(m) if k.tur == kimlik.IBAN else m}
        if k.tur in (kimlik.TC, kimlik.VKN, kimlik.KART, kimlik.TELEFON):
            d.add(re.sub(r"\D", "", m))
        return {v for v in d if len(v) >= 6}
    etkin = _etkin(kayitlar, plan)
    kimlik_etkin = {id(k) for k in etkin}
    sonuc: Set[str] = set()
    for k in etkin:
        sonuc |= degerler(k)
    for k in kayitlar:                                  # bilerek bırakılan yerlerdeki aynı değer dosyada kalacağı için aranmaz
        if id(k) not in kimlik_etkin:
            sonuc -= degerler(k)
    return sonuc


def kitap_kopyala(kitap: CalismaKitabi) -> CalismaKitabi:
    """Kitabın bağımsız derin kopyası (dinleyiciler, motor, geri al yığını kopyalanmaz — kopya yalnız veridir)."""
    dinleyiciler, kitap._dinleyiciler = kitap._dinleyiciler, []
    try:
        kopya = copy.deepcopy(kitap)
    finally:
        kitap._dinleyiciler = dinleyiciler
    kopya.saglik_yoksay = set()                    # yoksayma kayıtları adres içerir: paylaşılan kopyaya taşınmaz
    return kopya


@dataclass
class FormulEtkisi:
    """Maskeleme sonrası değeri değişen/hataya dönen formül."""
    sayfa_ad: str
    sayfa_kimlik: int
    satir: int
    sutun: int
    formul: str
    eski: object
    yeni: object
    hataya_dondu: bool
    degere_cevrilebilir: bool

    @property
    def adres(self) -> str:
        return hucre_yaz(self.satir, self.sutun)


@dataclass
class TemizKopya:
    kitap: CalismaKitabi
    yasak: Set[str]
    etkiler: List[FormulEtkisi]
    degisen_yer: int
    degere_cevrilen: int = 0
    motor: object = None

    def degere_cevir(self, secilenler: List[FormulEtkisi]) -> int:
        """Seçili formülleri **özgün** sonuçlarıyla değere çevirir; yalnız `degere_cevrilebilir` olanlar (sonuç maskelenen bir
        değeri içermiyor). Döner: çevrilen sayı."""
        n = 0
        for e in secilenler:
            if not e.degere_cevrilebilir:
                continue
            s = self.kitap.sayfa_kimlikle(e.sayfa_kimlik)
            if s is not None and s.hucre(e.satir, e.sutun) is not None and s.hucre(e.satir, e.sutun).formul is not None:
                s.ata(e.satir, e.sutun, Hucre(e.eski))
                n += 1
        self.degere_cevrilen += n
        return n

    def kapat(self) -> None:
        if self.motor is not None:
            self.motor.kapat()
            self.motor = None


def _deger_metni(v) -> str:
    if isinstance(v, float) and v == int(v) and abs(v) < 1e16:
        return str(int(v))
    return "" if v is None else str(v)


def _sizdirir_mi(deger, yasak: Set[str]) -> bool:
    t = re.sub(r"[\s\-().]", "", _deger_metni(deger))
    return any(y in t or y in _deger_metni(deger) for y in yasak)


def temiz_kopya(kitap: CalismaKitabi, kayitlar: List[Kayit], plan: Plan, motor_kur=True) -> TemizKopya:
    """Özgün kitaba dokunmadan temizlenmiş derin kopya üretir. Formül sonuçları kopyada yeniden hesaplanır; özgün kitapta hesaplı
    sonuç yoksa (motor bağlı değilse) çağıran önce `Hesaplayici(kitap)` kurmalıdır."""
    from ..formul.motor import Hesaplayici
    kopya = kitap_kopyala(kitap)
    etkin = _etkin(kayitlar, plan)
    gruplar: Dict[tuple, List[Kayit]] = {}
    for k in etkin:
        gruplar.setdefault((k.yer.tur, k.yer.sayfa_kimlik, k.yer.anahtar), []).append(k)
    degisen = 0

    def sira(oge):
        t, _, a = oge[0]
        # sayfa adı en sona; aynı formüldeki metin sabitleri sondan başa (konumlar kaymasın)
        bas = a[2] if (t == FORMUL or (t == AD and a[1] == "formul")) else 0
        return (t == SAYFA_ADI, -bas)
    for anahtar, grup in sorted(gruplar.items(), key=sira):
        tur, sk = anahtar[0], anahtar[1]
        sayfa = kopya.sayfa_kimlikle(sk) if sk is not None else None
        if tur == HUCRE:
            r, c = anahtar[2]
            sayfa.ata(r, c, None if (y := _yeni_metin(grup, plan)) == "" else Hucre(y))
        elif tur == FORMUL:
            r, c, bas, son = anahtar[2]
            f = sayfa.hucre(r, c).formul
            sayfa.ata(r, c, Hucre(None, f[:bas] + _yeni_metin(grup, plan).replace('"', '""') + f[son:]))
        elif tur == NOT:
            r, c = anahtar[2]
            n = sayfa.notlar[(r, c)]
            sayfa.notlari_yaz({(r, c): Not(_yeni_metin(grup, plan), n.yazar)})
        elif tur == NOT_YAZAR:
            r, c = anahtar[2]
            n = sayfa.notlar[(r, c)]
            sayfa.notlari_yaz({(r, c): Not(n.metin, _yeni_metin(grup, plan))})
        elif tur == AD:
            ad_anahtari, alan = anahtar[2][0], anahtar[2][1]
            tanim = kopya.adlar[ad_anahtari]
            if alan == "aciklama":
                yeni = dataclasses.replace(tanim, aciklama=_yeni_metin(grup, plan))
            else:
                bas, son = anahtar[2][2], anahtar[2][3]
                f = tanim.formul
                yeni = dataclasses.replace(tanim, formul=f[:bas] + _yeni_metin(grup, plan).replace('"', '""') + f[son:])
            kopya.adlar[ad_anahtari] = yeni
        elif tur == GRAFIK:
            kimlik_, alan, sira = anahtar[2]
            nesne = sayfa.nesne(kimlik_)
            yeni_metin = _yeni_metin(grup, plan)
            if alan == "seri":
                seriler = list(nesne.seriler)
                seriler[sira] = dataclasses.replace(seriler[sira], ad=yeni_metin or None)
                yeni = dataclasses.replace(nesne, seriler=tuple(seriler))
            else:
                yeni = dataclasses.replace(nesne, **{alan: yeni_metin or None})
            sayfa.nesne_degistir(yeni)
        elif tur == DOGRULAMA:
            _, sira, alan = anahtar[2]
            dv = sayfa.dogrulamalar[sira]
            yeni_metin = _yeni_metin(grup, plan)
            if alan in ("formul1", "formul2"):
                dv = dataclasses.replace(dv, **{alan: yeni_metin})
            elif alan.startswith("giris"):
                g = list(dv.giris)
                g[1 if alan == "giris_baslik" else 2] = yeni_metin
                dv = dataclasses.replace(dv, giris=tuple(g))
            else:
                h = list(dv.hata)
                h[2 if alan == "hata_baslik" else 3] = yeni_metin
                dv = dataclasses.replace(dv, hata=tuple(h))
            sayfa.dogrulamalar[sira] = dv
        elif tur == SABLON:
            from ..sablon import saklama
            try:
                kopya.sablon = saklama.json_oku(_yeni_metin(grup, plan))
            except (ValueError, KeyError, TypeError, AttributeError):
                kopya.sablon = None                         # metin değişimi JSON'u bozduysa şablon bilgisi korunmaz (veri sızmasın)
        elif tur == SAYFA_ADI and plan.sayfa_adlarini_degistir:
            yeni = _yeni_metin(grup, plan, maske_karakteri="x").strip().strip("'")
            if not yeni or any(x is not sayfa and x.ad.casefold() == yeni.casefold() for x in kopya.sayfalar):
                yeni = ""
            else:
                try:
                    sayfa_adi_dogrula(yeni)
                except ValueError:
                    yeni = ""
            if not yeni:
                i = 1
                while any(x.ad.casefold() == f"sayfa{i}" for x in kopya.sayfalar):
                    i += 1
                yeni = f"Sayfa{i}"
            kopya.yeniden_adlandir(sayfa, yeni)
        degisen += 1
    if kopya.sablon is not None:
        kopya.sablon.uretici = ""                           # üretici/sürüm bilgisi paylaşılan kopyaya yazılmaz
    kopya.sablon_ham = None                                  # okunamayan şablon bilgisi temizlenemez → kopyaya taşınmaz
    kopya.sablon_denetim = None
    yasak = yasak_degerler(kayitlar, plan)
    tk = TemizKopya(kopya, yasak, [], degisen)
    if motor_kur:
        tk.motor = Hesaplayici(kopya)
        for s in kitap.sayfalar:
            ks = kopya.sayfa_kimlikle(s.kimlik)
            for (r, c), h in s._hucreler.items():
                if h.formul is None or type(h) is TasmaHucre:
                    continue
                eski, yeni = s.deger(r, c), ks.deger(r, c)
                if eski == yeni or (isinstance(eski, float) and isinstance(yeni, float) and abs(eski - yeni) < 1e-12):
                    continue
                tk.etkiler.append(FormulEtkisi(s.ad, s.kimlik, r, c, h.formul, eski, yeni,
                                               isinstance(yeni, Hata) and not isinstance(eski, Hata),
                                               not isinstance(eski, Hata) and not _sizdirir_mi(eski, yasak)))
    return tk
