"""“Ne yapmak istiyorsun?” asistanı — Türkçe cümleden formül / Özet Tablo önerisi (Faz 8f). Qt yok; tamamen yerel ve
**kural tabanlı** (dil modeli ya da bulut yok: CLAUDE.md kural 6). Tablonun başlıklarına ve metin sütunlarındaki değerlere
bakarak cümleyi eşler; ne yazacağını önizlemede gösterir, kullanıcı onaylayınca tek geri al adımıyla uygular.

Anlaşılan kalıplar (örnekler `ORNEKLER`de): toplam/ortalama/sayı/en yüksek/en düşük (koşullu: “Kuzey bölgesinin toplam satışı”,
“1000'den büyük satış sayısı”), gruplama (“bölgeye göre toplam satış” → Özet Tablo; “bölge ve ürüne göre …” → satır+sütun),
filtreleme (“tutarı 500'den büyük olanları listele” → FİLTRE), en yüksek/düşük N, sıralama, benzersiz/tekrar eden değerler,
ortalamanın üstü/altı, yeni sütun: pay (yüzde), değişim, kümülatif toplam.

Eşleme: büyük/küçük harf, Türkçe harf (ç/ğ/ı/ö/ş/ü) ve ek farkı gözetmez (`bölgeye` = `Bölge`, `satışların` = `Satış`); başlık
sözcüğünün öneki kabul edilir. Anlaşılmazsa tahmin yürütülmez: nedenini ve örnekleri söyler (`OneriSonucu.mesaj`)."""
import difflib
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..metin_tr import kucuk
from ..model.adres import Aralik, AdresHatasi, bitisik_bolge, hucre_yaz
from ..model.komutlar import Grup, HucrelerDegis, bicim_komutu
from ..model.ozet import ISLEVLER, DegerAlani, OzetEkle, OzetHatasi, OzetTanimi, baslik_oku
from ..model.sayfa import Hucre
from ..model.stil import StilYama
from . import ceviri

ORNEKLER = (
    "Satış sütununun toplamı",
    "Bölgeye göre toplam satış",
    "Bölge ve ürüne göre ortalama tutar",
    "Kuzey bölgesinin toplam satışı",
    "Tutarı 1000'den büyük olanları listele",
    "En yüksek 5 satışı göster",
    "Tutara göre büyükten küçüğe sırala",
    "Ürünlerin benzersiz listesi",
    "Tekrar eden müşteriler",
    "Ortalamanın üstünde olan satışlar",
    "Satışların toplamdaki payı",
    "Satışın aylık değişimi",
    "Kümülatif satış",
    "Kaç kayıt var",
)

_TR = str.maketrans("çğıöşüâîû", "cgiosuaiu")


def sade(s: str) -> str:
    """Eşleme için: Türkçe küçük harf, aksansız, yalnız [a-z0-9] ve tek boşluk."""
    return re.sub(r"[^a-z0-9]+", " ", kucuk(s).translate(_TR)).strip()


def _eslesir(tok: str, w: str) -> bool:
    """`tok` (cümleden) başlık/değer sözcüğü `w` ile eşleşir mi: eşit, ekli (`bölgeye`), kısaltılmış ya da küçük yazım hatası."""
    if tok == w:
        return True
    if len(w) >= 3 and tok.startswith(w) and len(tok) - len(w) <= (8 if len(w) >= 4 else 5):
        return True
    if len(tok) >= 4 and w.startswith(tok) and len(w) - len(tok) <= 3:
        return True
    return len(w) >= 5 and len(tok) >= 5 and difflib.SequenceMatcher(None, tok, w).ratio() >= 0.86


