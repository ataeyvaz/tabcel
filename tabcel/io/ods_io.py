"""OpenDocument Hesap Tablosu (.ods) aç/kaydet — Faz 8c. Yeni bağımlılık yok: `zipfile` + `ElementTree`.

Desteklenen: sayfalar (+ sekme adı), değerler (sayı, metin, mantıksal, tarih/saat → seri sayı, yüzde, para), hata değerleri,
formüller (ODF `of:=` ⇄ kanonik; sonuçlar yeniden hesaplanır), birleşimler, sütun genişliği/satır yüksekliği/gizleme,
hücre biçimi (yazı tipi, kalın/italik/altı-üstü çizili, renk, dolgu, kenarlık, hizalama, kaydırma) ve temel sayı biçimleri
(sayı, binlik, yüzde, para, tarih/saat, metin), dondurma (yazarken). **Okunmayanlar/yazılmayanlar** (uyarı verilir): grafik,
resim, koşullu biçim, veri doğrulama, notlar, tanımlı adlar, filtre, sayfa yapısı, desteklenmeyen sayı biçimi kodları.
Excel ve LibreOffice ile uyum gerçek Excel'de (COM) iki yönde denenir (`araclar/ods_dogrula.ps1`)."""
import datetime
import io
import os
import re
import zipfile
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape, quoteattr

from ..formul import ceviri
from ..formul.sozcuk import FormulHatasi
from ..model import olcu
from ..model.adres import MAX_COL, MAX_ROW, Aralik
from ..model.deger import Hata, hata_bul
from ..model.sayfa import CalismaKitabi, Hucre, Sayfa
from ..model.stil import Kenarlik, Stil
from .xlsx_io import Rapor, XlsxHatasi, _FormulOnbellek, _formul_oku, _formul_yaz

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "number": "urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0",
    "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
    "of": "urn:oasis:names:tc:opendocument:xmlns:of:1.2",       # `of:=…` formül öneki bu ad alanıyla çözülür (Excel şart koşar)
}
MIME = "application/vnd.oasis.opendocument.spreadsheet"
_EPOCH = datetime.datetime(1899, 12, 30)
_MAKS_TEKRAR = 200                                              # biçimli boş hücre tekrarı üst sınırı (sütun stili yok)


def _q(onek: str, ad: str) -> str:
    return "{%s}%s" % (NS[onek], ad)


# ====================================================================== OKUMA
_BIRIM = re.compile(r"^\s*(-?[\d.]+)\s*(cm|mm|in|pt|px|pc)?\s*$")


def _piksel(metin: Optional[str]) -> Optional[float]:
    """"2.5cm" → 96 dpi piksel; çözülemezse None."""
    m = _BIRIM.match(metin or "")
    if not m:
        return None
    d, b = float(m.group(1)), m.group(2) or "px"
    return d * {"cm": 96 / 2.54, "mm": 96 / 25.4, "in": 96.0, "pt": 96 / 72, "px": 1.0, "pc": 16.0}[b]


def _renk(metin: Optional[str]) -> Optional[str]:
    return metin.upper() if metin and re.fullmatch(r"#[0-9a-fA-F]{6}", metin) else None


def _sayi_kodu_tarih(ogeler) -> str:
    """number:date-style / time-style çocukları → kanonik kod."""
    k = []
    for o in ogeler:
        ad = o.tag.split("}")[1]
        uzun = o.get(_q("number", "style")) == "long"
        if ad == "day":
            k.append("dd" if uzun else "d")
        elif ad == "month":
            if o.get(_q("number", "textual")) == "true":
                k.append("mmmm" if uzun else "mmm")
            else:
                k.append("mm" if uzun else "m")
        elif ad == "year":
            k.append("yyyy" if uzun else "yy")
        elif ad == "day-of-week":
            k.append("dddd" if uzun else "ddd")
        elif ad == "hours":
            k.append("hh" if uzun else "h")
        elif ad == "minutes":
            k.append("mm" if uzun else "m")
        elif ad == "seconds":
            k.append("ss" if uzun else "s")
        elif ad == "am-pm":
            k.append("AM/PM")
        elif ad == "text":
            k.append((o.text or "").replace('"', ""))
    return "".join(k)


def _sayi_kodu(ogeler, ust) -> str:
    """number:number / scientific / fraction → "#,##0.00" benzeri kod (yalnız sayı kısmı)."""
    n = next((o for o in ogeler if o.tag == _q("number", "number")), None)
    if n is None:
        return "General"
    if n.get(_q("number", "decimal-places")) is None:               # ODF: yoksa "gerektiği kadar" = Genel
        return "General"
    ondalik = int(n.get(_q("number", "decimal-places"), "0") or 0)
    min_tam = int(n.get(_q("number", "min-integer-digits"), "1") or 1)
    binlik = n.get(_q("number", "grouping")) == "true"
    tam = ("#,##" + "0" * max(min_tam, 1)) if binlik else "0" * max(min_tam, 1)
    return tam + (("." + "0" * ondalik) if ondalik else "")


def _veri_stilleri(*kokler) -> Dict[str, str]:
    """{veri stili adı: kanonik sayı biçimi kodu}."""
    sonuc: Dict[str, str] = {}
    for kok in kokler:
        if kok is None:
            continue
        for o in kok.iter():
            etiket = o.tag.split("}")[-1] if "}" in o.tag else ""
            ad = o.get(_q("style", "name"))
            if not ad:
                continue
            if etiket == "number-style":
                sonuc[ad] = _sayi_kodu(list(o), o)
            elif etiket == "percentage-style":
                sonuc[ad] = _sayi_kodu(list(o), o) + "%"
            elif etiket == "currency-style":
                sembol = next((c.text for c in o if c.tag == _q("number", "currency-symbol") and c.text), "")
                kod = _sayi_kodu(list(o), o)
                sonuc[ad] = f'"{sembol}"{kod}' if sembol else kod
            elif etiket in ("date-style", "time-style"):
                sonuc[ad] = _sayi_kodu_tarih(list(o))
            elif etiket == "text-style":
                sonuc[ad] = "@"
    return sonuc


