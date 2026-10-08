"""Izgara: QAbstractScrollArea + QPainter (QTableView değil — bkz. plan.md).

Bu aşamada: çizim, kaydırma, seçim, gezinme. Düzenleme sonraki adımda.
Kaydırma çubukları hücre sırasıyla çalışır (değer = ilk görünen satır/sütun − 1), Excel gibi.
"""
import uuid
from typing import Dict, Iterator, List, Optional, Tuple

from PySide6.QtCore import QEvent, QMimeData, QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen, QStaticText
from PySide6.QtWidgets import QAbstractScrollArea, QApplication, QInputDialog, QLineEdit, QMenu

from ..model.adres import (
    MAX_COL, MAX_ROW, AdresHatasi, Aralik, aralik_icinde, hucre_yaz, sutun_harfe,
)
from ..model.girdi import duzenleme_metni, girdi_coz
from ..model.deger import Hata
from ..model.gosterim import goster, sayiyi_sigdir  # noqa: F401  (testler grid.goster'i de kullanır)
from ..model.komutlar import (
    GeriAlYigini, Grup, HucrelerDegis, OlcuDegis, SatirEkleSil, SutunEkleSil,
)
from ..model import olcu, pano
from ..model.sayfa import Sayfa
from . import theme


class _Duzenleyici(QLineEdit):
    """Hücre üstünde satır içi düzenleme kutusu.

    `yazma_modu` (doğrudan yazarak başlandı): oklar onaylayıp hücre değiştirir.
    F2/çift tık modunda oklar kutu içinde imleci gezdirir (Excel'in Düzenle modu).
    """
    bitir = Signal(bool, int, int)   # onayla, satır farkı, sütun farkı

    def __init__(self, parent, yazma_modu: bool):
        super().__init__(parent)
        self.yazma_modu = yazma_modu
        self._bitti = False
        self.setFrame(False)

    def _son(self, onayla: bool, dr: int = 0, dc: int = 0):
        if not self._bitti:
            self._bitti = True
            self.bitir.emit(onayla, dr, dc)

    def event(self, olay):
        # Tab/Shift+Tab Qt'de odak gezintisi olarak keyPressEvent'ten önce yakalanır
        if olay.type() == QEvent.KeyPress and olay.key() in (Qt.Key_Tab, Qt.Key_Backtab):
            self.keyPressEvent(olay)
            return True
        return super().event(olay)

    def keyPressEvent(self, olay):
        k, shift = olay.key(), bool(olay.modifiers() & Qt.ShiftModifier)
        if k in (Qt.Key_Return, Qt.Key_Enter) and olay.modifiers() & Qt.AltModifier:
            self.insert("\n")             # Alt+Enter: hücre içinde yeni satır
        elif k in (Qt.Key_Return, Qt.Key_Enter):
            self._son(True, -1 if shift else 1, 0)
        elif k in (Qt.Key_Tab, Qt.Key_Backtab):
            self._son(True, 0, -1 if (k == Qt.Key_Backtab or shift) else 1)
        elif k == Qt.Key_Escape:
            self._son(False)
        elif self.yazma_modu and k in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right):
            d = {Qt.Key_Up: (-1, 0), Qt.Key_Down: (1, 0),
                 Qt.Key_Left: (0, -1), Qt.Key_Right: (0, 1)}[k]
            self._son(True, *d)
        else:
            super().keyPressEvent(olay)

    def focusOutEvent(self, olay):
        super().focusOutEvent(olay)
        self._son(True)


