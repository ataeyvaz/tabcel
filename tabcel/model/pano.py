"""Pano: kopyalanan hücre verisi, TSV/HTML okuma-yazma, yapıştırma planı. Qt yok.

Kendi içinde tam (değer + formül; biçim Faz 3'te), dışarıya/dışarıdan TSV ve HTML tablo
(Excel, Google E-Tablolar, Sözcük, web tabloları). Dışarıdan gelen metin hücreye elle
yazılmış gibi çözülür (`girdi_coz`).

Formül kopyalanınca göreli başvurular kayar (`formul.kaydir.kopyala`); kes-yapıştır
`komutlar.HucreTasi` ile yapılır (grid). Kendi biçimimiz formülü saklanan biçimde (sayfa
kimlikli) taşır; başka oturumdan gelirse `en_formul` (İngilizce, sayfa adlı) kullanılır.
"""
import json
import re
from dataclasses import dataclass, field
from html import escape
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple

from .adres import MAX_COL, MAX_ROW, AdresHatasi, Aralik
from .girdi import girdi_coz
from .gosterim import goster
from .notlar import Not
from .sayfa import Anahtar, Hucre, Sayfa
from .stil import Stil, stil_sozluk, stil_sozlukten

TOPLU_DOLDURMA_SINIRI = 200_000     # tek hücreyi seçime yayarken en çok hücre


# ---------------------------------------------------------------- kopyalanan veri
@dataclass
class PanoVerisi:
    satir_sayisi: int
    sutun_sayisi: int
    hucreler: Dict[Tuple[int, int], Hucre] = field(default_factory=dict)   # (satır farkı, sütun farkı)
    # formül hücrelerinin hesaplanmış sonuçları (yalnızca dışarıya metin verirken; kendi biçimimize girmez)
    sonuclar: Dict[Tuple[int, int], object] = field(default_factory=dict, compare=False)
    # kaynağın sol üst köşesi (formül kopyalanırken başvuru kaydırması için); bilinmiyorsa None
    kaynak_satir: Optional[int] = None
    kaynak_sutun: Optional[int] = None
    oturum: Optional[str] = None                      # verinin geldiği uygulama oturumu
    # (satır farkı, sütun farkı) → İngilizce sayfa adlı formül (başka oturuma taşımak için)
    en_formul: Dict[Tuple[int, int], str] = field(default_factory=dict, compare=False)
    # (satır farkı, sütun farkı) → Stil: yalnız varsayılandan farklı etkin stiller (Stil nesnesi, kimlik
    # değil: başka kitap/oturuma güvenli). Boş ama biçimli hücreler de burada olur
    stiller: Dict[Tuple[int, int], Stil] = field(default_factory=dict, compare=False)
    # birleşik hücreler: (satır farkı, sütun farkı, yükseklik, genişlik) — yalnız tamamı kopyalanan birleşimler
    birlesimler: List[Tuple[int, int, int, int]] = field(default_factory=list, compare=False)
    # (satır farkı, sütun farkı) → Not (kendi biçimimizde taşınır; dışarıya metin/HTML'de gitmez)
    notlar: Dict[Tuple[int, int], Not] = field(default_factory=dict, compare=False)

    def json_yaz(self) -> str:
        return json.dumps({
            "s": self.satir_sayisi, "c": self.sutun_sayisi,
            "ks": self.kaynak_satir, "kc": self.kaynak_sutun, "o": self.oturum,
            "h": [[dr, dc, h.deger, h.formul, self.en_formul.get((dr, dc))]
                  for (dr, dc), h in sorted(self.hucreler.items())],
            "st": [[dr, dc, stil_sozluk(st)] for (dr, dc), st in sorted(self.stiller.items())],
            "b": [list(b) for b in self.birlesimler],
            "n": [[dr, dc, n.metin, n.yazar] for (dr, dc), n in sorted(self.notlar.items())],
        })

    @staticmethod
    def json_oku(metin: str) -> "PanoVerisi":
        d = json.loads(metin)
        v = PanoVerisi(int(d["s"]), int(d["c"]), kaynak_satir=d.get("ks"),
                       kaynak_sutun=d.get("kc"), oturum=d.get("o"))
        for dr, dc, deger, formul, *ek in d["h"]:
            v.hucreler[(dr, dc)] = Hucre(deger, formul)
            if ek and ek[0]:
                v.en_formul[(dr, dc)] = ek[0]
        for dr, dc, sozluk in d.get("st", []):
            v.stiller[(dr, dc)] = stil_sozlukten(sozluk)
        v.birlesimler = [tuple(b) for b in d.get("b", [])]
        for dr, dc, metin, yazar in d.get("n", []):
            v.notlar[(dr, dc)] = Not(metin, yazar)
        return v