def _stil_ozellikleri(*kokler) -> Dict[Tuple[str, str], dict]:
    """{(aile, ad): {'ata': ata adı, 'veri': veri stili adı, 'oz': {nitelik adı: değer}}} — cell/column/row."""
    s: Dict[Tuple[str, str], dict] = {}
    for kok in kokler:
        if kok is None:
            continue
        for o in kok.iter(_q("style", "style")):
            ad, aile = o.get(_q("style", "name")), o.get(_q("style", "family"))
            if not ad or not aile:
                continue
            oz: dict = {}
            for c in o:
                for k, v in c.attrib.items():
                    oz[k] = v
            s[(aile, ad)] = {"ata": o.get(_q("style", "parent-style-name")),
                             "veri": o.get(_q("style", "data-style-name")), "oz": oz}
    return s


class _StilCozucu:
    def __init__(self, stiller, veri_stilleri, temel_ad):
        self.stiller, self.veri, self.temel_ad = stiller, veri_stilleri, temel_ad
        self._onb: Dict[Tuple[str, str], Tuple[dict, Optional[str]]] = {}
        self.temel = self._birlestir("table-cell", "Default")[0] if ("table-cell", "Default") in stiller else {}

    def _birlestir(self, aile: str, ad: str, derinlik: int = 0):
        anahtar = (aile, ad)
        if anahtar in self._onb:
            return self._onb[anahtar]
        k = self.stiller.get(anahtar)
        if k is None or derinlik > 8:
            return {}, None
        oz, veri = ({}, None)
        if k["ata"]:
            oz, veri = self._birlestir(aile, k["ata"], derinlik + 1)
        oz = {**oz, **k["oz"]}
        veri = k["veri"] or veri
        self._onb[anahtar] = (oz, veri)
        return oz, veri

    def hucre_stili(self, ad: str) -> Stil:
        oz, veri = self._birlestir("table-cell", ad)
        fo, st = (lambda x: _q("fo", x)), (lambda x: _q("style", x))
        temel = self.temel

        def fark(anahtar):
            v = oz.get(anahtar)
            return None if v is None or v == temel.get(anahtar) else v
        boyut = _piksel(oz.get(fo("font-size")))
        t_boyut = _piksel(temel.get(fo("font-size")))
        ad_ = oz.get(st("font-name")) or oz.get(fo("font-family"))
        t_ad = temel.get(st("font-name")) or temel.get(fo("font-family"))
        pt = round(boyut * 0.75, 1) if boyut and boyut != t_boyut else None
        kenarlik = {}
        genel = oz.get(fo("border"))
        for yon, anahtar in (("ust", "border-top"), ("alt", "border-bottom"), ("sol", "border-left"), ("sag", "border-right")):
            b = oz.get(fo(anahtar), genel)
            if b and b != "none":
                kalinlik = _piksel(b.split()[0]) if b.split() else None
                renk = _renk(b.split()[-1]) or "#000000"
                tur = "orta" if kalinlik and kalinlik * 0.75 >= 1.4 else "ince"
                if "double" in b:
                    tur = "cift"
                kenarlik[yon] = (tur, renk)
        yatay = {"start": "sol", "left": "sol", "end": "sag", "right": "sag", "center": "orta",
                 "justify": "iki_yana"}.get(oz.get(fo("text-align")), "genel")
        dikey = {"top": "ust", "middle": "orta", "bottom": "alt"}.get(oz.get(st("vertical-align")), "alt")
        girinti = 0
        sol = _piksel(oz.get(fo("margin-left")))
        if sol:
            girinti = min(max(int(round(sol / 9)), 0), 15)
        dolgu = _renk(oz.get(fo("background-color")))
        kod = self.veri.get(veri, "General") if veri else "General"
        try:
            return Stil(
                yazi_tipi=ad_ if ad_ and ad_ != t_ad else None, boyut=pt if pt and 1 <= pt <= 409 else None,
                kalin=oz.get(fo("font-weight")) == "bold", italik=oz.get(fo("font-style")) == "italic",
                ustu_cizili=(oz.get(st("text-line-through-style")) not in (None, "none")),
                alti_cizili="tek" if oz.get(st("text-underline-style")) not in (None, "none") else "yok",
                yazi_rengi=_renk(fark(fo("color"))), dolgu=dolgu, kenar=Kenarlik(**kenarlik), yatay=yatay,
                dikey=dikey, girinti=girinti, kaydir=oz.get(fo("wrap-option")) == "wrap", sayi_bicimi=kod)
        except ValueError:
            return Stil()


def _metin(hucre) -> str:
    """table-cell içindeki text:p'lerin düz metni (text:s boşluk, text:tab sekme, text:line-break satır sonu)."""
    paragraflar = []
    for p in hucre.findall(_q("text", "p")):
        parca = []

        def gez(e):
            if e.text:
                parca.append(e.text)
            for c in e:
                etiket = c.tag.split("}")[-1]
                if etiket == "s":
                    parca.append(" " * int(c.get(_q("text", "c"), "1")))
                elif etiket == "tab":
                    parca.append("\t")
                elif etiket == "line-break":
                    parca.append("\n")
                else:
                    gez(c)
                if c.tail:
                    parca.append(c.tail)
        gez(p)
        paragraflar.append("".join(parca))
    return "\n".join(paragraflar)


_TARIH = re.compile(r"^(-?\d{4,})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}):(\d{2})(\.\d+)?)?$")
_SURE = re.compile(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$")


def _tarih_seri(metin: str) -> Optional[float]:
    m = _TARIH.match(metin or "")
    if not m:
        return None
    try:
        t = datetime.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4) or 0),
                              int(m.group(5) or 0), int(m.group(6) or 0))
    except ValueError:
        return None
    return (t - _EPOCH).total_seconds() / 86400


