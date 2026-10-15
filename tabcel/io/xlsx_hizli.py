"""Hızlı sayfa hücre okuyucu (2026-10-15): openpyxl'in `WorksheetReader.bind_cells` adımının yerine geçen, aynı sonucu (aynı `Cell` nesneleri,
aynı `ws._cells`) çok daha ucuza üreten yama. Nedeni: 800.000 hücreli dosya ≈ 47 sn'de açılıyordu; zamanın ~%75'i openpyxl'in hücre başına
XML olay döngüsü + sözlük + `Cell` + `StyleArray` kopyası + tarih dönüşümü işindeydi.

Nasıl çalışır:
1. Sayfa XML'i belleğe alınır; `<sheetData>…</sheetData>` bölümü ayrılır. Geri kalan (`sheetPr`, `cols`, `mergeCells`, `conditionalFormatting`…)
   özgün `WorkSheetParser.parse` ile okunur (satır yok → hızlı).
2. `sheetData` doğrudan `expat` ile okunur; `<c>` öğeleri tek geçişte `Cell` nesnesine çevrilir (`Cell.__new__`, kitap düzeyinde paylaşılan `StyleArray`).
3. Tarih biçimli sayılar `datetime`a çevrilmez (Tabcel zaten seri sayıya geri çeviriyordu): sayı olarak kalır.
4. **Formüllü hücreler** (paylaşılan/dizi/veri tablosu çevirisi) ve **süre biçimli hücreler**, özgün `parse_cell`'e küçük bir sahte `<c>` öğesiyle verilir →
   anlam aynı. **1904 tarih sistemi, zengin metin istenen okuma, önekli ad alanı ya da `<sheetData>` bulunamayan** dosyalarda özgün okuyucu çalışır.
Ortam değişkeni `TABCEL_YAVAS_OKUYUCU=1` yamayı kapatır. Yama `kur()` ile bir kez uygulanır; başarısızsa özgün okuyucu çalışır.
`Cell` sınıfı, `ws._cells`, `ws.max_row`, köprü/yorum bağlama, satır/sütun boyutları özgün kalır.
"""
import io
import os
import re
import threading
from contextlib import contextmanager
import xml.etree.ElementTree as ET
from xml.parsers import expat

from openpyxl.cell.cell import Cell
from openpyxl.utils.cell import column_index_from_string, coordinate_to_tuple
from openpyxl.worksheet._reader import WorkSheetParser, WorksheetReader, _cast_number
from openpyxl.xml.constants import SHEET_MAIN_NS

from ..model.deger import Hata, hata_bul                       # noqa: E402
from ..model.sayfa import Hucre                                 # noqa: E402

_YAMALI = False
_YEREL = threading.local()               # `demet_izni`: yalnız `xlsx_io.ac` içinde açılır (başka `load_workbook` çağrıları Cell nesnesi alır)
_SUTUN: dict = {}                    # sütun harfi → numara önbelleği
_NS = SHEET_MAIN_NS
_ROW, _C, _V, _F, _IS, _T, _RPH = (f"{_NS}}}{x}" for x in ("row", "c", "v", "f", "is", "t", "rPh"))
_ozgun_bind_cells = WorksheetReader.bind_cells
_ozgun_parse_cell = WorkSheetParser.parse_cell


