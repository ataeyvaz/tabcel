"""Özet Tablo Oluştur penceresi (Faz 8d): kaynak aralık, satır/sütun/değer alanları, hedef. Mantık `model/ozet.py`da."""
from typing import List, Optional, Tuple

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QRadioButton, QVBoxLayout,
)

from .. import APP_NAME
from ..model.adres import Aralik, AdresHatasi, aralik_coz, aralik_yaz, hucre_coz
from ..model.ozet import ISLEVLER, DegerAlani, OzetTanimi, baslik_oku

YOK = "(yok)"
DEGER_YUVASI = 3                                           # en çok değer alanı


class OzetPenceresi(QDialog):
    def __init__(self, sayfa, kaynak: Aralik, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Özet Tablo Oluştur")
        self.setMinimumWidth(460)
        self.sayfa = sayfa
        d = QVBoxLayout(self)
        form = QFormLayout()
        self.kaynak_kutusu = QLineEdit(aralik_yaz(kaynak))
        self.kaynak_kutusu.setToolTip("İlk satır alan başlıklarıdır")
        form.addRow("Kaynak aralık:", self.kaynak_kutusu)
        self.satir_kutusu, self.sutun_kutusu = QComboBox(), QComboBox()
        form.addRow("Satırlar:", self.satir_kutusu)
        form.addRow("Sütunlar:", self.sutun_kutusu)
        d.addLayout(form)
        degerler = QGroupBox("Değerler")
        dv = QVBoxLayout(degerler)
        self.deger_alanlari: List[QComboBox] = []
        self.deger_islevleri: List[QComboBox] = []
        for i in range(DEGER_YUVASI):
            satir = QHBoxLayout()
            a, f = QComboBox(), QComboBox()
            f.addItems(ISLEVLER)
            a.setMinimumWidth(200)
            satir.addWidget(a, 1)
            satir.addWidget(f)
            dv.addLayout(satir)
            self.deger_alanlari.append(a)
            self.deger_islevleri.append(f)
        d.addWidget(degerler)
        self.satir_toplami = QCheckBox("Satırlar için genel toplam (sağda sütun)")
        self.sutun_toplami = QCheckBox("Sütunlar için genel toplam (altta satır)")
        self.satir_toplami.setChecked(True)
        self.sutun_toplami.setChecked(True)
        d.addWidget(self.satir_toplami)
        d.addWidget(self.sutun_toplami)
        hedef = QGroupBox("Özet tablonun yerleştirileceği yer")
        hv = QVBoxLayout(hedef)
        self.yeni_sayfa = QRadioButton("Yeni sayfa")
        self.mevcut = QRadioButton("Bu sayfada, şu hücreden başlayarak:")
        self.yeni_sayfa.setChecked(True)
        self.hedef_hucre = QLineEdit("H1")
        self.hedef_hucre.setEnabled(False)
        self.mevcut.toggled.connect(self.hedef_hucre.setEnabled)
        hv.addWidget(self.yeni_sayfa)
        satir = QHBoxLayout()
        satir.addWidget(self.mevcut)
        satir.addWidget(self.hedef_hucre)
        hv.addLayout(satir)
        d.addWidget(hedef)
        self.not_etiketi = QLabel("Özet tablo bir anlık görüntüdür: kaynak değişince kendiliğinden güncellenmez.")
        self.not_etiketi.setWordWrap(True)
        d.addWidget(self.not_etiketi)
        dugmeler = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dugmeler.button(QDialogButtonBox.Ok).setText("Tamam")
        dugmeler.button(QDialogButtonBox.Cancel).setText("İptal")
        dugmeler.accepted.connect(self._onayla)
        dugmeler.rejected.connect(self.reject)
        d.addWidget(dugmeler)
        self.kaynak_kutusu.editingFinished.connect(self._alanlari_doldur)
        self._alanlari_doldur(varsayilan=True)

    # ------------------------------------------------------------------ alanlar
    def _kaynak(self) -> Optional[Aralik]:
        try:
            a = aralik_coz(self.kaynak_kutusu.text())
        except (AdresHatasi, ValueError):
            return None
        return a if a.son_satir > a.ilk_satir else None

    def _alanlari_doldur(self, varsayilan: bool = False) -> None:
        a = self._kaynak()
        basliklar = baslik_oku(self.sayfa, a) if a else []
        self.basliklar = basliklar
        for kutu, bos in ([(self.satir_kutusu, True), (self.sutun_kutusu, True)]
                          + [(k, True) for k in self.deger_alanlari]):
            eski = kutu.currentText()
            kutu.blockSignals(True)
            kutu.clear()
            kutu.addItems([YOK] + basliklar)
            i = kutu.findText(eski)
            kutu.setCurrentIndex(max(i, 0))
            kutu.blockSignals(False)
        if varsayilan and len(basliklar) >= 2:                  # makul bir başlangıç: ilk alan satır, son alan değer
            self.satir_kutusu.setCurrentIndex(1)
            self.deger_alanlari[0].setCurrentIndex(len(basliklar))

    # ------------------------------------------------------------------ sonuç
    def kaynak(self) -> Optional[Aralik]:
        return self._kaynak()

    def tanim(self) -> OzetTanimi:
        def secili(kutu):
            t = kutu.currentText()
            return None if t == YOK else t
        degerler = tuple(DegerAlani(secili(a), f.currentText())
                         for a, f in zip(self.deger_alanlari, self.deger_islevleri) if secili(a))
        return OzetTanimi(secili(self.satir_kutusu), secili(self.sutun_kutusu), degerler,
                          self.satir_toplami.isChecked(), self.sutun_toplami.isChecked())

    def hedef(self) -> Tuple[bool, Optional[Tuple[int, int]]]:
        """(yeni sayfa mı, (satır, sütun) | None)."""
        if self.yeni_sayfa.isChecked():
            return True, None
        h = hucre_coz(self.hedef_hucre.text())
        return False, (h.satir, h.sutun)

    def _onayla(self) -> None:
        if self._kaynak() is None:
            QMessageBox.warning(self, APP_NAME, "Kaynak aralık geçerli değil (en az başlık + bir veri satırı gerekir).")
            return
        t = self.tanim()
        if not t.degerler:
            QMessageBox.warning(self, APP_NAME, "En az bir değer alanı seçin.")
            return
        if t.satir and t.satir == t.sutun:
            QMessageBox.warning(self, APP_NAME, "Satır ve sütun alanı aynı olamaz.")
            return
        if not self.yeni_sayfa.isChecked():
            try:
                self.hedef()
            except (AdresHatasi, ValueError):
                QMessageBox.warning(self, APP_NAME, "Hedef hücre geçerli değil (ör. H1).")
                return
        self.accept()
