"""Pano: kopyalanan hücre verisi, TSV/HTML okuma-yazma, yapıştırma planı. Qt yok.

Kendi içinde tam (değer + formül; biçim Faz 3'te), dışarıya/dışarıdan TSV ve HTML tablo
(Excel, Google E-Tablolar, Sözcük, web tabloları). Dışarıdan gelen metin hücreye elle
yazılmış gibi çözülür (`girdi_coz`).

Bilerek eksik: formül kopyalanınca göreli başvuruların kayması Faz 2'de (başvuru
kaydırma ile birlikte); şimdilik formül metni olduğu gibi taşınır.
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

    def json_yaz(self) -> str:
        return json.dumps({
            "s": self.satir_sayisi, "c": self.sutun_sayisi,
            "h": [[dr, dc, h.deger, h.formul] for (dr, dc), h in sorted(self.hucreler.items())],
        })

    @staticmethod
    def json_oku(metin: str) -> "PanoVerisi":
        d = json.loads(metin)
        v = PanoVerisi(int(d["s"]), int(d["c"]))
        for dr, dc, deger, formul in d["h"]:
            v.hucreler[(dr, dc)] = Hucre(deger, formul)
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
    v = PanoVerisi(ar.son_satir - ar.ilk_satir + 1, ar.son_sutun - ar.ilk_sutun + 1)
    for r, c, h in sayfa.dolu_hucreler():
        if ar.ilk_satir <= r <= ar.son_satir and ar.ilk_sutun <= c <= ar.son_sutun:
            v.hucreler[(r - ar.ilk_satir, c - ar.ilk_sutun)] = h
    return v


def hucre_metni(h: Optional[Hucre]) -> str:
    """Dışarı verilen metin. Formülün hesaplanmış değeri henüz yok (Faz 2): formül metni verilir."""
    if h is None:
        return ""
    if h.deger is None and h.formul is not None:
        return h.formul
    return goster(h.deger)


def metin_satirlari(v: PanoVerisi) -> List[List[str]]:
    return [[hucre_metni(v.hucreler.get((r, c))) for c in range(v.sutun_sayisi)]
            for r in range(v.satir_sayisi)]


def metinden_pano_verisi(satirlar: List[List[str]]) -> Optional[PanoVerisi]:
    if not satirlar:
        return None
    v = PanoVerisi(len(satirlar), max(len(s) for s in satirlar))
    for r, satir in enumerate(satirlar):
        for c, metin in enumerate(satir):
            h = girdi_coz(metin)
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
def yapistirma_plani(veri: PanoVerisi, satir: int, sutun: int,
                     secim: Optional[Aralik] = None) -> Dict[Anahtar, Optional[Hucre]]:
    """Yapıştırma sonucu: {(satır, sütun): Hucre | None}. Kaynaktaki boş hücreler hedefi boşaltır.

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
                    plan[(satir + tr * sr + dr, sutun + tc * sc + dc)] = veri.hucreler.get((dr, dc))
    return plan
