"""Ana pencere: yeşil başlık şeridi, ad kutusu + formül çubuğu, ızgara, sayfa sekmeleri,
durum çubuğu (mod, Ortalama · Sayım · Toplam, yakınlaştırma).

Her sayfanın kendi `Izgara`'sı vardır (seçim ve kaydırma konumu sayfada kalır); geri al
yığını çalışma kitabı genelinde ortaktır.
"""
from typing import Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import (
    QColorDialog, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox,
    QSlider, QStackedWidget, QTabBar, QToolButton, QVBoxLayout, QWidget,
)

from .. import APP_NAME
from ..model.adres import AdresHatasi, aralik_coz, hucre_yaz
from ..model.girdi import duzenleme_metni
from ..model.komutlar import GeriAlYigini
from ..model.sayfa import CalismaKitabi, Sayfa
from . import theme
from .grid import Izgara, goster


class _SekmeCubugu(QTabBar):
    ciftTik = Signal(int)

    def paintEvent(self, olay):
        super().paintEvent(olay)
        renkler = [self.tabData(i) for i in range(self.count())]
        if not any(renkler):
            return
        p = QPainter(self)
        for i, renk in enumerate(renkler):
            if renk:                       # Excel gibi: sekmenin altında renkli şerit
                r = self.tabRect(i)
                p.fillRect(r.left() + 2, r.bottom() - 2, r.width() - 4, 3, QColor(renk))
        p.end()

    def mouseDoubleClickEvent(self, olay):
        i = self.tabAt(olay.position().toPoint())
        if i >= 0:
            self.ciftTik.emit(i)
        else:
            super().mouseDoubleClickEvent(olay)


class _FormulCubugu(QLineEdit):
    """Enter: onayla; Esc: vazgeç."""
    onayla = Signal(str)
    vazgec = Signal()

    def keyPressEvent(self, olay):
        if olay.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.onayla.emit(self.text())
        elif olay.key() == Qt.Key_Escape:
            self.vazgec.emit()
        else:
            super().keyPressEvent(olay)