def _sure_seri(metin: str) -> Optional[float]:
    m = _SURE.match(metin or "")
    if not m or metin == "P":
        return None
    g, sa, dk, sn = (float(x or 0) for x in m.groups())
    return g + (sa * 3600 + dk * 60 + sn) / 86400


# --- formül: ODF ⇄ kanonik ---------------------------------------------------------------------------
def _disarida(metin: str, islev) -> str:
    """Çift tırnaklı metin sabitlerinin dışındaki parçalara `islev` uygular."""
    p = metin.split('"')
    for i in range(0, len(p), 2):
        p[i] = islev(p[i])
    return '"'.join(p)


def _sayfa_oku(s: str) -> Optional[str]:
    s = s.lstrip("$")
    if not s:
        return None
    if s.startswith("'") and s.endswith("'"):
        s = s[1:-1].replace("''", "'")
    return s


def _odf_basvuru(ic: str) -> str:
    """[…] içi (`.A1`, `.A1:.B2`, `$Sayfa1.A1:.B2`, `'Ad'.A1`) → Excel başvurusu."""
    kis = re.split(r":(?=(?:[^']*'[^']*')*[^']*$)", ic)               # tırnak dışı ':'
    sonuc, sayfa_adi = [], None
    for i, k in enumerate(kis):
        nokta = k.rfind(".")
        ad, hucre = (k[:nokta], k[nokta + 1:]) if nokta >= 0 else ("", k)
        sayfa = _sayfa_oku(ad)
        if i == 0:
            sayfa_adi = sayfa
        sonuc.append(hucre)
    govde = ":".join(sonuc)
    if sayfa_adi is None:
        return govde
    return (f"'{sayfa_adi.replace(chr(39), chr(39) * 2)}'" if not re.fullmatch(r"\w+", sayfa_adi) else sayfa_adi) + "!" + govde


def formul_oku(metin: str) -> str:
    """ODF formülü ("of:=SUM([.A1:.A3];2)") → dosyadaki Excel biçimi ("=SUM(A1:A3,2)")."""
    f = re.sub(r"^[A-Za-z]+:", "", metin.strip())
    if not f.startswith("="):
        f = "=" + f

    def parca(p: str) -> str:
        p = re.sub(r"\[([^\]]*)\]", lambda m: _odf_basvuru(m.group(1)), p)
        return p.replace(";", ",")
    return _disarida(f, parca)


_BAS = (r"(?:(?P<sh>'(?:[^']|'')+'|[^\W\d][\w.]*)!)?")
_HUCRE = r"\$?[A-Z]{1,3}\$?\d+"
_BASV = re.compile(r"(?<![\w.$!])" + _BAS + r"(?P<a>" + _HUCRE + r")(?::(?P<b>" + _HUCRE + r"))?(?![\w(!])")


def formul_yaz(f: str) -> str:
    """Excel biçimli formül ("=SUM(Sayfa1!A1:A3,2)") → ODF ("of:=SUM([$Sayfa1.A1:.A3];2)")."""
    def parca(p: str) -> str:
        def baglan(m):
            sh, a, b = m.group("sh"), m.group("a"), m.group("b")
            if sh and sh.startswith("'"):
                sh = sh[1:-1].replace("''", "'")
                if not re.fullmatch(r"\w+", sh):                       # gereksiz tırnak Excel'de bozuluyor: yalnız gerekirse
                    sh = "'" + sh.replace("'", "''") + "'"
            on = f"${sh}" if sh else ""
            return "[" + on + "." + a + ((":." + b) if b else "") + "]"
        p = _BASV.sub(baglan, p)
        return re.sub(r",(?![^\[]*\])", ";", p)
    govde = _disarida(f[1:] if f.startswith("=") else f, parca)
    return "of:=" + govde


def _tarih_say(ad: str) -> int:
    return len(ad)