# ------------------------------------------------------------------ tablo
@dataclass
class Tablo:
    sayfa: Any
    aralik: Aralik                                 # başlık satırı dahil
    basliklar: List[str]
    sayisal: List[bool]
    metin_degerleri: Dict[int, Dict[str, str]] = field(default_factory=dict)       # sütun → {sade(değer): özgün değer}

    @property
    def ilk_veri(self) -> int:
        return self.aralik.ilk_satir + 1

    def sutun_no(self, j: int) -> int:
        return self.aralik.ilk_sutun + j

    def kol(self, j: int) -> str:
        c = self.sutun_no(j)
        return f"{hucre_yaz(self.ilk_veri, c, True, True)}:{hucre_yaz(self.aralik.son_satir, c, True, True)}"

    def veri(self) -> str:
        return (f"{hucre_yaz(self.ilk_veri, self.aralik.ilk_sutun, True, True)}:"
                f"{hucre_yaz(self.aralik.son_satir, self.aralik.son_sutun, True, True)}")


def tablo_oku(sayfa, secim: Aralik) -> Tablo:
    """Seçimden tablo (tek hücre → çevresindeki veri bölgesi); ilk satır başlıktır."""
    tek = (secim.ilk_satir, secim.ilk_sutun) == (secim.son_satir, secim.son_sutun)
    ar = bitisik_bolge(sayfa, secim.ilk_satir, secim.ilk_sutun) if tek else secim
    kul = sayfa.kullanilan_aralik()
    if kul is not None:
        ar = Aralik(ar.ilk_satir, ar.ilk_sutun, min(ar.son_satir, kul[2]), min(ar.son_sutun, kul[3]))
    basliklar = baslik_oku(sayfa, ar)
    sayisal, metinler = [], {}
    for j, c in enumerate(range(ar.ilk_sutun, ar.son_sutun + 1)):
        say = bos = 0
        dolu = []
        for r in range(ar.ilk_satir + 1, ar.son_satir + 1):
            v = sayfa.deger(r, c)
            if v is None or v == "":
                bos += 1
                continue
            dolu.append(v)
            if isinstance(v, float):
                say += 1
        sayisal.append(bool(dolu) and say / len(dolu) >= 0.7)
        if not sayisal[-1]:
            degerler = {}
            for v in dolu:
                if isinstance(v, str) and len(sade(v)) >= 2:
                    degerler.setdefault(sade(v), v)
                if len(degerler) > 400:
                    break
            metinler[j] = degerler
    return Tablo(sayfa, ar, basliklar, sayisal, metinler)


# ------------------------------------------------------------------ öneri nesneleri
@dataclass
class Oneri:
    baslik: str
    aciklama: str
    onizleme: str                                   # Türkçe formül metni ya da kısa özet
    hedef: Optional[Tuple[int, int]] = None          # yazılacak (satır, sütun); Özet Tablo için None
    uygula: Callable = None                          # (kitap, sayfa) -> Komut

    def komut(self, kitap, sayfa):
        return self.uygula(kitap, sayfa)


@dataclass
class OneriSonucu:
    oneriler: List[Oneri] = field(default_factory=list)
    mesaj: str = ""


# ------------------------------------------------------------------ cümle çözümleme
_ISLEV_ANAHTARLARI = (
    ("Sayı", ("kac", "sayisi", "say", "adet", "tane", "kayit")),
    ("Ortalama", ("ortalama", "ortalamasi", "ort")),
    ("Maks", ("en yuksek", "en buyuk", "en cok", "en fazla", "maksimum", "maks", "tavan")),
    ("Min", ("en dusuk", "en kucuk", "en az", "minimum", "min", "taban")),
    ("Toplam", ("topla", "toplam", "toplami", "toplasan", "toplamini", "toplaman")),
)
_ARTAN = ("kucukten buyuge", "artan", "a dan z ye")
_AZALAN = ("buyukten kucuge", "azalan", "z den a ya")
_SAYI_RE = re.compile(r"(?<![\w.,])(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)")


def _sayi(s: str) -> float:
    if "." in s and "," in s:
        return float(s.replace(".", "").replace(",", "."))
    if "," in s:
        return float(s.replace(",", "."))
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        return float(s.replace(".", ""))
    return float(s)


def _sayi_metni(x: float) -> str:
    return str(int(x)) if x == int(x) else repr(x)