class _HizliAyristirici:
    """`sheetData` baytlarını expat ile okuyup `ws._cells`'e `Cell` yazar."""

    def __init__(self, okuyucu: WorksheetReader):
        self.ws = okuyucu.ws
        self.p = okuyucu.parser
        self.stiller = self.ws.parent._cell_styles
        self.tarih = self.p.date_formats          # kullanılmaz (tarihler sayı kalır) ama özgün yola gidenler için p üzerinden çalışır
        self.sure = self.p.timedelta_formats
        self.paylasilan = self.p.shared_strings
        self.hucreler = self.ws._cells
        self.yeni = Cell.__new__
        # bağlam
        self._c = None
        self._metin = None
        self._f = None
        self._derin_is = 0
        self._derin_rph = 0
        self._t_icinde = False
        self._t_tampon = None
        self._v = None
        self._is = None

    # --- expat geri çağrıları
    def basla(self, ad, nitelik):
        if ad == _C:
            self._c = nitelik
            self._v = None
            self._f = None
            self._is = None
            self._metin = None
        elif ad == _V:
            self._metin = []
        elif ad == _T:
            if self._derin_is and not self._derin_rph:
                self._t_icinde = True
                self._t_tampon = self._metin = []
        elif ad == _IS:
            self._derin_is += 1
            self._is = []
        elif ad == _RPH:
            self._derin_rph += 1
        elif ad == _F:
            self._f = [nitelik, []]
            self._metin = self._f[1]
        elif ad == _ROW:
            self._satir(nitelik)

    def bitir(self, ad):
        if ad == _C:
            self._hucre_bitti()
            self._c = None
        elif ad == _V:
            self._v = ("".join(self._metin) or None) if self._metin is not None else None
            self._metin = None
        elif ad == _T:
            if self._t_icinde:
                self._t_icinde = False
                self._is.append("".join(self._t_tampon))
                self._metin = None
        elif ad == _IS:
            self._derin_is -= 1
        elif ad == _RPH:
            self._derin_rph -= 1
        elif ad == _F:
            self._metin = None

    def veri(self, metin):
        if self._metin is not None:
            self._metin.append(metin)

    # --- satır / hücre
    def _satir(self, attrs):
        p = self.p
        attrs = dict(attrs)
        if "r" in attrs:
            try:
                p.row_counter = int(attrs["r"])
            except ValueError:
                val = float(attrs["r"])
                if val.is_integer():
                    p.row_counter = int(val)
                else:
                    raise ValueError(f"{attrs['r']} is not a valid row number")
        else:
            p.row_counter += 1
        p.col_counter = 0
        if {k for k in attrs if not k.startswith("{")} - {"r", "spans"}:
            p.row_dimensions[str(p.row_counter)] = attrs

    def _hucre_bitti(self):
        a = self._c
        p = self.p
        t = a.get("t", "n")
        stil = a.get("s")
        stil = int(stil) if stil else 0
        r_ad = a.get("r")
        if r_ad:
            harf = r_ad.rstrip("0123456789")                      # "AB12" → "AB" (coordinate_to_tuple'dan ~3x hızlı)
            sutun = _SUTUN.get(harf)
            if sutun is None:
                satir, sutun = coordinate_to_tuple(r_ad)
                _SUTUN[harf] = sutun
            else:
                satir = int(r_ad[len(harf):])
            p.col_counter = sutun
        else:
            p.col_counter += 1
            satir, sutun = p.row_counter, p.col_counter
        f = self._f
        if (f is not None and not p.data_only) or stil in self.sure or t == "d":
            deger, tur, stil = self._ozgun(a, t, stil, f)           # formül / süre / ISO tarih: özgün çözümleme
        elif t == "inlineStr":
            deger, tur = ("".join(self._is) if self._is else None), "s"
        else:
            v = self._v
            if v is None or v == "":
                deger, tur = None, t
            elif t == "n":
                deger, tur = _cast_number(v), "n"                   # tarih biçimli sayı da sayı kalır
            elif t == "s":
                deger, tur = self.paylasilan[int(v)], "s"
            elif t == "b":
                deger, tur = bool(int(v)), "b"
            elif t == "str":
                deger, tur = v, "s"
            else:                                                   # "e" (hata) ve bilinmeyenler: değer olduğu gibi
                deger, tur = v, t
        c = self.yeni(Cell)
        c.parent = self.ws
        c.row = satir
        c.column = sutun
        c._style = self.stiller[stil]
        c._value = deger
        c.data_type = tur
        c._hyperlink = None
        c._comment = None
        self.hucreler[(satir, sutun)] = c

    def _ozgun(self, a, t, stil, f):
        """Küçük sahte `<c>` öğesi kurup özgün `parse_cell`'e verir (anlam birebir aynı kalır)."""
        el = ET.Element("c", {k: a[k] for k in ("r", "t", "s") if k in a})
        if self._v is not None:
            ET.SubElement(el, f"{{{_NS}}}v").text = self._v
        if f is not None:
            fe = ET.SubElement(el, f"{{{_NS}}}f", dict(f[0]))
            fe.text = "".join(f[1]) or None
        d = _ozgun_parse_cell(self.p, el)
        return d["value"], d["data_type"], d["style_id"]


