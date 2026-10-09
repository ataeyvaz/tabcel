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
from .sayfa import Anahtar, Hucre, Sayfa

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

    def json_yaz(self) -> str:
        return json.dumps({
            "s": self.satir_sayisi, "c": self.sutun_sayisi,
            "ks": self.kaynak_satir, "kc": self.kaynak_sutun, "o": self.oturum,
            "h": [[dr, dc, h.deger, h.formul, self.en_formul.get((dr, dc))]
                  for (dr, dc), h in sorted(self.hucreler.items())],
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
        return v


def pano_araligi(sayfa: Sayfa, secim: Aralik) -> Aralik:
    """Seçimi kullanılan alanla sınırlar (tam satır/sütun seçimi 1 milyon boş satır kopyalamasın)."""
    kul = sayfa.kullanilan_aralik()
    if kul is None:
        return Aralik(secim.ilk_satir, secim.ilk_sutun, secim.ilk_satir, secim.ilk_sutun)
    return Aralik(secim.ilk_satir, secim.ilk_sutun,
                  max(secim.ilk_satir, min(secim.son_satir, kul[2])),
                  max(secim.ilk_sutun, min(secim.son_sutun, kul[3])))


def pano_verisi_al(sayfa: Sayfa, ar: Aralik) -> PanoVerisi:
    v = PanoVerisi(ar.son_satir - ar.ilk_satir + 1, ar.son_sutun - ar.ilk_sutun + 1,
                   kaynak_satir=ar.ilk_satir, kaynak_sutun=ar.ilk_sutun)
    for r, c, h in sayfa.aralikta(ar):
        v.hucreler[(r - ar.ilk_satir, c - ar.ilk_sutun)] = h
        if h.formul is not None:
            sonuc = sayfa.sonuc(r, c)
            if sonuc is not None:
                v.sonuclar[(r - ar.ilk_satir, c - ar.ilk_sutun)] = sonuc
    return v


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
def html_yaz(satirlar: List[List[str]]) -> str:
    govde = "".join(
        "<tr>" + "".join(f"<td>{escape(m).replace(chr(10), '<br>')}</td>" for m in s) + "</tr>"
        for s in satirlar)
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


def yapistirma_plani(veri: PanoVerisi, satir: int, sutun: int,
                     secim: Optional[Aralik] = None) -> Dict[Anahtar, Optional[Hucre]]:
    """Yapıştırma sonucu: {(satır, sütun): Hucre | None}. Kaynaktaki boş hücreler hedefi boşaltır.
    Kaynak konumu biliniyorsa formüllerin göreli başvuruları hedefe göre kayar.

    Seçim kaynağın tam katıysa (ör. tek hücre → büyük seçim) desen seçime yinelenir (Excel gibi).
    Sayfa sınırını aşıyorsa AdresHatasi.
    """
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
    plan: Dict[Anahtar, Optional[Hucre]] = {}
    for tr in range(tekrar_r):
        for tc in range(tekrar_c):
            for dr in range(sr):
                for dc in range(sc):
                    r, c = satir + tr * sr + dr, sutun + tc * sc + dc
                    h = veri.hucreler.get((dr, dc))
                    if h is not None and h.formul is not None and veri.kaynak_satir is not None:
                        h = _kaydirilmis(h, r - (veri.kaynak_satir + dr), c - (veri.kaynak_sutun + dc))
                    plan[(r, c)] = h
    return plan