def ac(yol) -> "tuple[CalismaKitabi, Rapor]":
    """`yol`daki .ods dosyasını yeni bir kitaba okur."""
    rapor = Rapor()
    try:
        with zipfile.ZipFile(yol) as z:
            adlar = set(z.namelist())
            if "content.xml" not in adlar:
                raise XlsxHatasi("Dosya geçerli bir .ods değil (content.xml yok).")
            if "mimetype" in adlar and z.read("mimetype").strip() != MIME.encode():
                raise XlsxHatasi("Dosya bir hesap tablosu değil (başka bir OpenDocument türü).")
            if any(a.startswith("Object ") or a.startswith("Pictures/") for a in adlar):
                rapor.ekle("Dosyadaki grafik ve resimler okunmaz; kaydederseniz dosyadan çıkar.", True)
            kok = ET.fromstring(z.read("content.xml"))
            stil_kok = ET.fromstring(z.read("styles.xml")) if "styles.xml" in adlar else None
            sifreli = "META-INF/manifest.xml" in adlar and b"encryption-data" in z.read("META-INF/manifest.xml")
    except zipfile.BadZipFile as e:
        raise XlsxHatasi("Dosya geçerli bir .ods değil (bozuk ya da farklı biçim).") from e
    except ET.ParseError as e:
        raise XlsxHatasi(f"Dosya okunamadı (bozuk XML): {e}") from e
    except OSError as e:
        raise XlsxHatasi(f"Dosya açılamadı: {e.strerror or e}") from e
    if sifreli:
        raise XlsxHatasi("Bu .ods dosyası parolayla korunuyor; şimdilik açılamıyor.")

    veri_stilleri = _veri_stilleri(kok, stil_kok)
    ozellikler = _stil_ozellikleri(stil_kok, kok)
    coz = _StilCozucu(ozellikler, veri_stilleri, "Default")
    tablolar = kok.findall(f"{_q('office', 'body')}/{_q('office', 'spreadsheet')}/{_q('table', 'table')}")
    if not tablolar:
        raise XlsxHatasi("Dosyada hesap tablosu sayfası bulunamadı.")
    kitap = CalismaKitabi()
    havuz = kitap.stil_havuzu
    sayfalar = []
    for i, t in enumerate(tablolar):
        ad = t.get(_q("table", "name")) or f"Sayfa{i + 1}"
        if i == 0:
            s = kitap.sayfalar[0]
            kitap.yeniden_adlandir(s, ad)
        else:
            s = kitap.sayfa_ekle(ad)
        sayfalar.append((t, s))

    stil_onb: Dict[str, int] = {}

    def kimlik(ad: Optional[str]) -> int:
        if not ad:
            return 0
        k = stil_onb.get(ad)
        if k is None:
            k = stil_onb[ad] = havuz.kimlik(coz.hucre_stili(ad))
        return k

    formul_onb = _FormulOnbellek()
    bozuk = 0
    notlu = kosullu = False
    var = {o.tag.split("}")[-1] for o in kok.iter()}                  # dosyada gerçekten bulunan, okunmayan öğeler
    for etiket, ileti in (("named-expressions", "Tanımlı adlar"), ("content-validations", "Veri doğrulama"),
                          ("conditional-formats", "Koşullu biçim"), ("conditional-format", "Koşullu biçim"),
                          ("database-ranges", "Filtre/veritabanı aralıkları"), ("frame", "Çizim nesneleri"),
                          ("shapes", "Çizim nesneleri")):
        if etiket in var:
            rapor.ekle(f"{ileti} okunmaz; kaydederseniz dosyadan çıkar.", True)
    for t, s in sayfalar:
        yeni, stiller = {}, {}
        sutun_ozel: Dict[int, Tuple[Optional[float], bool]] = {}
        c = 1
        for sc in t:
            et = sc.tag.split("}")[-1]
            if et in ("table-column", "table-header-columns", "table-column-group"):
                kolonlar = [sc] if et == "table-column" else list(sc.iter(_q("table", "table-column")))
                for col in kolonlar:
                    tekrar = int(col.get(_q("table", "number-columns-repeated"), "1"))
                    st = ozellikler.get(("table-column", col.get(_q("table", "style-name"), "")), {})
                    cs, c0 = st.get("oz", {}), None
                    gen = _piksel(cs.get(_q("style", "column-width")))
                    gizli = col.get(_q("table", "visibility")) in ("collapse", "filter")
                    for k in range(c, min(c + tekrar, MAX_COL + 1)):
                        if tekrar > 1024:
                            break
                        if gen is not None or gizli:
                            sutun_ozel[k] = (gen, gizli)
                    c += tekrar
        for k, (gen, gizli) in sutun_ozel.items():
            if gen is not None and abs(gen - Sayfa.VARSAYILAN_SUTUN_GENISLIGI) > 1:
                s.sutun_genislik[k] = olcu.genislik_sinirla(gen)
            if gizli:
                s.gizli_sutun.add(k)

        satirlar = []
        for sc in t:
            et = sc.tag.split("}")[-1]
            if et == "table-row":
                satirlar.append(sc)
            elif et in ("table-header-rows", "table-row-group", "table-rows"):
                satirlar.extend(sc.iter(_q("table", "table-row")))
        r = 1
        birlesimler: List[Aralik] = []
        for sat in satirlar:
            tekrar_r = int(sat.get(_q("table", "number-rows-repeated"), "1"))
            if r > MAX_ROW:
                break
            hucreler = [h for h in sat if h.tag in (_q("table", "table-cell"), _q("table", "covered-table-cell"))]
            satir_stili = ozellikler.get(("table-row", sat.get(_q("table", "style-name"), "")), {}).get("oz", {})
            yuk = _piksel(satir_stili.get(_q("style", "row-height")))
            gizli_r = sat.get(_q("table", "visibility")) in ("collapse", "filter")
            bos_satir = all(h.get(_q("table", "style-name")) is None and h.get(_q("office", "value-type")) is None
                            and h.get(_q("table", "formula")) is None and not _metin(h)
                            and h.get(_q("table", "number-columns-spanned")) is None
                            and h.get(_q("table", "number-rows-spanned")) is None for h in hucreler)
            if bos_satir and not gizli_r and yuk is None:
                r += tekrar_r
                continue
            for rr in range(r, min(r + min(tekrar_r, 1 if not bos_satir else _MAKS_TEKRAR), MAX_ROW + 1)):
                if yuk is not None and abs(yuk - Sayfa.VARSAYILAN_SATIR_YUKSEKLIGI) > 1:
                    s.satir_yukseklik[rr] = olcu.yukseklik_sinirla(yuk)
                if gizli_r:
                    s.gizli_satir.add(rr)
            c = 1
            for h in hucreler:
                tekrar_c = int(h.get(_q("table", "number-columns-repeated"), "1"))
                if c > MAX_COL:
                    break
                tur = h.get(_q("office", "value-type"))
                formul = h.get(_q("table", "formula"))
                sn = h.get(_q("table", "style-name"))
                kapsanan = h.tag == _q("table", "covered-table-cell")
                hucre = None
                if not kapsanan:
                    if formul:
                        try:
                            hucre = Hucre(None, formul_onb.cevir(formul_oku(formul), r, c, lambda m: _formul_oku(m, kitap)))
                        except (FormulHatasi, ValueError):
                            bozuk += 1
                            hucre = None
                    if hucre is None and tur in ("float", "percentage", "currency"):
                        try:
                            hucre = Hucre(float(h.get(_q("office", "value"))))
                        except (TypeError, ValueError):
                            hucre = None
                    elif hucre is None and tur == "date":
                        v = _tarih_seri(h.get(_q("office", "date-value")))
                        hucre = Hucre(v) if v is not None else None
                    elif hucre is None and tur == "time":
                        v = _sure_seri(h.get(_q("office", "time-value")))
                        hucre = Hucre(v) if v is not None else None
                    elif hucre is None and tur == "boolean":
                        hucre = Hucre(h.get(_q("office", "boolean-value")) == "true")
                    elif hucre is None and (tur == "string" or tur is None):
                        m = h.get(_q("office", "string-value"))
                        m = m if m is not None else _metin(h)
                        if m:
                            hucre = Hucre(hata_bul(m) or m) if re.fullmatch(r"#[A-Z0-9/!?]+", m) and hata_bul(m) else Hucre(m)
                    if h.find(f"{_q('office', 'annotation')}") is not None:
                        notlu = True
                k = kimlik(sn)
                tekrar_ok = tekrar_c if (hucre is None and not k) else min(tekrar_c, _MAKS_TEKRAR if hucre is None else tekrar_c)
                if hucre is not None or k:
                    for cc in range(c, min(c + tekrar_ok, MAX_COL + 1)):
                        if hucre is not None:
                            for rr in range(r, min(r + (tekrar_r if hucre is not None and tekrar_r <= _MAKS_TEKRAR else 1), MAX_ROW + 1)):
                                yeni[(rr, cc)] = hucre
                        if k:
                            for rr in range(r, min(r + min(tekrar_r, _MAKS_TEKRAR), MAX_ROW + 1)):
                                stiller[(rr, cc)] = k
                if not kapsanan:
                    bs = int(h.get(_q("table", "number-columns-spanned"), "1"))
                    rs = int(h.get(_q("table", "number-rows-spanned"), "1"))
                    if bs > 1 or rs > 1:
                        birlesimler.append(Aralik(r, c, min(r + rs - 1, MAX_ROW), min(c + bs - 1, MAX_COL)))
                c += tekrar_c
            r += tekrar_r
        s.toplu_yaz(yeni)
        s.bicim_yaz(stiller, {}, {})
        temiz = []
        for a in birlesimler:
            if any(not (a.son_satir < x.ilk_satir or a.ilk_satir > x.son_satir or a.son_sutun < x.ilk_sutun
                        or a.ilk_sutun > x.son_sutun) for x in temiz):
                continue
            temiz.append(a)
        s.birlesim_yukle(temiz)
    if notlu:
        rapor.ekle("Hücre notları (açıklamalar) okunmaz; kaydederseniz dosyadan çıkar.", True)
    if bozuk:
        rapor.ekle(f"{bozuk} formül çevrilemedi; hücreler boş bırakıldı.", True)
    return kitap, rapor