# --- düzenli dosyalar için regex yolu: Excel/openpyxl/Tabcel çıktısı `<c r="A1" s="2" t="s"><v>5</v></c>` biçimindedir; C düzeyinde `re` ile
# hücre başına birkaç mikrosaniyeye iner. Beklenmedik her biçim (formül, zengin metin, öznitelik sırası, `&` varlıkları…) küçük bir XML
# parçasıyla özgün `parse_cell`'e verilir; sayımlar tutmazsa tüm sayfa expat yoluna düşer.
_TIP = {None: "n", b"n": "n", b"s": "s", b"inlineStr": "inlineStr", b"b": "b", b"str": "str", b"e": "e"}
_TOKEN = re.compile(
    rb'<row r="(\d+)"(?: spans="[\d:]+")?>'                                                  # 1: yalnız r/spans'lı satır
    rb'|<c r="([A-Z]+)(\d+)"(?: s="(\d+)")?(?: t="(\w+)")?\s?'                                # 2-5: sade hücre başı (r, s, t sırasıyla)
    rb'(?:/>|>(?:<v>([^<&]*)</v>|<is><t(?: xml:space="preserve")?>([^<&]*)</t></is>)?</c>)'   # 6: değer, 7: satır içi metin
    rb'|<row([^>]*?)/?>'                                                                    # 8: diğer satır öznitelikleri
    rb'|<c([^>]*?)(?:/>|>(.*?)</c>)', re.S)                                                 # 9, 10: beklenmeyen hücre → özgün parse_cell