def pano_araligi(sayfa: Sayfa, secim: Aralik) -> Aralik:
    """Seçimi kullanılan alanla sınırlar (tam satır/sütun seçimi 1 milyon boş satır kopyalamasın)."""
    kul = sayfa.kullanilan_aralik(bicim_dahil=True)      # biçimli boş hücreler de kopyalanır
    son_s, son_c = secim.ilk_satir, secim.ilk_sutun
    if kul is not None:
        son_s = max(secim.ilk_satir, min(secim.son_satir, kul[2]))
        son_c = max(secim.ilk_sutun, min(secim.son_sutun, kul[3]))
    for b in sayfa.birlesim_kesisen(secim):               # boş birleşim de kırpılmasın
        if b.son_satir <= secim.son_satir and b.son_sutun <= secim.son_sutun:
            son_s, son_c = max(son_s, b.son_satir), max(son_c, b.son_sutun)
    return Aralik(secim.ilk_satir, secim.ilk_sutun, son_s, son_c)


def pano_verisi_al(sayfa: Sayfa, ar: Aralik) -> PanoVerisi:
    v = PanoVerisi(ar.son_satir - ar.ilk_satir + 1, ar.son_sutun - ar.ilk_sutun + 1,
                   kaynak_satir=ar.ilk_satir, kaynak_sutun=ar.ilk_sutun)
    for r, c, h in sayfa.aralikta(ar):
        v.hucreler[(r - ar.ilk_satir, c - ar.ilk_sutun)] = h
        if h.formul is not None:
            sonuc = sayfa.sonuc(r, c)
            if sonuc is not None:
                v.sonuclar[(r - ar.ilk_satir, c - ar.ilk_sutun)] = sonuc
    if sayfa._stil or sayfa.satir_stil or sayfa.sutun_stil:
        stil_kimligi, havuz = sayfa.stil_kimligi, sayfa.havuz
        for r in range(ar.ilk_satir, ar.son_satir + 1):
            for c in range(ar.ilk_sutun, ar.son_sutun + 1):
                k = stil_kimligi(r, c)
                if k:
                    v.stiller[(r - ar.ilk_satir, c - ar.ilk_sutun)] = havuz.stil(k)
    for b in sayfa.birlesim_kesisen(ar):
        if (ar.ilk_satir <= b.ilk_satir and b.son_satir <= ar.son_satir
                and ar.ilk_sutun <= b.ilk_sutun and b.son_sutun <= ar.son_sutun):
            v.birlesimler.append((b.ilk_satir - ar.ilk_satir, b.ilk_sutun - ar.ilk_sutun,
                                  b.son_satir - b.ilk_satir + 1, b.son_sutun - b.ilk_sutun + 1))
    for (r, c), n in sayfa.notlar.items():
        if ar.ilk_satir <= r <= ar.son_satir and ar.ilk_sutun <= c <= ar.son_sutun:
            v.notlar[(r - ar.ilk_satir, c - ar.ilk_sutun)] = n
    return v


