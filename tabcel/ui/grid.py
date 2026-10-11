"""Izgara: QAbstractScrollArea + QPainter (QTableView değil — bkz. plan.md).

Bu aşamada: çizim, kaydırma, seçim, gezinme. Düzenleme sonraki adımda.
Kaydırma çubukları hücre sırasıyla çalışır (değer = ilk görünen satır/sütun − 1), Excel gibi.
"""
import math
import uuid
from bisect import bisect_left, bisect_right
from typing import Dict, Iterator, List, Optional, Tuple

from PySide6.QtCore import QEvent, QMimeData, QPoint, QPointF, QRect, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPen, QPolygon, QRegion, QStaticText, QTextLayout, QTextOption,
)
from PySide6.QtWidgets import (
    QAbstractScrollArea, QApplication, QInputDialog, QLabel, QLineEdit, QListWidget, QMenu,
    QPlainTextEdit, QToolTip,
)

from ..model.adres import (
    MAX_COL, MAX_ROW, AdresHatasi, Aralik, aralik_icinde, hucre_yaz, sutun_harfe,
)
from ..formul import ceviri, isaretleme
from ..formul.ceviri import hucre_girdisi, hucre_girdisi_akilli, hucre_metni
from ..formul.sozcuk import FormulHatasi
from ..formul.kosul import KosulluHesap, dogrula, liste_ogeleri
from ..model.harmanla import tr_kucuk
from ..model.deger import Hata
from ..model.gosterim import goster, sayiyi_sigdir  # noqa: F401  (testler grid.goster'i de kullanır)
from ..model import sayi_bicimi
from ..model.sayi_bicimi import BicimSonucu
from ..model import doldur as doldurma
from ..model.stil import VARSAYILAN, Stil, StilYama
from ..model.komutlar import (
    BicimDegis, BicimPlani, BirlesimDegis, GeriAlYigini, Grup, DogrulamaDegis, HucreTasi, HucrelerDegis, KosulluDegis, NotlarDegis, OlcuDegis, bicim_komutu, birlesim_komutu, birlesim_veri_kaybi,
    SatirEkleSil, SutunEkleSil,
)
from ..model import olcu, pano
from ..model.notlar import Not, varsayilan_yazar
from ..model.bicim_islem import boyaci_stilleri
from ..model.sayfa import Hucre, Sayfa
from . import theme
from .grid_nesne_etkilesim import NesneEtkilesimi
from .grid_nesneler import NesneKatmani
from .renkli import renkli_ciz

VARSAYILAN_DOGRULAMA_IL = "Bu değer, bu hücre için tanımlanan veri doğrulama kısıtlamalarıyla eşleşmiyor."
FILTRE_MAVISI = "#0563C1"        # filtreli listede satır numaraları (Excel)
VARSAYILAN_PUNTO = 11.0     # `Stil.boyut` bu değere göre ölçeklenir (Excel varsayılanı 11 punto)
_YATAY_BAYRAK = {"genel": Qt.AlignLeft, "sol": Qt.AlignLeft, "doldur": Qt.AlignLeft,
                 "iki_yana": Qt.AlignLeft, "orta": Qt.AlignHCenter,
                 "secim_ortasi": Qt.AlignHCenter, "sag": Qt.AlignRight}
_HIZA_BAYRAK = {"sol": Qt.AlignLeft, "orta": Qt.AlignHCenter, "sag": Qt.AlignRight}
_CIZGI_KALINLIK = {"ince": 1, "orta": 2, "kalin": 3, "kesikli": 1, "noktali": 1, "cift": 3, "sac": 1}


class _Sar:
    """Kaydırılmış (sarılmış) metnin yerleşimi: `QTextLayout` + toplam yükseklik (piksel)."""
    __slots__ = ("layout", "h")

    def __init__(self, layout, h: int):
        self.layout, self.h = layout, h


class _FontGirdisi:
    """Bir stilin yazı tipi + ölçüm/çizim önbellekleri (metin genişliği, QStaticText, sığdırılmış sayı)."""
    __slots__ = ("font", "olcer", "yukseklik", "gen", "statik", "sayilar", "dolgu", "kenarli", "sar", "sar_h")

    def __init__(self, font: QFont, stil: Stil):
        self.dolgu = stil.dolgu                       # hücre dolgusu / kenarlığı var mı (her çizimde sorulmasın)
        self.kenarli = not stil.kenar.bos_mu()
        self.font = font
        self.olcer = QFontMetrics(font)
        self.yukseklik = self.olcer.height()
        self.gen: Dict[str, int] = {}
        self.statik: Dict[str, QStaticText] = {}
        self.sayilar: Dict[tuple, tuple] = {}
        self.sar: Dict[tuple, _Sar] = {}              # (metin, genişlik, hizalama) → sarılmış yerleşim (çizim)
        self.sar_h: Dict[tuple, int] = {}             # aynı anahtar → yalnız yükseklik (otomatik satır yüksekliği)


class _Duzenleyici(QLineEdit):
    """Hücre üstünde satır içi düzenleme kutusu.

    `yazma_modu` (doğrudan yazarak başlandı): oklar onaylayıp hücre değiştirir.
    F2/çift tık modunda oklar kutu içinde imleci gezdirir (Excel'in Düzenle modu).
    """
    bitir = Signal(bool, int, int)   # onayla, satır farkı, sütun farkı
    okIsaret = Signal(int, int, bool)   # işaret modunda ok tuşu: satır farkı, sütun farkı, Shift
    modDegisti = Signal(str)            # F2: Gir ⇄ Düzenle

    def __init__(self, parent, yazma_modu: bool):
        super().__init__(parent)
        self.yazma_modu = yazma_modu
        self.isaret_denetimi = None      # () -> bool: şu an başvuru işaretlenebilir mi (ızgara verir)
        self.ad_saglayici = None         # () -> List[str]: öneri listesine eklenecek tanımlı adlar (ızgara verir)
        self._ad_kumesi = frozenset()    # son öneri listesindeki tanımlı adlar (kabulde "(" eklenmez)
        self._bitti = False
        self.setFrame(False)
        self._oneri_bas = 0              # önerinin değiştireceği metnin başlangıcı
        self._liste = QListWidget(parent)    # fonksiyon adı önerileri (odak almaz)
        self._liste.setFocusPolicy(Qt.NoFocus)
        self._liste.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._liste.hide()
        self.textChanged.connect(self._oneri_guncelle)
        self.destroyed.connect(self._liste.deleteLater)

    def paintEvent(self, olay):
        super().paintEvent(olay)
        renkli_ciz(self)

    # --- otomatik tamamlama / ipucu ---
    def oneri_acik(self) -> bool:
        return self._liste.isVisible()

    def _oneri_guncelle(self, _=None) -> None:
        self._liste.hide()
        QToolTip.hideText()
        if self._bitti or not self.text().startswith("="):
            return
        imlec = self.cursorPosition()
        ad = isaretleme.ad_oneki(self.text(), imlec)
        adlar = self.ad_saglayici() if (ad and self.ad_saglayici is not None) else ()
        liste = isaretleme.oneriler(ad[1], tanimli_adlar=adlar) if ad else []
        self._ad_kumesi = frozenset(a for a in liste if a in adlar)
        if ad and liste and not (len(liste) == 1 and liste[0].casefold() == ad[1].casefold()):
            self._oneri_bas = ad[0]
            self._liste.clear()
            self._liste.addItems(liste)
            self._liste.setCurrentRow(0)
            self.liste_konumla()
            self._liste.show()
            self._liste.raise_()
            return
        ipucu = isaretleme.ipucu(self.text(), imlec)
        if ipucu:
            QToolTip.showText(self.mapToGlobal(self.rect().bottomLeft()), ipucu, self)

    def liste_konumla(self) -> None:
        satir_y = self.fontMetrics().height() + 6
        self._liste.setGeometry(self.x(), self.y() + self.height(), max(self.width(), 160),
                                min(self._liste.count(), 8) * satir_y + 4)

    def oneri_kabul(self) -> None:
        oge = self._liste.currentItem()
        if oge is None:
            return
        imlec = self.cursorPosition()
        metin = self.text()
        yeni = oge.text() + ("" if oge.text() in self._ad_kumesi else "(")
        self._liste.hide()
        self.setText(metin[:self._oneri_bas] + yeni + metin[imlec:])
        self.setCursorPosition(self._oneri_bas + len(yeni))

    def _son(self, onayla: bool, dr: int = 0, dc: int = 0):
        if not self._bitti:
            self._bitti = True
            self._liste.hide()
            QToolTip.hideText()
            self.bitir.emit(onayla, dr, dc)

    def event(self, olay):
        # Tab/Shift+Tab Qt'de odak gezintisi olarak keyPressEvent'ten önce yakalanır
        if olay.type() == QEvent.KeyPress and olay.key() in (Qt.Key_Tab, Qt.Key_Backtab):
            self.keyPressEvent(olay)
            return True
        return super().event(olay)

    def keyPressEvent(self, olay):
        k, shift = olay.key(), bool(olay.modifiers() & Qt.ShiftModifier)
        if self._liste.isVisible():                  # öneri listesi açıkken
            if k in (Qt.Key_Down, Qt.Key_Up):
                n = self._liste.count()
                self._liste.setCurrentRow((self._liste.currentRow() + (1 if k == Qt.Key_Down else -1)) % n)
                return
            if k in (Qt.Key_Tab, Qt.Key_Backtab):
                self.oneri_kabul()
                return
            if k == Qt.Key_Escape:
                self._liste.hide()
                return
        if k in (Qt.Key_Return, Qt.Key_Enter) and olay.modifiers() & Qt.AltModifier:
            self.insert("\n")             # Alt+Enter: hücre içinde yeni satır
        elif k in (Qt.Key_Return, Qt.Key_Enter) and olay.modifiers() & Qt.ControlModifier:
            self.tum_secim = True                  # Ctrl+Enter: girdi tüm seçime yazılır
            self._son(True, 0, 0)
        elif k in (Qt.Key_Return, Qt.Key_Enter):
            self._son(True, -1 if shift else 1, 0)
        elif k in (Qt.Key_Tab, Qt.Key_Backtab):
            self._son(True, 0, -1 if (k == Qt.Key_Backtab or shift) else 1)
        elif k == Qt.Key_Escape:
            self._son(False)
        elif k == Qt.Key_F4:
            yeni, imlec = isaretleme.f4(self.text(), self.cursorPosition())
            if yeni != self.text():
                self.setText(yeni)
                self.setCursorPosition(imlec)
        elif k == Qt.Key_F2 and self.text().startswith("="):
            self.yazma_modu = not self.yazma_modu
            self.modDegisti.emit("Gir" if self.yazma_modu else "Düzenle")
        elif self.yazma_modu and k in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right):
            d = {Qt.Key_Up: (-1, 0), Qt.Key_Down: (1, 0),
                 Qt.Key_Left: (0, -1), Qt.Key_Right: (0, 1)}[k]
            if self.isaret_denetimi is not None and self.isaret_denetimi():
                self.okIsaret.emit(d[0], d[1], shift)
            else:
                self._son(True, *d)
        else:
            super().keyPressEvent(olay)

    def focusOutEvent(self, olay):
        super().focusOutEvent(olay)
        neden = olay.reason()
        if neden in (Qt.ActiveWindowFocusReason, Qt.PopupFocusReason):
            return                        # pencere dışına geçiş / menü: onaylama, açık bırak (Excel gibi)
        if neden == Qt.MouseFocusReason and self.isaret_denetimi is not None and self.isaret_denetimi():
            return                        # hücreye tıklama başvuru işaretler; ızgara odağı geri verir
        self._son(True)


class _NotDuzenleyici(QPlainTextEdit):
    """Not düzenleme kutusu (açık sarı, ince siyah çerçeve): odak kaybında kaydeder, Esc vazgeçer."""
    bitti = Signal(object)          # str (kaydet) | None (vazgeç)

    def __init__(self, parent):
        super().__init__(parent)
        self.setStyleSheet("QPlainTextEdit{background:#FFFFE1;color:#000;border:1px solid #000;}")
        self._bitti = False

    def _bitir(self, metin) -> None:
        if not self._bitti:
            self._bitti = True
            self.bitti.emit(metin)

    def keyPressEvent(self, olay):
        if olay.key() == Qt.Key_Escape:
            self._bitir(None)
            return
        super().keyPressEvent(olay)

    def focusOutEvent(self, olay):
        super().focusOutEvent(olay)
        self._bitir(self.toPlainText())