class _Cumle:
    """Cümlenin sözcük dizisi + tabloyla eşleşen sütun ve değer anmaları."""

    def __init__(self, metin: str, tablo: Tablo):
        self.metin = metin
        self.t = sade(metin)
        self.tok = self.t.split()
        self.tablo = tablo
        self.kolonlar: List[Tuple[int, int]] = []        # (sözcük indisi, sütun)
        self.degerler: List[Tuple[int, int, str]] = []   # (sözcük indisi, sütun, özgün değer)
        self._kolon_bul()
        self._deger_bul()
        anilan = set(self._kolon_sozcukleri) | {i for i, _, _ in self.degerler}
        # niyet sözcükleri sütun/değer adlarından ayrılsın (`Adet` sütunu “adet” sözcüğü sayılmasın)
        self.t = " ".join("_" if i in anilan else tk for i, tk in enumerate(self.tok))

    def _kolon_bul(self) -> None:
        aday = []
        for j, b in enumerate(self.tablo.basliklar):
            hw = sade(b).split()
            if not hw:
                continue
            konum = []
            for w in hw:
                i = next((i for i, tk in enumerate(self.tok) if _eslesir(tk, w)), None)
                if i is None:
                    break
                konum.append(i)
            else:
                aday.append((-len(hw), min(konum), j, set(konum)))
        kullanilan, sonuc = set(), []
        for _, i, j, kume in sorted(aday):             # çok sözcüklü başlık önce
            if kume & kullanilan:
                continue
            kullanilan |= kume
            sonuc.append((i, j))
        self.kolonlar = sorted(sonuc)
        self._kolon_sozcukleri = kullanilan

    def _deger_bul(self) -> None:
        for j, d in self.tablo.metin_degerleri.items():
            for norm, ozgun in d.items():
                vw = norm.split()
                for i in range(len(self.tok) - len(vw) + 1):
                    if i in self._kolon_sozcukleri:
                        continue
                    if all(_eslesir(self.tok[i + k], w) for k, w in enumerate(vw)):
                        self.degerler.append((i, j, ozgun))
                        break

    def var(self, *anahtarlar: str) -> bool:
        return any(re.search(r"(?<![a-z0-9])" + re.escape(a), self.t) for a in anahtarlar)

    def kolon_var(self, j: int) -> bool:
        return any(c == j for _, c in self.kolonlar)

    def sayisal_kolon(self, haric=()) -> Optional[int]:
        """Anılan ilk sayısal sütun; hiçbiri anılmadıysa ve tabloda tek sayısal sütun varsa o."""
        for _, j in self.kolonlar:
            if self.tablo.sayisal[j] and j not in haric:
                return j
        tek = [j for j, s in enumerate(self.tablo.sayisal) if s and j not in haric]
        return tek[0] if len(tek) == 1 else None


def _islev(c: _Cumle) -> Optional[str]:
    """Cümledeki özetleme işlevi (ilk anılan; “en yüksek/en düşük” Maks/Min)."""
    en_iyi, konum = None, 10 ** 6
    for islev, anahtarlar in _ISLEV_ANAHTARLARI:
        for a in anahtarlar:
            m = re.search(r"(?<![a-z0-9])" + re.escape(a), c.t)
            if m and m.start() < konum:
                en_iyi, konum = islev, m.start()
    return en_iyi


def _kosullar(c: _Cumle, haric_kolon=()) -> List[Tuple[int, str, Any]]:
    """[(sütun, işleç, değer)]: metin değerleri (Kuzey) ve sayısal karşılaştırmalar (1000'den büyük)."""
    t = c.tablo
    kos: List[Tuple[int, str, Any]] = []
    for _, j, ozgun in c.degerler:
        kos.append((j, "=", ozgun))
    sayilar = [(m.start(), _sayi(m.group(1))) for m in _SAYI_RE.finditer(kucuk(c.metin))]
    if not sayilar:
        return kos
    karsilastirmalar = (("buyuk", ">"), ("fazla", ">"), ("ustunde", ">"), ("uzerinde", ">"), ("asan", ">"),
                        ("kucuk", "<"), ("az", "<"), ("altinda", "<"), ("alti", "<"), ("esit", "="))
    for pozisyon, sayi in sayilar:
        yakin = sade(kucuk(c.metin)[pozisyon:pozisyon + 40]).split()[1:5]          # sayıdan sonraki sözcükler
        islec = None
        for sozcuk in yakin:
            for anahtar, i in karsilastirmalar:
                if sozcuk.startswith(anahtar):
                    islec = i
                    break
            if islec:
                break
        if islec is None:
            continue
        sayisallar = [j for _, j in c.kolonlar if t.sayisal[j] and j not in haric_kolon]
        j = sayisallar[0] if sayisallar else next((k for k, s in enumerate(t.sayisal) if s and k not in haric_kolon), None)
        if j is not None:
            kos.append((j, islec, sayi))
    return kos