def yapistirma_notlari(veri: PanoVerisi, sayfa: Sayfa, satir: int, sutun: int,
                       secim: Optional[Aralik] = None) -> Dict[Anahtar, Optional[Not]]:
    """Yapıştırmanın not planı (Excel "Tümü"): kaynaktaki not hedefe yazılır; notsuz kaynak hücre
    hedefteki notu siler. Yalnız kendi biçimimizde (kaynak konumu bilinen) anlamlıdır; yapılacak
    değişiklik yoksa boş sözlük."""
    if veri.kaynak_satir is None or not (veri.notlar or sayfa.notlar):
        return {}
    plan: Dict[Anahtar, Optional[Not]] = {}
    for r, c, dr, dc in _yerlestir(veri, satir, sutun, secim):
        n = veri.notlar.get((dr, dc))
        if n is not None or (r, c) in sayfa.notlar:
            plan[(r, c)] = n
    return plan


def hucre_metni(h: Optional[Hucre], sonuc=None) -> str:
    """Dışarı verilen metin (Excel gibi görünen değer). Formülün hesaplanmış sonucu yoksa
    (Faz 2'ye kadar hep böyle) formül metni verilir."""
    if h is None:
        return ""
    if h.formul is not None:
        return goster(sonuc) if sonuc is not None else h.formul
    return goster(h.deger)


def metin_satirlari(v: PanoVerisi) -> List[List[str]]:
    return [[hucre_metni(v.hucreler.get((r, c)), v.sonuclar.get((r, c))) for c in range(v.sutun_sayisi)]
            for r in range(v.satir_sayisi)]


def metinden_pano_verisi(satirlar: List[List[str]], coz=girdi_coz) -> Optional[PanoVerisi]:
    """`coz(metin) -> Hucre | None`: hücreye elle yazılmış gibi çözer (arayüz, formülü saklanan
    biçime çeviren `ceviri.hucre_girdisi`'ni verir; hatalı formül metin olarak kalır)."""
    if not satirlar:
        return None
    v = PanoVerisi(len(satirlar), max(len(s) for s in satirlar))
    for r, satir in enumerate(satirlar):
        for c, metin in enumerate(satir):
            h = coz(metin)
            if h is not None:
                v.hucreler[(r, c)] = h
    return v


# ---------------------------------------------------------------- TSV
def tsv_yaz(satirlar: List[List[str]]) -> str:
    """Excel gibi: sekme/satır sonu/çift tırnak içeren hücre tırnaklanır, tırnak ikilenir."""
    def alan(m: str) -> str:
        if any(ch in m for ch in '\t\r\n"'):
            return '"' + m.replace('"', '""') + '"'
        return m
    return "\r\n".join("\t".join(alan(m) for m in s) for s in satirlar) + "\r\n"


def tsv_coz(metin: str) -> List[List[str]]:
    satirlar: List[List[str]] = []
    satir: List[str] = []
    alan: List[str] = []
    tirnakli = False
    i, n = 0, len(metin)
    alan_basi = True
    while i < n:
        ch = metin[i]
        if tirnakli:
            if ch == '"':
                if i + 1 < n and metin[i + 1] == '"':
                    alan.append('"')
                    i += 1
                else:
                    tirnakli = False
            else:
                alan.append(ch)
        elif ch == '"' and alan_basi:
            tirnakli = True
            alan_basi = False
        elif ch == "\t":
            satir.append("".join(alan)); alan = []; alan_basi = True
            i += 1
            continue
        elif ch in "\r\n":
            if ch == "\r" and i + 1 < n and metin[i + 1] == "\n":
                i += 1
            satir.append("".join(alan)); alan = []
            satirlar.append(satir); satir = []
            alan_basi = True
            i += 1
            continue
        else:
            alan.append(ch)
        alan_basi = False
        i += 1
    if alan or satir or tirnakli:
        satir.append("".join(alan))
        satirlar.append(satir)
    return satirlar


