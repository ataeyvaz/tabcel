"""CSV içe aktarma penceresi (Faz 4 / 4c): kodlama ve ayraç seçimi, canlı önizleme, "metin olarak al"."""
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHeaderView, QLabel, QTableWidget,
    QTableWidgetItem, QVBoxLayout,
)

from .. import APP_NAME
from ..io import csv_io

ONIZLEME_BAYT = 200_000


class CsvAlmaPenceresi(QDialog):
    """Dosya baytları bir kez okunur; kodlama/ayraç değişince önizleme (ilk ~200 KB) yeniden çözülür.
    `Tamam` sonrası `satirlar()` tüm dosyayı seçili ayarlarla ayrıştırır."""

    def __init__(self, yol: str, veri: bytes, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Metin Alma — {APP_NAME}")
        self.resize(640, 460)
        self._veri = veri
        self._yol = yol
        tani = csv_io.kodlama_tani(veri)
        form = QFormLayout()
        self.kodlama = QComboBox()
        for ad, kod in csv_io.KODLAMALAR.items():
            self.kodlama.addItem(ad, kod)
        self.kodlama.setCurrentIndex(max(0, self.kodlama.findData(tani)))
        self.ayrac = QComboBox()
        for ad, a in csv_io.AYRACLAR.items():
            self.ayrac.addItem(ad, a)
        self.ayrac.setCurrentIndex(max(0, self.ayrac.findData(
            csv_io.ayrac_tani(csv_io.coz(veri[:ONIZLEME_BAYT], tani)))))
        self.metin_olarak = QCheckBox("Tüm alanları metin olarak al (sayı/tarih/formül çevrilmesin)")
        form.addRow("Dosya kodlaması:", self.kodlama)
        form.addRow("Ayraç:", self.ayrac)
        self.tablo = QTableWidget()
        self.tablo.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tablo.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.bilgi = QLabel()
        dugmeler = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dugmeler.button(QDialogButtonBox.Ok).setText("Aç")
        dugmeler.button(QDialogButtonBox.Cancel).setText("İptal")
        dugmeler.accepted.connect(self.accept)
        dugmeler.rejected.connect(self.reject)
        d = QVBoxLayout(self)
        d.addLayout(form)
        d.addWidget(self.metin_olarak)
        d.addWidget(self.tablo, 1)
        d.addWidget(self.bilgi)
        d.addWidget(dugmeler)
        self.kodlama.currentIndexChanged.connect(self._onizle)
        self.ayrac.currentIndexChanged.connect(self._onizle)
        self._onizle()

    def secili_kodlama(self) -> str:
        return self.kodlama.currentData()

    def secili_ayrac(self) -> str:
        return self.ayrac.currentData()

    def _onizle(self) -> None:
        parca = self._veri[:ONIZLEME_BAYT]
        metin = csv_io.coz(parca, self.secili_kodlama())
        if len(self._veri) > ONIZLEME_BAYT and "\n" in metin:
            metin = metin[:metin.rindex("\n")]                 # yarım satırı önizlemeden at
        try:
            satirlar = csv_io.satirlari_oku(metin, self.secili_ayrac())[:50]
        except csv_io.CsvHatasi as e:
            satirlar = []
            self.bilgi.setText(str(e))
        genis = max((len(s) for s in satirlar), default=0)
        self.tablo.clear()
        self.tablo.setRowCount(len(satirlar))
        self.tablo.setColumnCount(genis)
        for r, s in enumerate(satirlar):
            for c, a in enumerate(s):
                self.tablo.setItem(r, c, QTableWidgetItem(a))
        if satirlar:
            self.bilgi.setText(f"Önizleme: ilk {len(satirlar)} satır, {genis} sütun")

    def satirlar(self) -> List[List[str]]:
        metin = csv_io.coz(self._veri, self.secili_kodlama())
        return csv_io.satirlari_oku(metin, self.secili_ayrac())

    def metin_olarak_mi(self) -> bool:
        return self.metin_olarak.isChecked()


def csv_ayarlari_sor(yol: str, parent=None) -> Optional[tuple]:
    """Pencereyi gösterir; (satırlar, metin_olarak) ya da iptalde None. Dosya okunamazsa CsvHatasi."""
    try:
        with open(yol, "rb") as f:
            veri = f.read()
    except FileNotFoundError as e:
        raise csv_io.CsvHatasi(f"Dosya bulunamadı: {yol}") from e
    except OSError as e:
        raise csv_io.CsvHatasi(f"Dosya açılamadı: {e.strerror or e}") from e
    p = CsvAlmaPenceresi(yol, veri, parent)
    if p.exec() != QDialog.Accepted:
        return None
    return p.satirlar(), p.metin_olarak_mi()