def _kriter(islec: str, deger) -> str:
    if isinstance(deger, float):
        return f'"{islec if islec != "=" else ""}{_sayi_metni(deger)}"' if islec != "=" else _sayi_metni(deger)
    return '"' + str(deger).replace('"', '""') + '"'


def _filtre_ifadesi(t: Tablo, kos) -> str:
    parcalar = []
    for j, islec, deger in kos:
        sag = _sayi_metni(deger) if isinstance(deger, float) else '"' + str(deger).replace('"', '""') + '"'
        parcalar.append(f"({t.kol(j)}{islec}{sag})")
    return "*".join(parcalar)


# ------------------------------------------------------------------ hedef
def hedef_bul(sayfa, tablo: Tablo, etkin: Optional[Tuple[int, int]] = None) -> Tuple[int, int]:
    """Sonucun yazılacağı hücre: etkin hücre boş ve tablonun dışındaysa orası; değilse tablonun sağındaki ilk boş sütun
    (tablonun ilk satırı)."""
    ar = tablo.aralik
    if etkin is not None:
        r, c = etkin
        icinde = ar.ilk_satir <= r <= ar.son_satir and ar.ilk_sutun <= c <= ar.son_sutun
        if not icinde and sayfa.hucre(r, c) is None:
            return etkin
    c = ar.son_sutun + 2
    while any(sayfa.hucre(r, c) is not None for r in range(ar.ilk_satir, ar.ilk_satir + 3)) and c < 16000:
        c += 1
    return ar.ilk_satir, c


def _formul_oneri(baslik: str, aciklama: str, formul: str, tablo: Tablo, hedef: Tuple[int, int],
                  kitap_ceviri=None) -> Oneri:
    def uygula(kitap, sayfa):
        return HucrelerDegis(sayfa, {hedef: Hucre(formul=formul)})
    return Oneri(baslik, aciklama, ceviri.gosterime(formul, kitap_ceviri), hedef, uygula)


def _sutun_oneri(baslik: str, aciklama: str, tablo: Tablo, j: int, ad: str, satir_formulu: Callable[[int], Optional[str]],
                 yuzde: bool) -> Oneri:
    ar = tablo.aralik
    c = ar.son_sutun + 1
    r0 = ar.ilk_satir

    def uygula(kitap, sayfa):
        yeni = {(r0, c): Hucre(ad)}
        for r in range(ar.ilk_satir + 1, ar.son_satir + 1):
            f = satir_formulu(r)
            if f is not None:
                yeni[(r, c)] = Hucre(formul=f)
        komutlar = [HucrelerDegis(sayfa, yeni),
                    bicim_komutu(sayfa, [Aralik(r0, c, r0, c)], StilYama(kalin=True))]
        if yuzde:
            komutlar.append(bicim_komutu(sayfa, [Aralik(r0 + 1, c, ar.son_satir, c)], StilYama(sayi_bicimi="0.0%")))
        return Grup(komutlar)
    ilk = satir_formulu(ar.ilk_satir + 1) or satir_formulu(ar.ilk_satir + 2) or ""
    return Oneri(baslik, aciklama, ceviri.gosterime(ilk, None) + f"  → {hucre_yaz(r0, c)} sütununa, tüm satırlara",
                 (r0, c), uygula)