def _regex_yukle(self, govde: bytes) -> bool:
    """`sheetData` gövdesini regex ile okuyup `ws._cells`'e yazar. Başarısızsa (sayım tutmaz/beklenmeyen biçim) False; çağıran hücreleri temizler."""
    if b"<![CDATA[" in govde or b"<!--" in govde:
        return False
    p = self.parser
    ws = self.ws
    stiller = ws.parent._cell_styles
    sure = p.timedelta_formats
    paylasilan = p.shared_strings
    hucreler = ws._cells
    yeni = Cell.__new__
    ns = _NS.encode()
    sutun_onb = _SUTUN
    islenen = satir_sayisi = 0
    ozgun = _ozgun_parse_cell
    # Köprü varsa (özgün `bind_hyperlinks` boş hücreye başvuru metnini yazar) ya da kapalıysa Cell nesneleri üretilir; aksi hâlde basit hücreler
    # `(satır, sütun, değer, tür, stil)` demeti olarak `ws._hizli_hucreler`e konur (Cell oluşturma maliyeti yok; `xlsx_io.ac` doğrudan okur).
    demet_modu = (getattr(_YEREL, "izin", False) and not (p.hyperlinks and p.hyperlinks.hyperlink) and ws.title != "_tabcel"          # `_tabcel` sayfası `iter_rows` ile okunur → Cell
                  and os.environ.get("TABCEL_HUCRE_NESNESI") != "1")
    yeni_hucre: dict = {}                                     # (satır, sütun) → Hucre (Tabcel modeli; basit hücreler)
    stil_idx: dict = {}                                       # (satır, sütun) → dosyadaki stil numarası (0 olmayanlar)
    en_son = 0

    stil_onb: dict = {}
    son_satir_b, son_satir_i = b"", 0
    tip_tablosu = _TIP
    for m in _TOKEN.finditer(govde):
        g = m.groups()
        harf = g[1]
        if harf is not None:                                       # sade hücre: r, s, t, <v> ya da <is><t>
            islenen += 1
            sutun = sutun_onb.get(harf)
            if sutun is None:
                sutun = sutun_onb[harf] = column_index_from_string(harf.decode())
            satir_b = g[2]
            if satir_b == son_satir_b:
                satir = son_satir_i
            else:
                satir = son_satir_i = int(satir_b)
                son_satir_b = satir_b
            sb = g[3]
            stil = stil_onb.get(sb)
            if stil is None:
                stil = stil_onb[sb] = int(sb) if sb else 0
            t = g[4]
            p.col_counter = sutun
            tip = tip_tablosu.get(t)
            if (sure and stil in sure) or t == b"d":
                ozel = True
            else:
                ozel = False
                if tip is None:
                    tip = t.decode()
                v = g[5]
                if v is None:
                    v = g[6]
                    if v is not None and tip != "inlineStr":
                        ozel = True                                # <is> yalnız inlineStr'de beklenir
                if not ozel:
                    if not v:
                        deger, tur = None, ("s" if tip == "inlineStr" else tip)
                    elif tip == "n":
                        deger, tur = (float(v) if (b"." in v or b"E" in v or b"e" in v) else int(v)), "n"
                    elif tip == "s":
                        deger, tur = paylasilan[int(v)], "s"
                    elif tip == "inlineStr" or tip == "str":
                        deger, tur = v.decode("utf-8"), "s"
                    elif tip == "b":
                        deger, tur = bool(int(v)), "b"
                    else:                                          # "e" hata ve bilinmeyenler
                        deger, tur = v.decode("utf-8"), tip
        elif g[0] is not None:                                     # sade satır
            satir_sayisi += 1
            p.row_counter = int(g[0])
            p.col_counter = 0
            continue
        elif g[7] is not None:                                     # satır yüksekliği/gizli/stil…: ayrıntılı çözümle
            satir_sayisi += 1
            try:
                et = ET.fromstring(b"<row" + g[7] + b"/>")
            except ET.ParseError:
                return False
            _satir_oznitelik(self, dict(et.attrib))
            continue
        else:                                                      # beklenmeyen hücre (formül, öznitelik sırası, `&`…)
            islenen += 1
            ozel = True
        if ozel:
            try:
                el = ET.fromstring(m.group(0).replace(b"<c", b'<c xmlns="' + ns + b'"', 1))
                d = ozgun(p, el)
            except (ET.ParseError, KeyError, ValueError, IndexError):
                return False
            satir, sutun, deger, tur, stil = d["row"], d["column"], d["value"], d["data_type"], d["style_id"]
        elif demet_modu:
            if deger is not None:
                if tur == "n":
                    hc = Hucre(float(deger))
                elif tur == "s":
                    hc = Hucre(deger)
                elif tur == "b":
                    hc = Hucre(bool(deger))
                elif tur == "e":
                    hc = Hucre(hata_bul(str(deger)) or Hata(str(deger)))
                else:
                    hc = Hucre(deger) if isinstance(deger, (str, bool)) else Hucre(float(deger))
                yeni_hucre[(satir, sutun)] = hc
            if stil:
                stil_idx[(satir, sutun)] = stil
            if satir > en_son:
                en_son = satir
            continue
        c = yeni(Cell)
        c.parent = ws
        c.row = satir
        c.column = sutun
        c._style = stiller[stil]
        c._value = deger
        c.data_type = tur
        c._hyperlink = None
        c._comment = None
        hucreler[(satir, sutun)] = c
    beklenen = govde.count(b"<c ") + govde.count(b"<c>") + govde.count(b"<c/>")
    if not (islenen == beklenen and satir_sayisi == govde.count(b"<row")):
        return False
    if demet_modu:
        ws._hizli_yeni = yeni_hucre
        ws._hizli_stil = stil_idx
        ws._hizli_en_son_satir = en_son
    return True


def _satir_oznitelik(self, attrs: dict) -> None:
    """Satır öznitelikleri (`r`, yükseklik, gizli, stil…): özgün `parse_row` mantığı."""
    p = self.parser
    if "r" in attrs:
        try:
            p.row_counter = int(attrs["r"])
        except ValueError:
            val = float(attrs["r"])
            if val.is_integer():
                p.row_counter = int(val)
            else:
                raise ValueError(f"{attrs['r']} is not a valid row number")
    else:
        p.row_counter += 1
    p.col_counter = 0
    if {k for k in attrs if not k.startswith("{")} - {"r", "spans"}:
        p.row_dimensions[str(p.row_counter)] = attrs


