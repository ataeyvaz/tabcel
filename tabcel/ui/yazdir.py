"""Yazdırma, PDF ve önizleme (Faz 4 / 4d). Sayfalama `model/sayfalama.py`'de (Qt'siz); burası çizim.

Çizim 96 dpi "ızgara pikseli" biriminde yapılır, painter yazıcı çözünürlüğüne ve sayfa ölçeğine göre
ölçeklenir. Taşan metin (sola hizalı, kaydırmasız, sağdaki hücreler boşsa) komşu boş hücrelere taşar.
Sığmayan sayı Excel gibi `####` basılır. Bilerek eksik: üst/alt bilgi, sayfa numarası, el ile sayfa sonu,
çift çizgili kenarlıkta çizgi aralığı, döndürülmüş metin.
"""
import os
from typing import Callable, List, Optional, Sequence

from PySide6.QtCore import QMarginsF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPageLayout, QPageSize, QPainter, QPen
from PySide6.QtPrintSupport import QPrinter

from ..formul.kosul import KosulluHesap
from ..io.csv_io import hucre_metni
from ..model.adres import Aralik
from ..model.deger import Hata
from ..model.grafik import Grafik, Resim
from ..model.grafik_verisi import grafik_verisi
from .grafik_boyayici import grafik_ciz
from ..model.sayfa import Sayfa
from ..model.sayfa_yapisi import SayfaYapisi
from ..model.sayfalama import SayfaDilimi, sayfala

_KAGIT_ID = {"A3": QPageSize.A3, "A4": QPageSize.A4, "A5": QPageSize.A5,
             "Letter": QPageSize.Letter, "Legal": QPageSize.Legal}
_CIZGI_GENISLIK = {"ince": 1.0, "orta": 2.0, "kalin": 3.0, "kesikli": 1.0, "noktali": 1.0, "cift": 3.0, "sac": 0.5}
_CIZGI_TUR = {"kesikli": Qt.DashLine, "noktali": Qt.DotLine}
_GIRINTI_PX = 9
_PAD = 3


def sayfa_yerlesimi(yapi: SayfaYapisi) -> QPageLayout:
    return QPageLayout(
        QPageSize(_KAGIT_ID[yapi.kagit]),
        QPageLayout.Landscape if yapi.yon == "yatay" else QPageLayout.Portrait,
        QMarginsF(yapi.sol * 10, yapi.ust * 10, yapi.sag * 10, yapi.alt * 10), QPageLayout.Millimeter)