class Pencere(QMainWindow):
    def __init__(self, kitap: Optional[CalismaKitabi] = None):
        super().__init__()
        self.kitap = kitap or CalismaKitabi()
        self.yigin = GeriAlYigini()
        self.belge_adi = "Adsız"
        self._izgaralar: Dict[Sayfa, Izgara] = {}
        self._mod = "Hazır"
        self.setStyleSheet(theme.stylesheet())
        self._kur()
        for s in self.kitap.sayfalar:
            self._sekme_ekle(s)
        self.sekmeler.setCurrentIndex(0)
        self._sekme_degisti(0)
        self._baslik_guncelle()
        self.resize(1100, 700)

    # ------------------------------------------------------------------ kurulum
    def _kur(self):
        merkez = QWidget()
        merkez.setObjectName("central")
        dikey = QVBoxLayout(merkez)
        dikey.setContentsMargins(0, 0, 0, 0)
        dikey.setSpacing(0)
        self.setCentralWidget(merkez)

        # başlık şeridi
        baslik = QWidget()
        baslik.setObjectName("header")
        h = QHBoxLayout(baslik)
        h.setContentsMargins(8, 6, 8, 6)
        self.dosya_dugmesi = QToolButton()
        self.dosya_dugmesi.setObjectName("fileButton")
        self.dosya_dugmesi.setText("Dosya")
        self.dosya_dugmesi.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self.dosya_dugmesi)
        menu.addAction("Çıkış", self.close)
        self.dosya_dugmesi.setMenu(menu)
        self.geri_dugmesi = QToolButton()
        self.geri_dugmesi.setText("Geri Al")
        self.geri_dugmesi.setToolTip("Geri Al (Ctrl+Z)")
        self.geri_dugmesi.clicked.connect(lambda: self.izgara().geri_al())
        self.yinele_dugmesi = QToolButton()
        self.yinele_dugmesi.setText("Yinele")
        self.yinele_dugmesi.setToolTip("Yinele (Ctrl+Y)")
        self.yinele_dugmesi.clicked.connect(lambda: self.izgara().yinele())
        self.belge_etiketi = QLabel()
        self.belge_etiketi.setObjectName("docTitle")
        h.addWidget(self.dosya_dugmesi)
        h.addWidget(self.geri_dugmesi)
        h.addWidget(self.yinele_dugmesi)
        h.addStretch(1)
        h.addWidget(self.belge_etiketi)
        h.addStretch(1)
        dikey.addWidget(baslik)

        # ad kutusu + formül çubuğu
        cubuk = QWidget()
        cubuk.setObjectName("formulaBar")
        f = QHBoxLayout(cubuk)
        f.setContentsMargins(6, 4, 6, 4)
        self.ad_kutusu = QLineEdit()
        self.ad_kutusu.setFixedWidth(110)
        self.ad_kutusu.setToolTip("Ad Kutusu: hücre/aralık adresi yazıp Enter'a basın (ör. B7 veya A1:C5)")
        self.ad_kutusu.returnPressed.connect(self._ad_kutusundan_git)
        fx = QLabel("fx")
        self.formul = _FormulCubugu()
        self.formul.onayla.connect(self._formul_onayla)
        self.formul.vazgec.connect(self._formul_vazgec)
        f.addWidget(self.ad_kutusu)
        f.addWidget(fx)
        f.addWidget(self.formul, 1)
        dikey.addWidget(cubuk)

        # ızgaralar
        self.izgara_yigini = QStackedWidget()
        dikey.addWidget(self.izgara_yigini, 1)

        # sayfa sekmeleri
        alt = QWidget()
        alt.setObjectName("sheetBar")
        a = QHBoxLayout(alt)
        a.setContentsMargins(6, 0, 6, 0)
        self.sekmeler = _SekmeCubugu()
        self.sekmeler.setShape(QTabBar.RoundedSouth)
        self.sekmeler.setMovable(True)
        self.sekmeler.setDrawBase(False)
        self.sekmeler.setExpanding(False)
        self.sekmeler.setContextMenuPolicy(Qt.CustomContextMenu)
        self.sekmeler.currentChanged.connect(self._sekme_degisti)
        self.sekmeler.tabMoved.connect(self._sekme_tasindi)
        self.sekmeler.ciftTik.connect(self.sayfa_yeniden_adlandir)
        self.sekmeler.customContextMenuRequested.connect(self._sekme_menusu)
        ekle = QToolButton()
        ekle.setText("+")
        ekle.setToolTip("Yeni sayfa")
        ekle.clicked.connect(self.sayfa_ekle)
        a.addWidget(self.sekmeler)
        a.addWidget(ekle)
        a.addStretch(1)
        dikey.addWidget(alt)

        # durum çubuğu
        self.mod_etiketi = QLabel("Hazır")
        self.mod_etiketi.setMinimumWidth(60)
        self.ozet_etiketi = QLabel("")
        self.yakin_etiketi = QLabel("100%")
        self.yakin_etiketi.setMinimumWidth(40)
        self.yakin_etiketi.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.yakin_kaydirici = QSlider(Qt.Horizontal)
        self.yakin_kaydirici.setRange(10, 400)
        self.yakin_kaydirici.setValue(100)
        self.yakin_kaydirici.setFixedWidth(120)
        self.yakin_kaydirici.valueChanged.connect(self._kaydirici_degisti)
        sb = self.statusBar()
        sb.setSizeGripEnabled(False)
        sb.addWidget(self.mod_etiketi)
        sb.addPermanentWidget(self.ozet_etiketi)
        sb.addPermanentWidget(self.yakin_kaydirici)
        sb.addPermanentWidget(self.yakin_etiketi)

        QShortcut(QKeySequence("Ctrl+PgDown"), self, activated=lambda: self._sekme_git(1))
        QShortcut(QKeySequence("Ctrl+PgUp"), self, activated=lambda: self._sekme_git(-1))

    def showEvent(self, olay):
        super().showEvent(olay)
        theme.baslik_cubugu_rengi(self)

    # ------------------------------------------------------------------ yardımcılar
    def izgara(self) -> Izgara:
        return self.izgara_yigini.currentWidget()

    def _baslik_guncelle(self):
        self.setWindowTitle(f"{self.belge_adi} - {APP_NAME}")
        self.belge_etiketi.setText(f"{self.belge_adi} — {APP_NAME}")

    # ------------------------------------------------------------------ sayfalar
    def _sekme_ekle(self, sayfa: Sayfa, indeks: Optional[int] = None) -> Izgara:
        g = Izgara(sayfa, yigin=self.yigin)
        g.aktifDegisti.connect(self._arayuzu_guncelle)
        g.secimDegisti.connect(self._arayuzu_guncelle)
        g.degisti.connect(self._icerik_degisti)
        g.modDegisti.connect(self._mod_degisti)
        g.duzenlemeMetniDegisti.connect(self._duzenleme_aynala)
        g.suruklemeBitti.connect(self._arayuzu_guncelle)
        g.yakinlastirmaDegisti.connect(self._yakinlastirma_degisti)
        g.uyari.connect(self._uyari)
        self._izgaralar[sayfa] = g
        self.izgara_yigini.addWidget(g)
        if indeks is None:
            i = self.sekmeler.addTab(sayfa.ad)
        else:
            i = self.sekmeler.insertTab(indeks, sayfa.ad)
        self.sekmeler.setTabData(i, sayfa.sekme_rengi)
        return g

    def sayfa_ekle(self):
        s = self.kitap.sayfa_ekle()
        self._sekme_ekle(s)
        self.sekmeler.setCurrentIndex(len(self.kitap.sayfalar) - 1)

    def sayfa_sil(self, i: int):
        sayfa = self.kitap.sayfalar[i]
        if len(self.kitap.sayfalar) == 1:
            QMessageBox.information(self, APP_NAME, "Çalışma kitabındaki son sayfa silinemez.")
            return
        if sayfa.kullanilan_aralik() is not None:
            c = QMessageBox.question(
                self, APP_NAME,
                f"“{sayfa.ad}” sayfası silinecek ve bu işlem geri alınamaz. Devam edilsin mi?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if c != QMessageBox.Yes:
                return
        self.kitap.sayfa_sil(sayfa)
        Izgara._pano_durumu = None        # kesilen/kopyalanan sayfa silinmiş olabilir
        g = self._izgaralar.pop(sayfa)
        self.izgara_yigini.removeWidget(g)
        g.deleteLater()
        self.sekmeler.removeTab(i)
        self.yigin.temizle()      # silinen sayfaya ait komutlar geçersiz kalır
        self._sekme_degisti(self.sekmeler.currentIndex())

    def sayfa_yeniden_adlandir(self, i: int, yeni: Optional[str] = None):
        sayfa = self.kitap.sayfalar[i]
        if yeni is None:
            yeni, tamam = QInputDialog.getText(self, "Sayfayı yeniden adlandır", "Sayfa adı:",
                                               text=sayfa.ad)
            if not tamam:
                return
        try:
            self.kitap.yeniden_adlandir(sayfa, yeni)
        except ValueError as e:
            QMessageBox.warning(self, APP_NAME, str(e))
            return
        self.sekmeler.setTabText(i, sayfa.ad)

    def sekme_rengi_ata(self, i: int, renk: Optional[str]):
        self.kitap.sayfalar[i].sekme_rengi = renk
        self.sekmeler.setTabData(i, renk)
        self.sekmeler.update()

    def _sekme_rengi_sor(self, i: int):
        mevcut = self.kitap.sayfalar[i].sekme_rengi
        r = QColorDialog.getColor(QColor(mevcut) if mevcut else QColor(theme.ACCENT), self,
                                  "Sekme rengi")
        if r.isValid():
            self.sekme_rengi_ata(i, r.name())

    def sekme_menusu_olustur(self, nokta) -> QMenu:
        i = self.sekmeler.tabAt(nokta)
        m = QMenu(self)
        m.addAction("Yeni sayfa", self.sayfa_ekle)
        if i >= 0:
            m.addAction("Yeniden adlandır…", lambda: self.sayfa_yeniden_adlandir(i))
            m.addAction("Sekme rengi…", lambda: self._sekme_rengi_sor(i))
            if self.kitap.sayfalar[i].sekme_rengi:
                m.addAction("Sekme rengini kaldır", lambda: self.sekme_rengi_ata(i, None))
            m.addAction("Sil", lambda: self.sayfa_sil(i))
        return m

    def _sekme_menusu(self, nokta):
        self.sekme_menusu_olustur(nokta).exec(self.sekmeler.mapToGlobal(nokta))

    def _sekme_tasindi(self, kaynak: int, hedef: int):
        self.kitap.sayfa_tasi(self.kitap.sayfalar[kaynak], hedef)

    def _sekme_git(self, yon: int):
        n = self.sekmeler.count()
        self.sekmeler.setCurrentIndex((self.sekmeler.currentIndex() + yon) % n)

    def _sekme_degisti(self, i: int):
        if i < 0 or i >= len(self.kitap.sayfalar):
            return
        g = self._izgaralar[self.kitap.sayfalar[i]]
        self.izgara_yigini.setCurrentWidget(g)
        self.yakin_kaydirici.blockSignals(True)
        self.yakin_kaydirici.setValue(round(g.yakinlastirma * 100))
        self.yakin_kaydirici.blockSignals(False)
        self.yakin_etiketi.setText(f"{round(g.yakinlastirma * 100)}%")
        self._arayuzu_guncelle()
        g.setFocus()

    # ------------------------------------------------------------------ ad kutusu / formül çubuğu
    def _arayuzu_guncelle(self, *_):
        g = self.izgara()
        kaynak = self.sender()
        if kaynak is not g and kaynak in self._izgaralar.values():
            return       # arka plandaki sayfanın sinyali
        sec = g.secim
        coklu = (sec.ilk_satir, sec.ilk_sutun) != (sec.son_satir, sec.son_sutun)
        if g.suruklenuyor() and coklu:
            self.ad_kutusu.setText(f"{sec.son_satir - sec.ilk_satir + 1}S x "
                                   f"{sec.son_sutun - sec.ilk_sutun + 1}Sü")
        else:
            self.ad_kutusu.setText(hucre_yaz(*g.aktif))
        if not g.duzenleniyor():
            self.formul.setText(duzenleme_metni(g.sayfa.hucre(*g.aktif)))
        self._ozet_guncelle()

    def _uyari(self, metin: str):
        self.statusBar().showMessage(metin, 6000)
        QMessageBox.warning(self, APP_NAME, metin)

    def _icerik_degisti(self):
        for g in self._izgaralar.values():
            g.viewport().update()
        self._arayuzu_guncelle()

    def _ad_kutusundan_git(self):
        g = self.izgara()
        try:
            ar = aralik_coz(self.ad_kutusu.text())
        except AdresHatasi:
            QMessageBox.warning(self, APP_NAME, "Başvuru geçerli değil.")
            self._arayuzu_guncelle()
            g.setFocus()
            return
        tam = ar.son_satir - ar.ilk_satir > 1000 or ar.son_sutun - ar.ilk_sutun > 100
        g.sec((ar.ilk_satir, ar.ilk_sutun), (ar.son_satir, ar.son_sutun), kaydir=not tam)
        if tam:
            g._gorunur_yap((ar.ilk_satir, ar.ilk_sutun))
        g.setFocus()
        self._arayuzu_guncelle()

    def _formul_onayla(self, metin: str):
        g = self.izgara()
        g.hucre_gir(*g.aktif, metin)
        g.setFocus()
        g.sec((g.aktif[0] + 1, g.aktif[1]))

    def _formul_vazgec(self):
        g = self.izgara()
        self.formul.setText(duzenleme_metni(g.sayfa.hucre(*g.aktif)))
        g.setFocus()

    def _duzenleme_aynala(self, metin: str):
        if self.sender() is self.izgara() and self.formul.text() != metin:
            self.formul.setText(metin)

    # ------------------------------------------------------------------ durum çubuğu
    def _mod_degisti(self, mod: str):
        self._mod = mod
        self.mod_etiketi.setText(mod)
        if mod == "Hazır":
            self._arayuzu_guncelle()

    def _ozet_guncelle(self):
        """Seçimde Ortalama · Sayım · Toplam (Excel gibi; yalnızca dolu hücreler gezilir)."""
        g = self.izgara()
        sec = g.secim
        if not g._ekler and (sec.ilk_satir, sec.ilk_sutun) == (sec.son_satir, sec.son_sutun):
            self.ozet_etiketi.setText("")
            return
        sayilar, dolu = [], 0
        hucreler = {(r, c): h for a in g.secimler for r, c, h in g.sayfa.aralikta(a)}
        for h in hucreler.values():                  # üst üste binen aralıklarda hücre bir kez sayılır
            dolu += 1
            if isinstance(h.deger, float):
                sayilar.append(h.deger)
        if not sayilar:
            self.ozet_etiketi.setText(f"Sayım: {dolu}  " if dolu else "")
            return
        toplam = sum(sayilar)
        self.ozet_etiketi.setText(
            f"Ortalama: {goster(toplam / len(sayilar))}    Sayım: {dolu}    "
            f"Toplam: {goster(toplam)}    ")

    # ------------------------------------------------------------------ yakınlaştırma
    def _kaydirici_degisti(self, v: int):
        self.izgara().yakinlastir(v / 100)

    def _yakinlastirma_degisti(self, oran: float):
        if self.sender() is not self.izgara():
            return
        self.yakin_etiketi.setText(f"{round(oran * 100)}%")
        self.yakin_kaydirici.blockSignals(True)
        self.yakin_kaydirici.setValue(round(oran * 100))
        self.yakin_kaydirici.blockSignals(False)