# ====================================================================== YAZMA
def _px_cm(px: float) -> str:
    return f"{px / 96 * 2.54:.4f}cm"


class _Stiller:
    """Hücre/sütun/satır/sayı stillerini toplayıp content.xml `automatic-styles` metnine çevirir."""

    def __init__(self):
        self.hucre: Dict[int, str] = {}                 # stil kimliği → ce<N>
        self.hucre_xml: List[str] = []
        self.sutun: Dict[float, str] = {}
        self.satir: Dict[float, str] = {}
        self.sayi: Dict[str, Optional[str]] = {}        # kod → veri stili adı (None: desteklenmiyor)
        self.sayi_xml: List[str] = []
        self.uyari_kod: set = set()

    def sutun_adi(self, px: float) -> str:
        if px not in self.sutun:
            self.sutun[px] = f"co{len(self.sutun) + 1}"
        return self.sutun[px]

    def satir_adi(self, px: float) -> str:
        if px not in self.satir:
            self.satir[px] = f"ro{len(self.satir) + 1}"
        return self.satir[px]

    def hucre_adi(self, kimlik: int, stil: Stil) -> str:
        ad = self.hucre.get(kimlik)
        if ad is None:
            ad = self.hucre[kimlik] = f"ce{len(self.hucre) + 1}"
            self.hucre_xml.append(self._hucre_xml(ad, stil))
        return ad

    # --- sayı biçimi
    def veri_stili(self, kod: str) -> Optional[str]:
        if kod == "General":
            return None
        if kod in self.sayi:
            return self.sayi[kod]
        ad = None
        xml = self._sayi_xml(f"N{len(self.sayi) + 1}", kod)
        if xml is not None:
            ad = f"N{len(self.sayi) + 1}"
            self.sayi_xml.append(xml)
        else:
            self.uyari_kod.add(kod)
        self.sayi[kod] = ad
        return ad

    @staticmethod
    def _sayi_xml(ad: str, kod: str) -> Optional[str]:
        a = f'style:name="{ad}"'
        if kod == "@":
            return f'<number:text-style {a}><number:text-content/></number:text-style>'
        m = re.fullmatch(r'(?:"([^"]*)")?(#,##)?0(?:\.(0+))?(%)?', kod)
        if m:
            sembol, binlik, ond, yuzde = m.groups()
            n = (f'<number:number number:decimal-places="{len(ond or "")}" number:min-integer-digits="1"'
                 + (' number:grouping="true"' if binlik else "") + "/>")
            if yuzde:
                return f'<number:percentage-style {a}>{n}<number:text>%</number:text></number:percentage-style>'
            if sembol:
                return (f'<number:currency-style {a}><number:currency-symbol>{escape(sembol)}</number:currency-symbol>'
                        f"{n}</number:currency-style>")
            return f"<number:number-style {a}>{n}</number:number-style>"
        # tarih / saat
        if not re.fullmatch(r"(?:d{1,4}|m{1,4}|y{2}|y{4}|h{1,2}|s{1,2}|AM/PM|[ .:/\-,])+", kod):
            return None
        jetonlar = re.findall(r"d{1,4}|m{1,4}|y{4}|y{2}|h{1,2}|s{1,2}|AM/PM|.", kod)
        ogeler, tarih, saat = [], False, False
        for i, j in enumerate(jetonlar):
            uzun = len(j) >= 2
            if j[0] == "d" and len(j) <= 2:
                ogeler.append(f'<number:day number:style="{"long" if uzun else "short"}"/>')
                tarih = True
            elif j[0] == "d":
                ogeler.append(f'<number:day-of-week number:style="{"long" if len(j) == 4 else "short"}"/>')
                tarih = True
            elif j[0] == "y":
                ogeler.append(f'<number:year number:style="{"long" if len(j) == 4 else "short"}"/>')
                tarih = True
            elif j[0] == "h":
                ogeler.append(f'<number:hours number:style="{"long" if uzun else "short"}"/>')
                saat = True
            elif j[0] == "s":
                ogeler.append(f'<number:seconds number:style="{"long" if uzun else "short"}"/>')
                saat = True
            elif j[0] == "m":
                once = "".join(jetonlar[:i]).replace(" ", "")
                sonra = "".join(jetonlar[i + 1:]).replace(" ", "")
                dakika = (once.endswith(("h", "hh", "h:", "hh:")) or once.rstrip(":").endswith(("h", "hh"))) or \
                         sonra.startswith(":s") or sonra.startswith(":ss") or sonra.startswith("s")
                if dakika:
                    ogeler.append(f'<number:minutes number:style="{"long" if uzun else "short"}"/>')
                    saat = True
                else:
                    ogeler.append(f'<number:month number:style="{"long" if uzun else "short"}"'
                                  + (' number:textual="true"' if len(j) >= 3 else "") + "/>")
                    tarih = True
            elif j == "AM/PM":
                ogeler.append("<number:am-pm/>")
            else:
                ogeler.append(f"<number:text>{escape(j)}</number:text>")
        etiket = "date-style" if tarih else "time-style"
        return f"<number:{etiket} {a}>{''.join(ogeler)}</number:{etiket}>"

    # --- hücre stili
    def _hucre_xml(self, ad: str, st: Stil) -> str:
        vs = self.veri_stili(st.sayi_bicimi)
        h, m, p = [], [], []
        if st.dolgu:
            h.append(f'fo:background-color="{st.dolgu.lower()}"')
        for yon, k in (("top", st.kenar.ust), ("bottom", st.kenar.alt), ("left", st.kenar.sol), ("right", st.kenar.sag)):
            if k:
                kalin = {"ince": "0.75pt", "orta": "1.5pt", "kalin": "2.25pt", "cift": "2.25pt solid"}.get(k[0], "0.75pt")
                h.append(f'fo:border-{yon}="{kalin if "solid" in kalin else kalin + " solid"} {k[1].lower()}"')
        if st.kaydir:
            h.append('fo:wrap-option="wrap"')
        h.append('style:vertical-align="%s"' % {"ust": "top", "orta": "middle", "alt": "bottom"}.get(st.dikey, "bottom"))
        if st.yazi_tipi:
            m.append(f'style:font-name={quoteattr(st.yazi_tipi)} fo:font-family={quoteattr(st.yazi_tipi)}')
        if st.boyut:
            m.append(f'fo:font-size="{st.boyut:g}pt"')
        if st.kalin:
            m.append('fo:font-weight="bold"')
        if st.italik:
            m.append('fo:font-style="italic"')
        if st.ustu_cizili:
            m.append('style:text-line-through-style="solid"')
        if st.alti_cizili != "yok":
            m.append('style:text-underline-style="solid" style:text-underline-width="auto" '
                     'style:text-underline-color="font-color"')
        if st.yazi_rengi:
            m.append(f'fo:color="{st.yazi_rengi.lower()}"')
        hiza = {"sol": "start", "sag": "end", "orta": "center", "iki_yana": "justify"}.get(st.yatay)
        if hiza:
            p.append(f'fo:text-align="{hiza}"')
        if st.girinti:
            p.append(f'fo:margin-left="{_px_cm(st.girinti * 9)}"')
        govde = (f"<style:table-cell-properties {' '.join(h)}/>" if h else "")
        govde += (f"<style:paragraph-properties {' '.join(p)}/>" if p else "")
        govde += (f"<style:text-properties {' '.join(m)}/>" if m else "")
        veri = f' style:data-style-name="{vs}"' if vs else ""
        return f'<style:style style:name="{ad}" style:family="table-cell" style:parent-style-name="Default"{veri}>{govde}</style:style>'

    def xml(self) -> str:
        parcalar = list(self.sayi_xml)
        for px, ad in self.sutun.items():
            parcalar.append(f'<style:style style:name="{ad}" style:family="table-column"><style:table-column-properties '
                            f'style:column-width="{_px_cm(px)}" fo:break-before="auto"/></style:style>')
        for px, ad in self.satir.items():
            parcalar.append(f'<style:style style:name="{ad}" style:family="table-row"><style:table-row-properties '
                            f'style:row-height="{_px_cm(px)}" style:use-optimal-row-height="false"/></style:style>')
        parcalar += self.hucre_xml
        return "".join(parcalar)