class SayfaCizici:
    """Bir sayfanın (`Sayfa`) dilimlerini çizer. `yukseklik(r)`: 100% piksel (otomatik satır yüksekliği dahil)."""

    def __init__(self, sayfa: Sayfa, yukseklik: Callable[[int], float], taban_yazi_tipi: QFont):
        self.sayfa = sayfa
        self.yukseklik = yukseklik
        self.taban = taban_yazi_tipi
        self.yapi = sayfa.sayfa_yapisi
        self._yazi_onb = {}
        self._kosullu = KosulluHesap(sayfa) if sayfa.kosullu else None   # koşullu biçim çıktıda da görünür (Excel)

    def _stil(self, r: int, c: int):
        """Hücrenin çıktıdaki stili: hücre stili + koşullu biçim yaması."""
        st = self.sayfa.stil(r, c)
        if self._kosullu is not None:
            yama = self._kosullu.hucre(r, c)[0]
            if yama is not None:
                st = yama.uygula(st)
        return st

    def genislik(self, c: int) -> float:
        return float(self.sayfa.genislik(c))

    def dilimler(self) -> List[SayfaDilimi]:
        return sayfala(self.sayfa, self.yapi, self.genislik, self.yukseklik)

    # ------------------------------------------------------------------ bir dilim
    def ciz(self, p: QPainter, dilim: SayfaDilimi, alan: QRectF, cozunurluk: float) -> None:
        """`alan`: yazıcı cihaz pikselinde yazdırılabilir dikdörtgen; `cozunurluk`: yazıcı dpi."""
        s = self.sayfa
        faktor = cozunurluk / 96.0 * dilim.olcek
        xs, x = {}, 0.0
        for c in dilim.sutunlar:
            xs[c] = x
            x += self.genislik(c)
        ys, y = {}, 0.0
        for r in dilim.satirlar:
            ys[r] = y
            y += self.yukseklik(r)
        toplam_g, toplam_y = x, y
        p.save()
        p.setClipRect(alan)
        ox = alan.x()
        if self.yapi.yatay_ortala:
            ox += max(0.0, (alan.width() - toplam_g * faktor) / 2)
        p.translate(ox, alan.y())
        p.scale(faktor, faktor)
        satirlar, sutunlar = dilim.satirlar, dilim.sutunlar
        sut_kume = set(sutunlar)
        # birleşimler: sol üst hücresi dilimdeyse tüm (dilimdeki) alanı tek hücre gibi çizilir
        birlesim_ust = {}
        kapsanan = set()
        for b in s.birlesimler:
            if b.ilk_satir in ys and b.ilk_sutun in xs:
                birlesim_ust[(b.ilk_satir, b.ilk_sutun)] = b
            for r in range(b.ilk_satir, b.son_satir + 1):
                if r in ys:
                    for c in range(b.ilk_sutun, b.son_sutun + 1):
                        if c in xs and (r, c) != (b.ilk_satir, b.ilk_sutun):
                            kapsanan.add((r, c))
        yatay_son = {c: (xs[c] + self.genislik(c)) for c in sutunlar}

        def hucre_dikdortgeni(r, c):
            b = birlesim_ust.get((r, c))
            if b is None:
                return QRectF(xs[c], ys[r], self.genislik(c), self.yukseklik(r))
            sol_c = [k for k in sutunlar if b.ilk_sutun <= k <= b.son_sutun]
            alt_r = [k for k in satirlar if b.ilk_satir <= k <= b.son_satir]
            return QRectF(xs[c], ys[r], yatay_son[sol_c[-1]] - xs[c], ys[alt_r[-1]] + self.yukseklik(alt_r[-1]) - ys[r])

        # 1) dolgular, 2) kılavuz, 3) metin, 4) kenarlıklar (kalın olan üstte)
        for r in satirlar:
            for c in sutunlar:
                if (r, c) in kapsanan:
                    continue
                st = self._stil(r, c)
                if st.dolgu:
                    p.fillRect(hucre_dikdortgeni(r, c), QColor(st.dolgu))
                if self._kosullu is not None:
                    cubuk = self._kosullu.hucre(r, c)[1]
                    if cubuk is not None:
                        self._cubuk(p, cubuk, hucre_dikdortgeni(r, c))
        if self.yapi.kilavuz:
            p.setPen(QPen(QColor("#BFBFBF"), 0.75))
            for r in satirlar:
                for c in sutunlar:
                    if (r, c) not in kapsanan:
                        p.drawRect(hucre_dikdortgeni(r, c))
        for r in satirlar:
            for c in sutunlar:
                if (r, c) in kapsanan:
                    continue
                self._metin(p, r, c, hucre_dikdortgeni(r, c), sutunlar, xs, birlesim_ust, kapsanan, toplam_g)
        for r in satirlar:
            for c in sutunlar:
                if (r, c) in kapsanan:
                    continue
                self._kenarlik(p, self._stil(r, c), hucre_dikdortgeni(r, c))
        if s.nesneler:
            self._nesneleri_ciz(p, dilim, ys, toplam_g, toplam_y)
        p.restore()

    # ------------------------------------------------------------------ nesneler (grafik / resim)
    def _nesneleri_ciz(self, p: QPainter, dilim: SayfaDilimi, ys, toplam_g: float, toplam_y: float) -> None:
        """Dilimle kesişen nesneleri dilim alanına kırparak çizer (nesne iki baskı sayfasına bölünebilir).
        Painter 96 dpi piksel biriminde ölçeklenmiş durumda; grafik vektör, resim yazıcı pikseline ölçeklenir."""
        s = self.sayfa
        sutunlar, satirlar = dilim.sutunlar, dilim.satirlar
        ilk_c = sutunlar[0]
        govde = dilim.baslik_sayisi
        ilk_r = satirlar[govde]
        baslik_y = ys[ilk_r] if govde else 0.0
        baslik_satirlar = set(satirlar[:govde])
        son_c, son_r = sutunlar[-1], satirlar[-1]
        for n in s.nesneler:
            k = n.konum
            if k.sutun > son_c:
                continue
            x = self._aralik_toplami(ilk_c, k.sutun, self.genislik) + k.dx
            if k.satir in baslik_satirlar:
                y, kes_ust, kes_alt = ys[k.satir] + k.dy, 0.0, baslik_y
            else:
                if k.satir > son_r:
                    continue
                y = ys[ilk_r] + self._aralik_toplami(ilk_r, k.satir, self.yukseklik) + k.dy
                kes_ust, kes_alt = baslik_y, toplam_y
            w, h = n.boyut
            kes = QRectF(0, kes_ust, toplam_g, kes_alt - kes_ust).intersected(QRectF(x, y, w, h))
            if kes.isEmpty():
                continue
            p.save()
            p.setClipRect(kes, Qt.IntersectClip)
            try:
                if isinstance(n, Resim):
                    img = QImage.fromData(n.veri)
                    if not img.isNull():
                        p.setRenderHint(QPainter.SmoothPixmapTransform)
                        p.drawImage(QRectF(x, y, w, h), img)
                elif isinstance(n, Grafik):
                    p.translate(x, y)
                    p.fillRect(QRectF(0, 0, w, h), Qt.white)
                    grafik_ciz(p, grafik_verisi(s.kitap, n), n, (w, h), olcek=1.0, aile=self.taban.family())
            finally:
                p.restore()

    @staticmethod
    def _aralik_toplami(bas: int, son: int, olcu: Callable[[int], float]) -> float:
        """`bas`'tan `son`'a ölçülerin işaretli toplamı: son < bas ise negatif (önceki dilimde başlayan nesne)."""
        if son >= bas:
            return sum(olcu(i) for i in range(bas, son))
        return -sum(olcu(i) for i in range(son, bas))

    # ------------------------------------------------------------------ hücre
    def _yazi_tipi(self, st) -> QFont:
        f = self._yazi_onb.get(st)
        if f is None:
            f = QFont(self.taban)
            if st.yazi_tipi:
                f.setFamily(st.yazi_tipi)
            f.setPixelSize(max(1, round((st.boyut or 11.0) * 4 / 3)))
            f.setBold(st.kalin)
            f.setItalic(st.italik)
            f.setUnderline(st.alti_cizili != "yok")
            f.setStrikeOut(st.ustu_cizili)
            self._yazi_onb[st] = f
        return f

    def _metin(self, p, r, c, kutu: QRectF, sutunlar, xs, birlesim_ust, kapsanan, toplam_g) -> None:
        s = self.sayfa
        h = s.hucre(r, c)
        if h is None:
            return
        metin = hucre_metni(s, r, c)
        if metin == "":
            return
        if self._kosullu is not None:
            cb = self._kosullu.hucre(r, c)[1]
            if cb is not None and cb[2]:
                return
        st = self._stil(r, c)
        v = s.sonuc(r, c) if h.formul is not None else h.deger
        yatay = st.yatay
        if yatay == "genel":
            yatay = "sag" if isinstance(v, float) and not isinstance(v, bool) else \
                "orta" if isinstance(v, (bool, Hata)) else "sol"
        bayrak = {"sol": Qt.AlignLeft, "orta": Qt.AlignHCenter, "sag": Qt.AlignRight,
                  "secim_ortasi": Qt.AlignHCenter, "doldur": Qt.AlignLeft,
                  "iki_yana": Qt.AlignLeft}[yatay]
        bayrak |= {"ust": Qt.AlignTop, "orta": Qt.AlignVCenter, "alt": Qt.AlignBottom}[st.dikey]
        alan = QRectF(kutu)
        if yatay == "sol" and not st.kaydir and isinstance(v, str) and (r, c) not in birlesim_ust:
            alan.setRight(self._tasma_sagi(r, c, kutu, sutunlar, xs, toplam_g))
        klip = QRectF(alan)
        girinti = st.girinti * _GIRINTI_PX if yatay in ("sol", "sag") else 0
        if yatay == "sag":
            alan.adjust(_PAD, 0, -(_PAD + girinti), 0)
        else:
            alan.adjust(_PAD + girinti, 0, -_PAD, 0)
        if st.kaydir:
            bayrak |= Qt.TextWordWrap
        yazi = self._yazi_tipi(st)
        if isinstance(v, float) and not isinstance(v, bool):
            fm = QFontMetricsF(yazi)
            if fm.horizontalAdvance(metin) > alan.width():            # sayı sığmıyor: Excel gibi ####
                metin = "#" * max(1, int(alan.width() / max(1.0, fm.horizontalAdvance("#"))))
        p.save()
        p.setClipRect(klip)
        p.setFont(yazi)
        p.setPen(QColor(st.yazi_rengi or "#000000"))
        p.drawText(alan.adjusted(0, 1, 0, -1), int(bayrak), metin)
        p.restore()

    def _cubuk(self, p, cubuk, kutu: QRectF) -> None:
        """Veri çubuğu (hücre içinde 2 px iç boşlukla; gradyan renkten beyaza)."""
        from PySide6.QtGui import QLinearGradient
        oran, renk, _yalniz, gradyan = cubuk
        k = QRectF(kutu.x() + 2, kutu.y() + 2, max(0.0, (kutu.width() - 4) * oran), max(0.0, kutu.height() - 4))
        if k.width() <= 0 or k.height() <= 0:
            return
        c1 = QColor(renk)
        if gradyan:
            gr = QLinearGradient(k.left(), 0, k.right(), 0)
            gr.setColorAt(0.0, c1)
            gr.setColorAt(1.0, QColor((c1.red() + 765) // 4, (c1.green() + 765) // 4, (c1.blue() + 765) // 4))
            p.fillRect(k, gr)
        else:
            p.fillRect(k, c1)

    def _tasma_sagi(self, r, c, kutu, sutunlar, xs, toplam_g) -> float:
        """Sola hizalı metnin sağa taşabileceği son x: bitişik hücreler boş ve birleşik değilse sayfa kenarına
        kadar uzanır."""
        s = self.sayfa
        son = kutu.right()
        i = sutunlar.index(c)
        for k in sutunlar[i + 1:]:
            if s.hucre(r, k) is not None or s.birlesim(r, k) is not None:
                break
            son = xs[k] + self.genislik(k)
        return son

    def _kenarlik(self, p, st, kutu: QRectF) -> None:
        if st.kenar.bos_mu():
            return
        for yon, a, b in (("ust", kutu.topLeft(), kutu.topRight()), ("alt", kutu.bottomLeft(), kutu.bottomRight()),
                          ("sol", kutu.topLeft(), kutu.bottomLeft()), ("sag", kutu.topRight(), kutu.bottomRight())):
            cizgi = getattr(st.kenar, yon)
            if not cizgi:
                continue
            tur, renk = cizgi
            kalem = QPen(QColor(renk), _CIZGI_GENISLIK[tur])
            kalem.setStyle(_CIZGI_TUR.get(tur, Qt.SolidLine))
            kalem.setCapStyle(Qt.FlatCap)
            p.setPen(kalem)
            p.drawLine(a, b)


# ------------------------------------------------------------------ yazıcıya
def _yazici_ayarla(printer: QPrinter, yapi: SayfaYapisi) -> None:
    printer.setPageLayout(sayfa_yerlesimi(yapi))


def yazdir(printer: QPrinter, izgaralar: Sequence, baslik: str = "") -> bool:
    """`izgaralar` sırayla yazıcıya/PDF'e yazılır; her sayfa kendi yönü/kenar boşluğuyla. Yazdırılacak hiçbir
    şey yoksa False."""
    cizicilar = []
    for g in izgaralar:
        c = SayfaCizici(g.sayfa, g.yazdirma_yuksekligi, g.font())
        d = c.dilimler()
        if d:
            cizicilar.append((c, d))
    if not cizicilar:
        return False
    ilk_yapi = cizicilar[0][0].yapi
    _yazici_ayarla(printer, ilk_yapi)
    if baslik:
        printer.setDocName(baslik)
    p = QPainter()
    if not p.begin(printer):
        raise OSError("Çıktı hedefi açılamadı (klasör yok, yazma izni yok ya da yazıcı hazır değil)")
    try:
        ilk = True
        for c, dilimler in cizicilar:
            for d in dilimler:
                if not ilk:
                    _yazici_ayarla(printer, c.yapi)
                    printer.newPage()
                ilk = False
                alan = printer.pageRect(QPrinter.DevicePixel)
                c.ciz(p, d, QRectF(alan), printer.resolution())
    finally:
        p.end()
    return True


def pdf_yaz(izgaralar: Sequence, yol: str) -> bool:
    """PDF'i önce geçici dosyaya yazar, sonra yerine koyar (kural 8). Yazdırılacak içerik yoksa False.
    Yazma hatasında OSError."""
    gecici = f"{yol}.{os.getpid()}.tmp"
    pr = QPrinter(QPrinter.HighResolution)
    pr.setOutputFormat(QPrinter.PdfFormat)
    pr.setOutputFileName(gecici)
    try:
        ok = yazdir(pr, izgaralar, os.path.basename(yol))
        if not ok:
            return False
        if not os.path.exists(gecici) or os.path.getsize(gecici) == 0:
            raise OSError("PDF yazılamadı (hedef klasöre yazma izni yok ya da disk dolu olabilir)")
        os.replace(gecici, yol)
        return True
    finally:
        if os.path.exists(gecici):
            try:
                os.remove(gecici)
            except OSError:
                pass
