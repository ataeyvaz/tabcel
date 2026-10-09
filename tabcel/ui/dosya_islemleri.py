"""Pencerenin dosya işlemleri (Faz 4 / 4b): Yeni, Aç, Kaydet, Farklı Kaydet, kapatırken sorma, veri kaybı
uyarısı, son dosyalar. `Pencere` bu karışımı miras alır; her dosya bir pencerede açılır (Excel gibi),
boş ve değişmemiş pencere yerine yenisi açılırsa o pencere kapanır."""
import os
import weakref
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QMenu, QMessageBox, QToolButton,
)

from .. import APP_NAME
from ..io import son_dosyalar, xlsx_io
from ..io.xlsx_io import Rapor, XlsxHatasi
from ..model.sayfa import CalismaKitabi

XLSX_FILTRESI = "Excel Çalışma Kitabı (*.xlsx)"
ACMA_FILTRESI = "Excel Çalışma Kitabı (*.xlsx);;Tüm Dosyalar (*.*)"


def _ayni_yol(a: Optional[str], b: Optional[str]) -> bool:
    return bool(a and b) and os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


class DosyaIslemleri:
    """`Pencere` karışımı. Gerektirdiği alanlar: `kitap`, `yigin`, `belge_adi`, `_baslik_guncelle()`."""

    _acik_pencereler = weakref.WeakSet()                  # aynı dosyayı iki kez açmamak için (zayıf)
    _tutulan: List["DosyaIslemleri"] = []                 # yeni()/dosya_ac() ile açılanlar: kapanana dek canlı

    # ------------------------------------------------------------------ kurulum
    def _dosya_kur(self) -> None:
        self.yol: Optional[str] = None
        self.rapor: Rapor = Rapor()
        self._temiz_damga = self.yigin.damga()
        DosyaIslemleri._acik_pencereler.add(self)
        for tus, islem in (("Ctrl+N", self.yeni), ("Ctrl+O", self.ac_penceresi), ("Ctrl+S", self.kaydet),
                           ("Ctrl+Shift+S", self.farkli_kaydet), ("F12", self.farkli_kaydet)):
            QShortcut(QKeySequence(tus), self, activated=lambda f=islem: f(), context=Qt.WindowShortcut)

    def _bilgi_cubugu_olustur(self) -> QFrame:
        """Açılan dosyada korunamayan öğe varsa uyarı şeridi (kapatılabilir)."""
        b = QFrame()
        b.setObjectName("infoBar")
        b.setStyleSheet("#infoBar { background: #FFF4CE; border-bottom: 1px solid #E0C97A; }"
                        " #infoBar QLabel { color: #5A4A00; }")
        h = QHBoxLayout(b)
        h.setContentsMargins(10, 4, 6, 4)
        self.bilgi_etiketi = QLabel()
        self.bilgi_etiketi.setWordWrap(True)
        kapat = QToolButton()
        kapat.setText("×")
        kapat.setToolTip("Kapat")
        kapat.clicked.connect(b.hide)
        h.addWidget(self.bilgi_etiketi, 1)
        h.addWidget(kapat)
        b.hide()
        return b

    def _bilgi_goster(self) -> None:
        if self.rapor.uyarilar:
            self.bilgi_etiketi.setText("\n".join(self.rapor.uyarilar))
            self.bilgi_cubugu.show()
        else:
            self.bilgi_cubugu.hide()

    def _dosya_menusu_doldur(self, menu: QMenu) -> None:
        menu.addAction("Yeni\tCtrl+N", self.yeni)
        menu.addAction("Aç…\tCtrl+O", self.ac_penceresi)
        menu.addSeparator()
        menu.addAction("Kaydet\tCtrl+S", self.kaydet)
        menu.addAction("Farklı Kaydet…\tCtrl+Shift+S", self.farkli_kaydet)
        menu.addSeparator()
        self.son_menusu = menu.addMenu("Son Kullanılanlar")
        self.son_menusu.aboutToShow.connect(self._son_menusu_hazirla)
        menu.addSeparator()
        menu.addAction("Çıkış", self.close)

    def _son_menusu_hazirla(self) -> None:
        self.son_menusu.clear()
        liste = son_dosyalar.oku()
        if not liste:
            self.son_menusu.addAction("(boş)").setEnabled(False)
            return
        for y in liste:
            self.son_menusu.addAction(os.path.basename(y)).triggered.connect(
                lambda _=False, yol=y: self.dosya_ac(yol))
            self.son_menusu.actions()[-1].setToolTip(y)

    # ------------------------------------------------------------------ durum
    def degisti_mi(self) -> bool:
        """Son kayıt/açılıştan beri geri al yığını değişti mi (geri alıp kayıt noktasına dönülürse hayır)."""
        temiz = getattr(self, "_temiz_damga", None)          # kurulum sırasında henüz yok
        return temiz is not None and not self.yigin.damga_esit(self.yigin.damga(), temiz)

    def _bos_ve_temiz(self) -> bool:
        return (self.yol is None and not self.degisti_mi() and len(self.kitap.sayfalar) == 1
                and self.kitap.sayfalar[0].kullanilan_aralik() is None)

    def _belge_adi_guncelle(self) -> None:
        self.belge_adi = os.path.basename(self.yol) if self.yol else "Adsız"
        self._baslik_guncelle()

    def _isaretle_temiz(self) -> None:
        self._temiz_damga = self.yigin.damga()
        self._baslik_guncelle()

    # ------------------------------------------------------------------ yeni / aç
    def yeni(self):
        """Boş kitapla yeni pencere."""
        from .window import Pencere
        p = Pencere(CalismaKitabi())
        DosyaIslemleri._tutulan.append(p)
        p._dosya_gorunur_yap()
        return p

    def _dosya_gorunur_yap(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def ac_penceresi(self):
        yol, _ = QFileDialog.getOpenFileName(self, "Aç", self._baslangic_klasoru(), ACMA_FILTRESI)
        if yol:
            return self.dosya_ac(yol)
        return None

    def _baslangic_klasoru(self) -> str:
        return os.path.dirname(self.yol) if self.yol else ""

    def dosya_ac(self, yol: str):
        """`yol`u yeni pencerede açar (açıksa o pencereyi öne getirir); başarısızsa None ve ileti."""
        from .window import Pencere
        for p in list(DosyaIslemleri._acik_pencereler):
            if _ayni_yol(p.yol, yol):
                son_dosyalar.ekle(yol)
                p._dosya_gorunur_yap()
                return p
        try:
            kitap, rapor = self._kitap_oku(yol)
        except XlsxHatasi as e:
            son_dosyalar.sil(yol)
            QMessageBox.critical(self, APP_NAME, str(e))
            return None
        p = Pencere(kitap)
        p.yol = os.path.abspath(yol)
        p.rapor = rapor
        p._belge_adi_guncelle()
        p._bilgi_goster()
        son_dosyalar.ekle(yol)
        DosyaIslemleri._tutulan.append(p)
        p._dosya_gorunur_yap()
        if self._bos_ve_temiz() and p is not self:
            self.close()                                     # boş, değişmemiş pencere yerine açıldı
        return p

    @staticmethod
    def _kitap_oku(yol: str):
        if not os.path.exists(yol):
            raise XlsxHatasi(f"Dosya bulunamadı: {yol}")
        return xlsx_io.ac(yol)

    # ------------------------------------------------------------------ kaydet
    def kaydet(self) -> bool:
        if self.yol is None:
            return self.farkli_kaydet()
        if self.rapor.veri_kaybi:
            secim = self._veri_kaybi_sorusu()
            if secim == "farkli":
                return self.farkli_kaydet()
            if secim != "kaydet":
                return False
        return self._kaydet_yola(self.yol)

    def farkli_kaydet(self) -> bool:
        onerilen = self.yol or os.path.join(self._baslangic_klasoru(), "Kitap1.xlsx")
        yol, _ = QFileDialog.getSaveFileName(self, "Farklı Kaydet", onerilen, XLSX_FILTRESI)
        if not yol:
            return False
        if not os.path.splitext(yol)[1]:
            yol += ".xlsx"
        return self._kaydet_yola(yol)

    def _kaydet_yola(self, yol: str) -> bool:
        try:
            xlsx_io.kaydet(self.kitap, yol)
        except XlsxHatasi as e:
            QMessageBox.critical(self, APP_NAME, str(e))
            return False
        self.yol = os.path.abspath(yol)
        self.rapor = Rapor()                                 # artık dosya bu kitabın kendisi: kayıp uyarısı biter
        self._bilgi_goster()
        self._belge_adi_guncelle()
        self._isaretle_temiz()
        son_dosyalar.ekle(yol)
        self.statusBar().showMessage("Kaydedildi", 4000)
        return True

    def _veri_kaybi_sorusu(self) -> str:
        """'farkli' | 'kaydet' | 'iptal'."""
        k = QMessageBox(QMessageBox.Warning, APP_NAME,
                        "Bu dosyada " + APP_NAME + "'in koruyamadığı öğeler var (grafik, resim, koşullu biçim vb.). "
                        "Üzerine kaydederseniz bu öğeler dosyadan çıkar.\n\nÖzgün dosyaya dokunmamak için "
                        "“Farklı Kaydet”i seçin.", parent=self)
        farkli = k.addButton("Farklı Kaydet", QMessageBox.AcceptRole)
        yine = k.addButton("Yine de Kaydet", QMessageBox.DestructiveRole)
        k.addButton("İptal", QMessageBox.RejectRole)
        k.setDefaultButton(farkli)
        k.exec()
        b = k.clickedButton()
        return "farkli" if b is farkli else "kaydet" if b is yine else "iptal"

    # ------------------------------------------------------------------ kapatma
    def _kapatma_sorusu(self) -> str:
        """'kaydet' | 'kaydetme' | 'iptal'."""
        k = QMessageBox(QMessageBox.Question, APP_NAME,
                        f"“{self.belge_adi}” içindeki değişiklikler kaydedilsin mi?", parent=self)
        kay = k.addButton("Kaydet", QMessageBox.AcceptRole)
        kayma = k.addButton("Kaydetme", QMessageBox.DestructiveRole)
        k.addButton("İptal", QMessageBox.RejectRole)
        k.setDefaultButton(kay)
        k.exec()
        b = k.clickedButton()
        return "kaydet" if b is kay else "kaydetme" if b is kayma else "iptal"

    def _kapanabilir_mi(self) -> bool:
        if not self.degisti_mi():
            return True
        c = self._kapatma_sorusu()
        if c == "kaydet":
            return self.kaydet()
        return c == "kaydetme"

    def _pencere_kapandi(self) -> None:
        DosyaIslemleri._acik_pencereler.discard(self)
        if self in DosyaIslemleri._tutulan:
            DosyaIslemleri._tutulan.remove(self)