def _deger_oznitelik(v) -> Tuple[str, str]:
    """(öznitelikler, text:p içeriği) — `v` hücre değeri ya da formülün hesaplanmış sonucu."""
    if v is None:
        return "", ""
    if isinstance(v, bool):
        return (f' office:value-type="boolean" office:boolean-value="{"true" if v else "false"}"',
                f"<text:p>{'DOĞRU' if v else 'YANLIŞ'}</text:p>")
    if isinstance(v, (int, float)):
        return f' office:value-type="float" office:value="{float(v)!r}"', f"<text:p>{v:g}</text:p>"
    if isinstance(v, Hata):
        return f' office:value-type="string" office:string-value={quoteattr(v.kod)}', f"<text:p>{escape(v.kod)}</text:p>"
    m = str(v)
    return f' office:value-type="string" office:string-value={quoteattr(m)}', f"<text:p>{escape(m)}</text:p>"


def _hucre_xml(h: Hucre, kitap, r: int, c: int, onb, stil_adi: Optional[str], sonuc=None) -> str:
    st = f' table:style-name="{stil_adi}"' if stil_adi else ""
    if h.formul is not None:
        try:
            f = onb.cevir(h.formul, r, c, lambda m: formul_yaz(_formul_yaz(m, kitap)))
        except FormulHatasi:
            f = None
        if f:
            oz, p = _deger_oznitelik(sonuc)                         # Excel önbellek değeri olmadan formül hücresini boş gösterir
            return f"<table:table-cell{st} table:formula={quoteattr(f)}{oz}>{p}</table:table-cell>" if p else                 f"<table:table-cell{st} table:formula={quoteattr(f)}/>"
        return f"<table:table-cell{st}/>"
    v = h.deger
    if v is None:
        return f"<table:table-cell{st}/>"
    if isinstance(v, bool):
        s = "true" if v else "false"
        return (f'<table:table-cell{st} office:value-type="boolean" office:boolean-value="{s}">'
                f"<text:p>{'DOĞRU' if v else 'YANLIŞ'}</text:p></table:table-cell>")
    if isinstance(v, (int, float)):
        return (f'<table:table-cell{st} office:value-type="float" office:value="{float(v)!r}">'
                f"<text:p>{v:g}</text:p></table:table-cell>")
    if isinstance(v, Hata):
        return (f'<table:table-cell{st} office:value-type="string" office:string-value={quoteattr(v.kod)}>'
                f"<text:p>{escape(v.kod)}</text:p></table:table-cell>")
    metin = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(v))
    govde = []
    for satir in metin.split("\n"):
        t = escape(satir)
        t = re.sub(r"(  +)", lambda m: f'<text:s text:c="{len(m.group(1))}"/>', t) if "  " in t else t
        t = t.replace("\t", "<text:tab/>")
        govde.append(f"<text:p>{t}</text:p>")
    return f'<table:table-cell{st} office:value-type="string">{"".join(govde)}</table:table-cell>'