class Izgara(QAbstractScrollArea):
    aktifDegisti = Signal(int, int)       # satır, sütun
    secimDegisti = Signal(object)         # Aralik
    degisti = Signal()                    # içerik değişti (düzenleme, silme, geri al)
    modDegisti = Signal(str)              # 'Hazır' | 'Gir' | 'Düzenle'
    duzenlemeMetniDegisti = Signal(str)   # hücre içi düzenleyicideki metin (formül çubuğu aynalar)
    suruklemeBitti = Signal()
    gecmisIslemi = Signal(bool)           # geri al/yinele başladı (True) / bitti (False)
    yakinlastirmaDegisti = Signal(float)
    uyari = Signal(str)                   # kullanıcıya gösterilecek iletiler

    TOPLU_SINIR = 20000                   # tek işlemde en çok satır/sütun (gizle, boyutlandır)
    MIME_HUCRELER = "application/x-tabcel-hucreler"
    MIME_JETON = "application/x-tabcel-jeton"
    _pano_durumu: Optional[dict] = None   # tüm ızgaralarda ortak: kopyalanan/kesilen aralık

    SATIR_BASLIK_GENISLIGI = 46
    SUTUN_BASLIK_YUKSEKLIGI = 20

    def __init__(self, sayfa: Sayfa, parent=None, yigin: Optional[GeriAlYigini] = None):
        super().__init__(parent)
        self.sayfa = sayfa
        self.yakinlastirma = 1.0
        self._aktif = (1, 1)
        self._uc = (1, 1)            # seçimin hareketli ucu
        self._surukleme: Optional[str] = None   # 'hucre' | 'satir' | 'sutun'
        self.yigin = yigin if yigin is not None else GeriAlYigini()
        self._duzenleyici: Optional[_Duzenleyici] = None
        self._duzenlenen = (1, 1)
        self._ekler: List[Aralik] = []         # Ctrl ile eklenen önceki aralıklar (birincil aralık hariç)
        self._koru = False                      # fare düğmesi basılıyken çoklu seçim korunur
        self._genislik_onb: Dict[str, int] = {}     # metin → piksel genişliği (kaydırmada yeniden ölçülmesin)
        self._sayi_onb: Dict[tuple, str] = {}       # (sayı, sığan px) → gösterilen metin
        self._statik_onb: Dict[str, QStaticText] = {}   # çizim için hazır metin düzenleri
        self._onbellek_anahtari = None
        self._dikey_son = 0                         # artımlı kaydırma için önceki dikey kaydırma değeri
        self._boyut: Optional[dict] = None     # kenardan boyutlandırma durumu
        self.setFocusPolicy(Qt.StrongFocus)
        self.viewport().setMouseTracking(True)
        self.horizontalScrollBar().setRange(0, MAX_COL - 1)
        self.verticalScrollBar().setRange(0, MAX_ROW - 1)
        self.horizontalScrollBar().valueChanged.connect(self._yatay_kaydi)
        self.verticalScrollBar().valueChanged.connect(self._dikey_kaydi)
        QApplication.clipboard().dataChanged.connect(self._pano_degisti)

    # --- ölçüler ---
    def _z(self, v: float) -> int:
        return max(1, round(v * self.yakinlastirma))

    def _baslik_g(self) -> int:
        return self._z(self.SATIR_BASLIK_GENISLIGI)

    def _baslik_y(self) -> int:
        return self._z(self.SUTUN_BASLIK_YUKSEKLIGI)

    def _gen(self, sutun: int) -> int:
        w = self.sayfa.genislik(sutun)
        return self._z(w) if w else 0

    def _yuk(self, satir: int) -> int:
        h = self.sayfa.yukseklik(satir)
        return self._z(h) if h else 0

    @property
    def ilk_satir(self) -> int:
        return self.verticalScrollBar().value() + 1

    @property
    def ilk_sutun(self) -> int:
        return self.horizontalScrollBar().value() + 1

    def _gorunen_sutunlar(self) -> Iterator[Tuple[int, int, int]]:
        """(sütun, x, genişlik) — viewport sağına kadar."""
        x, c, w = self._baslik_g(), self.ilk_sutun, self.viewport().width()
        while x < w and c <= MAX_COL:
            g = self._gen(c)
            if g:                       # gizli sütun atlanır
                yield c, x, g
                x += g
            c += 1

    def _gorunen_satirlar(self) -> Iterator[Tuple[int, int, int]]:
        y, r, h = self._baslik_y(), self.ilk_satir, self.viewport().height()
        while y < h and r <= MAX_ROW:
            yk = self._yuk(r)
            if yk:
                yield r, y, yk
                y += yk
            r += 1

    def hucre_dikdortgeni(self, satir: int, sutun: int) -> Optional[QRect]:
        """Hücrenin viewport içindeki dikdörtgeni; görünmüyorsa None."""
        x = y = None
        w = h = 0
        for c, cx, cg in self._gorunen_sutunlar():
            if c == sutun:
                x, w = cx, cg
                break
        for r, ry, rh in self._gorunen_satirlar():
            if r == satir:
                y, h = ry, rh
                break
        if x is None or y is None:
            return None
        return QRect(x, y, w, h)

    def _noktadan(self, p: QPoint) -> Tuple[Optional[int], Optional[int]]:
        """Piksel → (satır, sütun); başlık alanındaysa ilgili taraf None."""
        sutun = satir = None
        if p.x() >= self._baslik_g():
            for c, x, g in self._gorunen_sutunlar():
                if x <= p.x() < x + g:
                    sutun = c
                    break
            else:
                sutun = self._son_gorunen_sutun()
        if p.y() >= self._baslik_y():
            for r, y, h in self._gorunen_satirlar():
                if y <= p.y() < y + h:
                    satir = r
                    break
            else:
                satir = self._son_gorunen_satir()
        return satir, sutun

    def _son_gorunen_sutun(self) -> int:
        return max((c for c, _, _ in self._gorunen_sutunlar()), default=self.ilk_sutun)

    def _son_gorunen_satir(self) -> int:
        return max((r for r, _, _ in self._gorunen_satirlar()), default=self.ilk_satir)

    # --- seçim ---
    @property
    def aktif(self) -> Tuple[int, int]:
        return self._aktif

    @property
    def secim(self) -> Aralik:
        (r1, c1), (r2, c2) = self._aktif, self._uc
        return Aralik(min(r1, r2), min(c1, c2), max(r1, r2), max(c1, c2))

    @property
    def secimler(self) -> List[Aralik]:
        """Tüm seçili aralıklar (Ctrl ile eklenenler + birincil, son sırada)."""
        return list(self._ekler) + [self.secim]

    def secili_mi(self, satir: int, sutun: int) -> bool:
        return any(aralik_icinde(a, satir, sutun) for a in self.secimler)

    def sec(self, aktif: Tuple[int, int], uc: Optional[Tuple[int, int]] = None,
            kaydir: bool = True) -> None:
        eski_aktif, eski_secim, eski_ekler = self._aktif, self.secim, list(self._ekler)
        if not self._koru:
            self._ekler.clear()
        self._aktif = (min(max(aktif[0], 1), MAX_ROW), min(max(aktif[1], 1), MAX_COL))
        uc = uc or self._aktif
        self._uc = (min(max(uc[0], 1), MAX_ROW), min(max(uc[1], 1), MAX_COL))
        if kaydir:
            self._gorunur_yap(self._uc if uc != self._aktif else self._aktif)
        self._secim_boya(eski_ekler + [eski_secim], eski_aktif)
        if self._aktif != eski_aktif:
            self.aktifDegisti.emit(*self._aktif)
        if self.secim != eski_secim or self._ekler != eski_ekler:
            self.secimDegisti.emit(self.secim)

    def _secim_boya(self, eski_aralik_listesi, eski_aktif) -> None:
        """Seçim değişince tüm viewport yerine yalnızca eski + yeni seçimin (ve ilgili başlıkların)
        kapladığı bölgeleri yeniden boyar."""
        sutunlar = list(self._gorunen_sutunlar())
        satirlar = list(self._gorunen_satirlar())
        vp = self.viewport()
        bg, bh = self._baslik_g(), self._baslik_y()
        aralik_listesi = list(eski_aralik_listesi) + self.secimler
        aralik_listesi += [Aralik(*eski_aktif, *eski_aktif), Aralik(*self._aktif, *self._aktif)]
        for a in aralik_listesi:
            xs = [(x, x + g) for c, x, g in sutunlar if a.ilk_sutun <= c <= a.son_sutun]
            ys = [(y, y + h) for r, y, h in satirlar if a.ilk_satir <= r <= a.son_satir]
            if xs:                                        # sütun başlıkları (satırlar ekran dışında olsa da)
                vp.update(QRect(xs[0][0], 0, xs[-1][1] - xs[0][0], bh))
            if ys:                                        # satır başlıkları
                vp.update(QRect(0, ys[0][0], bg, ys[-1][1] - ys[0][0]))
            if xs and ys:
                x1, x2, y1, y2 = xs[0][0], xs[-1][1], ys[0][0], ys[-1][1]
                vp.update(QRect(x1 - 3, y1 - 3, x2 - x1 + 6, y2 - y1 + 6))

    def _gorunur_yap(self, hedef: Tuple[int, int]) -> None:
        satir, sutun = hedef
        hs, vs = self.horizontalScrollBar(), self.verticalScrollBar()
        if sutun < self.ilk_sutun:
            hs.setValue(sutun - 1)
        else:
            if sutun > self._son_gorunen_sutun() + 1:    # uzak hedef: tek seferde yaklaş
                hs.setValue(max(hs.value(), sutun - 1 - hs.pageStep()))
            while sutun > self.ilk_sutun and not self._sigiyor_mu(sutun, True):
                hs.setValue(hs.value() + 1)
        if satir < self.ilk_satir:
            vs.setValue(satir - 1)
        else:
            if satir > self._son_gorunen_satir() + 1:
                vs.setValue(max(vs.value(), satir - 1 - vs.pageStep()))
            while satir > self.ilk_satir and not self._sigiyor_mu(satir, False):
                vs.setValue(vs.value() + 1)

    def _sigiyor_mu(self, indeks: int, sutun_mu: bool) -> bool:
        """Hücre viewport içinde tam görünüyor mu (sağ/alt kenar)."""
        if sutun_mu:
            for c, x, g in self._gorunen_sutunlar():
                if c == indeks:
                    return x + g <= self.viewport().width()
        else:
            for r, y, h in self._gorunen_satirlar():
                if r == indeks:
                    return y + h <= self.viewport().height()
        return False

    # --- çizim ---
    def _onbellek_hazirla(self) -> None:
        anahtar = (self.yakinlastirma, self.font().key())
        if anahtar != self._onbellek_anahtari or len(self._genislik_onb) > 60000:
            self._onbellek_anahtari = anahtar
            self._genislik_onb.clear()
            self._sayi_onb.clear()
            self._statik_onb.clear()

    def _yerlesim(self, sutunlar, satirlar, olcer, pad):
        """Görünen hücrelerin metin yerleşimi.

        Döner: (metinler, tasma). metinler: (kırpma dikdörtgeni, metin dikdörtgeni, hizalama, metin,
        metin genişliği px); tasma: {(satır, sütun)} — sağındaki dikey çizgi taşan metin yüzünden
        çizilmeyecek hücreler.
        Kurallar (Excel): metin sola yaslı ve sığmıyorsa sağdaki BOŞ hücrelere taşar; sayı taşmaz,
        sığmıyorsa önce kısaltılır, olmazsa `####` olur; mantıksal değer ortalanır.
        Ölçümler önbelleğe alınır: aynı hücreler kaydırırken tekrar tekrar ölçülmez.
        """
        self._onbellek_hazirla()
        genislikler, sayilar = self._genislik_onb, self._sayi_onb
        hucre_al = self.sayfa.hucre
        sonuc_al = self.sayfa._sonuc.get

        def olc(t: str) -> int:
            w = genislikler.get(t)
            if w is None:
                w = genislikler[t] = olcer.horizontalAdvance(t)
            return w

        sol, sag, orta = Qt.AlignLeft, Qt.AlignRight, Qt.AlignHCenter
        metinler, tasma = [], set()
        for r, y, h in satirlar:
            for i, (c, x, g) in enumerate(sutunlar):
                hucre = hucre_al(r, c)
                if hucre is None:
                    continue
                v = hucre.deger if hucre.formul is None else sonuc_al((r, c))
                if v is None:
                    continue
                if isinstance(v, str):
                    # Alt+Enter ile girilen satır sonları kaydırma kapalıyken görünmez
                    metin = v.replace("\r", "").replace("\n", "") if ("\n" in v or "\r" in v) else v
                    w = olc(metin)
                    gerek = w + 2 * pad
                    toplam, j = g, i
                    while toplam < gerek and j + 1 < len(sutunlar):
                        c2, _, g2 = sutunlar[j + 1]
                        komsu = hucre_al(r, c2)
                        if komsu is not None and not komsu.bos_mu():
                            break
                        tasma.add((r, sutunlar[j][0]))
                        toplam += g2
                        j += 1
                    metinler.append((QRect(x, y, toplam - 1, h),
                                     QRect(x + pad, y, toplam - 2 * pad, h), sol, metin, w))
                elif isinstance(v, (bool, Hata)):           # mantıksal ve hata değerleri ortalanır
                    metin = goster(v)
                    metinler.append((QRect(x, y, g - 1, h), QRect(x + pad, y, g - 2 * pad, h),
                                     orta, metin, olc(metin)))
                else:
                    sigan = g - 2 * pad
                    anahtar = (v, sigan)
                    metin = sayilar.get(anahtar)
                    if metin is None:
                        metin = sayiyi_sigdir(v, lambda t: olc(t) <= sigan)
                        if metin is None:
                            metin = "#" * max(1, sigan // max(1, olc("#")))
                        sayilar[anahtar] = metin
                    metinler.append((QRect(x, y, g - 1, h), QRect(x + pad, y, g - 2 * pad, h),
                                     sag, metin, olc(metin)))
        return metinler, tasma

    def paintEvent(self, olay):
        p = QPainter(self.viewport())
        p.setFont(self._yazi_tipi())
        kirp = olay.rect()                     # yalnızca açığa çıkan bölge (artımlı kaydırmada küçük)
        p.fillRect(kirp, QColor(theme.SURFACE))
        sutunlar = list(self._gorunen_sutunlar())
        tum_satirlar = list(self._gorunen_satirlar())
        satirlar = [s for s in tum_satirlar if s[1] <= kirp.bottom() and s[1] + s[2] > kirp.top()]
        bg, bh = self._baslik_g(), self._baslik_y()
        sec = self.secim
        izgara = QPen(QColor(theme.GRID_LINE))
        sag = sutunlar[-1][1] + sutunlar[-1][2] if sutunlar else bg
        alt = tum_satirlar[-1][1] + tum_satirlar[-1][2] if tum_satirlar else bh

        # hücre içerikleri: önce yerleşim (taşma/####), sonra ızgara çizgileri, sonra metinler
        pad = self._z(4)
        olcer = p.fontMetrics()
        metinler, tasma = self._yerlesim(sutunlar, satirlar, olcer, pad)

        p.setPen(izgara)
        y1, y2 = max(bh, kirp.top()), min(alt - 1, kirp.bottom())
        tasan_sutunlar = {c for _, c in tasma}
        for c, x, g in sutunlar:
            if c not in tasan_sutunlar:
                p.drawLine(x + g - 1, y1, x + g - 1, y2)
            else:               # taşan metnin altındaki dikey çizgi çizilmez (Excel gibi)
                for r, y, h in satirlar:
                    if (r, c) not in tasma:
                        p.drawLine(x + g - 1, y, x + g - 1, y + h - 1)
        for _, y, h in satirlar:
            p.drawLine(bg, y + h - 1, sag - 1, y + h - 1)

        p.setPen(QColor(theme.TEXT))
        yukseklik = olcer.height()
        statik = self._statik_onb
        for kirp_k, kutu, bayrak, metin, w in metinler:
            if bayrak == Qt.AlignRight:
                x = kutu.left() + kutu.width() - w
            elif bayrak == Qt.AlignHCenter:
                x = kutu.left() + (kutu.width() - w) // 2
            else:
                x = kutu.left()
            sigmiyor = w > kutu.width()        # yalnızca sığmayan metinde (taşma sınırı) kırpılır
            if sigmiyor:
                p.setClipRect(kirp_k)
            st = statik.get(metin)
            if st is None:
                st = statik[metin] = QStaticText(metin)
                st.setTextFormat(Qt.PlainText)
                st.setPerformanceHint(QStaticText.AggressiveCaching)
            p.drawStaticText(x, kutu.top() + (kutu.height() - yukseklik) // 2, st)
            if sigmiyor:
                p.setClipping(False)

        # seçim
        dolgu = QColor(theme.SELECTION_FILL)
        dolgu.setAlpha(36)
        tum = self.secimler
        for a in tum:
            for c, x, g in sutunlar:
                if a.ilk_sutun <= c <= a.son_sutun:
                    for r, y, h in satirlar:
                        if a.ilk_satir <= r <= a.son_satir and (r, c) != self._aktif:
                            p.fillRect(x, y, g - 1, h - 1, dolgu)
        if sutunlar and tum_satirlar:
            for a in self._ekler:
                self._secim_cercevesi(p, a, sutunlar, tum_satirlar, tek_hucre=True)
            self._secim_cercevesi(p, sec, sutunlar, tum_satirlar)
        d = Izgara._pano_durumu
        if d and d["sayfa"] is self.sayfa and sutunlar and tum_satirlar:
            self._secim_cercevesi(p, d["aralik"], sutunlar, tum_satirlar,
                                  QPen(QColor(theme.ACCENT), 2, Qt.DashLine), tek_hucre=True)
        ar = self.hucre_dikdortgeni(*self._aktif)
        if ar:
            p.setPen(QPen(QColor(theme.ACCENT), 2))
            p.drawRect(ar.adjusted(0, 0, -2, -2))

        # başlıklar
        # (yalnızca açığa çıkan bölgeye değenler: artımlı kaydırmada sütun başlıkları yeniden çizilmez)
        p.setClipping(False)
        genislik, yukseklik_vp = self.viewport().width(), self.viewport().height()
        baslik_zemin = QColor(theme.HEADER_BG)
        sutun_basligi_gerek = kirp.top() < bh
        if sutun_basligi_gerek:
            p.fillRect(QRect(0, 0, genislik, bh).intersected(kirp), baslik_zemin)
        if kirp.left() < bg:
            p.fillRect(QRect(0, 0, bg, yukseklik_vp).intersected(kirp), baslik_zemin)
        p.setPen(izgara)
        if sutun_basligi_gerek:
            p.drawLine(0, bh - 1, genislik, bh - 1)
        if kirp.left() < bg:
            p.drawLine(bg - 1, max(0, kirp.top()), bg - 1, min(yukseklik_vp, kirp.bottom()))
        if sutun_basligi_gerek:
            for c, x, g in sutunlar:
                self._baslik_ciz(p, QRect(x, 0, g, bh), sutun_harfe(c),
                                 any(a.ilk_sutun <= c <= a.son_sutun for a in tum), izgara)
        if kirp.left() < bg:
            for r, y, h in satirlar:
                self._baslik_ciz(p, QRect(0, y, bg, h), str(r),
                                 any(a.ilk_satir <= r <= a.son_satir for a in tum), izgara)
        p.end()

    def _yazi_tipi(self) -> QFont:
        yazi = QFont(self.font())
        yazi.setPointSizeF(max(6.0, self.font().pointSizeF() * self.yakinlastirma))
        return yazi

    def _secim_cercevesi(self, p, sec, sutunlar, satirlar, kalem=None, tek_hucre=False):
        """Aralığın dış çerçevesi (görünen kısım). Seçimde yalnızca çok hücreli aralık çizilir."""
        if not tek_hucre and sec.ilk_satir == sec.son_satir and sec.ilk_sutun == sec.son_sutun:
            return
        x1 = next((x for c, x, g in sutunlar if c >= sec.ilk_sutun), None)
        y1 = next((y for r, y, h in satirlar if r >= sec.ilk_satir), None)
        sag = [x + g for c, x, g in sutunlar if c <= sec.son_sutun]
        alt = [y + h for r, y, h in satirlar if r <= sec.son_satir]
        if None in (x1, y1) or not sag or not alt:
            return
        w, h = max(sag) - x1 - 2, max(alt) - y1 - 2
        p.setPen(kalem or QPen(QColor(theme.ACCENT), 2))
        sol = sec.ilk_sutun >= sutunlar[0][0]            # aralığın gerçek kenarı görünüyor mu?
        ust = sec.ilk_satir >= satirlar[0][0]
        sagda = sec.son_sutun <= sutunlar[-1][0]
        altta = sec.son_satir <= satirlar[-1][0]
        if sol and ust and sagda and altta:
            p.drawRect(QRect(x1, y1, w, h))
            return
        # Aralık görünür alanı aşıyorsa görünür-alan kenarına çizgi çizilmez: çerçeve içerikle
        # birlikte kayar, kaydırmada artefakt kalmaz.
        kalem2 = QPen(p.pen())
        kalem2.setCapStyle(Qt.FlatCap)        # uçlar içerikten bağımsız; köşeler elle birleştirilir
        p.setPen(kalem2)
        e = max(1, round(kalem2.widthF() / 2))
        # Kenar görünmüyorsa çizgi son satırın/sütunun sonuna kadar (iki piksel pay dahil) uzar;
        # yoksa kaydırınca içerikte boşluk kalır.
        x_son = x1 + w + (e if sagda else 2)
        y_son = y1 + h + (e if altta else 2)
        x_ilk = x1 - (e if sol else 0)
        y_ilk = y1 - (e if ust else 0)
        if ust:
            p.drawLine(x_ilk, y1, x_son, y1)
        if altta:
            p.drawLine(x_ilk, y1 + h, x_son, y1 + h)
        if sol:
            p.drawLine(x1, y_ilk, x1, y_son)
        if sagda:
            p.drawLine(x1 + w, y_ilk, x1 + w, y_son)

    def _baslik_ciz(self, p, ar: QRect, metin: str, secili: bool, izgara: QPen):
        if secili:
            p.fillRect(ar, QColor(theme.HEADER_BG_SELECTED))
        p.setPen(izgara)
        p.drawLine(ar.right(), ar.top(), ar.right(), ar.bottom())
        p.drawLine(ar.left(), ar.bottom(), ar.right(), ar.bottom())
        p.setPen(QColor(theme.HEADER_TEXT_SELECTED if secili else theme.HEADER_TEXT))
        p.drawText(ar, int(Qt.AlignCenter), metin)

    def resizeEvent(self, olay):
        super().resizeEvent(olay)
        self._duzenleyici_yerlestir()
        self._sayfa_adimlari()

    def _sayfa_adimlari(self) -> None:
        self.horizontalScrollBar().setPageStep(max(1, len(list(self._gorunen_sutunlar())) - 1))
        self.verticalScrollBar().setPageStep(max(1, len(list(self._gorunen_satirlar())) - 1))

    # --- fare ---
    def mousePressEvent(self, olay):
        if olay.button() != Qt.LeftButton:
            return
        self.duzenlemeyi_bitir()
        nokta = olay.position().toPoint()
        kenar = self._kenar_bul(nokta)
        if kenar:
            self._boyut_basla(kenar, nokta)
            self.setFocus()
            return
        satir, sutun = self._noktadan(nokta)
        shift = bool(olay.modifiers() & Qt.ShiftModifier)
        ekleme = False
        if olay.modifiers() & Qt.ControlModifier and not (satir is None and sutun is None):
            self._ekler.append(self.secim)          # Ctrl: önceki seçim kalsın, yenisi eklensin
            self._koru = True
            ekleme = True
        elif shift and self._ekler:
            self._koru = True                       # Shift: son aralığı genişlet, öncekiler kalsın
        if satir is not None and sutun is not None:
            self._surukleme = "hucre"
            self.sec(self._aktif, (satir, sutun)) if shift else self.sec((satir, sutun))
        elif sutun is not None:      # sütun başlığı
            self._surukleme = "sutun"
            self._sutun_sec(sutun, shift)
        elif satir is not None:      # satır başlığı
            self._surukleme = "satir"
            self._satir_sec(satir, shift)
        else:                        # sol üst köşe: tümünü seç
            self.sec((1, 1), (MAX_ROW, MAX_COL), kaydir=False)
        if ekleme:
            self.secimDegisti.emit(self.secim)       # aynı hücreye Ctrl+tıkta da özet yenilensin
        self.setFocus()

    def mouseMoveEvent(self, olay):
        p = olay.position().toPoint()
        if not (olay.buttons() & Qt.LeftButton):
            self._imlec_guncelle(p)
            return
        if self._surukleme == "boyut":
            self._boyut_surukle(p)
            return
        if not self._surukleme:
            return
        satir, sutun = self._noktadan(QPoint(max(p.x(), self._baslik_g()),
                                             max(p.y(), self._baslik_y())))
        ayar_s = self.viewport().height()
        ayar_g = self.viewport().width()
        if p.y() > ayar_s:
            satir = min(self._uc[0] + 1, MAX_ROW)
        elif p.y() < self._baslik_y():
            satir = max(self._uc[0] - 1, 1)
        if p.x() > ayar_g:
            sutun = min(self._uc[1] + 1, MAX_COL)
        elif p.x() < self._baslik_g():
            sutun = max(self._uc[1] - 1, 1)
        if self._surukleme == "hucre" and satir and sutun:
            self.sec(self._aktif, (satir, sutun))
        elif self._surukleme == "sutun" and sutun:
            self.sec(self._aktif, (MAX_ROW, sutun), kaydir=False)
        elif self._surukleme == "satir" and satir:
            self.sec(self._aktif, (satir, MAX_COL), kaydir=False)

    def mouseReleaseEvent(self, olay):
        if self._surukleme == "boyut":
            self._boyut_bitir()
        self._surukleme = None
        self._koru = False
        self.suruklemeBitti.emit()

    def suruklenuyor(self) -> bool:
        return self._surukleme is not None

    def yakinlastir(self, oran: float) -> None:
        oran = min(max(oran, 0.1), 4.0)
        if abs(oran - self.yakinlastirma) < 1e-9:
            return
        self.yakinlastirma = oran
        self._sayfa_adimlari()
        self._duzenleyici_yerlestir()
        self.viewport().update()
        self.yakinlastirmaDegisti.emit(oran)

    def wheelEvent(self, olay):
        if olay.modifiers() & Qt.ControlModifier:
            yon = 1 if olay.angleDelta().y() > 0 else -1
            self.yakinlastir(round(self.yakinlastirma + 0.1 * yon, 2))
            olay.accept()
        else:
            super().wheelEvent(olay)

    def _sutun_sec(self, sutun: int, shift: bool):
        if shift:
            self.sec((1, self._aktif[1]), (MAX_ROW, sutun), kaydir=False)
        else:
            self.sec((1, sutun), (MAX_ROW, sutun), kaydir=False)

    def _satir_sec(self, satir: int, shift: bool):
        if shift:
            self.sec((self._aktif[0], 1), (satir, MAX_COL), kaydir=False)
        else:
            self.sec((satir, 1), (satir, MAX_COL), kaydir=False)

    def focusOutEvent(self, olay):
        self._koru = False        # fare bırakma olayı kaybolsa bile çoklu seçim kipi takılı kalmaz
        super().focusOutEvent(olay)

    # --- klavye ---
    def event(self, olay):
        if olay.type() == QEvent.KeyPress and olay.key() in (Qt.Key_Tab, Qt.Key_Backtab):
            self.keyPressEvent(olay)      # odak gezintisi yerine hücre gezintisi
            return True
        return super().event(olay)

    def keyPressEvent(self, olay):
        k, m = olay.key(), olay.modifiers()
        ctrl = bool(m & Qt.ControlModifier)
        shift = bool(m & Qt.ShiftModifier)
        yon = {Qt.Key_Up: (-1, 0), Qt.Key_Down: (1, 0),
               Qt.Key_Left: (0, -1), Qt.Key_Right: (0, 1)}.get(k)
        sayfa_adimi = max(1, self.verticalScrollBar().pageStep())
        if yon:
            kaynak = self._uc if shift else self._aktif
            if ctrl:
                hedef = self._atla(kaynak, yon)
            else:
                hedef = self._gizlileri_atla((kaynak[0] + yon[0], kaynak[1] + yon[1]), yon) or kaynak
            self._git(hedef, shift)
        elif k in (Qt.Key_PageDown, Qt.Key_PageUp):
            kaynak = self._uc if shift else self._aktif
            d = sayfa_adimi if k == Qt.Key_PageDown else -sayfa_adimi
            self._git((kaynak[0] + d, kaynak[1]), shift)
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() + d)
        elif k == Qt.Key_Home:
            if ctrl:
                self._git((1, 1), shift)
            else:
                kaynak = self._uc if shift else self._aktif
                self._git((kaynak[0], 1), shift)
        elif k == Qt.Key_End and ctrl:
            kul = self.sayfa.kullanilan_aralik()
            self._git((kul[2], kul[3]) if kul else (1, 1), shift)
        elif k == Qt.Key_A and ctrl:
            self.sec((1, 1), (MAX_ROW, MAX_COL), kaydir=False)
        elif k == Qt.Key_Space and ctrl:
            self._sutun_sec(self._aktif[1], False)
        elif k == Qt.Key_Space and shift:
            self._satir_sec(self._aktif[0], False)
        elif k in (Qt.Key_Tab, Qt.Key_Backtab):
            geri = k == Qt.Key_Backtab or shift
            yon = (0, -1 if geri else 1)
            self.sec(self._gizlileri_atla((self._aktif[0], self._aktif[1] + yon[1]), yon) or self._aktif)
        elif k in (Qt.Key_Return, Qt.Key_Enter):
            yon = (-1 if shift else 1, 0)
            self.sec(self._gizlileri_atla((self._aktif[0] + yon[0], self._aktif[1]), yon) or self._aktif)
        elif k == Qt.Key_F2:
            self.duzenle_baslat(None)
        elif k == Qt.Key_Delete and not shift:
            self.secimi_temizle()
        elif k == Qt.Key_Backspace:
            self.duzenle_baslat("")
        elif ctrl and k == Qt.Key_9:
            self.satirlari_gizle()
        elif ctrl and k == Qt.Key_0:
            self.sutunlari_gizle()
        elif ctrl and k == Qt.Key_ParenLeft:
            self.satirlari_goster()
        elif ctrl and k == Qt.Key_ParenRight:
            self.sutunlari_goster()
        elif ctrl and k == Qt.Key_Minus and (self._tam_satir_secimi() or self._tam_sutun_secimi()):
            self.satirlari_sil() if self._tam_satir_secimi() else self.sutunlari_sil()
        elif ctrl and k in (Qt.Key_Plus, Qt.Key_Equal) and (self._tam_satir_secimi() or self._tam_sutun_secimi()):
            self.satirlari_ekle() if self._tam_satir_secimi() else self.sutunlari_ekle()
        elif ctrl and k == Qt.Key_C or (ctrl and k == Qt.Key_Insert):
            self.kopyala()
        elif ctrl and k == Qt.Key_X or (shift and k == Qt.Key_Delete):
            self.kes()
        elif ctrl and k == Qt.Key_V or (shift and k == Qt.Key_Insert):
            self.yapistir()
        elif k == Qt.Key_Escape:
            self._pano_isareti_temizle()
        elif k == Qt.Key_Z and ctrl:
            self.geri_al()
        elif k == Qt.Key_Y and ctrl:
            self.yinele()
        elif (olay.text() and olay.text()[0].isprintable()
              and not (ctrl and not (m & Qt.AltModifier))):
            self.duzenle_baslat(olay.text())
        else:
            super().keyPressEvent(olay)

    # --- pano ---
    def kopyala(self) -> None:
        self._panoya_koy(kesilen=False)

    def kes(self) -> None:
        """Kes: hücreler yapıştırılana kadar yerinde kalır (Excel gibi), kesik çizgili çerçeveyle işaretlenir."""
        self._panoya_koy(kesilen=True)

    def _panoya_koy(self, kesilen: bool) -> None:
        if self._ekler:
            self.uyari.emit("Bu komut birden çok seçimde kullanılamaz.")
            return
        ar = pano.pano_araligi(self.sayfa, self.secim)
        veri = pano.pano_verisi_al(self.sayfa, ar)
        satirlar = pano.metin_satirlari(veri)
        jeton = uuid.uuid4().hex
        Izgara._pano_durumu = {"sayfa": self.sayfa, "aralik": ar, "kesildi": kesilen, "jeton": jeton}
        md = QMimeData()
        md.setText(pano.tsv_yaz(satirlar))
        md.setHtml(pano.html_yaz(satirlar))
        md.setData(self.MIME_HUCRELER, veri.json_yaz().encode("utf-8"))
        md.setData(self.MIME_JETON, jeton.encode("ascii"))
        QApplication.clipboard().setMimeData(md)
        self.viewport().update()

    def _pano_degisti(self) -> None:
        """Pano başka bir uygulamadan/kopyalamadan değiştiyse işareti kaldır."""
        d = Izgara._pano_durumu
        if d is not None:
            md = QApplication.clipboard().mimeData()
            if md is None or not md.hasFormat(self.MIME_JETON) or \
                    bytes(md.data(self.MIME_JETON)).decode("ascii") != d["jeton"]:
                Izgara._pano_durumu = None
        self.viewport().update()

    def _pano_isareti_temizle(self) -> None:
        if Izgara._pano_durumu is not None:
            Izgara._pano_durumu = None
            self.viewport().update()

    def _pano_oku(self) -> Optional[pano.PanoVerisi]:
        md = QApplication.clipboard().mimeData()
        if md is None:
            return None
        try:
            if md.hasFormat(self.MIME_HUCRELER):
                return pano.PanoVerisi.json_oku(bytes(md.data(self.MIME_HUCRELER)).decode("utf-8"))
            if md.hasHtml() and "<table" in md.html().lower():
                satirlar = pano.html_tablo_coz(md.html())
                if satirlar:
                    return pano.metinden_pano_verisi(satirlar)
            if md.hasText() and md.text() != "":
                return pano.metinden_pano_verisi(pano.tsv_coz(md.text()))
        except (ValueError, KeyError, TypeError):
            return None
        return None

    def yapistirilabilir(self) -> bool:
        md = QApplication.clipboard().mimeData()
        return md is not None and (md.hasFormat(self.MIME_HUCRELER) or md.hasHtml() or md.hasText())

    def yapistir(self) -> None:
        veri = self._pano_oku()
        if veri is None:
            return
        sec = self.secim
        try:
            plan = pano.yapistirma_plani(veri, sec.ilk_satir, sec.ilk_sutun, sec)
        except AdresHatasi:
            self.uyari.emit("Yapıştırılan veri sayfa sınırlarını aşıyor.")
            return
        komutlar = []
        d = Izgara._pano_durumu
        kesme = bool(d and d["kesildi"])
        if kesme:
            ar = d["aralik"]
            temizle = {(r, c): None for r, c, _ in d["sayfa"].aralikta(ar)}
            if temizle:
                komutlar.append(HucrelerDegis(d["sayfa"], temizle))
        komutlar.append(HucrelerDegis(self.sayfa, plan))
        self.yigin.calistir(Grup(komutlar))
        if kesme:
            Izgara._pano_durumu = None       # kesilen yalnızca bir kez yapıştırılır
        satirlar = [k[0] for k in plan]
        sutunlar = [k[1] for k in plan]
        self.sec((min(satirlar), min(sutunlar)), (max(satirlar), max(sutunlar)))
        self._guncelle(pano_iptal=False)          # kopya işareti kalır (art arda yapıştırma); kes zaten bitti

    # --- hücre sağ tık menüsü ---
    def _pano_eylemleri(self, m: QMenu) -> None:
        m.addAction("Kes", self.kes)
        m.addAction("Kopyala", self.kopyala)
        yap = m.addAction("Yapıştır", self.yapistir)
        yap.setEnabled(self.yapistirilabilir())

    def hucre_menusu(self, p: QPoint) -> Optional[QMenu]:
        satir, sutun = self._noktadan(p)
        if satir is None or sutun is None:
            return None
        if not aralik_icinde(self.secim, satir, sutun):
            self.sec((satir, sutun))
        m = QMenu(self)
        self._pano_eylemleri(m)
        m.addSeparator()
        m.addAction("İçeriği temizle", self.secimi_temizle)
        return m

    # --- gizli satır/sütun atlama ---
    def _gizlileri_atla(self, hedef: Tuple[int, int], yon: Tuple[int, int]):
        r, c = hedef
        while yon[0] and 1 <= r <= MAX_ROW and r in self.sayfa.gizli_satir:
            r += yon[0]
        while yon[1] and 1 <= c <= MAX_COL and c in self.sayfa.gizli_sutun:
            c += yon[1]
        if 1 <= r <= MAX_ROW and 1 <= c <= MAX_COL:
            return r, c
        return None

    # --- başlık kenarından boyutlandırma ---
    def _kenar_bul(self, p: QPoint):
        """Başlıkta bir sütunun sağ / satırın alt kenarına (±3 px) denk gelindiyse ('sutun'|'satir', indeks)."""
        bg, bh = self._baslik_g(), self._baslik_y()
        if p.y() < bh and p.x() >= bg:
            for c, x, g in self._gorunen_sutunlar():
                if abs(p.x() - (x + g)) <= 3:
                    return "sutun", c
        elif p.x() < bg and p.y() >= bh:
            for r, y, h in self._gorunen_satirlar():
                if abs(p.y() - (y + h)) <= 3:
                    return "satir", r
        return None

    def _kenar_dizini(self, kenar):
        """Boyutlandırma/sığdırma bu kenar için hangi satır/sütunlara uygulanır (seçili tam satır/sütunlar dahil)."""
        eksen, i = kenar
        sec = self.secim
        if eksen == "sutun" and self._tam_sutun_secimi() and sec.ilk_sutun <= i <= sec.son_sutun:
            araligi = range(sec.ilk_sutun, sec.son_sutun + 1)
        elif eksen == "satir" and self._tam_satir_secimi() and sec.ilk_satir <= i <= sec.son_satir:
            araligi = range(sec.ilk_satir, sec.son_satir + 1)
        else:
            araligi = range(i, i + 1)
        return list(araligi) if len(araligi) <= self.TOPLU_SINIR else [i]

    def _imlec_guncelle(self, p: QPoint) -> None:
        kenar = self._kenar_bul(p)
        sekil = Qt.ArrowCursor
        if kenar:
            sekil = Qt.SplitHCursor if kenar[0] == "sutun" else Qt.SplitVCursor
        self.viewport().setCursor(sekil)

    def _boyut_basla(self, kenar, p: QPoint) -> None:
        eksen, i = kenar
        self._surukleme = "boyut"
        self._boyut = {
            "eksen": eksen, "dizin": self._kenar_dizini(kenar),
            "p0": p.x() if eksen == "sutun" else p.y(),
            "o0": self.sayfa.genislik(i) if eksen == "sutun" else self.sayfa.yukseklik(i),
            "eski": self.sayfa.boyut_durumu(),
        }

    def _boyut_surukle(self, p: QPoint) -> None:
        b = self._boyut
        if not b:
            return
        fark = ((p.x() if b["eksen"] == "sutun" else p.y()) - b["p0"]) / self.yakinlastirma
        if b["eksen"] == "sutun":
            yeni = olcu.genislik_sinirla(b["o0"] + fark)
            for c in b["dizin"]:
                self.sayfa.sutun_genislik[c] = yeni
        else:
            yeni = olcu.yukseklik_sinirla(b["o0"] + fark)
            for r in b["dizin"]:
                self.sayfa.satir_yukseklik[r] = yeni
        self._duzenleyici_yerlestir()
        self._sayfa_adimlari()
        self.viewport().update()

    def _boyut_bitir(self) -> None:
        b, self._boyut = self._boyut, None
        if not b:
            return
        yeni = self.sayfa.boyut_durumu()
        if yeni != b["eski"]:
            self.yigin.calistir(OlcuDegis(self.sayfa, eski=b["eski"], yeni=yeni))
            self._guncelle(pano_iptal=False)

    # --- satır/sütun işlemleri (seçime uygulanır) ---
    def _tam_satir_secimi(self) -> bool:
        s = self.secim
        return s.ilk_sutun == 1 and s.son_sutun == MAX_COL

    def _tam_sutun_secimi(self) -> bool:
        s = self.secim
        return s.ilk_satir == 1 and s.son_satir == MAX_ROW

    def secili_satirlar(self) -> range:
        return range(self.secim.ilk_satir, self.secim.son_satir + 1)

    def secili_sutunlar(self) -> range:
        return range(self.secim.ilk_sutun, self.secim.son_sutun + 1)

    def _sinirli(self, adet: int) -> bool:
        if adet > self.TOPLU_SINIR:
            self.uyari.emit("Seçim bu işlem için çok büyük; daha az satır/sütun seçin.")
            return False
        return True

    def _olcu_uygula(self, uygula) -> None:
        self.yigin.calistir(OlcuDegis(self.sayfa, uygula=uygula))
        self._guncelle(pano_iptal=False)

    def satir_yuksekligi_ayarla(self, px: float) -> None:
        satirlar = self.secili_satirlar()
        if not self._sinirli(len(satirlar)):
            return
        px = olcu.yukseklik_sinirla(px)
        self._olcu_uygula(lambda s: s.satir_yukseklik.update({r: px for r in satirlar}))

    def sutun_genisligi_ayarla(self, px: float) -> None:
        sutunlar = self.secili_sutunlar()
        if not self._sinirli(len(sutunlar)):
            return
        px = olcu.genislik_sinirla(px)
        self._olcu_uygula(lambda s: s.sutun_genislik.update({c: px for c in sutunlar}))

    def sutun_otomatik_sigdir(self, sutunlar=None) -> None:
        sutunlar = list(sutunlar) if sutunlar is not None else list(self.secili_sutunlar())
        if not self._sinirli(len(sutunlar)):
            return
        hedef = set(sutunlar)
        olcer = QFontMetrics(self.font())          # 100% yakınlaştırmadaki yazı tipi
        en: Dict[int, int] = {}
        for r, c, _ in self.sayfa.dolu_hucreler(sirali=False):
            if c in hedef:
                v = self.sayfa.deger(r, c)
                if v is not None:
                    en[c] = max(en.get(c, 0), olcer.horizontalAdvance(goster(v)))

        def uygula(s):
            for c in sutunlar:
                if c in en:
                    s.sutun_genislik[c] = olcu.genislik_sinirla(en[c] + 10)
                else:
                    s.sutun_genislik.pop(c, None)
        self._olcu_uygula(uygula)

    def satir_otomatik_sigdir(self, satirlar=None) -> None:
        """Metin kaydırma henüz yok: otomatik sığdır satırı varsayılan yüksekliğe döndürür."""
        satirlar = list(satirlar) if satirlar is not None else list(self.secili_satirlar())
        if not self._sinirli(len(satirlar)):
            return
        self._olcu_uygula(lambda s: [s.satir_yukseklik.pop(r, None) for r in satirlar])

    def satirlari_gizle(self) -> None:
        satirlar = self.secili_satirlar()
        if self._sinirli(len(satirlar)):
            self._olcu_uygula(lambda s: s.gizli_satir.update(satirlar))

    def sutunlari_gizle(self) -> None:
        sutunlar = self.secili_sutunlar()
        if self._sinirli(len(sutunlar)):
            self._olcu_uygula(lambda s: s.gizli_sutun.update(sutunlar))

    def satirlari_goster(self) -> None:
        a, b = self.secim.ilk_satir, self.secim.son_satir
        if any(a <= r <= b for r in self.sayfa.gizli_satir):
            self._olcu_uygula(lambda s: s.gizli_satir.difference_update(
                {r for r in s.gizli_satir if a <= r <= b}))

    def sutunlari_goster(self) -> None:
        a, b = self.secim.ilk_sutun, self.secim.son_sutun
        if any(a <= c <= b for c in self.sayfa.gizli_sutun):
            self._olcu_uygula(lambda s: s.gizli_sutun.difference_update(
                {c for c in s.gizli_sutun if a <= c <= b}))

    def satirlari_ekle(self) -> None:
        """Seçili satır sayısı kadar boş satırı seçimin üstüne ekler."""
        sec = self.secim
        adet = sec.son_satir - sec.ilk_satir + 1
        if not self._sinirli(adet):
            return
        kul = self.sayfa.kullanilan_aralik()
        if kul and kul[2] >= sec.ilk_satir and kul[2] + adet > MAX_ROW:
            self.uyari.emit("Sayfanın sonundaki dolu hücreler dışarı itileceği için satır eklenemiyor.")
            return
        self.yigin.calistir(SatirEkleSil(self.sayfa, sec.ilk_satir, adet, ekle=True))
        self._guncelle()

    def sutunlari_ekle(self) -> None:
        sec = self.secim
        adet = sec.son_sutun - sec.ilk_sutun + 1
        if not self._sinirli(adet):
            return
        kul = self.sayfa.kullanilan_aralik()
        if kul and kul[3] >= sec.ilk_sutun and kul[3] + adet > MAX_COL:
            self.uyari.emit("Sayfanın sağ ucundaki dolu hücreler dışarı itileceği için sütun eklenemiyor.")
            return
        self.yigin.calistir(SutunEkleSil(self.sayfa, sec.ilk_sutun, adet, ekle=True))
        self._guncelle()

    def satirlari_sil(self) -> None:
        sec = self.secim
        self.yigin.calistir(SatirEkleSil(self.sayfa, sec.ilk_satir,
                                         sec.son_satir - sec.ilk_satir + 1, ekle=False))
        self._guncelle()

    def sutunlari_sil(self) -> None:
        sec = self.secim
        self.yigin.calistir(SutunEkleSil(self.sayfa, sec.ilk_sutun,
                                         sec.son_sutun - sec.ilk_sutun + 1, ekle=False))
        self._guncelle()

    # --- başlık sağ tık menüsü ---
    def baslik_menusu(self, p: QPoint) -> Optional[QMenu]:
        """Satır/sütun başlığına sağ tıklanınca menü (başlık dışındaysa None)."""
        bg, bh = self._baslik_g(), self._baslik_y()
        if p.y() < bh and p.x() >= bg:
            satir_mi = False
            _, i = self._noktadan(p)
        elif p.x() < bg and p.y() >= bh:
            satir_mi = True
            i, _ = self._noktadan(p)
        else:
            return None
        sec = self.secim
        if satir_mi and not (self._tam_satir_secimi() and sec.ilk_satir <= i <= sec.son_satir):
            self._satir_sec(i, False)
        elif not satir_mi and not (self._tam_sutun_secimi() and sec.ilk_sutun <= i <= sec.son_sutun):
            self._sutun_sec(i, False)
        sec = self.secim
        m = QMenu(self)
        self._pano_eylemleri(m)
        m.addSeparator()
        if satir_mi:
            m.addAction("Ekle", self.satirlari_ekle)
            m.addAction("Sil", self.satirlari_sil)
            m.addAction("Gizle", self.satirlari_gizle)
            goster_ = m.addAction("Göster", self.satirlari_goster)
            goster_.setEnabled(any(sec.ilk_satir <= r <= sec.son_satir for r in self.sayfa.gizli_satir))
            m.addSeparator()
            m.addAction("Satır yüksekliği…", self._satir_yuksekligi_sor)
            m.addAction("Otomatik sığdır", self.satir_otomatik_sigdir)
        else:
            m.addAction("Ekle", self.sutunlari_ekle)
            m.addAction("Sil", self.sutunlari_sil)
            m.addAction("Gizle", self.sutunlari_gizle)
            goster_ = m.addAction("Göster", self.sutunlari_goster)
            goster_.setEnabled(any(sec.ilk_sutun <= c <= sec.son_sutun for c in self.sayfa.gizli_sutun))
            m.addSeparator()
            m.addAction("Sütun genişliği…", self._sutun_genisligi_sor)
            m.addAction("Otomatik sığdır", self.sutun_otomatik_sigdir)
        return m

    def _sutun_genisligi_sor(self) -> None:
        simdi = olcu.px_karakter(self.sayfa.genislik(self.secim.ilk_sutun) or Sayfa.VARSAYILAN_SUTUN_GENISLIGI)
        deger, tamam = QInputDialog.getDouble(self, "Sütun genişliği", "Genişlik (karakter):",
                                              simdi, 0.1, 255.0, 2)
        if tamam:
            self.sutun_genisligi_ayarla(olcu.karakter_px(deger))

    def _satir_yuksekligi_sor(self) -> None:
        simdi = olcu.px_punto(self.sayfa.yukseklik(self.secim.ilk_satir) or Sayfa.VARSAYILAN_SATIR_YUKSEKLIGI)
        deger, tamam = QInputDialog.getDouble(self, "Satır yüksekliği", "Yükseklik (punto):",
                                              simdi, 0.1, 409.0, 2)
        if tamam:
            self.satir_yuksekligi_ayarla(olcu.punto_px(deger))

    def contextMenuEvent(self, olay):
        m = self.baslik_menusu(olay.pos()) or self.hucre_menusu(olay.pos())
        if m:
            m.exec(olay.globalPos())

    # --- düzenleme ---
    def duzenleniyor(self) -> bool:
        return self._duzenleyici is not None

    def duzenle_baslat(self, metin: Optional[str]) -> None:
        """metin None: mevcut içerikle (F2/çift tık, Düzenle modu); aksi halde yazma modu."""
        if self._duzenleyici is not None:
            return
        self._gorunur_yap(self._aktif)
        ar = self.hucre_dikdortgeni(*self._aktif)
        if ar is None:
            return
        yazma = metin is not None
        e = _Duzenleyici(self.viewport(), yazma)
        e.setFont(self._yazi_tipi())
        e.setText(metin if yazma else duzenleme_metni(self.sayfa.hucre(*self._aktif)))
        e.bitir.connect(self._duzenleme_bitti)
        e.textChanged.connect(self.duzenlemeMetniDegisti.emit)
        e.textChanged.connect(lambda _: self._duzenleyici_yerlestir())
        self._duzenleyici = e
        self._duzenlenen = self._aktif
        self._duzenleyici_yerlestir()
        e.show()
        e.setFocus()
        self.modDegisti.emit("Gir" if yazma else "Düzenle")
        self.duzenlemeMetniDegisti.emit(e.text())
        if not yazma:
            e.deselect()
            e.setCursorPosition(len(e.text()))

    def _duzenleyici_yerlestir(self) -> None:
        e = self._duzenleyici
        if e is None:
            return
        ar = self.hucre_dikdortgeni(*self._duzenlenen)
        if ar is None:
            e.hide()
            return
        # Yazdıkça sağa doğru genişler (en çok viewport sağ kenarına kadar)
        gerekli = e.fontMetrics().horizontalAdvance(e.text()) + self._z(14)
        genislik = min(max(ar.width() - 1, gerekli), self.viewport().width() - ar.x())
        e.setGeometry(ar.x(), ar.y(), max(genislik, 1), ar.height() - 1)
        e.show()

    def duzenlemeyi_bitir(self, onayla: bool = True) -> None:
        if self._duzenleyici is not None:
            self._duzenleyici._son(onayla)

    def scrollContentsBy(self, dx: int, dy: int) -> None:
        """Qt'nin varsayılanı tüm viewport'u geçersiz kılar; kaydırmayı `_dikey_kaydi` /
        `_yatay_kaydi` kendisi yönetir (artımlı çizim için)."""

    def _yatay_kaydi(self, _=None) -> None:
        self._duzenleyici_yerlestir()
        self.viewport().update()

    def _dikey_kaydi(self, yeni: int) -> None:
        """Dikey kaydırma: küçük adımlarda mevcut pikselleri kaydırır, yalnızca açığa çıkan
        satırlar yeniden çizilir (100.000 hücrede akıcılık için); büyük sıçramada tam çizim."""
        eski, self._dikey_son = self._dikey_son, yeni
        fark = yeni - eski
        n = len(list(self._gorunen_satirlar()))
        if fark == 0:
            return
        if abs(fark) < n - 1:
            if fark > 0:      # üstteki `fark` satır görünümden çıktı
                dy = -sum(self._yuk(r) for r in range(eski + 1, eski + 1 + fark))
            else:             # üstte `-fark` satır göründü
                dy = sum(self._yuk(r) for r in range(yeni + 1, yeni + 1 - fark))
            bh, vp = self._baslik_y(), self.viewport()
            vp.scroll(0, dy, QRect(0, bh, vp.width(), vp.height() - bh))
        else:
            self.viewport().update()
        self._duzenleyici_yerlestir()

    def _duzenleme_bitti(self, onayla: bool, dr: int, dc: int) -> None:
        e = self._duzenleyici
        if e is None:
            return
        self._duzenleyici = None
        metin = e.text()
        e.hide()
        e.deleteLater()
        if onayla:
            self.hucre_gir(*self._duzenlenen, metin)
        self.setFocus()
        self.modDegisti.emit("Hazır")
        if dr or dc:
            r, c = self._aktif
            self.sec((r + dr, c + dc))

    def hucre_gir(self, satir: int, sutun: int, metin: str) -> None:
        """Yazılan metni çözüp hücreye yazar (geri alınabilir). Değişmediyse bir şey yapmaz."""
        yeni = girdi_coz(metin)
        if yeni == self.sayfa.hucre(satir, sutun):
            return
        self.yigin.calistir(HucrelerDegis(self.sayfa, {(satir, sutun): yeni}))
        self._guncelle()

    def secimi_temizle(self) -> None:
        yeni = {(r, c): None for a in self.secimler for r, c, _ in self.sayfa.aralikta(a)}
        if yeni:
            self.yigin.calistir(HucrelerDegis(self.sayfa, yeni))
            self._guncelle()

    def geri_al(self) -> None:
        self._gecmis(self.yigin.geri_al)

    def yinele(self) -> None:
        self._gecmis(self.yigin.yinele)

    def _gecmis(self, islem) -> None:
        self.gecmisIslemi.emit(True)       # pencere: başka sayfadaki değişikliğe geçebilsin
        try:
            tamam = islem()
        finally:
            self.gecmisIslemi.emit(False)
        if tamam:
            self._guncelle()

    def _guncelle(self, pano_iptal: bool = True) -> None:
        """İçerik/yapı değişikliği sonrası yenile. Varsayılan olarak kopyala/kes işaretini iptal eder
        (Excel gibi: kaynak değişince kes modu biter; yoksa eski konum bayat kalır).
        Boyutlandırma/gizleme ve yapıştırmanın kendisi işareti korur."""
        if pano_iptal:
            Izgara._pano_durumu = None
        self._duzenleyici_yerlestir()
        self._sayfa_adimlari()
        self.viewport().update()
        self.degisti.emit()

    def mouseDoubleClickEvent(self, olay):
        kenar = self._kenar_bul(olay.position().toPoint())
        if kenar and olay.button() == Qt.LeftButton:
            self._boyut = None
            self._surukleme = None
            if kenar[0] == "sutun":
                self.sutun_otomatik_sigdir(self._kenar_dizini(kenar))
            else:
                self.satir_otomatik_sigdir(self._kenar_dizini(kenar))
            return
        satir, sutun = self._noktadan(olay.position().toPoint())
        if olay.button() == Qt.LeftButton and satir is not None and sutun is not None:
            self.duzenle_baslat(None)

    def _git(self, hedef: Tuple[int, int], genislet: bool):
        hedef = (min(max(hedef[0], 1), MAX_ROW), min(max(hedef[1], 1), MAX_COL))
        if genislet:
            self.sec(self._aktif, hedef)
        else:
            self.sec(hedef)

    def _atla(self, kaynak: Tuple[int, int], yon: Tuple[int, int]) -> Tuple[int, int]:
        """Ctrl+ok: Excel'deki gibi veri bloğunun ucuna / sonraki dolu hücreye atla."""
        kul = self.sayfa.kullanilan_aralik()
        r, c = kaynak
        dr, dc = yon

        def dolu(a, b):
            h = self.sayfa.hucre(a, b)
            return h is not None and not h.bos_mu()

        def sinirda(a, b):
            return not (1 <= a <= MAX_ROW and 1 <= b <= MAX_COL)

        if kul is None:
            return (1 if dr < 0 else MAX_ROW if dr else r,
                    1 if dc < 0 else MAX_COL if dc else c)
        # kullanılan alanın ötesindeyse doğrudan kenara
        sinir_satir = kul[2] if dr > 0 else kul[0]
        sinir_sutun = kul[3] if dc > 0 else kul[1]
        sonraki = (r + dr, c + dc)
        if sinirda(*sonraki):
            return kaynak
        if dolu(r, c) and dolu(*sonraki):
            a, b = sonraki
            while not sinirda(a + dr, b + dc) and dolu(a + dr, b + dc):
                a, b = a + dr, b + dc
            return a, b
        a, b = sonraki
        while not dolu(a, b):
            if (dr > 0 and a >= sinir_satir) or (dr < 0 and a <= sinir_satir) or \
               (dc > 0 and b >= sinir_sutun) or (dc < 0 and b <= sinir_sutun):
                return (MAX_ROW if dr > 0 else 1 if dr < 0 else r,
                        MAX_COL if dc > 0 else 1 if dc < 0 else c)
            a, b = a + dr, b + dc
        return a, b