# ---------------------------------------------------------------- HTML
def _css(st: Optional[Stil]) -> str:
    """Dışarıya (Excel/Word/web) giden HTML için temel satır içi CSS: kalın, italik, çizgiler, renk, dolgu, hizalama."""
    if st is None:
        return ""
    k = []
    if st.kalin:
        k.append("font-weight:bold")
    if st.italik:
        k.append("font-style:italic")
    cizgi = [d for d, a in (("underline", st.alti_cizili != "yok"), ("line-through", st.ustu_cizili)) if a]
    if cizgi:
        k.append("text-decoration:" + " ".join(cizgi))
    if st.yazi_rengi:
        k.append(f"color:{st.yazi_rengi}")
    if st.dolgu:
        k.append(f"background:{st.dolgu}")
    hiza = {"sol": "left", "orta": "center", "sag": "right"}.get(st.yatay)
    if hiza:
        k.append(f"text-align:{hiza}")
    return f' style="{";".join(k)}"' if k else ""


def html_yaz(satirlar: List[List[str]], stiller: Optional[Dict[Tuple[int, int], Stil]] = None) -> str:
    stiller = stiller or {}
    govde = "".join(
        "<tr>" + "".join(f"<td{_css(stiller.get((r, c)))}>{escape(m).replace(chr(10), '<br>')}</td>"
                         for c, m in enumerate(s)) + "</tr>"
        for r, s in enumerate(satirlar))
    return f"<table>{govde}</table>"