def _icerik(kitap: CalismaKitabi, rapor: Rapor) -> str:
    havuz = kitap.stil_havuzu
    stiller = _Stiller()
    onb = _FormulOnbellek()
    sayfa_xml = []
    tasan_sayisi = 0
    for sayfa in kitap.sayfalar:
        hucreler = sayfa._hucreler
        stil_haritasi = {k: v for k, v in sayfa._stil.items() if v}
        gizli_sut = sayfa.gizli_sutun
        son_s = max([r for r, _ in hucreler] + [r for r, _ in stil_haritasi] + list(sayfa.satir_yukseklik)
                    + list(sayfa.gizli_satir) + [b.son_satir for b in sayfa.birlesimler] + [1])
        son_c = max([c for _, c in hucreler] + [c for _, c in stil_haritasi] + list(sayfa.sutun_genislik)
                    + list(gizli_sut) + [b.son_sutun for b in sayfa.birlesimler] + [1])
        birlesim_basi = {(b.ilk_satir, b.ilk_sutun): b for b in sayfa.birlesimler}
        kapsanan = set()
        for b in sayfa.birlesimler:
            for rr in range(b.ilk_satir, b.son_satir + 1):
                for cc in range(b.ilk_sutun, b.son_sutun + 1):
                    if (rr, cc) != (b.ilk_satir, b.ilk_sutun):
                        kapsanan.add((rr, cc))
        sutunlar = []
        for c in range(1, son_c + 1):
            px = sayfa.sutun_genislik.get(c, Sayfa.VARSAYILAN_SUTUN_GENISLIGI)
            sutunlar.append((stiller.sutun_adi(px), c in gizli_sut))
        sx = []
        i = 0
        while i < len(sutunlar):
            j = i
            while j + 1 < len(sutunlar) and sutunlar[j + 1] == sutunlar[i]:
                j += 1
            ad, gz = sutunlar[i]
            sx.append(f'<table:table-column table:style-name="{ad}"' + (f' table:number-columns-repeated="{j - i + 1}"' if j > i else "")
                      + (' table:visibility="collapse"' if gz else "") + "/>")
            i = j + 1
        satirlar_xml = []
        bos_say = 0

        def bos_bayrakla():
            nonlocal bos_say
            if bos_say:
                satirlar_xml.append(f'<table:table-row table:number-rows-repeated="{bos_say}"><table:table-cell table:number-columns-repeated="{son_c}"/></table:table-row>'
                                    if bos_say > 1 else f'<table:table-row><table:table-cell table:number-columns-repeated="{son_c}"/></table:table-row>')
                bos_say = 0
        satir_dolu = {r for r, _ in hucreler} | {r for r, _ in stil_haritasi}
        ozel_satir = set(sayfa.satir_yukseklik) | sayfa.gizli_satir | {b.ilk_satir for b in sayfa.birlesimler}
        for r in range(1, son_s + 1):
            if r not in satir_dolu and r not in ozel_satir and not any(b.ilk_satir < r <= b.son_satir for b in sayfa.birlesimler):
                bos_say += 1
                continue
            bos_bayrakla()
            hx = []
            bos_c = 0
            for c in range(1, son_c + 1):
                if (r, c) in kapsanan:
                    if bos_c:
                        hx.append(f'<table:table-cell table:number-columns-repeated="{bos_c}"/>' if bos_c > 1 else "<table:table-cell/>")
                        bos_c = 0
                    hx.append("<table:covered-table-cell/>")
                    continue
                h = hucreler.get((r, c))
                if h is not None and h.formul is not None and (r, c) in sayfa.tasma:   # taşan formül: değer olarak (aksi halde
                    h = Hucre(sayfa.deger(r, c))                                         # yeniden açınca taşma alanı engellenir)
                    tasan_sayisi += 1
                k = stil_haritasi.get((r, c), 0)
                if h is None and not k and (r, c) not in birlesim_basi:
                    bos_c += 1
                    continue
                if bos_c:
                    hx.append(f'<table:cell-placeholder/>')
                    hx[-1] = f'<table:table-cell table:number-columns-repeated="{bos_c}"/>' if bos_c > 1 else "<table:table-cell/>"
                    bos_c = 0
                sn = stiller.hucre_adi(k, havuz.stil(k)) if k else None
                xml = _hucre_xml(h, kitap, r, c, onb, sn, sayfa.deger(r, c) if h.formul is not None else None) if h is not None else (
                    f'<table:table-cell table:style-name="{sn}"/>' if sn else "<table:table-cell/>")
                b = birlesim_basi.get((r, c))
                if b is not None:
                    ek = f' table:number-columns-spanned="{b.son_sutun - b.ilk_sutun + 1}" table:number-rows-spanned="{b.son_satir - b.ilk_satir + 1}"'
                    xml = xml.replace("<table:table-cell", "<table:table-cell" + ek, 1)
                hx.append(xml)
            if bos_c:
                hx.append(f'<table:table-cell table:number-columns-repeated="{bos_c}"/>' if bos_c > 1 else "<table:table-cell/>")
            if not hx:                                              # hücresiz satır (yalnız gizli/yükseklik): Excel yok sayar
                hx.append(f'<table:table-cell table:number-columns-repeated="{son_c}"/>' if son_c > 1 else "<table:table-cell/>")
            ek = ""
            if r in sayfa.satir_yukseklik or r in sayfa.gizli_satir:       # Excel gizli satırı yalnız stilli satırda tanır
                ek += f' table:style-name="{stiller.satir_adi(sayfa.satir_yukseklik.get(r, Sayfa.VARSAYILAN_SATIR_YUKSEKLIGI))}"'
            if r in sayfa.gizli_satir:
                ek += ' table:visibility="collapse"'
            satirlar_xml.append(f"<table:table-row{ek}>{''.join(hx)}</table:table-row>")
        bos_say = 0                                                # sondaki boş satırlar yazılmaz
        sayfa_xml.append(f'<table:table table:name={quoteattr(sayfa.ad)}>{"".join(sx)}{"".join(satirlar_xml)}</table:table>')
    if tasan_sayisi:
        rapor.ekle(f"{tasan_sayisi} dinamik dizi formülü .ods dosyasına değer olarak yazıldı (formül kaybolur).", True)
    for kod in sorted(stiller.uyari_kod):
        rapor.ekle(f"“{kod}” sayı biçimi .ods'ye taşınamadı (Genel olarak yazıldı).")
    ns = " ".join(f'xmlns:{k}="{v}"' for k, v in NS.items())
    return (f'<?xml version="1.0" encoding="UTF-8"?><office:document-content {ns} office:version="1.2">'
            f"<office:automatic-styles>{stiller.xml()}</office:automatic-styles>"
            f'<office:body><office:spreadsheet>{"".join(sayfa_xml)}</office:spreadsheet></office:body></office:document-content>')


