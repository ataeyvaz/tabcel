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


# ---------------------------------------------------------------- Excel/Word ile biçim sadakati (2026-10-15)
# Dışarıya: görünen metin + Excel'in anladığı HTML öznitelikleri (`x:num`, `x:fmla`, `mso-number-format`); içeri: Excel HTML'indeki
# sınıf/satır içi CSS (kalın, italik, renk, dolgu, hizalama, sayı biçimi) ve `x:num`/`x:fmla`. Gerçek Excel 16 (COM) ile denendi.
_KALIPLAR = {"General": "General", "Standard": "#,##0.00", "Percent": "0%", "Fixed": "0.00", "Scientific": "0.00E+00",
             "Short Date": "dd.mm.yyyy", "@": "@"}


def gorunen_satirlar(v: PanoVerisi) -> List[List[str]]:
    """`metin_satirlari` gibi, ama sayı biçimi olan hücrelerde (tarih, para, yüzde…) ekranda görünen metni verir (Excel dışarıya
    biçimli metin verir; tarih seri sayı olarak değil `15.10.2026` olarak gider)."""
    from .sayi_bicimi import BicimHatasi, bicimle
    cikti = []
    for r in range(v.satir_sayisi):
        satir = []
        for c in range(v.sutun_sayisi):
            h = v.hucreler.get((r, c))
            st = v.stiller.get((r, c))
            deger = v.sonuclar.get((r, c)) if h is not None and h.formul is not None else (None if h is None else h.deger)
            if st is not None and st.sayi_bicimi not in ("General", "@") and isinstance(deger, float):
                try:
                    satir.append(bicimle(deger, st.sayi_bicimi).metin)
                    continue
                except (BicimHatasi, ArithmeticError, OverflowError, ValueError):
                    pass
            satir.append(hucre_metni(h, v.sonuclar.get((r, c))))
        cikti.append(satir)
    return cikti


def _mso_kod(kod: str) -> str:
    """Kanonik biçim kodu → CSS `mso-number-format` değeri (Excel'in yaptığı gibi `# , . /` ters bölüyle kaçırılır)."""
    kacis = "".join("\\" + ch if ch in '#,./"' else ch for ch in kod)
    return '"' + kacis + '"'


def html_ayrintilari(v: PanoVerisi) -> Dict[Tuple[int, int], dict]:
    """Excel'e giden HTML için hücre başına {num, fmla, kod}: sayısal değer, İngilizce formül, kanonik sayı biçimi."""
    cikti = {}
    for (r, c), h in v.hucreler.items():
        d = {}
        if h.formul is not None:
            f = v.en_formul.get((r, c))
            if f:
                d["fmla"] = f
            sonuc = v.sonuclar.get((r, c))
            if isinstance(sonuc, float) and not isinstance(sonuc, bool):
                d["num"] = sonuc
        elif isinstance(h.deger, float) and not isinstance(h.deger, bool):
            d["num"] = h.deger
        st = v.stiller.get((r, c))
        if st is not None and st.sayi_bicimi != "General":
            d["kod"] = st.sayi_bicimi
        if d:
            cikti[(r, c)] = d
    return cikti


def html_yaz_excel(satirlar: List[List[str]], stiller: Optional[Dict[Tuple[int, int], Stil]] = None,
                   ayrinti: Optional[Dict[Tuple[int, int], dict]] = None) -> str:
    """`html_yaz` + Excel uyumlu öznitelikler. Excel yapıştırınca sayıyı sayı, biçimi biçim, formülü formül olarak alır."""
    stiller, ayrinti = stiller or {}, ayrinti or {}
    govde = []
    for r, s in enumerate(satirlar):
        hucreler = []
        for c, m in enumerate(s):
            d = ayrinti.get((r, c), {})
            oz = ""
            if "fmla" in d:
                oz += f' x:fmla="{escape(d["fmla"], quote=True)}"'
            if "num" in d:
                oz += f' x:num="{d["num"]!r}"'
            css = _css(stiller.get((r, c)))
            mso = f"mso-number-format:{_mso_kod(d['kod'])}" if "kod" in d else ""
            if mso:
                if css:
                    css = css[:-1] + ";" + escape(mso, quote=True) + '"'
                else:
                    css = f' style="{escape(mso, quote=True)}"'
            hucreler.append(f"<td{oz}{css}>{escape(m).replace(chr(10), '<br>')}</td>")
        govde.append("<tr>" + "".join(hucreler) + "</tr>")
    return ('<html xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40"><body>'
            f'<table>{"".join(govde)}</table></body></html>')


def _kod_coz(deger: str) -> Optional[str]:
    """CSS `mso-number-format` değeri → kanonik sayı biçimi kodu (None = Genel/çözülemedi)."""
    d = deger.strip()
    if len(d) >= 2 and d[0] == d[-1] == '"':
        d = d[1:-1]
    d = re.sub(r"\\(.)", r"\1", d)
    if d in _KALIPLAR:
        d = _KALIPLAR[d]
    return None if d in ("", "General") else d


_RENKLER = {"black": "#000000", "white": "#FFFFFF", "red": "#FF0000", "green": "#008000", "blue": "#0000FF", "yellow": "#FFFF00"}