class _TabloAyristirici(HTMLParser):
    """İlk (en dıştaki) tablonun satır/hücrelerini okur; colspan kadar boş hücre ekler."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.satirlar: List[List[str]] = []
        self._tablo = 0
        self._satir: Optional[List[str]] = None
        self._hucre: Optional[List[str]] = None
        self._span = 1
        self._yoksay = 0           # <script>/<style> içi

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._yoksay += 1
        elif tag == "table":
            self._tablo += 1
        elif self._tablo != 1:
            return
        elif tag == "tr":
            self._satir = []
        elif tag in ("td", "th") and self._satir is not None:
            self._hucre = []
            try:
                self._span = max(1, min(int(dict(attrs).get("colspan", 1)), 1000))
            except (TypeError, ValueError):
                self._span = 1
        elif tag == "br" and self._hucre is not None:
            self._hucre.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._yoksay = max(0, self._yoksay - 1)
        elif tag == "table":
            self._tablo -= 1
        elif self._tablo != 1:
            return
        elif tag in ("td", "th") and self._hucre is not None and self._satir is not None:
            parcalar = "".join(self._hucre).replace("\xa0", " ").split("\n")
            metin = "\n".join(p.strip() for p in parcalar).strip("\n ")
            self._satir.append(metin)
            self._satir.extend([""] * (self._span - 1))
            self._hucre = None
        elif tag == "tr" and self._satir is not None:
            self.satirlar.append(self._satir)
            self._satir = None

    def handle_data(self, data):
        if self._hucre is not None and not self._yoksay:
            self._hucre.append(re.sub(r"\s+", " ", data))   # kaynak HTML'deki satır sonları boşluktur


def html_tablo_coz(html: str) -> List[List[str]]:
    p = _TabloAyristirici()
    try:
        p.feed(html)
        p.close()
    except Exception:
        return []
    return p.satirlar


# ---------------------------------------------------------------- yapıştırma
def _kaydirilmis(h: Hucre, dr: int, dc: int) -> Hucre:
    if h.formul is None or (dr == 0 and dc == 0):
        return h
    from ..formul.kaydir import kopyala                 # model → formul yalnız burada
    yeni = kopyala(h.formul, dr, dc)
    return h if yeni == h.formul else Hucre(None, yeni)


def _yerlestir(veri: PanoVerisi, satir: int, sutun: int, secim: Optional[Aralik]):
    """Yapıştırma yerleşimi: (satır, sütun, kaynak satır farkı, kaynak sütun farkı) üretir.
    Seçim kaynağın tam katıysa desen seçime yinelenir. Sayfa sınırını aşarsa AdresHatasi."""
    sr, sc = veri.satir_sayisi, veri.sutun_sayisi
    tekrar_r = tekrar_c = 1
    if secim is not None:
        yr = secim.son_satir - secim.ilk_satir + 1
        yc = secim.son_sutun - secim.ilk_sutun + 1
        if (yr, yc) != (1, 1) and yr % sr == 0 and yc % sc == 0 and yr * yc <= TOPLU_DOLDURMA_SINIRI:
            tekrar_r, tekrar_c = yr // sr, yc // sc
            satir, sutun = secim.ilk_satir, secim.ilk_sutun
    if satir + sr * tekrar_r - 1 > MAX_ROW or sutun + sc * tekrar_c - 1 > MAX_COL:
        raise AdresHatasi("Yapıştırılan veri sayfa sınırlarını aşıyor")
    for tr in range(tekrar_r):
        for tc in range(tekrar_c):
            for dr in range(sr):
                for dc in range(sc):
                    yield satir + tr * sr + dr, sutun + tc * sc + dc, dr, dc


def yapistirma_stilleri(veri: PanoVerisi, satir: int, sutun: int, secim: Optional[Aralik],
                        havuz) -> Dict[Anahtar, int]:
    """Yapıştırmanın biçim planı {(satır, sütun): stil kimliği} (Excel "Tümü": kaynakta biçimsiz hücre
    hedefin biçimini de varsayılana döndürür). Veride hiç stil yoksa boş sözlük DEĞİL, her hedef için 0
    döner; çağıran hedefte biçim yoksa atlayabilir."""
    kimlikler = {anahtar: havuz.kimlik(st) for anahtar, st in veri.stiller.items()}
    return {(r, c): kimlikler.get((dr, dc), 0) for r, c, dr, dc in _yerlestir(veri, satir, sutun, secim)}


def yapistirma_birlesimleri(veri: PanoVerisi, satir: int, sutun: int,
                            secim: Optional[Aralik] = None) -> List[Aralik]:
    """Yapıştırmanın oluşturacağı birleşimler (seçim deseni yinelerse her yinelemede)."""
    if not veri.birlesimler:
        return []
    ust_sol = {(dr, dc): (y, g) for dr, dc, y, g in veri.birlesimler}
    sonuc = []
    for r, c, dr, dc in _yerlestir(veri, satir, sutun, secim):
        if (dr, dc) in ust_sol:
            y, g = ust_sol[(dr, dc)]
            sonuc.append(Aralik(r, c, r + y - 1, c + g - 1))
    return sonuc


def birlesim_kismen_kesiyor(sayfa: Sayfa, bolge: Aralik) -> bool:
    """Hedef bölge, bölgenin dışına taşan bir birleşimi kesiyor mu (yapıştırma/taşıma reddedilir)."""
    for b in sayfa.birlesim_kesisen(bolge):
        if not (bolge.ilk_satir <= b.ilk_satir and b.son_satir <= bolge.son_satir
                and bolge.ilk_sutun <= b.ilk_sutun and b.son_sutun <= bolge.son_sutun):
            return True
    return False


def yapistirma_plani(veri: PanoVerisi, satir: int, sutun: int,
                     secim: Optional[Aralik] = None) -> Dict[Anahtar, Optional[Hucre]]:
    """Yapıştırma sonucu: {(satır, sütun): Hucre | None}. Kaynaktaki boş hücreler hedefi boşaltır.
    Kaynak konumu biliniyorsa formüllerin göreli başvuruları hedefe göre kayar.

    Seçim kaynağın tam katıysa (ör. tek hücre → büyük seçim) desen seçime yinelenir (Excel gibi).
    Sayfa sınırını aşıyorsa AdresHatasi.
    """
    plan: Dict[Anahtar, Optional[Hucre]] = {}
    for r, c, dr, dc in _yerlestir(veri, satir, sutun, secim):
        h = veri.hucreler.get((dr, dc))
        if h is not None and h.formul is not None and veri.kaynak_satir is not None:
            h = _kaydirilmis(h, r - (veri.kaynak_satir + dr), c - (veri.kaynak_sutun + dc))
        plan[(r, c)] = h
    return plan