class Izgara(NesneEtkilesimi, NesneKatmani, QAbstractScrollArea):
    aktifDegisti = Signal(int, int)       # satır, sütun
    secimDegisti = Signal(object)         # Aralik
    degisti = Signal()                    # içerik değişti (düzenleme, silme, geri al)
    modDegisti = Signal(str)              # 'Hazır' | 'Gir' | 'Düzenle'
    duzenlemeMetniDegisti = Signal(str)   # hücre içi düzenleyicideki metin (formül çubuğu aynalar)
    suruklemeBitti = Signal()
    boyaciDegisti = Signal(bool)          # biçim boyacısı açıldı (True) / bitti (False)
    gecmisIslemi = Signal(bool)           # geri al/yinele başladı (True) / bitti (False)
    yakinlastirmaDegisti = Signal(float)
    uyari = Signal(str)                   # kullanıcıya gösterilecek iletiler
    nesneSecimiDegisti = Signal(int)      # seçili yüzen nesnenin kimliği (0 = seçim yok)
    nesneAyarIstendi = Signal(int, str)   # nesne kimliği, istek: 'ayarlar' | 'veri' | 'tur' (pencereyi pencere açar)
    filtreDugmesi = Signal(int)           # filtre açılır düğmesine tıklandı / Alt+Aşağı (mutlak sütun)
    uzakOnay = Signal()                   # devredilen (başka sayfadan) formül düzenlemesi sürerken işaret dışı tıklama

    TOPLU_SINIR = 20000                   # tek işlemde en çok satır/sütun (gizle, boyutlandır)
    MIME_HUCRELER = "application/x-tabcel-hucreler"
    MIME_JETON = "application/x-tabcel-jeton"
    _OTURUM = uuid.uuid4().hex            # bu uygulama oturumu (sayfa kimlikleri yalnız burada geçerli)
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
        self._boyaci: Optional[dict] = None     # biçim boyacısı: {"kaynak": Aralik, "kalici": bool}
        self.yigin = yigin if yigin is not None else GeriAlYigini()
        self._duzenleyici: Optional[_Duzenleyici] = None
        self._duzenlenen = (1, 1)
        self._isaret: Optional[Tuple[int, int]] = None      # son işaretlenen başvurunun metin aralığı
        self._isaret_capa: Optional[Tuple[int, int]] = None  # işaret aralığının sabit / hareketli ucu
        self._isaret_ucu: Optional[Tuple[int, int]] = None
        self._isaret_yaziyor = False
        self._oto: Dict[int, int] = {}                       # satır → otomatik yükseklik (piksel, yakınlaştırılmış)
        self._oto_ok = False                                 # otomatik yükseklikler güncel mi
        self._doldur: Optional[dict] = None                # doldurma tutamacı sürüklemesi: {kaynak, hedef}
        self.veri_kaybi_onayi = None                       # () -> bool: birleştirme veri silecekse pencere sorar
        self.uzak_sayfa: Optional[Sayfa] = None            # formül başka sayfadan yazılıyorsa asıl sayfa
        self.dis_duzenleyici: Optional[QLineEdit] = None   # formül çubuğu (pencere verir): aynı işaretleme modu
        self._ekler: List[Aralik] = []         # Ctrl ile eklenen önceki aralıklar (birincil aralık hariç)
        self._koru = False                      # fare düğmesi basılıyken çoklu seçim korunur
        self._font_onb: Dict[int, _FontGirdisi] = {}    # stil kimliği → yazı tipi + metin önbellekleri
        self._bicim_onb: Dict[tuple, BicimSonucu] = {}  # (değer, sayı biçimi kodu) → biçimlenmiş sonuç
        self._renk_onb: Dict[str, QColor] = {}
        self._baslik_onb: Dict[str, QStaticText] = {}   # satır/sütun başlığı metinleri
        self._stilli: list = []                     # son yerleşimde dolgu/kenarlıklı görünen hücreler
        self._cubuklar: list = []                   # son yerleşimde veri çubuklu hücreler [(x, y, g, h, çubuk)]
        self._kosullu: Optional[KosulluHesap] = None  # koşullu biçim değerlendirmesi (olayda geçersiz kılınır)
        self._onbellek_anahtari = None
        self._dikey_son = 0                         # artımlı kaydırma için önceki dikey kaydırma değeri
        self._yatay_son = 0                         # ... yatay kaydırma değeri
        self._boyut: Optional[dict] = None     # kenardan boyutlandırma durumu
        self._not_adayi: Optional[Tuple[int, int]] = None    # fare üstündeki notlu hücre
        self._not_kutusu: Optional[QLabel] = None            # fare üstü not kutusu (salt okunur)
        self._not_duzen: Optional[_NotDuzenleyici] = None    # Shift+F2 not düzenleyici
        self._not_duzen_hucre: Tuple[int, int] = (1, 1)
        self.dogrulama_soru = None                           # (Dogrulama) -> 'devam' | 'tekrar' | 'iptal' (testler yamalar)
        self._giris_etiketi: Optional[QLabel] = None         # veri doğrulama giriş iletisi (sarı ipucu kutusu)
        self._liste_acik: Optional[QListWidget] = None       # açılır liste penceresi
        self._not_zamani = QTimer(self)
        self._not_zamani.setSingleShot(True)
        self._not_zamani.setInterval(400)
        self._not_zamani.timeout.connect(self._not_goster)
        self.setFocusPolicy(Qt.StrongFocus)
        self.viewport().setMouseTracking(True)
        self.horizontalScrollBar().setRange(0, MAX_COL - 1)
        self.verticalScrollBar().setRange(0, MAX_ROW - 1)
        self._dondur_uygula()
        self.aktifDegisti.connect(lambda *_: self._giris_iletisi_guncelle())
        self._nesne_kur()                                    # Faz 6: yüzen nesne katmanı
        self._sayfa_sonlari_kur()                            # T9: sayfa sınırı çizgileri
        self._etkilesim_kur()
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

    def yazdirma_yuksekligi(self, satir: int) -> float:
        """Satır yüksekliği, 100% piksel (içeriğe göre otomatik uzayan satırlar dahil); gizli satır 0."""
        h = self.sayfa.yukseklik(satir)
        if not h:
            return 0.0
        if not self._oto_ok:
            self._oto_hesapla()
        if self._oto and satir not in self.sayfa.satir_yukseklik:
            o = self._oto.get(satir)
            if o:
                return o / self.yakinlastirma
        return float(h)

    def _yuk(self, satir: int) -> int:
        h = self.sayfa.yukseklik(satir)
        if not h:
            return 0
        if not self._oto_ok:
            self._oto_hesapla()
        if self._oto and satir not in self.sayfa.satir_yukseklik:
            o = self._oto.get(satir)
            if o:
                return o                        # elle ayarlanmamış satır içeriğe göre uzar (Excel)
        return self._z(h)

    def _oto_gecersiz(self) -> None:
        """İçerik/biçim/genişlik/yakınlaştırma değişti: otomatik satır yükseklikleri bir sonraki
        kullanımda yeniden hesaplanır."""
        self._oto_ok = False

    _SAR_SINIRI = 4000              # çizim yerleşim önbelleğinde en çok girdi (QTextLayout ağırdır)
    _SAR_H_SINIRI = 200000

    def _sar(self, fe: "_FontGirdisi", metin: str, genislik: int, hiza, yalniz_yukseklik: bool = False) -> _Sar:
        """Metni `genislik` pikselde sarar (kelime sınırında, uzun kelime gerekirse her yerde; \n satır sonu).
        `yalniz_yukseklik`: yalnız yükseklik gerekir (otomatik satır yüksekliği) — yerleşim saklanmaz, yalnız
        tamsayı yükseklik önbelleğe girer; sayfadaki tüm kaydırılmış hücreler için layout biriktirmez."""
        anahtar = (metin, genislik, int(hiza.value) if hasattr(hiza, "value") else int(hiza))
        sar = fe.sar.get(anahtar)
        if sar is None and yalniz_yukseklik:
            h = fe.sar_h.get(anahtar)
            if h is not None:
                return _Sar(None, h)
        if sar is None:
            lay = QTextLayout(metin.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\u2028"), fe.font)
            opt = QTextOption()
            opt.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
            opt.setAlignment(hiza)
            lay.setTextOption(opt)
            lay.beginLayout()
            y = 0.0
            while True:
                satir = lay.createLine()
                if not satir.isValid():
                    break
                satir.setLineWidth(max(1, genislik))
                satir.setPosition(QPointF(0, y))
                y += satir.height()
            lay.endLayout()
            sar = _Sar(lay, int(math.ceil(y)))
            if yalniz_yukseklik:
                if len(fe.sar_h) > self._SAR_H_SINIRI:
                    fe.sar_h.clear()
                fe.sar_h[anahtar] = sar.h
            else:
                if len(fe.sar) > self._SAR_SINIRI:
                    fe.sar.clear()
                fe.sar[anahtar] = sar
        return sar

    def _oto_hesapla(self) -> None:
        """Elle yüksekliği ayarlanmamış satırların içeriğe göre yüksekliği: metni kaydır açık hücrelerin
        sarılmış metni ve büyük yazı boyutlu (biçimli) hücreler. Birleşik hücreler katılmaz."""
        self._oto_ok = True                      # (yinelemeyi önle)
        sayfa = self.sayfa
        havuz = sayfa.havuz
        stiller = havuz._stiller
        sar_k = {k for k, st in enumerate(stiller) if st.kaydir}
        buyuk_k = {k for k, st in enumerate(stiller) if st.boyut and st.boyut > VARSAYILAN_PUNTO}
        oto: Dict[int, int] = {}
        if sar_k or buyuk_k:
            self._onbellek_hazirla()
            ek = self._z(4)
            manuel, gizli = sayfa.satir_yukseklik, sayfa.gizli_satir
            ham, satir_stil, sutun_stil = sayfa._stil.get, sayfa.satir_stil.get, sayfa.sutun_stil.get
            bir = sayfa._birlesim_idx
            girinti_px = self._z(9)
            pad = self._z(4)
            yatay_bayrak = _YATAY_BAYRAK
            if buyuk_k:
                for (r, c), k in sayfa._stil.items():
                    if k in buyuk_k and r not in manuel and r not in gizli:
                        gerek = self._font_girdisi(k, havuz.stil(k)).yukseklik + ek
                        if gerek > oto.get(r, 0):
                            oto[r] = gerek
            if sar_k:
                for (r, c), h in sayfa._hucreler.items():
                    if r in manuel or r in gizli:
                        continue
                    k = ham((r, c))
                    if k is None:
                        k = satir_stil(r)
                        if k is None:
                            k = sutun_stil(c, 0)
                    if k not in sar_k or (bir and (r, c) in bir):
                        continue
                    v = h.deger if h.formul is None else sayfa._sonuc.get((r, c))
                    g = self._gen(c)
                    if not isinstance(v, str) or not g:
                        continue
                    stil = havuz.stil(k)
                    fe = self._font_girdisi(k, stil)
                    kod = stil.sayi_bicimi
                    metin = v if kod == "General" else self._bicimle(v, kod).metin
                    bayrak = yatay_bayrak.get(stil.yatay, Qt.AlignLeft)
                    ind = stil.girinti * girinti_px if (stil.girinti and bayrak != Qt.AlignHCenter) else 0
                    sar = self._sar(fe, metin, g - 2 * pad - ind, bayrak, True)
                    gerek = sar.h + ek
                    if gerek > oto.get(r, 0):
                        oto[r] = gerek
            ust = self._z(olcu.MAX_YUKSEKLIK_PX)
            alt = self._z(Sayfa.VARSAYILAN_SATIR_YUKSEKLIGI)
            oto = {r: min(v, ust) for r, v in oto.items() if v > alt}
        self._oto = oto

    @property
    def ilk_satir(self) -> int:
        return self.verticalScrollBar().value() + 1

    @property
    def ilk_sutun(self) -> int:
        return self.horizontalScrollBar().value() + 1

    @property
    def _kayan_ilk_sutun(self) -> int:
        """Kaydırılabilir bölgenin ilk sütunu (dondurma yoksa 1)."""
        d = self.sayfa.dondur
        return d[1] if d else 1

    @property
    def _kayan_ilk_satir(self) -> int:
        d = self.sayfa.dondur
        return d[0] if d else 1

    def _gorunen_sutunlar(self) -> Iterator[Tuple[int, int, int]]:
        """(sütun, x, genişlik) — önce dondurulmuş sütunlar, sonra kaydırılan bölge, viewport sağına kadar."""
        x, w = self._baslik_g(), self.viewport().width()
        kayan = self._kayan_ilk_sutun
        for c in range(1, kayan):
            g = self._gen(c)
            if g:
                yield c, x, g
                x += g
        c = max(self.ilk_sutun, kayan)
        while x < w and c <= MAX_COL:
            g = self._gen(c)
            if g:                       # gizli sütun atlanır
                yield c, x, g
                x += g
            c += 1

    def _gorunen_satirlar(self) -> Iterator[Tuple[int, int, int]]:
        y, h = self._baslik_y(), self.viewport().height()
        kayan = self._kayan_ilk_satir
        for r in range(1, kayan):
            yk = self._yuk(r)
            if yk:
                yield r, y, yk
                y += yk
        r = max(self.ilk_satir, kayan)
        while y < h and r <= MAX_ROW:
            yk = self._yuk(r)
            if yk:
                yield r, y, yk
                y += yk
            r += 1

    def _donuk_olcu(self) -> Tuple[int, int]:
        """Dondurulmuş bölmelerin (genişlik, yükseklik) pikseli; dondurma yoksa (0, 0)."""
        return (sum(self._gen(c) for c in range(1, self._kayan_ilk_sutun)),
                sum(self._yuk(r) for r in range(1, self._kayan_ilk_satir)))

    def _dondur_uygula(self) -> None:
        """Kaydırma çubuklarının alt sınırını dondurulmuş bölmeye göre ayarlar (kayan bölge oradan başlar)."""
        self.horizontalScrollBar().setMinimum(self._kayan_ilk_sutun - 1)
        self.verticalScrollBar().setMinimum(self._kayan_ilk_satir - 1)
        self._sayfa_adimlari()

    def dondur_ayarla(self, tur: str) -> bool:
        """`bolme` (etkin hücrenin üstü ve solu), `ust_satir`, `ilk_sutun`, `coz`. Dondurulan bölge pencereyi
        doldurursa reddedilir. Geri alınamaz (Excel gibi)."""
        r, c = self._aktif
        hedef = {"bolme": (r, c), "ust_satir": (2, 1), "ilk_sutun": (1, 2), "coz": None}.get(tur, "?")
        if hedef == "?":
            raise ValueError(f"Bilinmeyen dondurma türü: {tur!r}")
        if hedef is not None and hedef != (1, 1):
            gen = sum(self._gen(i) for i in range(1, hedef[1]))
            yuk = sum(self._yuk(i) for i in range(1, hedef[0]))
            vp = self.viewport()
            if gen > vp.width() - self._baslik_g() - 80 or yuk > vp.height() - self._baslik_y() - 60:
                self.uyari.emit("Dondurulacak bölme pencereyi dolduruyor; daha küçük bir bölge seçin.")
                return False
        self.sayfa.gorunum_yaz(dondur=hedef)
        self._dondur_uygula()
        hs, vs = self.horizontalScrollBar(), self.verticalScrollBar()
        hs.setValue(max(hs.value(), hs.minimum()))
        vs.setValue(max(vs.value(), vs.minimum()))
        self._yatay_son, self._dikey_son = hs.value(), vs.value()
        self._duzenleyici_yerlestir()
        self.viewport().update()
        return True

    def kilavuz_goster(self, goster: bool) -> None:
        if self.sayfa.gorunum_yaz(kilavuz=goster):
            self.viewport().update()

    # --- sayfa sınırı çizgileri (T9, t9_tasarim.md §4) ---
    _SB_ANINDA = ("yapi", "boyut", "bicim", "nesne", "sayfa", "yazdirma")   # yerleşimi hemen değiştirir
    _SB_ERTELI = ("hucre", "sonuc")                                         # yazarken: boşta kalınca yenilenir
    _SB_ERTELEME_MS = 300

    def _sayfa_sonlari_kur(self) -> None:
        self._sb = None                                      # (anahtar, SayfaSinirlari): olay gelince düşer
        self._sb_zamanlayici = QTimer(self)
        self._sb_zamanlayici.setSingleShot(True)
        self._sb_zamanlayici.setInterval(self._SB_ERTELEME_MS)
        self._sb_zamanlayici.timeout.connect(self._sb_yenile)
        kitap = self.sayfa.kitap
        if kitap is not None:
            birak = kitap.dinle(self._sb_olayi)
            self.destroyed.connect(lambda *_: birak())

    def _sb_olayi(self, olay) -> None:
        """Yalnız KENDİ sayfamızın olayları (başka sayfadaki düzenleme bu sayfanın sayfa yerleşimini değiştirmez;
        Opus bulgusu: eskiden her olay 100.000 satırda 0,18 sn'lik yeniden hesap başlatıyordu)."""
        if olay.sayfa is not self.sayfa:
            return
        if olay.tur in self._SB_ANINDA:
            self._sb = None
            if self.sayfa.sayfa_sonlari:
                self.viewport().update()
        elif olay.tur in self._SB_ERTELI:
            if self.sayfa.sayfa_sonlari:
                self._sb_zamanlayici.start()                 # eski sınırlar boşta kalınca (300 ms) yenilenir
            else:
                self._sb = None

    def _sb_yenile(self) -> None:
        self._sb = None
        self.viewport().update()

    def sayfa_sonlari_goster(self, goster: bool) -> None:
        if self.sayfa.gorunum_yaz(sayfa_sonlari=goster):
            self.viewport().update()

    def sayfa_sinirlari_ver(self):
        """Etkin sayfanın ekran sınırları (`sayfalama.sayfa_sinirlari`); yazdırma ile aynı bölme kodu ve aynı
        ölçüler (`yazdirma_yuksekligi`). Olay/ayar değişene dek önbellekte."""
        from ..model.sayfalama import sayfa_sinirlari
        anahtar = self.sayfa.sayfa_yapisi
        if self._sb is None or self._sb[0] != anahtar:
            sn = sayfa_sinirlari(self.sayfa, anahtar, lambda c: float(self.sayfa.genislik(c)),
                                 self.yazdirma_yuksekligi)
            self._sb = (anahtar, sn)
        return self._sb[1]

    def _sayfa_sonlarini_ciz(self, p: QPainter, sutunlar, satirlar, kirp: QRect) -> None:
        """Kesikli gri = otomatik, düz koyu = el ile; çizgi yeni sayfanın ilk satırının/sütununun ÖN kenarında,
        yazdırma alanı boyunca. Yalnız görünen satır/sütunlar taranır."""
        sn = self.sayfa_sinirlari_ver()
        if sn is None or not (sn.satirlar or sn.sutunlar):
            return
        alan = sn.alan
        xs = {c: (x, g) for c, x, g in sutunlar}
        ys = {r: (y, h) for r, y, h in satirlar}
        sol = sag = ust = alt = None
        gc, gr = sorted(xs), sorted(ys)                      # görünen sütun/satırlar: ikili aramayla alanın uçları
        i, j = bisect_left(gc, alan.ilk_sutun), bisect_right(gc, alan.son_sutun) - 1
        if i <= j:
            sol, sag = xs[gc[i]][0], xs[gc[j]][0] + xs[gc[j]][1]
        i, j = bisect_left(gr, alan.ilk_satir), bisect_right(gr, alan.son_satir) - 1
        if i <= j:
            ust, alt = ys[gr[i]][0], ys[gr[j]][0] + ys[gr[j]][1]
        p.save()
        p.setClipRect(kirp)
        for r, el_ile in sn.satirlar:
            if r in ys and sol is not None and sag is not None:
                p.setPen(self._sb_kalem(el_ile))
                y = ys[r][0] - 1
                p.drawLine(max(sol, self._baslik_g()), y, sag - 1, y)
        for c, el_ile in sn.sutunlar:
            if c in xs and ust is not None and alt is not None:
                p.setPen(self._sb_kalem(el_ile))
                x = xs[c][0] - 1
                p.drawLine(x, max(ust, self._baslik_y()), x, alt - 1)
        p.restore()

    @staticmethod
    def _sb_kalem(el_ile: bool) -> QPen:
        return QPen(QColor("#404040"), 1) if el_ile else QPen(QColor("#7f7f7f"), 1, Qt.DashLine)

    def hucre_dikdortgeni(self, satir: int, sutun: int) -> Optional[QRect]:
        """Hücrenin viewport içindeki dikdörtgeni; görünmüyorsa None. Birleşimin sol üst hücresi için
        birleşimin tamamı."""
        b = self.sayfa.birlesim(satir, sutun)
        if b is not None and (b.ilk_satir, b.ilk_sutun) == (satir, sutun):
            return self._birlesim_dikdortgeni(b)
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
        if self.sayfa.birlesimler:
            self._birlesime_uydur()
        if kaydir:
            self._gorunur_yap(self._uc if uc != self._aktif else self._aktif)
        self._secim_boya(eski_ekler + [eski_secim], eski_aktif)
        if self._aktif != eski_aktif:
            self.aktifDegisti.emit(*self._aktif)
        if self.secim != eski_secim or self._ekler != eski_ekler:
            self.secimDegisti.emit(self.secim)

    def _birlesime_uydur(self) -> None:
        """Birleşik hücreler tek hücre gibi seçilir (Excel): etkin hücre birleşimin sol üstüne gider,
        seçim kestiği tüm birleşimleri kapsayacak kadar genişler."""
        sayfa = self.sayfa
        tek = self._aktif == self._uc
        b = sayfa.birlesim(*self._aktif)
        if b is not None:
            self._aktif = (b.ilk_satir, b.ilk_sutun)
        (ar, ac), (ur, uc_) = self._aktif, self._uc
        r1, r2, c1, c2 = min(ar, ur), max(ar, ur), min(ac, uc_), max(ac, uc_)
        degisti = True
        while degisti:
            degisti = False
            for m in sayfa.birlesim_kesisen(Aralik(r1, c1, r2, c2)):
                if m.ilk_satir < r1 or m.son_satir > r2 or m.ilk_sutun < c1 or m.son_sutun > c2:
                    r1, r2 = min(r1, m.ilk_satir), max(r2, m.son_satir)
                    c1, c2 = min(c1, m.ilk_sutun), max(c2, m.son_sutun)
                    degisti = True
        if tek:
            self._uc = (r2, c2)                              # tek tıklama: birleşimin tamamı
        else:                                                # uç, genişleyen alanın yön korunan köşesi
            self._uc = (r2 if ur >= ar else r1, c2 if uc_ >= ac else c1)

    def _secim_boya(self, eski_aralik_listesi, eski_aktif) -> None:
        """Seçim değişince tüm viewport yerine yalnızca eski + yeni seçimin (ve ilgili başlıkların)
        kapladığı bölgeleri yeniden boyar."""
        sutunlar = list(self._gorunen_sutunlar())
        satirlar = list(self._gorunen_satirlar())
        vp = self.viewport()
        bg, bh = self._baslik_g(), self._baslik_y()
        if self._secim_farki_boya(sutunlar, satirlar, list(eski_aralik_listesi), eski_aktif):
            return
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

    def _secim_farki_boya(self, sutunlar, satirlar, eski, eski_aktif) -> bool:
        """Tek aralıklı seçim büyüyüp küçülürken yalnız FARK bölgesini (+ iki çerçevenin şeridi, başlıklar)
        boyar; ortak iç alan yeniden çizilmez (Shift+Ok'ta seçim büyüdükçe kare süresi artmasın).
        Uygun değilse (çoklu aralık, aktif hücre değişti, görünürde değil) False döner."""
        yeni = self.secimler
        if len(eski) != 1 or len(yeni) != 1 or eski_aktif != self._aktif:
            return False

        def kutu(a):
            xs = [(x, x + g) for c, x, g in sutunlar if a.ilk_sutun <= c <= a.son_sutun]
            ys = [(y, y + h) for r, y, h in satirlar if a.ilk_satir <= r <= a.son_satir]
            if not xs or not ys:
                return None
            return QRect(xs[0][0], ys[0][0], xs[-1][1] - xs[0][0], ys[-1][1] - ys[0][0])
        ra, rb = kutu(eski[0]), kutu(yeni[0])
        if ra is None or rb is None:
            return False
        bolge = QRegion(ra).xored(QRegion(rb))
        for r in (ra, rb):
            bolge = bolge.united(QRegion(r.adjusted(-3, -3, 3, 3)).subtracted(
                QRegion(r.adjusted(3, 3, -3, -3))))
        birlesik = ra.united(rb)
        bg, bh = self._baslik_g(), self._baslik_y()
        bolge = bolge.united(QRegion(QRect(birlesik.left(), 0, birlesik.width(), bh)))
        bolge = bolge.united(QRegion(QRect(0, birlesik.top(), bg, birlesik.height())))
        self.viewport().update(bolge)
        return True

    def _gorunur_yap(self, hedef: Tuple[int, int]) -> None:
        satir, sutun = hedef
        hs, vs = self.horizontalScrollBar(), self.verticalScrollBar()
        if sutun < self._kayan_ilk_sutun:
            pass                                          # dondurulmuş sütun her zaman görünür
        elif sutun < self.ilk_sutun:
            hs.setValue(sutun - 1)
        else:
            if sutun > self._son_gorunen_sutun() + 1:    # uzak hedef: tek seferde yaklaş
                hs.setValue(max(hs.value(), sutun - 1 - hs.pageStep()))
            while sutun > self.ilk_sutun and not self._sigiyor_mu(sutun, True):
                hs.setValue(hs.value() + 1)
        if satir < self._kayan_ilk_satir:
            pass
        elif satir < self.ilk_satir:
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
        anahtar = (self.yakinlastirma, self.font().key(), id(self.sayfa.havuz))
        buyuk = any(len(f.gen) > 60000 or len(f.sayilar) > 60000 for f in self._font_onb.values())
        if anahtar != self._onbellek_anahtari or buyuk or len(self._bicim_onb) > 60000:
            self._onbellek_anahtari = anahtar
            self._font_onb.clear()
            self._bicim_onb.clear()
            self._baslik_onb.clear()
            self._oto_ok = False

    def _font_girdisi(self, kimlik: int, stil: Stil) -> "_FontGirdisi":
        """Stil kimliğine göre yazı tipi + ölçüm/çizim önbellekleri (yakınlaştırma ve havuz değişince sıfırlanır)."""
        fe = self._font_onb.get(kimlik)
        if fe is None:
            f = self._yazi_tipi()
            if stil.yazi_tipi:
                f.setFamily(stil.yazi_tipi)
            if stil.boyut:                    # 11 punto = ızgaranın temel yazı boyutu (Excel varsayılanı)
                f.setPointSizeF(max(4.0, f.pointSizeF() * stil.boyut / VARSAYILAN_PUNTO))
            f.setBold(stil.kalin)
            f.setItalic(stil.italik)
            f.setUnderline(stil.alti_cizili != "yok")
            f.setStrikeOut(stil.ustu_cizili)
            fe = self._font_onb[kimlik] = _FontGirdisi(f, stil)
        return fe

    def _bicimle(self, deger, kod: str) -> BicimSonucu:
        """Sayı biçimi sonucu (değer, kod) başına önbellekli; geçersiz kod Genel gibi davranır."""
        anahtar = (deger, kod)
        s = self._bicim_onb.get(anahtar)
        if s is None:
            try:
                s = sayi_bicimi.bicimle(deger, kod)
            except (sayi_bicimi.BicimHatasi, ArithmeticError, OverflowError, ValueError):
                s = sayi_bicimi.bicimle(deger, "General")
            self._bicim_onb[anahtar] = s
        return s

    def _renk(self, renk: str) -> QColor:
        c = self._renk_onb.get(renk)
        if c is None:
            c = self._renk_onb[renk] = QColor(renk)
        return c

    def _yerlesim(self, sutunlar, satirlar, olcer, pad, kirp_x=None, _birlesim_ciz=False):
        """Görünen hücrelerin metin yerleşimi.

        Döner: (metinler, tasma). metinler: (kırpma dikdörtgeni, metin dikdörtgeni, hizalama, metin,
        metin genişliği px, (renk, yazı tipi girdisi, stil)); tasma: {(satır, sütun)} — sağındaki dikey
        çizgi taşan metin yüzünden çizilmeyecek hücreler. Yan ürün: `self._stilli` — dolgusu ya da
        kenarlığı olan görünen hücreler [(x, y, genişlik, yükseklik, Stil, yazı tipi girdisi)] (boş hücreler dahil).
        Kurallar (Excel): metin sola yaslı ve sığmıyorsa sağdaki BOŞ hücrelere taşar; sayı taşmaz,
        sığmıyorsa önce kısaltılır, olmazsa `####` olur; mantıksal değer ortalanır; hizalama, girinti ve
        sayı biçimi hücre stilinden gelir.
        `kirp_x=(x1, x2)` verilirse yalnız bu yatay aralığa değebilecek hücreler işlenir (artımlı çizim:
        solda kalan hücreler yalnız metinse, taşma ihtimali yüzünden).
        Ölçümler yazı tipi girdisinde önbelleğe alınır: aynı hücreler kaydırırken yeniden ölçülmez.
        """
        self._onbellek_hazirla()
        sayfa = self.sayfa
        hucre_al = sayfa.hucre
        sonuc_al = sayfa._sonuc.get
        havuz = sayfa.havuz
        ham_stil, satir_stil, sutun_stil = sayfa._stil.get, sayfa.satir_stil.get, sayfa.sutun_stil.get
        stilli_var = bool(sayfa._stil or sayfa.satir_stil or sayfa.sutun_stil)
        kosullu = self._kosullu_hesap()                          # kural yoksa None: ek maliyet tek denetim
        cubuklar = []
        self._cubuklar = cubuklar
        varsayilan_fe = self._font_girdisi(0, VARSAYILAN)
        girinti_px = self._z(9)
        x1, x2 = kirp_x if kirp_x else (None, None)
        sol, sag, orta = Qt.AlignLeft, Qt.AlignRight, Qt.AlignHCenter
        yatay_bayrak = _YATAY_BAYRAK
        metinler, tasma, stilli = [], set(), []
        self._stilli = stilli
        bir = sayfa._birlesim_idx if (sayfa.birlesimler and not _birlesim_ciz) else None
        donuk_son = (sayfa.dondur[1] - 1) if sayfa.dondur else 0     # taşan metin dondurma çizgisini geçmez
        for r, y, h in satirlar:
            for i, (c, x, g) in enumerate(sutunlar):
                if x2 is not None and x > x2:
                    break                                   # sağdakiler bölgeye değmez; taşma sağa gider
                if bir and (r, c) in bir:
                    continue                                # birleşik hücreyi `_birlesimleri_ciz` çizer
                hucre = hucre_al(r, c)
                if hucre is None:
                    v = None
                else:
                    v = hucre.deger if hucre.formul is None else sonuc_al((r, c))
                solda = x1 is not None and x + g <= x1
                if solda and not isinstance(v, str):
                    continue
                k = 0
                if stilli_var:
                    k = ham_stil((r, c))
                    if k is None:
                        k = satir_stil(r)
                        if k is None:
                            k = sutun_stil(c, 0)
                if kosullu is not None:
                    yama, cubuk = kosullu.hucre(r, c)
                    if yama is not None:
                        k = havuz.yama_uygula(k, yama)
                    if cubuk is not None and not solda and not _birlesim_ciz:
                        cubuklar.append((x, y, g, h, cubuk))
                        if cubuk[2]:
                            v = None                        # "yalnız çubuğu göster": metin çizilmez
                if k:
                    stil = havuz.stil(k)
                    fe = self._font_girdisi(k, stil)
                    if not solda and (fe.dolgu or fe.kenarli):
                        stilli.append((x, y, g, h, stil, fe))
                else:
                    stil = VARSAYILAN
                    fe = varsayilan_fe
                if v is None:
                    continue
                kod = stil.sayi_bicimi
                genel = kod == "General"
                yatay = stil.yatay
                ind = stil.girinti * girinti_px if stil.girinti else 0
                gen = fe.gen
                renk = None
                if isinstance(v, str) and stil.kaydir:
                    if genel:
                        ham_metin = v
                    else:
                        sb = self._bicimle(v, kod)
                        ham_metin, renk = sb.metin, sb.renk
                    bayrak = yatay_bayrak.get(yatay, sol)
                    kw = g - 2 * pad - (ind if bayrak != orta else 0)
                    kx = x + pad + (ind if bayrak == sol else 0)
                    kutu = QRect(kx, y, max(1, kw), h)
                    metinler.append((QRect(x, y, g - 1, h), kutu, bayrak,
                                     self._sar(fe, ham_metin, kutu.width(), bayrak), 0, (renk, fe, stil)))
                    continue
                if isinstance(v, str):
                    if genel:
                        # Alt+Enter ile girilen satır sonları kaydırma kapalıyken görünmez
                        metin = v.replace("\r", "").replace("\n", "") if ("\n" in v or "\r" in v) else v
                    else:
                        s = self._bicimle(v, kod)
                        metin, renk = s.metin, s.renk
                        if "\n" in metin or "\r" in metin:
                            metin = metin.replace("\r", "").replace("\n", "")
                    w = gen.get(metin)
                    if w is None:
                        w = gen[metin] = fe.olcer.horizontalAdvance(metin)
                    bayrak = yatay_bayrak.get(yatay, sol)
                    if bayrak == sol:
                        gerek = w + 2 * pad + ind
                        toplam, j = g, i
                        while (not stil.kaydir and toplam < gerek and j + 1 < len(sutunlar)
                               and sutunlar[j][0] != donuk_son):
                            c2, _, g2 = sutunlar[j + 1]
                            komsu = hucre_al(r, c2)
                            if (komsu is not None and not komsu.bos_mu()) or (bir and (r, c2) in bir):
                                break
                            tasma.add((r, sutunlar[j][0]))
                            toplam += g2
                            j += 1
                        if solda and x + toplam <= x1:
                            continue
                        kirpma = QRect(x, y, toplam - 1, h)
                        kutu = QRect(x + pad + ind, y, toplam - 2 * pad - ind, h)
                    elif bayrak == sag:
                        kirpma = QRect(x, y, g - 1, h)
                        kutu = QRect(x + pad, y, g - 2 * pad - ind, h)
                    else:
                        kirpma = QRect(x, y, g - 1, h)
                        kutu = QRect(x + pad, y, g - 2 * pad, h)
                elif isinstance(v, (bool, Hata)):           # mantıksal ve hata değerleri varsayılan ortalanır
                    metin = goster(v)
                    w = gen.get(metin)
                    if w is None:
                        w = gen[metin] = fe.olcer.horizontalAdvance(metin)
                    bayrak = yatay_bayrak.get(yatay, orta) if yatay != "genel" else orta
                    kirpma = QRect(x, y, g - 1, h)
                    kutu = QRect(x + pad, y, g - 2 * pad, h)
                else:
                    sigan = g - 2 * pad - ind
                    anahtar = (v, kod, sigan)
                    ek = fe.sayilar.get(anahtar)
                    if ek is None:
                        ek = fe.sayilar[anahtar] = self._sayi_metni(fe, v, kod, genel, sigan)
                    metin, renk, hiz = ek
                    w = gen.get(metin)
                    if w is None:
                        w = gen[metin] = fe.olcer.horizontalAdvance(metin)
                    bayrak = yatay_bayrak.get(yatay, sag) if yatay != "genel" else _HIZA_BAYRAK[hiz]
                    kirpma = QRect(x, y, g - 1, h)
                    kutu = QRect(x + pad, y, g - 2 * pad - ind, h)
                metinler.append((kirpma, kutu, bayrak, metin, w, (renk, fe, stil)))
        return metinler, tasma

    def _sayi_metni(self, fe: "_FontGirdisi", v: float, kod: str, genel: bool, sigan: int):
        """(görünen metin, renk, hizalama) — sütuna sığmayan sayı kısaltılır, olmazsa `####`."""
        gen = fe.gen
        ol = fe.olcer

        def sigar(t: str) -> bool:
            w = gen.get(t)
            if w is None:
                w = gen[t] = ol.horizontalAdvance(t)
            return w <= sigan
        renk, hiz = None, sayi_bicimi.SAG
        metin = None
        if genel:
            metin = sayiyi_sigdir(v, sigar)
        else:
            s = self._bicimle(v, kod)
            renk, hiz = s.renk, s.hizalama
            try:
                metin = None if s.diyez else sayi_bicimi.sigdir(v, kod, sigar)
            except (sayi_bicimi.BicimHatasi, ArithmeticError, OverflowError, ValueError):
                metin = sayiyi_sigdir(v, sigar)
        if metin is None:
            w = gen.get("#")
            if w is None:
                w = gen["#"] = ol.horizontalAdvance("#")
            metin = "#" * max(1, sigan // max(1, w))
        return metin, renk, hiz

    # --- koşullu biçim (5h) ---
    def _kosullu_hesap(self) -> Optional[KosulluHesap]:
        """Sayfada kural varsa değerlendirici (tembel kurulur); yoksa None."""
        if not self.sayfa.kosullu:
            self._kosullu = None
            return None
        if self._kosullu is None:
            self._kosullu = KosulluHesap(self.sayfa)
        return self._kosullu

    def _kosullu_gecersiz(self) -> None:
        """İçerik/sonuç/yapı/kural değişti: önbellek boşalır (bir sonraki çizimde yeniden kurulur)."""
        self._kosullu = None

    def _cubuk_ciz(self, p: QPainter, cubuklar, kirp: QRect) -> None:
        """Veri çubukları: hücrenin içinde 2 px iç boşlukla, soldan sağa uzar; gradyan renkten beyaza açılır."""
        ic = self._z(2)
        for x, y, g, h, (oran, renk, _yalniz, gradyan) in cubuklar:
            w, hh = round((g - 1 - 2 * ic) * oran), h - 1 - 2 * ic
            if w <= 0 or hh <= 0:
                continue
            kutu = QRect(x + ic, y + ic, w, hh)
            if not kutu.intersects(kirp):
                continue
            c1 = self._renk(renk)
            if gradyan:
                gr = QLinearGradient(kutu.left(), 0, kutu.right() + 1, 0)
                gr.setColorAt(0.0, c1)
                acik = QColor(c1)
                acik.setRed((c1.red() + 255 * 3) // 4)
                acik.setGreen((c1.green() + 255 * 3) // 4)
                acik.setBlue((c1.blue() + 255 * 3) // 4)
                gr.setColorAt(1.0, acik)
                p.fillRect(kutu, gr)
            else:
                p.fillRect(kutu, c1)

    def _dolgu_ciz(self, p: QPainter, stilli, kirp: QRect) -> None:
        for x, y, g, h, stil, fe in stilli:
            if fe.dolgu:
                alan = QRect(x, y, g, h)
                if alan.intersects(kirp):
                    p.fillRect(alan, self._renk(stil.dolgu))

    def _kenar_ciz(self, p: QPainter, stilli, kirp: QRect) -> None:
        """Hücre kenarlıkları. Komşu hücreler aynı kenarı farklı kalınlıkta isterse kalın olan kazanır
        (kalınlığa göre sıralı çizim). Sol/üst kenar komşunun sağ/alt çizgisi üstüne oturur."""
        parcalar = []
        for x, y, g, h, stil, fe in stilli:
            if not fe.kenarli or not QRect(x - 1, y - 1, g + 2, h + 2).intersects(kirp):
                continue
            k = stil.kenar
            sol_x, ust_y = x - 1, y - 1       # ilk satır/sütunda başlığın altında kalır (kaydırma geçmişinden bağımsız)
            sag_x, alt_y = x + g - 1, y + h - 1
            for yon, cizgi in (("ust", k.ust), ("alt", k.alt), ("sol", k.sol), ("sag", k.sag)):
                if not cizgi:
                    continue
                tur, renk = cizgi
                if yon == "ust":
                    seg = (sol_x, ust_y, sag_x, ust_y)
                elif yon == "alt":
                    seg = (sol_x, alt_y, sag_x, alt_y)
                elif yon == "sol":
                    seg = (sol_x, ust_y, sol_x, alt_y)
                else:
                    seg = (sag_x, ust_y, sag_x, alt_y)
                parcalar.append((_CIZGI_KALINLIK[tur], tur, renk, yon, seg))
        parcalar.sort(key=lambda t: t[0])
        for kalinlik, tur, renk, yon, (ax, ay, bx, by) in parcalar:
            renk = self._renk(renk)
            yatay = yon in ("ust", "alt")
            if tur == "cift":                   # iki ince çizgi, aralarında 1 piksel
                p.setPen(QPen(renk, 1))
                for d in (-1, 1):
                    if yatay:
                        p.drawLine(ax, ay + d, bx, by + d)
                    else:
                        p.drawLine(ax + d, ay, bx + d, by)
                continue
            kalem = QPen(renk, kalinlik)
            kalem.setCapStyle(Qt.FlatCap)
            if tur == "kesikli":
                kalem.setStyle(Qt.DashLine)
            elif tur == "noktali":
                kalem.setStyle(Qt.DotLine)
            elif tur == "sac":
                kalem.setDashPattern([1, 1])
            p.setPen(kalem)
            # yatay çizgi uçları köşelerde birleşsin diye bir piksel uzatılır
            if yatay:
                p.drawLine(ax, ay, bx + 1, by)
            else:
                p.drawLine(ax, ay, bx, by + 1)

    def paintEvent(self, olay):
        """Geçersiz bölgenin her dikdörtgeni ayrı boyanır: `olay.rect()` dikdörtgenlerin sınır kutusudur
        (ör. Ok tuşunda başlık şeritleri + hücre → neredeyse tüm ızgara); yalnız gerçek parçalar işlenir."""
        p = QPainter(self.viewport())
        try:
            for kirp in list(olay.region()):
                self._boya(p, kirp)
        finally:
            p.end()

    def _boya(self, p: QPainter, kirp: QRect) -> None:
        p.setClipRect(kirp)           # bölgenin her parçası kendi dikdörtgeniyle sınırlı (üst üste çizim olmasın)
        p.setFont(self._yazi_tipi())
        p.fillRect(kirp, QColor(theme.SURFACE))
        sutunlar = list(self._gorunen_sutunlar())
        tum_satirlar = list(self._gorunen_satirlar())
        # kalın kenarlıklar komşu satıra/sütuna 2 piksel taşar: bölgenin 3 piksel çevresindeki hücreler de işlenir
        satirlar = [s for s in tum_satirlar if s[1] <= kirp.bottom() + 3 and s[1] + s[2] > kirp.top() - 3]
        bg, bh = self._baslik_g(), self._baslik_y()
        sec = self.secim
        izgara = QPen(QColor(theme.GRID_LINE))
        sag = sutunlar[-1][1] + sutunlar[-1][2] if sutunlar else bg
        alt = tum_satirlar[-1][1] + tum_satirlar[-1][2] if tum_satirlar else bh

        # hücre içerikleri: önce yerleşim (taşma/####), sonra ızgara çizgileri, dolgu, kenarlık, metinler
        pad = self._z(4)
        olcer = p.fontMetrics()
        metinler, tasma = self._yerlesim(sutunlar, satirlar, olcer, pad, (kirp.left() - 3, kirp.right() + 3))

        p.setPen(izgara)
        y1, y2 = max(bh, kirp.top()), min(alt - 1, kirp.bottom())
        tasan_sutunlar = {c for _, c in tasma}
        sutunlar_k = [t for t in sutunlar if t[1] <= kirp.right() + 3 and t[1] + t[2] > kirp.left() - 3]
        if self.sayfa.kilavuz:
            for c, x, g in sutunlar_k:
                if c not in tasan_sutunlar:
                    p.drawLine(x + g - 1, y1, x + g - 1, y2)
                else:               # taşan metnin altındaki dikey çizgi çizilmez (Excel gibi)
                    for r, y, h in satirlar:
                        if (r, c) not in tasma:
                            p.drawLine(x + g - 1, y, x + g - 1, y + h - 1)
            for _, y, h in satirlar:
                p.drawLine(bg, y + h - 1, sag - 1, y + h - 1)

        if self._stilli:
            self._dolgu_ciz(p, self._stilli, kirp)
        if self._cubuklar:
            self._cubuk_ciz(p, self._cubuklar, kirp)
        if self._stilli:
            self._kenar_ciz(p, self._stilli, kirp)

        self._metinleri_ciz(p, metinler, kirp)
        if self.sayfa.birlesimler:
            self._birlesimleri_ciz(p, kirp, pad)
        if self.sayfa.sayfa_sonlari and sutunlar and tum_satirlar:      # birleşimin zemininin ÜSTÜNDE görünsün
            self._sayfa_sonlarini_ciz(p, sutunlar, tum_satirlar, kirp)
        if self.sayfa.notlar:
            self._not_uclari_ciz(p, sutunlar_k, satirlar)
        if self.sayfa.filtre is not None:
            self._filtre_dugmeleri_ciz(p, kirp)
        if self.sayfa.dogrulamalar:
            self._acilir_dugme_ciz(p, kirp)
        p.setFont(self._yazi_tipi())

        # seçim
        dolgu = QColor(theme.SELECTION_FILL)
        dolgu.setAlpha(36)
        tum = self.secimler
        bir = self.sayfa._birlesim_idx
        aktif_birlesim = self.sayfa.birlesim(*self._aktif)
        for a in tum:
            for c, x, g in sutunlar_k:
                if a.ilk_sutun <= c <= a.son_sutun:
                    for r, y, h in satirlar:
                        if (a.ilk_satir <= r <= a.son_satir and (r, c) != self._aktif
                                and not (bir and (r, c) in bir)):
                            p.fillRect(x, y, g - 1, h - 1, dolgu)
            if bir:
                for b in self.sayfa.birlesim_kesisen(a):
                    if b == aktif_birlesim:
                        continue                            # etkin birleşim Excel'de boyanmaz
                    dik = self._birlesim_dikdortgeni(b)
                    if dik is not None:
                        p.fillRect(dik.x(), dik.y(), dik.width() - 1, dik.height() - 1, dolgu)
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
        self._basvuru_vurgulari_ciz(p, sutunlar, tum_satirlar)
        if self._doldur and self._doldur["hedef"] is not None and sutunlar and tum_satirlar:
            k, h = self._doldur["kaynak"], self._doldur["hedef"]
            birlesik = Aralik(min(k.ilk_satir, h.ilk_satir), min(k.ilk_sutun, h.ilk_sutun),
                              max(k.son_satir, h.son_satir), max(k.son_sutun, h.son_sutun))
            self._secim_cercevesi(p, birlesik, sutunlar, tum_satirlar,
                                QPen(QColor(theme.TEXT), 1, Qt.DashLine), tek_hucre=True)
        tut = self._tutamac_dikdortgeni()
        if tut is not None and tut.intersects(kirp):
            p.fillRect(tut, QColor("#ffffff"))
            p.fillRect(tut.adjusted(1, 1, -1, -1), QColor(theme.ACCENT))

        if self.sayfa.nesneler:                 # grafik/resim: hücrelerin ve seçimin üstünde (faz6_tasarim.md §5)
            self._nesneleri_ciz(p, kirp)
        if self.sayfa.dondur:                   # dondurma çizgisi (Excel: koyu gri, ince)
            dg, dy = self._donuk_olcu()
            p.setPen(QPen(QColor("#7f7f7f"), 1))
            if dg:
                p.drawLine(bg + dg - 1, bh, bg + dg - 1, alt)
            if dy:
                p.drawLine(bg, bh + dy - 1, sag, bh + dy - 1)

        # başlıklar
        # (yalnızca açığa çıkan bölgeye değenler: artımlı kaydırmada sütun başlıkları yeniden çizilmez)
        p.setClipRect(kirp)
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
            for c, x, g in sutunlar_k:
                self._baslik_ciz(p, QRect(x, 0, g, bh), sutun_harfe(c),
                                 any(a.ilk_sutun <= c <= a.son_sutun for a in tum), izgara)
        fk = self.sayfa.filtre
        mavi = (fk.aralik.ilk_satir, fk.aralik.son_satir) if fk is not None and fk.kosullar else None
        if kirp.left() < bg:
            for r, y, h in satirlar:
                if y + h <= kirp.top() or y > kirp.bottom():
                    continue
                self._baslik_ciz(p, QRect(0, y, bg, h), str(r),
                                 any(a.ilk_satir <= r <= a.son_satir for a in tum), izgara,
                                 FILTRE_MAVISI if mavi and mavi[0] < r <= mavi[1] else None)

    def _not_uclari_ciz(self, p: QPainter, sutunlar, satirlar) -> None:
        """Notlu hücrenin sağ üst köşesinde kırmızı üçgen (Excel ~6 px); birleşimde tüm alanın köşesi."""
        xs = {c: (x, g) for c, x, g in sutunlar}
        ys = {r: (y, h) for r, y, h in satirlar}
        z = self._z(6)
        bir = self.sayfa._birlesim_idx
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#C00000"))
        for (r, c) in self.sayfa.notlar:
            b = bir.get((r, c)) if bir else None
            if b is not None:
                if (b.ilk_satir, b.ilk_sutun) != (r, c):
                    continue
                dik = self._birlesim_dikdortgeni(b)
                if dik is None:
                    continue
                sag, ust = dik.x() + dik.width() - 1, dik.y()
            else:
                a, d = xs.get(c), ys.get(r)
                if a is None or d is None or a[1] <= 1 or d[1] <= 1:
                    continue
                sag, ust = a[0] + a[1] - 1, d[0]
            p.drawPolygon(QPolygon([QPoint(sag - z, ust), QPoint(sag, ust), QPoint(sag, ust + z)]))
        p.setBrush(Qt.NoBrush)

    # --- filtre düğmeleri ---
    def _filtre_dugmesi_dikdortgeni(self, sutun: int) -> Optional[QRect]:
        """Filtre başlık hücresinin sağ altındaki açılır düğme (16×16, yakınlaştırmayla ölçeklenir)."""
        f = self.sayfa.filtre
        if f is None or not f.aralik.ilk_sutun <= sutun <= f.aralik.son_sutun:
            return None
        ar = self.hucre_dikdortgeni(f.aralik.ilk_satir, sutun)
        if ar is None:
            return None
        k = self._z(16)
        if ar.width() < k + 4 or ar.height() < k // 2:
            return None
        return QRect(ar.right() - k - 1, ar.bottom() - min(k, ar.height() - 2), k, min(k, ar.height() - 2))

    def _filtre_dugmeleri_ciz(self, p: QPainter, kirp: QRect) -> None:
        f = self.sayfa.filtre
        for c in range(f.aralik.ilk_sutun, f.aralik.son_sutun + 1):
            d = self._filtre_dugmesi_dikdortgeni(c)
            if d is None or not d.intersects(kirp):
                continue
            kosullu = c in f.kosullar
            p.setPen(QPen(QColor(FILTRE_MAVISI if kosullu else "#a6a6a6"), 1))
            p.setBrush(QColor("#dbe9f8" if kosullu else "#ffffff"))
            p.drawRect(d.adjusted(0, 0, -1, -1))
            ortax, ortay, w = d.center().x(), d.center().y(), self._z(3)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(FILTRE_MAVISI if kosullu else "#444444"))
            p.drawPolygon(QPolygon([QPoint(ortax - w - 1, ortay - 1), QPoint(ortax + w, ortay - 1),
                                    QPoint(ortax, ortay + w)]))
            if kosullu:                          # huni simgesi yerine alta ince çizgi: koşullu sütun
                p.setPen(QPen(QColor(FILTRE_MAVISI), 1))
                p.drawLine(ortax - w, ortay + w + 1, ortax + w - 1, ortay + w + 1)
        p.setBrush(Qt.NoBrush)

    def filtre_dugmesi_sutunu(self, p: QPoint) -> Optional[int]:
        f = self.sayfa.filtre
        if f is None:
            return None
        for c in range(f.aralik.ilk_sutun, f.aralik.son_sutun + 1):
            d = self._filtre_dugmesi_dikdortgeni(c)
            if d is not None and d.contains(p):
                return c
        return None

    # --- notlar ---
    def _not_gizle(self) -> None:
        self._not_zamani.stop()
        self._not_adayi = None
        if self._not_kutusu is not None:
            self._not_kutusu.hide()

    def _not_ipucu_guncelle(self, p: QPoint) -> None:
        """Fare notlu hücrede ~400 ms beklerse not kutusu açılır; başka yere gidince kapanır."""
        hedef = None
        if self.sayfa.notlar and self._not_duzen is None:
            satir, sutun = self._noktadan(p)
            if satir is not None and sutun is not None:
                b = self.sayfa.birlesim(satir, sutun)
                if b is not None:
                    satir, sutun = b.ilk_satir, b.ilk_sutun
                if (satir, sutun) in self.sayfa.notlar:
                    hedef = (satir, sutun)
        if hedef == self._not_adayi:
            return
        self._not_gizle()
        if hedef is not None:
            self._not_adayi = hedef
            self._not_zamani.start()

    def _not_goster(self) -> None:
        hedef = self._not_adayi
        n = self.sayfa.notlar.get(hedef) if hedef else None
        ar = self.hucre_dikdortgeni(*hedef) if hedef else None
        if n is None or ar is None:
            return
        if self._not_kutusu is None:
            k = QLabel(self.viewport())
            k.setWordWrap(True)
            k.setTextFormat(Qt.RichText)
            k.setAttribute(Qt.WA_TransparentForMouseEvents)
            k.setStyleSheet("QLabel{background:#FFFFE1;color:#000;border:1px solid #000;padding:3px;}")
            self._not_kutusu = k
        k = self._not_kutusu
        from html import escape
        govde = escape(n.metin).replace("\n", "<br>")
        k.setText((f"<b>{escape(n.yazar)}:</b><br>" if n.yazar else "") + govde)
        k.setFixedWidth(self._z(200))
        k.adjustSize()
        k.setFixedHeight(k.heightForWidth(k.width()) if k.hasHeightForWidth() else k.sizeHint().height())
        vp = self.viewport()
        x = min(ar.right() + self._z(8), max(0, vp.width() - k.width()))
        y = min(max(0, ar.top() - self._z(4)), max(0, vp.height() - k.height()))
        k.move(x, y)
        k.show()
        k.raise_()

    def leaveEvent(self, olay):
        self._not_gizle()
        super().leaveEvent(olay)

    def not_var_mi(self, hucre: Optional[Tuple[int, int]] = None) -> bool:
        return (hucre or self._aktif) in self.sayfa.notlar

    def not_duzenle(self) -> None:
        """Shift+F2: etkin hücrenin notunu düzenler (yoksa ekler). Kutu açık sarıdır; dışına tıklayınca
        kaydedilir, Esc vazgeçer; boş metin notu siler."""
        if self.duzenleniyor() or self._not_duzen is not None:
            return
        self._not_gizle()
        b = self.sayfa.birlesim(*self._aktif)
        hucre = (b.ilk_satir, b.ilk_sutun) if b is not None else self._aktif
        self._gorunur_yap(hucre)
        ar = self.hucre_dikdortgeni(*hucre)
        if ar is None:
            return
        vp = self.viewport()
        e = _NotDuzenleyici(vp)
        mevcut = self.sayfa.notlar.get(hucre)
        e.setPlainText(mevcut.metin if mevcut else "")
        e.setFixedSize(self._z(200), self._z(90))
        e.move(min(ar.right() + self._z(8), max(0, vp.width() - e.width())),
               min(max(0, ar.top() - self._z(4)), max(0, vp.height() - e.height())))
        e.bitti.connect(self._not_duzen_bitti)
        self._not_duzen, self._not_duzen_hucre = e, hucre
        e.show()
        e.setFocus()
        e.moveCursor(e.textCursor().MoveOperation.End)

    def _not_duzen_bitti(self, metin) -> None:
        e, self._not_duzen = self._not_duzen, None
        hucre = self._not_duzen_hucre
        if e is not None:
            e.hide()
            e.deleteLater()
        self.setFocus()
        if metin is None:
            return
        eski = self.sayfa.notlar.get(hucre)
        if eski is not None and eski.metin == metin:
            return
        yeni = Not(metin, eski.yazar if eski else varsayilan_yazar()) if metin != "" else None
        self.not_yaz({hucre: yeni})

    def not_yaz(self, yeni) -> bool:
        """Notları ekler/değiştirir/siler (`{hücre: Not | None}`); tek geri al adımı. Değişen yoksa False."""
        kmt = NotlarDegis(self.sayfa, yeni)
        if kmt.bos_mu():
            return False
        self.yigin.calistir(kmt)
        self._guncelle()
        return True

    def notu_sil(self) -> bool:
        """Seçimdeki hücrelerin notlarını siler (Excel: Notu Sil)."""
        yeni = {a: None for a in self.sayfa.notlar if any(aralik_icinde(s, *a) for s in self.secimler)}
        return self.not_yaz(yeni) if yeni else False

    def notlari_temizle(self) -> bool:
        """Temizle ▸ Notlar: seçimdeki notlar silinir, içerik/biçim kalır."""
        return self.notu_sil()

    def _metinleri_ciz(self, p: QPainter, metinler, kirp: QRect) -> None:
        """`_yerlesim` çıktısındaki metinleri çizer (bölge dışı olanlar atlanır)."""
        onceki = None
        varsayilan_renk = QColor(theme.TEXT)
        p.setPen(varsayilan_renk)
        kalem_renk = None                                # son ayarlanan yazı rengi (None = varsayılan)
        alt_pay = self._z(2)
        for kirp_k, kutu, bayrak, metin, w, (renk, fe, stil) in metinler:
            if not kirp_k.intersects(kirp):
                continue                                 # artımlı çizimde bölge dışı metin atlanır
            if fe is not onceki:
                p.setFont(fe.font)
                onceki = fe
            renk = renk or stil.yazi_rengi
            if renk != kalem_renk:
                p.setPen(self._renk(renk) if renk else varsayilan_renk)
                kalem_renk = renk
            if w == 0 and isinstance(metin, _Sar):               # kaydırılmış metin: satır satır
                if kutu.height() <= metin.h + 2 and stil.dikey != "alt":
                    ty = kutu.top() + 1 if stil.dikey == "ust" else kutu.top() + (kutu.height() - metin.h) // 2
                elif stil.dikey == "ust":
                    ty = kutu.top() + 1
                elif stil.dikey == "orta":
                    ty = kutu.top() + (kutu.height() - metin.h) // 2
                else:
                    ty = kutu.top() + kutu.height() - metin.h - alt_pay
                p.setClipRect(kirp_k.intersected(kirp))
                metin.layout.draw(p, QPointF(kutu.left(), ty))
                p.setClipRect(kirp)
                continue
            if bayrak == Qt.AlignRight:
                x = kutu.left() + kutu.width() - w
            elif bayrak == Qt.AlignHCenter:
                x = kutu.left() + (kutu.width() - w) // 2
            else:
                x = kutu.left()
            th = fe.yukseklik
            if kutu.height() <= th + 2 or stil.dikey == "orta":
                ty = kutu.top() + (kutu.height() - th) // 2
            elif stil.dikey == "ust":
                ty = kutu.top() + 1
            else:                                        # alt (Excel varsayılanı)
                ty = kutu.top() + kutu.height() - th - alt_pay
            sigmiyor = w > kutu.width()        # yalnızca sığmayan metinde (taşma sınırı) kırpılır
            if sigmiyor:
                p.setClipRect(kirp_k.intersected(kirp))
            st = fe.statik.get(metin)
            if st is None:
                st = fe.statik[metin] = QStaticText(metin)
                st.setTextFormat(Qt.PlainText)
                st.setPerformanceHint(QStaticText.AggressiveCaching)
            p.drawStaticText(x, ty, st)
            if stil.alti_cizili == "cift":               # ikinci alt çizgi (QFont yalnız tek çizgi bilir)
                p.drawLine(x, ty + th - 1, x + w, ty + th - 1)
            if sigmiyor:
                p.setClipRect(kirp)
        p.setFont(self._yazi_tipi())

    def _birlesim_dikdortgeni(self, b: Aralik) -> Optional[QRect]:
        """Birleşimin viewport koordinatlarındaki TAM dikdörtgeni (kısmen ekran dışında olabilir);
        hiç görünmüyorsa None. Gizli satır/sütunlar 0 genişlik sayılır."""
        kc, kr = self._kayan_ilk_sutun, self._kayan_ilk_satir
        ic, ir = max(self.ilk_sutun, kc), max(self.ilk_satir, kr)
        if (b.son_sutun < ic and b.ilk_sutun >= kc) or (b.son_satir < ir and b.ilk_satir >= kr):
            return None
        bg, bh = self._baslik_g(), self._baslik_y()
        donuk_g, donuk_y = self._donuk_olcu()
        if b.ilk_sutun < kc:
            x = bg + sum(self._gen(c) for c in range(1, b.ilk_sutun))
        elif b.ilk_sutun >= ic:
            x = bg + donuk_g + sum(self._gen(c) for c in range(ic, b.ilk_sutun))
        else:
            x = bg + donuk_g - sum(self._gen(c) for c in range(b.ilk_sutun, ic))
        if b.ilk_satir < kr:
            y = bh + sum(self._yuk(r) for r in range(1, b.ilk_satir))
        elif b.ilk_satir >= ir:
            y = bh + donuk_y + sum(self._yuk(r) for r in range(ir, b.ilk_satir))
        else:
            y = bh + donuk_y - sum(self._yuk(r) for r in range(b.ilk_satir, ir))
        w = sum(self._gen(c) for c in range(b.ilk_sutun, b.son_sutun + 1))
        h = sum(self._yuk(r) for r in range(b.ilk_satir, b.son_satir + 1))
        vp = self.viewport()
        if not w or not h or x >= vp.width() or y >= vp.height():
            return None
        return QRect(x, y, w, h)

    def _birlesimleri_ciz(self, p: QPainter, kirp: QRect, pad: int) -> None:
        """Birleşik hücreler: iç çizgileri örten zemin, sol üst hücrenin dolgusu/kenarlığı/metni tüm alanda.
        (`_yerlesim` birleşik hücreleri atlar; burada tek hücre gibi yerleştirilir.)"""
        sayfa, havuz = self.sayfa, self.sayfa.havuz
        for b in sayfa.birlesimler:
            dik = self._birlesim_dikdortgeni(b)
            if dik is None or not dik.adjusted(-3, -3, 3, 3).intersects(kirp):
                continue
            k = sayfa.stil_kimligi(b.ilk_satir, b.ilk_sutun)
            kh = self._kosullu_hesap()
            if kh is not None:
                yama = kh.hucre(b.ilk_satir, b.ilk_sutun)[0]
                if yama is not None:
                    k = havuz.yama_uygula(k, yama)
            stil = havuz.stil(k)
            fe = self._font_girdisi(k, stil)
            p.setClipRect(kirp)
            p.fillRect(QRect(dik.x(), dik.y(), dik.width() - 1, dik.height() - 1),
                       self._renk(stil.dolgu) if stil.dolgu else QColor(theme.SURFACE))
            if fe.kenarli:
                self._kenar_ciz(p, [(dik.x(), dik.y(), dik.width(), dik.height(), stil, fe)], kirp)
            eski_stilli, eski_cubuklar = self._stilli, self._cubuklar
            metinler, _ = self._yerlesim([(b.ilk_sutun, dik.x(), dik.width())],
                                         [(b.ilk_satir, dik.y(), dik.height())], p.fontMetrics(), pad,
                                         _birlesim_ciz=True)
            self._stilli, self._cubuklar = eski_stilli, eski_cubuklar
            p.setClipRect(kirp.intersected(dik.adjusted(0, 0, -1, -1)))
            self._metinleri_ciz(p, metinler, kirp.intersected(dik))
            p.setClipRect(kirp)

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

    def _baslik_ciz(self, p, ar: QRect, metin: str, secili: bool, izgara: QPen, renk: Optional[str] = None):
        if secili:
            p.fillRect(ar, QColor(theme.HEADER_BG_SELECTED))
        p.setPen(izgara)
        p.drawLine(ar.right(), ar.top(), ar.right(), ar.bottom())
        p.drawLine(ar.left(), ar.bottom(), ar.right(), ar.bottom())
        p.setPen(QColor(renk or (theme.HEADER_TEXT_SELECTED if secili else theme.HEADER_TEXT)))
        st = self._baslik_onb.get(metin)
        if st is None:
            st = self._baslik_onb[metin] = QStaticText(metin)
            st.setTextFormat(Qt.PlainText)
            st.setPerformanceHint(QStaticText.AggressiveCaching)
        boy = st.size()
        p.drawStaticText(ar.left() + round((ar.width() - boy.width()) / 2),
                         ar.top() + round((ar.height() - boy.height()) / 2), st)

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
        if self._isaret_modu():
            satir, sutun = self._noktadan(olay.position().toPoint())
            if satir is not None and sutun is not None:
                self._isaret_tikla(satir, sutun, bool(olay.modifiers() & Qt.ShiftModifier))
                return
        if self.uzak_sayfa is not None:        # devredilen düzenleme: işaret dışı tıklama onaylar
            self.uzakOnay.emit()
            return
        self.duzenlemeyi_bitir()
        if self.duzenleniyor():
            return                    # formül hatalıydı, düzenleme yeniden açıldı: tıklama yok sayılır
        nokta = olay.position().toPoint()
        if self._nesne_fare_bas(nokta):                      # yüzen nesne (grafik/resim) hücrelerin üstündedir
            return
        ad_ = self._acilir_dugme_dikdortgeni() if self.sayfa.dogrulamalar else None
        if ad_ is not None and ad_.contains(nokta):          # açılır liste oku: seçim değişmez
            self.acilir_liste_ac()
            return
        fc = self.filtre_dugmesi_sutunu(nokta)
        if fc is not None:                     # düğme alanına tıklama hücre seçimini değiştirmez
            self.filtreDugmesi.emit(fc)
            return
        if self._tutamacta_mi(nokta):
            self._surukleme = "doldur"
            self._doldur = {"kaynak": self.secim, "hedef": None}
            self.setFocus()
            return
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
            self._not_ipucu_guncelle(p)
            return
        if self._surukleme == "nesne":
            self._nesne_fare_hareket(p, bool(olay.modifiers() & Qt.ShiftModifier))
            return
        if self._surukleme == "boyut":
            self._boyut_surukle(p)
            return
        if self._surukleme == "doldur":
            self._doldur_surukle(p)
            return
        if not self._surukleme:
            return
        if self._surukleme == "isaret":
            satir, sutun = self._noktadan(QPoint(max(p.x(), self._baslik_g()), max(p.y(), self._baslik_y())))
            if satir and sutun and self._isaret is not None:
                self._isaret_ucu = (satir, sutun)
                self._isaret_yaz_secim()
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
        if self._surukleme == "nesne":
            self._nesne_fare_birak()
            self.suruklemeBitti.emit()
            return
        if self._surukleme == "boyut":
            self._boyut_bitir()
        elif self._surukleme == "doldur":
            self._doldur_bitir()
        elif self._surukleme in ("hucre", "satir", "sutun") and self._boyaci is not None:
            self._boyaci_uygula()
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
        self._oto_ok = False
        self._sayfa_adimlari()
        self._duzenleyici_yerlestir()
        self.viewport().update()
        self.yakinlastirmaDegisti.emit(oran)

    def wheelEvent(self, olay):
        self._not_gizle()
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
        if self._not_kutusu is not None and self._not_kutusu.isVisible():
            self._not_gizle()
        if self._secili_nesne is not None and self._nesne_klavye(olay):
            return                      # seçili grafik/resim: Delete, Esc, ok, Ctrl+C/X/V
        if k == Qt.Key_F2 and shift and not ctrl:
            self.not_duzenle()
            return
        if k == Qt.Key_Down and (m & Qt.AltModifier) and self.acilir_liste_ac():
            return
        f = self.sayfa.filtre
        if (k == Qt.Key_Down and (m & Qt.AltModifier) and f is not None and self._aktif[0] == f.aralik.ilk_satir
                and f.aralik.ilk_sutun <= self._aktif[1] <= f.aralik.son_sutun):
            self.filtreDugmesi.emit(self._aktif[1])          # Alt+Aşağı: başlık hücresinde listeyi açar
            return
        yon = {Qt.Key_Up: (-1, 0), Qt.Key_Down: (1, 0),
               Qt.Key_Left: (0, -1), Qt.Key_Right: (0, 1)}.get(k)
        sayfa_adimi = max(1, self.verticalScrollBar().pageStep())
        if yon:
            kaynak = self._uc if shift else self._aktif
            if ctrl:
                hedef = self._atla(kaynak, yon)
            else:
                kb = self._birlesim_kaynagi(kaynak, yon)
                hedef = self._gizlileri_atla((kb[0] + yon[0], kb[1] + yon[1]), yon) or kaynak
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
            kb = self._birlesim_kaynagi(self._aktif, yon)
            self.sec(self._gizlileri_atla((kb[0], kb[1] + yon[1]), yon) or self._aktif)
        elif k in (Qt.Key_Return, Qt.Key_Enter):
            yon = (-1 if shift else 1, 0)
            kb = self._birlesim_kaynagi(self._aktif, yon)
            self.sec(self._gizlileri_atla((kb[0] + yon[0], kb[1]), yon) or self._aktif)
        elif k == Qt.Key_F2:
            self.duzenle_baslat(None)
        elif k == Qt.Key_Delete and not shift:
            self.secimi_temizle()
        elif k == Qt.Key_Backspace:
            self.duzenle_baslat("")
        elif (m & Qt.AltModifier) and not ctrl and k == Qt.Key_Equal:
            self.otomatik_toplam()
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
        elif ctrl and not shift and k == Qt.Key_D:
            self.asagi_doldur()
        elif ctrl and not shift and k == Qt.Key_R:
            self.saga_doldur()
        elif ctrl and k == Qt.Key_C or (ctrl and k == Qt.Key_Insert):
            self.kopyala()
        elif ctrl and k == Qt.Key_X or (shift and k == Qt.Key_Delete):
            self.kes()
        elif ctrl and k == Qt.Key_V or (shift and k == Qt.Key_Insert):
            self.yapistir()
        elif k == Qt.Key_Escape:
            if self._boyaci is not None:
                self.boyaci_iptal()
            else:
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

    # --- doldurma ---
    def _tutamac_dikdortgeni(self) -> Optional[QRect]:
        """Seçimin sağ alt köşesindeki doldurma tutamacı (6×6); çoklu seçimde/düzenlerken yok."""
        if self._ekler or self._duzenleyici is not None or self._surukleme in ("boyut", "isaret"):
            return None
        sec = self.secim
        if sec.ilk_satir == 1 and sec.son_satir == MAX_ROW or sec.ilk_sutun == 1 and sec.son_sutun == MAX_COL:
            return None                                      # tüm sütun/satır seçiminde tutamaç anlamsız
        r = self.hucre_dikdortgeni(sec.son_satir, sec.son_sutun)
        if r is None:
            return None
        return QRect(r.x() + r.width() - 5, r.y() + r.height() - 5, 6, 6)

    def _tutamacta_mi(self, p: QPoint) -> bool:
        t = self._tutamac_dikdortgeni()
        return t is not None and t.adjusted(-2, -2, 2, 2).contains(p)

    def doldur(self, kaynak: Aralik, hedef: Aralik, seri: bool = True) -> bool:
        """Kaynak bölgeyi hedefe doldurur (seri ya da kopya); içerik + biçim tek geri al adımı."""
        if self.sayfa.birlesim_kesisen(hedef):
            self.uyari.emit("Birleşik hücrelerin bulunduğu alana doldurulamaz.")
            return False
        try:
            hucreler, stiller = (doldurma.seri_plani if seri else doldurma.kopya_plani)(
                self.sayfa, kaynak, hedef)
        except ValueError:
            return False
        self.yigin.calistir(Grup([HucrelerDegis(self.sayfa, hucreler),
                                  BicimDegis(self.sayfa, hucreler=stiller)]))
        birlesik = Aralik(min(kaynak.ilk_satir, hedef.ilk_satir), min(kaynak.ilk_sutun, hedef.ilk_sutun),
                          max(kaynak.son_satir, hedef.son_satir), max(kaynak.son_sutun, hedef.son_sutun))
        geri = hedef.ilk_satir < kaynak.ilk_satir or hedef.ilk_sutun < kaynak.ilk_sutun
        if geri:
            self.sec((birlesik.son_satir, birlesik.son_sutun), (birlesik.ilk_satir, birlesik.ilk_sutun))
        else:
            self.sec((birlesik.ilk_satir, birlesik.ilk_sutun), (birlesik.son_satir, birlesik.son_sutun))
        self._guncelle()
        return True

    def asagi_doldur(self) -> bool:
        """Ctrl+D: seçimin ilk satırı kalanına kopyalanır (tek satırda üstteki satır)."""
        return self._ctrl_dr(True)

    def saga_doldur(self) -> bool:
        """Ctrl+R: seçimin ilk sütunu kalanına kopyalanır (tek sütunda soldaki sütun)."""
        return self._ctrl_dr(False)

    def _ctrl_dr(self, dikey: bool) -> bool:
        if self._ekler:
            self.uyari.emit("Bu komut birden çok seçimde kullanılamaz.")
            return False
        sec = self.secim
        if sec.ilk_satir == 1 and sec.son_satir == MAX_ROW or sec.ilk_sutun == 1 and sec.son_sutun == MAX_COL:
            sec = pano.pano_araligi(self.sayfa, sec)         # tam satır/sütun: kullanılan alanla sınırla
        try:
            plan = doldurma.asagi_yukari_dolu_plani(self.sayfa, sec, dikey)
        except ValueError:
            return False
        if plan is None:
            return False
        hucreler, stiller = plan
        if any(self.sayfa.birlesim(r, c) for r, c in hucreler):
            self.uyari.emit("Birleşik hücrelerin bulunduğu alana doldurulamaz.")
            return False
        self.yigin.calistir(Grup([HucrelerDegis(self.sayfa, hucreler),
                                  BicimDegis(self.sayfa, hucreler=stiller)]))
        self._guncelle()
        return True

    def tutamac_cift_tik(self) -> bool:
        """Tutamağa çift tık: komşu sütundaki verinin sonuna kadar aşağı doldurur."""
        if self._ekler:
            return False
        sec = self.secim
        son = doldurma.bitisik_son_satir(self.sayfa, sec)
        if son is None:
            return False
        return self.doldur(sec, Aralik(sec.son_satir + 1, sec.ilk_sutun, son, sec.son_sutun))

    def _doldur_surukle(self, p: QPoint) -> None:
        satir, sutun = self._noktadan(QPoint(max(p.x(), self._baslik_g()), max(p.y(), self._baslik_y())))
        d = self._doldur
        if d is None or not satir or not sutun:
            return
        k = d["kaynak"]
        dr = satir - k.son_satir if satir > k.son_satir else (satir - k.ilk_satir if satir < k.ilk_satir else 0)
        dc = sutun - k.son_sutun if sutun > k.son_sutun else (sutun - k.ilk_sutun if sutun < k.ilk_sutun else 0)
        hedef = None
        if abs(dr) >= abs(dc) and dr:
            hedef = (Aralik(k.son_satir + 1, k.ilk_sutun, satir, k.son_sutun) if dr > 0
                     else Aralik(satir, k.ilk_sutun, k.ilk_satir - 1, k.son_sutun))
        elif dc:
            hedef = (Aralik(k.ilk_satir, k.son_sutun + 1, k.son_satir, sutun) if dc > 0
                     else Aralik(k.ilk_satir, sutun, k.son_satir, k.ilk_sutun - 1))
        if hedef != d["hedef"]:
            d["hedef"] = hedef
            self.viewport().update()

    def _doldur_bitir(self) -> None:
        d, self._doldur = self._doldur, None
        self.viewport().update()
        if d and d["hedef"] is not None:
            self.doldur(d["kaynak"], d["hedef"])

    def _birlesim_kaynagi(self, konum: Tuple[int, int], yon: Tuple[int, int]) -> Tuple[int, int]:
        """Birleşik hücreden `yon` yönünde adım atılırken başlangıç: birleşimin o yöndeki kenarı."""
        b = self.sayfa.birlesim(*konum)
        if b is None:
            return konum
        r, c = konum
        if yon[0]:
            r = b.son_satir if yon[0] > 0 else b.ilk_satir
        if yon[1]:
            c = b.son_sutun if yon[1] > 0 else b.ilk_sutun
        return r, c

    # --- pano ---
    def kopyala(self) -> None:
        if self._secili_nesne is not None:
            self.nesne_kopyala(False)
            return
        self._panoya_koy(kesilen=False)

    def kes(self) -> None:
        """Kes: hücreler yapıştırılana kadar yerinde kalır (Excel gibi), kesik çizgili çerçeveyle işaretlenir."""
        if self._secili_nesne is not None:
            self.nesne_kopyala(True)
            return
        self._panoya_koy(kesilen=True)

    def _panoya_koy(self, kesilen: bool) -> None:
        Izgara._nesne_panosu = None                          # hücre kopyası nesne kopyasının yerini alır
        if self._ekler:
            self.uyari.emit("Bu komut birden çok seçimde kullanılamaz.")
            return
        ar = pano.pano_araligi(self.sayfa, self.secim)
        veri = pano.pano_verisi_al(self.sayfa, ar)
        veri.oturum = Izgara._OTURUM
        for anahtar, h in veri.hucreler.items():
            if h.formul is not None:
                veri.en_formul[anahtar] = ceviri.disa(h.formul, self.sayfa.kitap)
        satirlar = pano.metin_satirlari(veri)
        jeton = uuid.uuid4().hex
        Izgara._pano_durumu = {"sayfa": self.sayfa, "aralik": ar, "kesildi": kesilen, "jeton": jeton}
        md = QMimeData()
        md.setText(pano.tsv_yaz(satirlar))
        md.setHtml(pano.html_yaz(satirlar, veri.stiller))
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
                veri = pano.PanoVerisi.json_oku(bytes(md.data(self.MIME_HUCRELER)).decode("utf-8"))
                if veri.oturum != Izgara._OTURUM:        # sayfa kimlikleri bu oturumda geçersiz
                    veri = self._baska_oturumdan(veri)
                return veri
            if md.hasHtml() and "<table" in md.html().lower():
                satirlar = pano.html_tablo_coz(md.html())
                if satirlar:
                    return pano.metinden_pano_verisi(satirlar, self._dis_girdi)
            if md.hasText() and md.text() != "":
                return pano.metinden_pano_verisi(pano.tsv_coz(md.text()), self._dis_girdi)
        except (ValueError, KeyError, TypeError):
            return None
        return None

    def _dis_girdi(self, metin: str):
        """Dışarıdan gelen metin hücreye elle yazılmış gibi çözülür; `=…` Türkçe formül saklanan
        biçime çevrilir, çözülemeyen formül düz metin olarak kalır."""
        try:
            return hucre_girdisi(metin, self.sayfa.kitap)
        except FormulHatasi:
            return Hucre(metin)

    def _baska_oturumdan(self, veri: "pano.PanoVerisi") -> "pano.PanoVerisi":
        """Başka uygulama oturumundan gelen kendi biçimimiz: formüller İngilizce biçimden çevrilir,
        kaynak konumu korunur (göreli başvurular yine kayar)."""
        for anahtar, h in list(veri.hucreler.items()):
            if h.formul is None:
                continue
            try:
                veri.hucreler[anahtar] = Hucre(None, ceviri.iceri(veri.en_formul[anahtar], self.sayfa.kitap))
            except (KeyError, FormulHatasi):
                veri.hucreler[anahtar] = Hucre(h.formul)
        return veri

    def yapistirilabilir(self) -> bool:
        md = QApplication.clipboard().mimeData()
        return md is not None and (md.hasFormat(self.MIME_HUCRELER) or md.hasHtml() or md.hasText())

    def yapistir(self) -> None:
        if Izgara._nesne_panosu is not None and self.nesne_yapistir():
            return
        veri = self._pano_oku()
        if veri is None:
            return
        sec = self.secim
        d = Izgara._pano_durumu
        kesme = bool(d and d["kesildi"]) and veri.oturum == Izgara._OTURUM
        if kesme:
            # kes-yapıştır = taşıma: taşınan bölgeye işaret eden formüller de yeni yere kayar
            ar = d["aralik"]
            kutu = (ar.ilk_satir, ar.ilk_sutun, ar.son_satir, ar.son_sutun)
            r0, c0 = sec.ilk_satir, sec.ilk_sutun
            if r0 + veri.satir_sayisi - 1 > MAX_ROW or c0 + veri.sutun_sayisi - 1 > MAX_COL:
                self.uyari.emit("Yapıştırılan veri sayfa sınırlarını aşıyor.")
                return
            if pano.birlesim_kismen_kesiyor(self.sayfa, Aralik(
                    r0, c0, r0 + veri.satir_sayisi - 1, c0 + veri.sutun_sayisi - 1)):
                self.uyari.emit("Yapıştırma alanı birleşik bir hücreyi kısmen kapsıyor.")
                return
            self.yigin.calistir(HucreTasi(d["sayfa"], kutu, self.sayfa, (r0, c0)))
            Izgara._pano_durumu = None       # kesilen yalnızca bir kez yapıştırılır
            plan = {(r0, c0): None, (r0 + veri.satir_sayisi - 1, c0 + veri.sutun_sayisi - 1): None}
        else:
            try:
                plan = pano.yapistirma_plani(veri, sec.ilk_satir, sec.ilk_sutun, sec)
            except AdresHatasi:
                self.uyari.emit("Yapıştırılan veri sayfa sınırlarını aşıyor.")
                return
            komutlar = [HucrelerDegis(self.sayfa, plan)]
            s = self.sayfa
            if veri.kaynak_satir is not None:
                hedef = Aralik(min(k[0] for k in plan), min(k[1] for k in plan),
                               max(k[0] for k in plan), max(k[1] for k in plan))
                if pano.birlesim_kismen_kesiyor(s, hedef):
                    self.uyari.emit("Yapıştırma alanı birleşik bir hücreyi kısmen kapsıyor.")
                    return
                ekle = pano.yapistirma_birlesimleri(veri, sec.ilk_satir, sec.ilk_sutun, sec)
                kaldir = s.birlesim_kesisen(hedef)
                if ekle or kaldir:                      # Excel "Tümü": birleşim de yapışır / eskisi kalkar
                    komutlar.append(BirlesimDegis(s, ekle, kaldir))
            if veri.kaynak_satir is not None and (veri.stiller or s._stil or s.satir_stil or s.sutun_stil):
                # kendi biçimimiz: içerik + biçim (Excel "Tümü"); dışarıdan gelen metin biçime dokunmaz
                komutlar.append(BicimDegis(s, hucreler=pano.yapistirma_stilleri(
                    veri, sec.ilk_satir, sec.ilk_sutun, sec, s.havuz)))
            not_plani = pano.yapistirma_notlari(veri, s, sec.ilk_satir, sec.ilk_sutun, sec)
            if not_plani:
                komutlar.append(NotlarDegis(s, not_plani))
            self.yigin.calistir(komutlar[0] if len(komutlar) == 1 else Grup(komutlar))
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
        m.addAction("Biçimleri temizle", self.bicimleri_temizle)
        m.addAction("Tümünü temizle", self.tumunu_temizle)
        m.addSeparator()
        if self.not_var_mi((satir, sutun)):
            m.addAction("Notu Düzenle", self.not_duzenle)
            m.addAction("Notu Sil", self.notu_sil)
        else:
            m.addAction("Yeni Not", self.not_duzenle)
        pencere = self.window()
        if hasattr(pencere, "sirala_hizli"):
            m.addSeparator()
            sm = m.addMenu("Sırala")
            sm.addAction("A'dan Z'ye Sırala", lambda: pencere.sirala_hizli(True))
            sm.addAction("Z'den A'ya Sırala", lambda: pencere.sirala_hizli(False))
            sm.addAction("Özel Sıralama…", pencere.sirala_ozel)
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
        nesne_imleci = self._nesne_imleci(p) if self.sayfa.nesneler else None
        if nesne_imleci is not None:
            self.viewport().setCursor(nesne_imleci)
            return
        kenar = self._kenar_bul(p)
        sekil = Qt.ArrowCursor
        if self._tutamacta_mi(p):
            sekil = Qt.CrossCursor
        elif kenar:
            sekil = Qt.SplitHCursor if kenar[0] == "sutun" else Qt.SplitVCursor
        elif self._boyaci is not None:
            sekil = Qt.PointingHandCursor
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
        if b["eksen"] == "sutun":
            self._oto_ok = False                       # genişlik değişti: sarılmış satırlar bırakınca yeniden ölçülür
            self.viewport().update()
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

    def _tanimli_ad_listesi(self):
        """Formül yazarken öneri listesine girecek tanımlı adlar (bu sayfada görünenler)."""
        kitap = self.sayfa.kitap
        if kitap is None or not kitap.adlar:
            return ()
        from ..formul.ad_yardim import gorunur_adlar
        return [t.ad for t in gorunur_adlar(kitap, self.sayfa)]

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
        """Elle verilen yüksekliği kaldırır; satır içeriğe göre (metni kaydır, büyük yazı) otomatik uzar."""
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
        m = self.nesne_menusu(olay.pos()) or self.baslik_menusu(olay.pos()) or self.hucre_menusu(olay.pos())
        if m:
            m.exec(olay.globalPos())

    # --- düzenleme ---
    def duzenleniyor(self) -> bool:
        return self._duzenleyici is not None

    def duzenle_baslat(self, metin: Optional[str], *, duzenle_metni: Optional[str] = None,
                       imlec: Optional[int] = None) -> None:
        """metin None: Düzenle modu (F2/çift tık) — içerik hücreden ya da `duzenle_metni`nden
        (hatalı formülün yeniden açılması); aksi halde yazma modu."""
        if self._duzenleyici is not None:
            return
        self._gorunur_yap(self._aktif)
        ar = self.hucre_dikdortgeni(*self._aktif)
        if ar is None:
            return
        yazma = metin is not None
        e = _Duzenleyici(self.viewport(), yazma)
        e.setFont(self._yazi_tipi())
        if yazma:
            e.setText(metin)
        elif duzenle_metni is not None:
            e.setText(duzenle_metni)
        else:
            e.setText(self.aktif_duzenleme_metni())
        e.bitir.connect(self._duzenleme_bitti)
        e.isaret_denetimi = self._isaret_modu
        e.ad_saglayici = self._tanimli_ad_listesi
        e.okIsaret.connect(self._isaret_ok)
        e.modDegisti.connect(self.modDegisti.emit)
        e.textChanged.connect(self.duzenlemeMetniDegisti.emit)
        e.textChanged.connect(self._metin_degisti)
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
            e.setCursorPosition(len(e.text()) if imlec is None else imlec)

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
        if e.oneri_acik():
            e.liste_konumla()

    # --- Otomatik Toplam (Alt+=) ---
    def _sayisal_mi(self, r: int, c: int) -> bool:
        d = self.sayfa.deger(r, c)
        return isinstance(d, (int, float)) and not isinstance(d, bool)

    def otomatik_toplam(self) -> None:
        """Alt+=: etkin hücrenin üstündeki (yoksa solundaki) bitişik sayı bloğunu toplayan
        `=TOPLA(...)` ile düzenlemeyi başlatır; Enter onaylar. Blok yoksa `=TOPLA()` ve imleç içeride."""
        if self.duzenleniyor():
            return
        sec = self.secim
        if (sec.ilk_satir, sec.ilk_sutun) != (sec.son_satir, sec.son_sutun) and not self._ekler:
            self._secim_toplami(sec)
            return
        r, c = self._aktif
        k = r - 1
        while k >= 1 and self._sayisal_mi(k, c):
            k -= 1
        if k < r - 1:
            ar = Aralik(k + 1, c, r - 1, c)
        else:
            k = c - 1
            while k >= 1 and self._sayisal_mi(r, k):
                k -= 1
            ar = Aralik(r, k + 1, r, c - 1) if k < c - 1 else None
        govde = isaretleme.basvuru_metni(ar) if ar is not None else ""
        metin = ceviri.hucre_metni(Hucre(None, f"=SUM({govde})"), self.sayfa.kitap)
        self.duzenle_baslat(metin)
        if ar is None and self._duzenleyici is not None:
            self._duzenleyici.setCursorPosition(len(metin) - 1)

    def _secim_toplami(self, sec: Aralik) -> None:
        """Çok hücreli seçimde Alt+=: birden çok satırda her sütunun toplamı seçimin altındaki satıra,
        tek satırda toplam seçimin sağındaki hücreye yazılır (Excel gibi; doğrudan, tek geri al adımı)."""
        plan = {}
        if sec.son_satir > sec.ilk_satir:
            hedef = sec.son_satir + 1
            if hedef > MAX_ROW:
                return
            for c in range(sec.ilk_sutun, sec.son_sutun + 1):
                govde = isaretleme.basvuru_metni(Aralik(sec.ilk_satir, c, sec.son_satir, c))
                plan[(hedef, c)] = Hucre(None, f"=SUM({govde})")
        else:
            hedef = sec.son_sutun + 1
            if hedef > MAX_COL:
                return
            govde = isaretleme.basvuru_metni(sec)
            plan[(sec.ilk_satir, hedef)] = Hucre(None, f"=SUM({govde})")
        self.yigin.calistir(HucrelerDegis(self.sayfa, plan))
        self._guncelle()
        satirlar = [k[0] for k in plan]
        sutunlar = [k[1] for k in plan]
        self.sec((min(satirlar), min(sutunlar)), (max(satirlar), max(sutunlar)))

    # --- işaretleme modu (K7): formül yazarken fareyle/okla başvuru seçme ---
    def _metin_degisti(self, _=None) -> None:
        if not self._isaret_yaziyor:
            self._isaret = self._isaret_capa = self._isaret_ucu = None    # yazılan karakter "dondurur"
        self.viewport().update()                                           # renkli başvuru çerçeveleri

    def _hedef(self) -> Optional[QLineEdit]:
        """Başvuru işaretlenecek metin kutusu: hücre içi düzenleyici, yoksa formül çubuğu."""
        return self._duzenleyici if self._duzenleyici is not None else self.dis_duzenleyici

    def isaret_sifirla(self) -> None:
        self._isaret = self._isaret_capa = self._isaret_ucu = None

    def _isaret_modu(self) -> bool:
        e = self._hedef()
        if e is None:
            return False
        metin, imlec = e.text(), e.cursorPosition()
        if self._isaret is not None and self._isaret[1] == imlec and metin.startswith("="):
            return True                    # az önce eklenen başvuru: tıklama/ok onu değiştirir
        return isaretleme.eklenebilir(metin, imlec)

    def isaret_yaz(self, aralik: Aralik, sayfa_adi: Optional[str] = None) -> None:
        """Düzenleyicideki işaret başvurusunu (yoksa imleç konumuna yenisini) `aralik` ile değiştirir."""
        e = self._hedef()
        if e is None:
            return
        metin, imlec = e.text(), e.cursorPosition()
        bas, son = self._isaret if self._isaret and self._isaret[1] == imlec else (imlec, imlec)
        yeni = isaretleme.basvuru_metni(aralik, sayfa_adi)
        self._isaret_yaziyor = True
        try:
            e.setText(metin[:bas] + yeni + metin[son:])
            e.setCursorPosition(bas + len(yeni))
        finally:
            self._isaret_yaziyor = False
        self._isaret = (bas, bas + len(yeni))

    def _isaret_yaz_secim(self) -> None:
        (r1, c1), (r2, c2) = self._isaret_capa, self._isaret_ucu
        ad = self.sayfa.ad if self.uzak_sayfa is not None and self.sayfa is not self.uzak_sayfa else None
        self.isaret_yaz(Aralik(min(r1, r2), min(c1, c2), max(r1, r2), max(c1, c2)), ad)

    def _isaret_tikla(self, satir: int, sutun: int, shift: bool) -> None:
        if shift and self._isaret is not None and self._isaret_capa is not None:
            self._isaret_ucu = (satir, sutun)
        else:
            self._isaret_capa = self._isaret_ucu = (satir, sutun)
        self._isaret_yaz_secim()
        self._surukleme = "isaret"
        self._hedef().setFocus()

    def _isaret_ok(self, dr: int, dc: int, shift: bool) -> None:
        if self._isaret is None or self._isaret_ucu is None:
            self._isaret_capa = self._isaret_ucu = (
                self._duzenlenen if self._duzenleyici is not None else self._aktif)
        r, c = self._isaret_ucu
        yeni = (min(max(r + dr, 1), MAX_ROW), min(max(c + dc, 1), MAX_COL))
        self._isaret_ucu = yeni
        if not shift:
            self._isaret_capa = yeni
        self._gorunur_yap(yeni)
        self._isaret_yaz_secim()

    def _basvuru_vurgulari_ciz(self, p, sutunlar, satirlar) -> None:
        e = self._hedef()
        if e is None or not e.text().startswith("=") or not sutunlar or not satirlar:
            return
        for _, _, b, renk in isaretleme.renkli_basvurular(e.text()):
            if b.sayfa is None:
                if self.uzak_sayfa is not None and self.sayfa is not self.uzak_sayfa:
                    continue                  # öneksiz başvuru asıl (formülün yazıldığı) sayfaya aittir
            elif not (isinstance(b.sayfa, str) and b.sayfa.casefold() == self.sayfa.ad.casefold()):
                continue
            self._secim_cercevesi(p, Aralik(b.r1, b.c1, b.r2, b.c2), sutunlar, satirlar,
                                  QPen(QColor(renk), 2), tek_hucre=True)

    def duzenlemeyi_bitir(self, onayla: bool = True) -> None:
        if self._duzenleyici is not None:
            self._duzenleyici._son(onayla)

    def scrollContentsBy(self, dx: int, dy: int) -> None:
        """Qt'nin varsayılanı tüm viewport'u geçersiz kılar; kaydırmayı `_dikey_kaydi` /
        `_yatay_kaydi` kendisi yönetir (artımlı çizim için)."""

    def _yatay_kaydi(self, yeni: int = 0) -> None:
        """Yatay kaydırma: küçük adımlarda mevcut pikselleri kaydırır, yalnızca açığa çıkan sütunlar
        yeniden çizilir; büyük sıçramada tam çizim (dikey kaydırmayla aynı düzen)."""
        yeni = self.horizontalScrollBar().value()
        eski, self._yatay_son = self._yatay_son, yeni
        fark = yeni - eski
        if fark == 0:
            return
        if self.sayfa.dondur:                 # dondurulmuş bölme: piksel kaydırma yerine tam çizim
            self.viewport().update()
            self._duzenleyici_yerlestir()
            return
        n = len(list(self._gorunen_sutunlar()))
        if abs(fark) < n - 1 and self._yatay_artimli_uygun(eski + 1, yeni + 1):
            if fark > 0:      # soldaki `fark` sütun görünümden çıktı
                dx = -sum(self._gen(c) for c in range(eski + 1, eski + 1 + fark))
            else:             # solda `-fark` sütun göründü
                dx = sum(self._gen(c) for c in range(yeni + 1, yeni + 1 - fark))
            bg, vp = self._baslik_g(), self.viewport()
            vp.scroll(dx, 0, QRect(bg, 0, vp.width() - bg, vp.height()))
            sinir = bg + dx if dx > 0 else vp.width() + dx
            vp.update(QRect(sinir - 3, 0, 6, vp.height()))
        else:
            self.viewport().update()
        self._duzenleyici_yerlestir()

    def _son_sutun_ilkten(self, ilk: int) -> int:
        """`ilk` sütunu soldayken viewport'a sığan son sütun (kısmen görünen dahil)."""
        x, c, w = self._baslik_g(), ilk, self.viewport().width()
        son = ilk
        while x < w and c <= MAX_COL:
            g = self._gen(c)
            if g:
                x += g
                son = c
            c += 1
        return son

    def _yatay_artimli_uygun(self, eski_ilk: int, yeni_ilk: int) -> bool:
        """Piksel kaydırma yalnız çerçeveli aralıklar (seçim, kopyalama) kaydırma öncesi ve sonrası
        görünür pencerenin ortak kısmında tamamen duruyorsa güvenlidir; yarım görünen çerçevenin
        açık uçları içerikle birlikte kayınca artefakt bırakır → o zaman tam çizim."""
        ortak_ilk, ortak_son = max(eski_ilk, yeni_ilk), min(self._son_sutun_ilkten(eski_ilk),
                                                            self._son_sutun_ilkten(yeni_ilk))
        pencere_ilk = min(eski_ilk, yeni_ilk)
        pencere_son = max(self._son_sutun_ilkten(eski_ilk), self._son_sutun_ilkten(yeni_ilk))
        araliklar = list(self.secimler)
        d = Izgara._pano_durumu
        if d and d["sayfa"] is self.sayfa:
            araliklar.append(d["aralik"])
        for a in araliklar:
            if a.son_sutun < pencere_ilk or a.ilk_sutun > pencere_son:
                continue                                  # görünür değil
            if a.ilk_sutun < ortak_ilk or a.son_sutun > ortak_son:
                return False
        return True

    def _dikey_kaydi(self, yeni: int) -> None:
        """Dikey kaydırma: küçük adımlarda mevcut pikselleri kaydırır, yalnızca açığa çıkan
        satırlar yeniden çizilir (100.000 hücrede akıcılık için); büyük sıçramada tam çizim."""
        eski, self._dikey_son = self._dikey_son, yeni
        fark = yeni - eski
        n = len(list(self._gorunen_satirlar()))
        if fark == 0:
            return
        if self.sayfa.dondur:                 # dondurulmuş bölme: piksel kaydırma yerine tam çizim
            self.viewport().update()
            self._duzenleyici_yerlestir()
            return
        if abs(fark) < n - 1:
            if fark > 0:      # üstteki `fark` satır görünümden çıktı
                dy = -sum(self._yuk(r) for r in range(eski + 1, eski + 1 + fark))
            else:             # üstte `-fark` satır göründü
                dy = sum(self._yuk(r) for r in range(yeni + 1, yeni + 1 - fark))
            bh, vp = self._baslik_y(), self.viewport()
            vp.scroll(0, dy, QRect(0, bh, vp.width(), vp.height() - bh))
            sinir = bh + dy if dy > 0 else vp.height() + dy        # kaydırılan/açığa çıkan bölge sınırı
            vp.update(QRect(0, sinir - 3, vp.width(), 6))          # kalın kenarlıklar sınırın iki yanına taşar
        else:
            self.viewport().update()
        self._duzenleyici_yerlestir()

    def _duzenleme_bitti(self, onayla: bool, dr: int, dc: int) -> None:
        e = self._duzenleyici
        if e is None:
            return
        self._duzenleyici = None
        self._isaret = self._isaret_capa = self._isaret_ucu = None
        self.viewport().update()
        metin = e.text()
        imlec = e.cursorPosition()
        tum = bool(getattr(e, "tum_secim", False))
        e.hide()
        e.deleteLater()
        if onayla and not self.hucre_gir(*self._duzenlenen, metin, secime_yay=tum):
            # formül hatalı: Excel gibi düzenleme açık kalır (Düzenle modu, imleç hata yerinde)
            self._aktif = self._duzenlenen
            self.duzenle_baslat(None, duzenle_metni=metin, imlec=imlec)
            return
        self.setFocus()
        self.modDegisti.emit("Hazır")
        if dr or dc:
            r, c = self._aktif
            self.sec((r + dr, c + dc))

    SECIME_YAYMA_SINIRI = 500_000

    def _secime_yay(self, satir: int, sutun: int, yeni, kod) -> bool:
        """Ctrl+Enter: girdi seçimdeki tüm hücrelere yazılır (formül göreli kayar); tek geri al adımı.
        Seçim tek hücreyse False döner (olağan yol). Tek aralık/çoklu aralık desteklenir."""
        toplam = sum((a.son_satir - a.ilk_satir + 1) * (a.son_sutun - a.ilk_sutun + 1) for a in self.secimler)
        if toplam <= 1:
            return False
        if toplam > self.SECIME_YAYMA_SINIRI:
            self.uyari.emit("Seçim bu işlem için çok büyük.")
            return True
        plan = {}
        for a in self.secimler:
            for r in range(a.ilk_satir, a.son_satir + 1):
                for c in range(a.ilk_sutun, a.son_sutun + 1):
                    if self.sayfa.birlesim(r, c) and (r, c) != (satir, sutun):
                        continue
                    plan[(r, c)] = doldurma.kaydirilmis(yeni, r - satir, c - sutun)
        komutlar = [HucrelerDegis(self.sayfa, plan)]
        if kod is not None:
            havuz, yama = self.sayfa.havuz, StilYama(sayi_bicimi=kod)
            genel = {k: havuz.yama_uygula(self.sayfa.stil_kimligi(*k), yama) for k in plan
                     if self.sayfa.stil(*k).sayi_bicimi == "General"}
            if genel:
                komutlar.append(BicimDegis(self.sayfa, hucreler=genel))
        self.yigin.calistir(komutlar[0] if len(komutlar) == 1 else Grup(komutlar))
        self._guncelle()
        return True

    def aktif_duzenleme_metni(self) -> str:
        """Etkin hücrenin düzenleme/formül çubuğu metni (tarih ve yüzde biçimli hücre o yazımla)."""
        return hucre_metni(self.sayfa.hucre(*self._aktif), self.sayfa.kitap,
                           self.sayfa.stil(*self._aktif).sayi_bicimi)

    def hucre_gir(self, satir: int, sutun: int, metin: str, secime_yay: bool = False) -> bool:
        """Yazılan metni çözüp hücreye yazar (geri alınabilir). Değişmediyse bir şey yapmaz.
        Formül hatalıysa uyarı verir ve False döner (hiçbir şey yazılmaz)."""
        kod = None
        if self.sayfa.stil(satir, sutun).sayi_bicimi == "@":
            # Metin biçimli hücre (Excel): her girdi metin kalır, formül bile (başta ' varsa yine atılır)
            yeni = Hucre(metin[1:] if metin.startswith("'") else metin) if metin not in ("", "'") else None
        else:
            try:
                yeni, kod = hucre_girdisi_akilli(metin, self.sayfa.kitap)
            except FormulHatasi as h:
                self.uyari.emit(f"Bu formülde bir sorun var: {h}")
                return False
            if kod is not None and self.sayfa.stil(satir, sutun).sayi_bicimi != "General":
                kod = None                              # biçim yalnız Genel hücreye önerilir (Excel)
        if not self._dogrulama_izni(satir, sutun, yeni):
            return self._dogrulama_sonucu
        yama = {}
        if kod is not None:
            yama["sayi_bicimi"] = kod
        if (yeni is not None and isinstance(yeni.deger, str) and "\n" in yeni.deger
                and not self.sayfa.stil(satir, sutun).kaydir):
            yama["kaydir"] = True                       # Alt+Enter: Excel metni kaydırmayı kendiliğinden açar
        if secime_yay and self._secime_yay(satir, sutun, yeni, kod):
            return True
        if yeni == self.sayfa.hucre(satir, sutun) and not yama:
            return True
        komut = HucrelerDegis(self.sayfa, {(satir, sutun): yeni})
        if yama:
            komut = Grup([komut, bicim_komutu(self.sayfa, [Aralik(satir, sutun, satir, sutun)],
                                              StilYama(**yama))])
        self.yigin.calistir(komut)
        self._guncelle()
        return True

    # --- koşullu biçim kuralları (5h) ---
    def kosullu_kural_ekle(self, kural, araliklar=None) -> bool:
        """Seçime (ya da `araliklar`a) yeni kural ekler; EN YÜKSEK öncelikli olur (Excel). Kuralın formülleri
        etkin hücreye göre yazılmış sayılır; çapa (ilk aralığın sol üstü) etkin hücre değilse kaydırılır.
        Tek geri al adımı."""
        from dataclasses import replace
        from ..formul.kaydir import kopyala
        from ..model.kosullu import kural_ekle, KosulluKural
        araliklar = list(araliklar) if araliklar is not None else list(self.secimler)
        fr, fc = araliklar[0].ilk_satir - self._aktif[0], araliklar[0].ilk_sutun - self._aktif[1]

        def kay(f):
            return kopyala(f, fr, fc) if f is not None and f.startswith("=") and (fr, fc) != (0, 0) else f
        noktalar = tuple((n[0], kay(n[1])) + tuple(n[2:]) for n in kural.noktalar)
        kural = replace(kural, araliklar=tuple(araliklar), formul1=kay(kural.formul1), formul2=kay(kural.formul2),
                        noktalar=noktalar, min_nokta=(kural.min_nokta[0], kay(kural.min_nokta[1])),
                        max_nokta=(kural.max_nokta[0], kay(kural.max_nokta[1])))
        self.yigin.calistir(KosulluDegis(self.sayfa, lambda eski: kural_ekle(eski, kural)))
        self._guncelle(pano_iptal=False)
        return True

    def kosullu_listesi_yaz(self, liste) -> bool:
        """Kural listesini (sıra = öncelik) aynen yazar (Kuralları Yönet); değişen yoksa False."""
        kmt = KosulluDegis(self.sayfa, list(liste))
        if kmt.bos_mu():
            return False
        self.yigin.calistir(kmt)
        self._guncelle(pano_iptal=False)
        return True

    def kosullu_temizle(self, tum_sayfa: bool = False) -> bool:
        """Kuralları Temizle: seçili hücrelerden ya da tüm sayfadan; tek geri al adımı."""
        from ..model.kosullu import aralik_temizle
        if tum_sayfa:
            yeni = lambda eski: []
        else:
            secimler = list(self.secimler)
            yeni = lambda eski: aralik_temizle(eski, secimler)
        kmt = KosulluDegis(self.sayfa, yeni)
        if kmt.bos_mu():
            return False
        self.yigin.calistir(kmt)
        self._guncelle(pano_iptal=False)
        return True

    # --- veri doğrulama (5g) ---
    _dogrulama_sonucu = True              # `_dogrulama_izni` False dönerse `hucre_gir`'in döndüreceği değer

    def _dogrulama_izni(self, satir: int, sutun: int, yeni) -> bool:
        """Elle girişte kural denetlenir (formül girişi, yapıştırma, doldurma denetlenmez). Geçersizse kullanıcıya
        sorulur: devam -> True (yazılır); yeniden dene -> False ve `hucre_gir` False döner (düzenleme açık kalır);
        iptal -> False ve `hucre_gir` True döner (giriş bırakılır)."""
        dv = self.sayfa.dogrulama(satir, sutun) if self.sayfa.dogrulamalar else None
        if dv is None or (yeni is not None and yeni.formul is not None):
            return True
        if dogrula(self.sayfa, satir, sutun, None if yeni is None else yeni.deger, dv=dv):
            return True
        if not dv.hata[0]:
            return True                                         # hata uyarısı kapalı: her girişe izin
        yanit = (self.dogrulama_soru or self._dogrulama_kutusu)(dv)
        if yanit == "devam":
            return True
        self._dogrulama_sonucu = yanit != "tekrar"
        return False

    def _dogrulama_kutusu(self, dv) -> str:
        from PySide6.QtWidgets import QMessageBox
        _, stil, baslik, ileti = dv.hata
        pencere = self.window()
        ad = pencere.windowTitle().split(" - ")[-1] if pencere is not None else ""
        kutu = QMessageBox(self)
        kutu.setWindowTitle(baslik or ad or "Veri Doğrulama")
        if stil == "durdur":
            kutu.setIcon(QMessageBox.Critical)
            kutu.setText(ileti or VARSAYILAN_DOGRULAMA_IL)
            yeniden = kutu.addButton("Yeniden Dene", QMessageBox.AcceptRole)
            kutu.addButton("İptal", QMessageBox.RejectRole)
            kutu.exec()
            return "tekrar" if kutu.clickedButton() is yeniden else "iptal"
        if stil == "uyari":
            kutu.setIcon(QMessageBox.Warning)
            kutu.setText(ileti or VARSAYILAN_DOGRULAMA_IL + "\nDevam etmek istiyor musunuz?")
            evet = kutu.addButton("Evet", QMessageBox.YesRole)
            hayir = kutu.addButton("Hayır", QMessageBox.NoRole)
            kutu.addButton("İptal", QMessageBox.RejectRole)
            kutu.exec()
            t = kutu.clickedButton()
            return "devam" if t is evet else "tekrar" if t is hayir else "iptal"
        kutu.setIcon(QMessageBox.Information)
        kutu.setText(ileti or VARSAYILAN_DOGRULAMA_IL)
        tamam = kutu.addButton("Tamam", QMessageBox.AcceptRole)
        kutu.addButton("İptal", QMessageBox.RejectRole)
        kutu.exec()
        return "devam" if kutu.clickedButton() is tamam else "iptal"

    def dogrulama_uygula(self, dv, araliklar=None) -> bool:
        """Seçime (ya da `araliklar`a) kural koyar; `dv=None` ya da etkisiz kural ("herhangi bir değer", ileti yok)
        kuralı kaldırır. Tek geri al adımı; değişen yoksa False."""
        araliklar = list(araliklar) if araliklar is not None else list(self.secimler)
        if dv is not None and dv.etkisiz_mi():
            dv = None
        if dv is not None:
            from dataclasses import replace
            dv = replace(dv, araliklar=tuple(araliklar))
        kmt = DogrulamaDegis(self.sayfa, araliklar, dv)
        if kmt.bos_mu():
            return False
        self.yigin.calistir(kmt)
        self._guncelle(pano_iptal=False)
        return True

    def _liste_dogrulamasi(self):
        """Etkin hücrenin açılır listeli kuralı (yoksa None)."""
        if not self.sayfa.dogrulamalar or self.duzenleniyor():
            return None
        dv = self.sayfa.dogrulama(*self._aktif)
        return dv if dv is not None and dv.tur == "liste" and dv.acilir_liste else None

    def acilir_liste_ogeleri(self):
        """Etkin hücrenin açılır liste seçenekleri (aralıktaki boş hücre boş satır olur); yoksa None."""
        dv = self._liste_dogrulamasi()
        if dv is None:
            return None
        return liste_ogeleri(dv, self.sayfa, *self._aktif, self.sayfa.kitap, bos_dahil=True)

    def acilir_liste_sec(self, metin: str) -> bool:
        """Listeden seçim: değer elle yazılmış gibi `hucre_gir` yolundan girer (kural yine denetler)."""
        return self.hucre_gir(*self._aktif, metin)

    def _acilir_dugme_dikdortgeni(self) -> Optional[QRect]:
        if self._liste_dogrulamasi() is None or len(self.secimler) > 1:
            return None
        ar = self.hucre_dikdortgeni(*self._aktif)
        if ar is None:
            return None
        return QRect(ar.right() + 1, ar.top(), self._z(18), max(1, min(ar.height() - 1, self._z(20))))

    def _acilir_dugme_ciz(self, p: QPainter, kirp: QRect) -> None:
        d = self._acilir_dugme_dikdortgeni()
        if d is None or not d.intersects(kirp):
            return
        p.setPen(QPen(QColor("#a6a6a6"), 1))
        p.setBrush(QColor("#f3f3f3"))
        p.drawRect(d.adjusted(0, 0, -1, -1))
        cx, cy, w = d.center().x(), d.center().y(), self._z(3)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#444444"))
        p.drawPolygon(QPolygon([QPoint(cx - w - 1, cy - 1), QPoint(cx + w, cy - 1), QPoint(cx, cy + w)]))
        p.setBrush(Qt.NoBrush)

    def acilir_liste_ac(self) -> bool:
        """Etkin hücrenin listesini hücrenin altında açar (en çok 8 satır görünür, kaydırılabilir)."""
        ogeler = self.acilir_liste_ogeleri()
        ar = self.hucre_dikdortgeni(*self._aktif)
        if not ogeler or ar is None:
            return False
        liste = QListWidget(self.viewport())
        liste.setWindowFlags(Qt.Popup)
        liste.addItems(ogeler)
        satir_h = liste.sizeHintForRow(0) if liste.count() else 20
        liste.setFixedSize(max(ar.width(), 120), min(len(ogeler), 8) * (satir_h or 20) + 6)
        mevcut = self.sayfa.deger(*self._aktif)
        if mevcut is not None:
            for i, o in enumerate(ogeler):
                if tr_kucuk(o) == tr_kucuk(goster(mevcut)):
                    liste.setCurrentRow(i)
                    break

        def sec(oge):
            liste.close()
            self.acilir_liste_sec(oge.text())
        liste.itemClicked.connect(sec)
        self._liste_acik = liste
        liste.move(self.viewport().mapToGlobal(QPoint(ar.left(), ar.bottom() + 1)))
        liste.show()
        liste.setFocus()
        return True

    def _giris_iletisi_guncelle(self) -> None:
        """Etkin hücrenin kuralında giriş iletisi varsa hücrenin altında sarı kutu gösterir (hücreden ayrılınca kapanır)."""
        dv = self.sayfa.dogrulama(*self._aktif) if self.sayfa.dogrulamalar else None
        ar = self.hucre_dikdortgeni(*self._aktif) if dv is not None else None
        if dv is None or ar is None or not dv.giris[0] or (dv.giris[1] == "" and dv.giris[2] == ""):
            if self._giris_etiketi is not None:
                self._giris_etiketi.hide()
            return
        from html import escape
        if self._giris_etiketi is None:
            k = QLabel(self.viewport())
            k.setWordWrap(True)
            k.setTextFormat(Qt.RichText)
            k.setAttribute(Qt.WA_TransparentForMouseEvents)
            k.setStyleSheet("QLabel{background:#FFFFE1;color:#000;border:1px solid #000;padding:3px;}")
            self._giris_etiketi = k
        k = self._giris_etiketi
        baslik, ileti = dv.giris[1], dv.giris[2]
        k.setText((f"<b>{escape(baslik)}</b><br>" if baslik else "") + escape(ileti).replace("\n", "<br>"))
        k.setFixedWidth(self._z(180))
        k.adjustSize()
        k.setFixedHeight(k.heightForWidth(k.width()) if k.hasHeightForWidth() else k.sizeHint().height())
        vp = self.viewport()
        k.move(min(ar.left(), max(0, vp.width() - k.width())),
               min(ar.bottom() + self._z(3), max(0, vp.height() - k.height())))
        k.show()
        k.raise_()

    def filtreyle_gizli(self, satir: int) -> bool:
        """Satır etkin filtrenin veri aralığında ve gizli mi (Delete/Temizle/biçim yalnız görünenlere)."""
        f = self.sayfa.filtre
        return (f is not None and satir in self.sayfa.gizli_satir
                and f.aralik.ilk_satir < satir <= f.aralik.son_satir)

    def secimi_temizle(self) -> None:
        yeni = {(r, c): None for a in self.secimler for r, c, _ in self.sayfa.aralikta(a)
                if not self.filtreyle_gizli(r)}
        if yeni:
            self.yigin.calistir(HucrelerDegis(self.sayfa, yeni))
            self._guncelle()

    def bicimleri_temizle(self) -> None:
        """Seçimin biçimini varsayılana döndürür; içerik kalır (tek geri al adımı)."""
        try:
            kmt = bicim_komutu(self.sayfa, self.secimler, sifirla=True)
        except AdresHatasi as h:
            self.uyari.emit(str(h))
            return
        if not kmt.bos_mu():
            self.yigin.calistir(kmt)
            self._guncelle()

    # --- biçim boyacısı ---
    def boyaci_baslat(self, kalici: bool = False) -> bool:
        """Seçimin biçimini alır; sonraki hücre/aralık seçimine boyar. `kalici` (çift tık): Esc'e ya da
        düğmeye yeniden basana dek açık kalır. Çoklu seçimde alınamaz (Excel gibi)."""
        if self.duzenleniyor():
            return False
        if self._ekler:
            self.uyari.emit("Bu komut birden çok seçimde kullanılamaz.")
            return False
        self._boyaci = {"kaynak": self.secim, "kalici": kalici}
        self.viewport().setCursor(Qt.PointingHandCursor)
        self.boyaciDegisti.emit(True)
        return True

    def boyaci_iptal(self) -> None:
        if self._boyaci is None:
            return
        self._boyaci = None
        self.viewport().setCursor(Qt.ArrowCursor)
        self.boyaciDegisti.emit(False)

    def boyaci_acik_mi(self) -> bool:
        return self._boyaci is not None

    def _boyaci_uygula(self) -> None:
        b = self._boyaci
        if len(self.secimler) != 1:
            return
        try:
            stiller = boyaci_stilleri(self.sayfa, b["kaynak"], self.secim)
        except ValueError as h:
            self.uyari.emit(str(h))
            self.boyaci_iptal()
            return
        # kaynağın kendine boyanması gibi değişmeyen işlemde komut eklenmez
        degisen = {k: v for k, v in stiller.items() if self.sayfa.stil_kimligi(*k) != v}
        if degisen:
            self.yigin.calistir(BicimDegis(self.sayfa, hucreler=degisen))
            self._guncelle()
        if not b["kalici"]:
            self.boyaci_iptal()

    def bicim_uygula(self, yama_ya_da_plan) -> bool:
        """Seçime stil yaması uygular (biçim araç çubuğu). Ya tek `StilYama` (tüm seçim) ya da
        `model.bicim_islem` planı (`[(aralıklar, yama), …]`); hepsi tek geri al adımı. Uygulanacak
        değişiklik yoksa False."""
        try:
            if isinstance(yama_ya_da_plan, StilYama):
                kmt = bicim_komutu(self.sayfa, self.secimler, yama_ya_da_plan)
            else:
                kmt = BicimPlani(self.sayfa, yama_ya_da_plan)
                # tam satır/sütunda çok büyük seçim bu aşamada AdresHatası verir: önce dene
                for ar, y in kmt.plan:
                    bicim_komutu(self.sayfa, ar, y)
        except AdresHatasi as h:
            self.uyari.emit(str(h))
            return False
        if kmt.bos_mu():
            return False
        self.yigin.calistir(kmt)
        self._guncelle()
        return True

    def birlestir(self, tur: str = "ortala", onayli: bool = False) -> bool:
        """Seçimi birleştirir (`birlestir`/`ortala`/`satirlar`) ya da birleşimi çözer (`coz`); tek geri al
        adımı. Sol üst dışında dolu hücre silinecekse `veri_kaybi_onayi` (varsa) sorulur. Kısa yol:
        seçim zaten tam bir birleşimse `ortala` onu çözer (Excel'in aç/kapa düğmesi)."""
        if self.duzenleniyor():
            return False
        if tur == "ortala" and len(self.secimler) == 1 and self.sayfa.birlesim(*self._aktif) == self.secim:
            tur = "coz"
        try:
            if tur not in ("coz",) and len(self.secimler) == 1:
                if birlesim_veri_kaybi(self.sayfa, self.secim, tur) and not onayli:
                    if self.veri_kaybi_onayi is not None and not self.veri_kaybi_onayi():
                        return False
            kmt = birlesim_komutu(self.sayfa, self.secimler, tur)
        except ValueError as h:
            self.uyari.emit(str(h))
            return False
        if kmt is None:
            return False
        self.yigin.calistir(kmt)
        self._birlesime_uydur()
        self._guncelle()
        return True

    def tumunu_temizle(self) -> None:
        """İçerik + biçim + not (Temizle ▸ Tümü); tek geri al adımı."""
        icerik = {(r, c): None for a in self.secimler for r, c, _ in self.sayfa.aralikta(a)
                  if not self.filtreyle_gizli(r)}
        try:
            kmt = bicim_komutu(self.sayfa, self.secimler, sifirla=True)
        except AdresHatasi as h:
            self.uyari.emit(str(h))
            return
        notlar = {a: None for a in self.sayfa.notlar if any(aralik_icinde(s, *a) for s in self.secimler)}
        komutlar = ([HucrelerDegis(self.sayfa, icerik)] if icerik else []) + ([] if kmt.bos_mu() else [kmt])
        if notlar:
            komutlar.append(NotlarDegis(self.sayfa, notlar))
        from ..model.kosullu import aralik_temizle
        secimler = list(self.secimler)
        kkmt = KosulluDegis(self.sayfa, lambda eski: aralik_temizle(eski, secimler))
        if not kkmt.bos_mu():
            komutlar.append(kkmt)               # Excel Tümünü Temizle koşullu biçimi de kaldırır
        dkmt = DogrulamaDegis(self.sayfa, list(self.secimler), None)
        if not dkmt.bos_mu():
            komutlar.append(dkmt)               # Excel Tümünü Temizle veri doğrulamayı da kaldırır
        if komutlar:
            self.yigin.calistir(komutlar[0] if len(komutlar) == 1 else Grup(komutlar))
            self._guncelle()

    def geri_al(self) -> None:
        self._gecmis(self.yigin.geri_al)

    def yinele(self) -> None:
        self._gecmis(self.yigin.yinele)

    def _gecmis(self, islem) -> None:
        self.gecmisIslemi.emit(True)       # pencere: başka sayfadaki değişikliğe geçebilsin
        try:
            tamam = islem()
            if tamam:
                self._guncelle()           # `degisti` de bayrak açıkken çıkar (pencere döngü uyarısı vermesin)
        finally:
            self.gecmisIslemi.emit(False)

    def _guncelle(self, pano_iptal: bool = True) -> None:
        """İçerik/yapı değişikliği sonrası yenile. Varsayılan olarak kopyala/kes işaretini iptal eder
        (Excel gibi: kaynak değişince kes modu biter; yoksa eski konum bayat kalır).
        Boyutlandırma/gizleme ve yapıştırmanın kendisi işareti korur."""
        if pano_iptal:
            Izgara._pano_durumu = None
        self._oto_ok = False                       # içerik/biçim/genişlik değişti: otomatik satır yükseklikleri
        self._kosullu = None                       # koşullu biçim önbelleği (içerik/kural değişmiş olabilir)
        self._duzenleyici_yerlestir()
        self._sayfa_adimlari()
        self.viewport().update()
        self.degisti.emit()

    def mouseDoubleClickEvent(self, olay):
        if olay.button() == Qt.LeftButton and self._nesne_cift_tik(olay.position().toPoint()):
            return
        if olay.button() == Qt.LeftButton and self._tutamacta_mi(olay.position().toPoint()):
            self._doldur = None
            self._surukleme = None
            self.tutamac_cift_tik()
            return
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