# ------------------------------------------------------------------ ana işlev
def anla(metin: str, tablo: Tablo, etkin: Optional[Tuple[int, int]] = None) -> OneriSonucu:
    """Cümleden öneri(ler). Anlaşılmazsa `mesaj` nedeni ve örnekleri söyler."""
    if not metin.strip():
        return OneriSonucu(mesaj="Ne yapmak istediğinizi yazın. Örnekler:\n• " + "\n• ".join(ORNEKLER[:6]))
    c = _Cumle(metin, tablo)
    t = tablo
    sayfa = t.sayfa
    hedef = hedef_bul(sayfa, t, etkin)
    kitap = sayfa.kitap

    def sonuc(*o) -> OneriSonucu:
        return OneriSonucu(list(o))

    def sor(neden: str) -> OneriSonucu:
        return OneriSonucu(mesaj=f"{neden}\nTablodaki sütunlar: {', '.join(t.basliklar)}\nÖrnek: “{ORNEKLER[1]}”")

    kol = [j for _, j in c.kolonlar]
    islev = _islev(c)

    # --- sıralama
    if c.var("sirala"):
        if not kol:
            return sor("Hangi sütuna göre sıralanacağını anlayamadım.")
        j = kol[0]
        azalan = c.var(*_AZALAN) or (t.sayisal[j] and c.var("en cok", "en yuksek", "en buyuk")) and not c.var(*_ARTAN)
        f = f"=SORT({t.veri()},{j + 1},{-1 if azalan else 1})"
        return sonuc(_formul_oneri(f"“{t.basliklar[j]}” sütununa göre {'azalan' if azalan else 'artan'} sırala",
                                   "Sıralanmış kopya yeni bir alana yayılır; özgün tablo değişmez.", f, t, hedef, kitap))

    # --- benzersiz / tekrar eden
    if c.var("benzersiz", "tekil", "essiz", "farkli degerler", "tekrarsiz"):
        j = kol[0] if kol else 0
        f = f"=UNIQUE({t.kol(j)})"
        return sonuc(_formul_oneri(f"“{t.basliklar[j]}” benzersiz değerleri", "Her değer bir kez listelenir.", f, t, hedef, kitap))
    if c.var("tekrar", "yinelen", "ayni olan", "mukerrer", "cift kay"):
        if not kol:
            return sor("Hangi sütunda tekrar eden değerlerin aranacağını anlayamadım.")
        j = kol[0]
        f = f"=UNIQUE(FILTER({t.kol(j)},COUNTIF({t.kol(j)},{t.kol(j)})>1))"
        return sonuc(_formul_oneri(f"“{t.basliklar[j]}” içinde tekrar eden değerler", "Birden çok geçen değerler listelenir.",
                                   f, t, hedef, kitap))

    # --- en yüksek / en düşük N, son N
    m = re.search(r"en (yuksek|buyuk|cok|fazla|pahali|iyi) (\d+)|ilk (\d+)", c.t)
    m2 = re.search(r"en (dusuk|kucuk|az|ucuz|kotu) (\d+)", c.t)
    m3 = re.search(r"son (\d+)", c.t)
    if m or m2:
        j = c.sayisal_kolon()
        if j is None:
            return sor("En yüksek/en düşük değerin hangi sayısal sütuna göre bulunacağını anlayamadım.")
        n = int(m.group(2) or m.group(3)) if m else int(m2.group(2))
        yon = -1 if m else 1
        f = f"=TAKE(SORT({t.veri()},{j + 1},{yon}),{n})"
        return sonuc(_formul_oneri(f"“{t.basliklar[j]}” en {'yüksek' if yon < 0 else 'düşük'} {n} kayıt",
                                   "Sonuç yeni bir alana yayılır.", f, t, hedef, kitap))
    if m3:
        n = int(m3.group(1))
        f = f"=TAKE({t.veri()},-{n})"
        return sonuc(_formul_oneri(f"Son {n} kayıt", "Tablonun son satırları listelenir.", f, t, hedef, kitap))

    # --- ortalamanın üstü / altı
    if c.var("ortalamanin ustunde", "ortalamanin uzerinde", "ortalamadan fazla", "ortalamanin altinda", "ortalamadan az"):
        j = c.sayisal_kolon()
        if j is None:
            return sor("Hangi sütunun ortalamasıyla karşılaştırılacağını anlayamadım.")
        ust = not c.var("altinda", "ortalamadan az")
        f = f"=FILTER({t.veri()},{t.kol(j)}{'>' if ust else '<'}AVERAGE({t.kol(j)}))"
        return sonuc(_formul_oneri(f"“{t.basliklar[j]}” ortalamanın {'üstünde' if ust else 'altında'} olanlar",
                                   "Koşula uyan satırlar listelenir.", f, t, hedef, kitap))

    # --- yeni sütun: pay / değişim / kümülatif
    if c.var("kumulatif", "birikimli"):
        j = c.sayisal_kolon()
        if j is None:
            return sor("Kümülatif toplamın hangi sütun için hesaplanacağını anlayamadım.")
        col = hucre_yaz(1, t.sutun_no(j))[:-1]
        return sonuc(_sutun_oneri(f"“{t.basliklar[j]}” kümülatif toplamı", "Yeni bir sütun eklenir.", t, j,
                                  f"{t.basliklar[j]} Kümülatif",
                                  lambda r: f"=SUM({hucre_yaz(t.ilk_veri, t.sutun_no(j), True, True)}:"
                                            f"{hucre_yaz(r, t.sutun_no(j), False, True)})", False))
    if c.var("degisim", "artis", "azalis", "buyume"):
        j = c.sayisal_kolon()
        if j is None:
            return sor("Değişimin hangi sütun için hesaplanacağını anlayamadım.")
        sn = t.sutun_no(j)
        return sonuc(_sutun_oneri(f"“{t.basliklar[j]}” değişimi (bir önceki satıra göre %)", "Yeni bir sütun eklenir.", t, j,
                                  f"{t.basliklar[j]} Değişimi",
                                  lambda r: None if r == t.ilk_veri else
                                  f"=({hucre_yaz(r, sn)}-{hucre_yaz(r - 1, sn)})/{hucre_yaz(r - 1, sn)}", True))
    if c.var("yuzde", "payi", "orani", "oran", "pay"):
        j = c.sayisal_kolon()
        if j is None:
            return sor("Payın hangi sayısal sütun için hesaplanacağını anlayamadım.")
        sn = t.sutun_no(j)
        return sonuc(_sutun_oneri(f"“{t.basliklar[j]}” toplamdaki payı (%)", "Yeni bir sütun eklenir.", t, j,
                                  f"{t.basliklar[j]} Payı",
                                  lambda r: f"={hucre_yaz(r, sn)}/SUM({t.kol(j)})", True))

    # --- gruplama → Özet Tablo
    isaret = next((i for i, tk in enumerate(c.tok) if tk in ("gore", "bazinda", "basina", "bazli")), None)
    her = next((i for i, tk in enumerate(c.tok) if tk == "her"), None)
    if isaret is not None or (her is not None and c.var("icin")):
        sol = [j for i, j in c.kolonlar if isaret is not None and i < isaret]
        if her is not None and not sol:
            sol = [j for i, j in c.kolonlar if i > her and (isaret is None or i < isaret)]
        if not sol and isaret is not None:
            sag = [j for i, j in c.kolonlar if i > isaret and not t.sayisal[j]]
            sol = sag[:1]
        gruplar = [j for j in sol if not t.sayisal[j] or len(sol) == 1][-2:] or sol[-1:]
        if not gruplar:
            return sor("Neye göre gruplanacağını anlayamadım.")
        deger = next((j for j in kol if t.sayisal[j] and j not in gruplar), None)
        isl = islev or "Toplam"
        if deger is None:
            if isl == "Sayı":
                deger = gruplar[0]
            else:
                deger = next((j for j, s in enumerate(t.sayisal) if s and j not in gruplar), None)
                if deger is None or len(t.basliklar) <= 1:
                    return sor("Hangi sayısal sütunun özetleneceğini anlayamadım.")
        tanim = OzetTanimi(t.basliklar[gruplar[0]], t.basliklar[gruplar[1]] if len(gruplar) > 1 else None,
                           (DegerAlani(t.basliklar[deger], isl),))
        gruplar_ad = " ve ".join(t.basliklar[g] for g in gruplar)

        def uygula(kitap, sayfa, tanim=tanim, ar=t.aralik):
            ad, n = "Özet Tablo", 1
            while kitap.ad_var_mi(ad):
                n += 1
                ad = f"Özet Tablo{n}"
            return OzetEkle(kitap, sayfa, ar, tanim, None, (1, 1), ad)
        return sonuc(Oneri(f"{gruplar_ad} bazında {isl.lower()} “{t.basliklar[deger]}” (Özet Tablo)",
                           "Yeni bir sayfaya Özet Tablo olarak yazılır.",
                           f"Satırlar: {tanim.satir}" + (f"; Sütunlar: {tanim.sutun}" if tanim.sutun else "")
                           + f"; Değer: {isl} - {t.basliklar[deger]}", None, uygula))

    # --- listeleme / filtre
    kos = _kosullar(c)
    if c.var("listele", "goster", "bul", "filtrele", "sadece", "getir", "olanlari", "olanlar", "secili") and kos:
        f = f"=FILTER({t.veri()},{_filtre_ifadesi(t, kos)},\"Sonuç yok\")"
        return sonuc(_formul_oneri("Koşula uyan satırlar", "Uyan satırlar yeni bir alana yayılır.", f, t, hedef, kitap))

    # --- tek değer (özet formülü)
    if islev is not None:
        deger = next((j for j in kol if t.sayisal[j]), None)
        if deger is None and islev in ("Toplam", "Ortalama", "Maks", "Min"):
            sayisallar = [j for j, s in enumerate(t.sayisal) if s]
            if len(sayisallar) == 1:
                deger = sayisallar[0]
            else:
                return sor("Hangi sayısal sütunun kullanılacağını anlayamadım.")
        kos = [k for k in _kosullar(c) if not (k[0] == deger and k[1] == "=")]
        if islev == "Sayı":
            hedef_kol = deger if deger is not None else (kol[0] if kol else 0)
            if kos:
                if len(kos) == 1:
                    j, i, v = kos[0]
                    f = f"=COUNTIF({t.kol(j)},{_kriter(i, v)})"
                else:
                    f = "=COUNTIFS(" + ",".join(f"{t.kol(j)},{_kriter(i, v)}" for j, i, v in kos) + ")"
            else:
                f = f"=COUNTA({t.kol(hedef_kol)})"
            return sonuc(_formul_oneri("Kayıt sayısı" + (" (koşullu)" if kos else ""), "Tek bir hücreye yazılır.", f, t, hedef, kitap))
        fn = {"Toplam": ("SUM", "SUMIF", "SUMIFS"), "Ortalama": ("AVERAGE", "AVERAGEIF", "AVERAGEIFS")}.get(islev)
        if fn:
            if not kos:
                f = f"={fn[0]}({t.kol(deger)})"
            elif len(kos) == 1:
                j, i, v = kos[0]
                f = f"={fn[1]}({t.kol(j)},{_kriter(i, v)},{t.kol(deger)})"
            else:
                f = f"={fn[2]}({t.kol(deger)}," + ",".join(f"{t.kol(j)},{_kriter(i, v)}" for j, i, v in kos) + ")"
        else:                                            # Maks / Min
            ad = "MAX" if islev == "Maks" else "MIN"
            f = f"={ad}({t.kol(deger)})" if not kos else f"={ad}(FILTER({t.kol(deger)},{_filtre_ifadesi(t, kos)}))"
        etiket = {"Toplam": "toplamı", "Ortalama": "ortalaması", "Maks": "en yüksek değeri", "Min": "en düşük değeri"}[islev]
        return sonuc(_formul_oneri(f"“{t.basliklar[deger]}” {etiket}" + (" (koşullu)" if kos else ""),
                                   "Tek bir hücreye yazılır.", f, t, hedef, kitap))

    return sor("İsteğinizi anlayamadım.")