def _renk(deger: str) -> Optional[str]:
    d = deger.strip().lower()
    m = re.match(r"^#([0-9a-f]{6})\b", d)
    if m:
        return "#" + m.group(1).upper()
    m = re.match(r"^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", d)
    if m:
        return "#%02X%02X%02X" % tuple(min(255, int(x)) for x in m.groups())
    return _RENKLER.get(d.split()[0]) if d else None


def _css_kurallari(blok: str) -> Dict[str, Dict[str, str]]:
    """<style> içeriğinden {sınıf adı: {özellik: değer}} (yalnız `.sinif` seçicileri)."""
    blok = re.sub(r"<!--|-->", "", blok)
    cikti: Dict[str, Dict[str, str]] = {}
    for sec, govde in re.findall(r"([^{}]+)\{([^{}]*)\}", blok):
        d = dict((k.strip().lower(), v.strip()) for k, _, v in (p.partition(":") for p in govde.split(";")) if k.strip())
        for ad in re.findall(r"\.([A-Za-z0-9_\-]+)", sec):
            cikti.setdefault(ad, {}).update(d)
    return cikti


def _stilden(oz: Dict[str, str]) -> Tuple[Optional[Stil], Optional[str]]:
    """CSS özellikleri → (Stil | None, sayı biçimi kodu | None); varsayılandan farklı bir şey yoksa Stil None."""
    alan = {}
    if "font-weight" in oz and (oz["font-weight"].lower() == "bold" or (oz["font-weight"].isdigit() and int(oz["font-weight"]) >= 600)):
        alan["kalin"] = True
    if oz.get("font-style", "").lower() == "italic":
        alan["italik"] = True
    td = oz.get("text-decoration", "").lower()
    if "underline" in td:
        alan["alti_cizili"] = "tek"
    if "line-through" in td:
        alan["ustu_cizili"] = True
    r = _renk(oz["color"]) if "color" in oz else None
    if r and r != "#000000":
        alan["yazi_rengi"] = r
    bg = oz.get("background") or oz.get("background-color") or ""
    r = _renk(bg) if bg else None
    if r and r != "#FFFFFF":
        alan["dolgu"] = r
    hiza = {"left": "sol", "center": "orta", "right": "sag"}.get(oz.get("text-align", "").lower())
    if hiza and hiza != "sag":                       # Excel sayıya `align=right` ekler; bu varsayılan davranıştır
        alan["yatay"] = hiza
    if oz.get("white-space", "").lower() == "normal":
        alan["kaydir"] = True
    kod = _kod_coz(oz["mso-number-format"]) if "mso-number-format" in oz else None
    if kod:
        alan["sayi_bicimi"] = kod
    return (Stil(**alan) if alan else None), kod


class _StilliAyristirici(_TabloAyristirici):
    """`_TabloAyristirici` + hücre başına öznitelikler (`x:num`, `x:fmla`, `x:str`, sınıf ve satır içi CSS)."""

    def __init__(self):
        super().__init__()
        self.ayrinti: Dict[Tuple[int, int], dict] = {}
        self._css_metni: List[str] = []
        self._stil_ici = False
        self._gecerli: Optional[dict] = None

    def handle_starttag(self, tag, attrs):
        if tag == "style":
            self._stil_ici = True
        if tag in ("td", "th") and self._tablo == 1 and self._satir is not None:
            self._gecerli = {k.lower(): (v or "") for k, v in attrs}
        super().handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == "style":
            self._stil_ici = False
        if tag in ("td", "th") and self._tablo == 1 and self._hucre is not None and self._satir is not None:
            self.ayrinti[(len(self.satirlar), len(self._satir))] = self._gecerli or {}
            self._gecerli = None
        super().handle_endtag(tag)

    def handle_data(self, data):
        if self._stil_ici:
            self._css_metni.append(data)
        super().handle_data(data)


def html_tablo_stilli(html: str):
    """`(satırlar, {(r, c): {"num": float|None, "fmla": str|None, "str": bool, "stil": Stil|None, "kod": str|None}})`.
    Excel HTML'inden okunur; çözülemeyen/bozuk HTML için `([], {})`."""
    p = _StilliAyristirici()
    try:
        p.feed(html)
        p.close()
    except Exception:
        return [], {}
    kurallar = _css_kurallari("".join(p._css_metni))
    cikti: Dict[Tuple[int, int], dict] = {}
    for anahtar, oz in p.ayrinti.items():
        css: Dict[str, str] = {}
        for sinif in oz.get("class", "").split():
            css.update(kurallar.get(sinif, {}))
        for parca in oz.get("style", "").split(";"):
            k, _, v = parca.partition(":")
            if k.strip():
                css[k.strip().lower()] = v.strip()
        if oz.get("align") and "text-align" not in css:
            css["text-align"] = oz["align"]
        stil, kod = _stilden(css)
        d = {"stil": stil, "kod": kod, "str": "x:str" in oz}
        try:
            d["num"] = float(oz["x:num"]) if oz.get("x:num", "") != "" else None
        except ValueError:
            d["num"] = None
        d["fmla"] = oz.get("x:fmla") or None
        cikti[anahtar] = d
    return p.satirlar, cikti