def _stiller_xml() -> str:
    ns = " ".join(f'xmlns:{k}="{v}"' for k, v in NS.items())
    return (f'<?xml version="1.0" encoding="UTF-8"?><office:document-styles {ns} office:version="1.2">'
            '<office:styles><style:default-style style:family="table-cell"/>'
            '<style:style style:name="Default" style:family="table-cell"/></office:styles></office:document-styles>')


_MANIFEST = ('<?xml version="1.0" encoding="UTF-8"?><manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" '
             'manifest:version="1.2"><manifest:file-entry manifest:full-path="/" manifest:version="1.2" '
             f'manifest:media-type="{MIME}"/><manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>'
             '<manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/></manifest:manifest>')


def kaydet(kitap: CalismaKitabi, yol: str) -> Rapor:
    """Kitabı `yol`a .ods olarak yazar (geçici dosya → yerine koy). Rapor yazılamayanları söyler."""
    rapor = Rapor()
    icerik = _icerik(kitap, rapor)
    nesne = sum(len(s.nesneler) for s in kitap.sayfalar)
    if nesne:
        rapor.ekle(f"{nesne} grafik/resim .ods dosyasına yazılmaz.", True)
    if any(s.kosullu or s.dogrulamalar or s.notlar or s.filtre for s in kitap.sayfalar) or kitap.adlar:
        rapor.ekle("Koşullu biçim, veri doğrulama, notlar, filtre ve tanımlı adlar .ods dosyasına yazılmaz.", True)
    gecici = f"{yol}.{os.getpid()}.tmp"
    try:
        with zipfile.ZipFile(gecici, "w") as z:
            z.writestr(zipfile.ZipInfo("mimetype"), MIME, compress_type=zipfile.ZIP_STORED)
            z.writestr("META-INF/manifest.xml", _MANIFEST, compress_type=zipfile.ZIP_DEFLATED)
            z.writestr("content.xml", icerik, compress_type=zipfile.ZIP_DEFLATED)
            z.writestr("styles.xml", _stiller_xml(), compress_type=zipfile.ZIP_DEFLATED)
        os.replace(gecici, yol)
    except PermissionError as e:
        raise XlsxHatasi("Dosya başka bir uygulamada açık olabilir; kapatıp yeniden deneyin.") from e
    except OSError as e:
        raise XlsxHatasi(f"Dosya kaydedilemedi: {e.strerror or e}") from e
    finally:
        if os.path.exists(gecici):
            try:
                os.remove(gecici)
            except OSError:
                pass
    return rapor