def _hizli_bind_cells(self):
    """`WorksheetReader.bind_cells`'in yerine. Uygun değilse özgün yola düşer."""
    p = self.parser
    if p.epoch.year == 1904 or p.rich_text:
        return _ozgun_bind_cells(self)
    try:
        veri = p.source.read()
    except Exception:                                              # noqa: BLE001
        return _ozgun_bind_cells(self)
    bas = veri.find(b"<sheetData")
    if bas < 0:
        p.source = io.BytesIO(veri)
        return _ozgun_bind_cells(self)
    kapanis = veri.find(b"</sheetData>", bas)
    if kapanis < 0:                                                # <sheetData/> (boş) ya da bozuk
        bitis = veri.find(b"/>", bas)
        govde = b""
        geri = veri[:bas] + veri[bitis + 2:] if bitis >= 0 else veri
    else:
        ic_bas = veri.find(b">", bas) + 1
        govde = veri[ic_bas:kapanis]
        geri = veri[:bas] + veri[kapanis + len(b"</sheetData>"):]
    # satırsız geri kalan: özgün ayrıştırıcıyla (sütunlar, birleşimler, koşullu biçim, doğrulama, görünüm…)
    p.source = io.BytesIO(geri)
    for _ in p.parse():
        pass
    if govde and _regex_yukle(self, govde):
        govde = b""                                               # regex yolu tamam
    elif govde:
        self.ws._cells.clear()                                    # regex yolu yarım kaldıysa temizle, expat yolu
        a = _HizliAyristirici(self)
        ay = expat.ParserCreate(namespace_separator="}")
        ay.StartElementHandler = a.basla
        ay.EndElementHandler = a.bitir
        ay.CharacterDataHandler = a.veri
        ay.buffer_text = True
        try:
            ay.Parse(b"<sheetData xmlns=\"" + _NS.encode() + b"\">" + govde + b"</sheetData>", True)
        except expat.ExpatError:
            # bozuk XML: özgün okuyucuyla yeniden dene (hata mesajı özgün davranışla aynı olsun)
            self.ws._cells.clear()
            p.source = io.BytesIO(veri)
            return _ozgun_bind_cells(self)
    ws = self.ws
    if ws._cells or getattr(ws, "_hizli_yeni", None):
        ws._current_row = max(ws.max_row if ws._cells else 0, getattr(ws, "_hizli_en_son_satir", 0))


@contextmanager
def demet_izni():
    """Bu bağlamda (iş parçacığında) `load_workbook` basit hücreleri `Cell` yerine demet olarak bırakabilir: yalnız demetleri doğrudan okuyan
    `xlsx_io.ac` için. Dışarıdaki `load_workbook` çağrıları (testler, başka modüller) özgün anlamı görür."""
    onceki = getattr(_YEREL, "izin", False)
    _YEREL.izin = True
    try:
        yield
    finally:
        _YEREL.izin = onceki


def kur() -> bool:
    """Yamayı uygular (bir kez). `TABCEL_YAVAS_OKUYUCU=1` ise uygulamaz. Döner: uygulandı mı."""
    global _YAMALI
    if _YAMALI or os.environ.get("TABCEL_YAVAS_OKUYUCU") == "1":
        return _YAMALI
    try:
        WorksheetReader.bind_cells = _hizli_bind_cells
        _YAMALI = True
    except Exception:                                              # noqa: BLE001 — başarısızsa özgün okuyucu çalışır
        WorksheetReader.bind_cells = _ozgun_bind_cells
        _YAMALI = False
    return _YAMALI


def kapat() -> None:
    """Yamayı geri alır (testler/karşılaştırma)."""
    global _YAMALI
    WorksheetReader.bind_cells = _ozgun_bind_cells
    _YAMALI = False


def yamali_mi() -> bool:
    return _YAMALI
