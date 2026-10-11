"""“Ne yapmak istiyorsun?” penceresi (Faz 8f): cümle yaz → öneriler → önizleme → Uygula. Mantık `formul/asistan.py`da."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, QVBoxLayout,
)

from ..formul import asistan
from ..model.adres import hucre_yaz
from . import theme


class AsistanPenceresi(QDialog):
    def __init__(self, tablo, etkin, ust=None):
        super().__init__(ust)
        self.setWindowTitle("Ne yapmak istiyorsun?")
        self.setMinimumWidth(560)
        self.tablo, self.etkin = tablo, etkin
        self.secilen = None
        d = QVBoxLayout(self)
        ar = tablo.aralik
        self.tablo_etiketi = QLabel(
            f"Tablo: {hucre_yaz(ar.ilk_satir, ar.ilk_sutun)}:{hucre_yaz(ar.son_satir, ar.son_sutun)}  ·  "
            f"sütunlar: {', '.join(tablo.basliklar)}")
        self.tablo_etiketi.setWordWrap(True)
        self.tablo_etiketi.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        d.addWidget(self.tablo_etiketi)
        satir = QHBoxLayout()
        self.girdi = QLineEdit()
        self.girdi.setPlaceholderText("ör. " + asistan.ORNEKLER[1])
        self.oner = QPushButton("Öner")
        self.oner.setDefault(True)
        satir.addWidget(self.girdi, 1)
        satir.addWidget(self.oner)
        d.addLayout(satir)
        self.liste = QListWidget()
        self.liste.setMaximumHeight(110)
        d.addWidget(self.liste)
        self.ayrinti = QLabel("")
        self.ayrinti.setWordWrap(True)
        self.ayrinti.setTextFormat(Qt.PlainText)
        self.ayrinti.setMinimumHeight(110)
        self.ayrinti.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        d.addWidget(self.ayrinti)
        alt = QHBoxLayout()
        alt.addStretch(1)
        self.uygula = QPushButton("Uygula")
        self.uygula.setEnabled(False)
        iptal = QPushButton("İptal")
        alt.addWidget(self.uygula)
        alt.addWidget(iptal)
        d.addLayout(alt)
        self.oner.clicked.connect(self.sor)
        self.girdi.returnPressed.connect(self.sor)
        self.liste.currentRowChanged.connect(self._sec)
        self.liste.itemDoubleClicked.connect(lambda _i: self.uygula.click())
        self.uygula.clicked.connect(self._onayla)
        iptal.clicked.connect(self.reject)
        self.sonuc = asistan.OneriSonucu()
        self.sor()

    def sor(self) -> None:
        self.sonuc = asistan.anla(self.girdi.text(), self.tablo, self.etkin)
        self.liste.clear()
        self.liste.addItems([o.baslik for o in self.sonuc.oneriler])
        if self.sonuc.oneriler:
            self.liste.setCurrentRow(0)
        else:
            self.secilen = None
            self.uygula.setEnabled(False)
            self.ayrinti.setText(self.sonuc.mesaj)

    def _sec(self, i: int) -> None:
        if not 0 <= i < len(self.sonuc.oneriler):
            return
        o = self.sonuc.oneriler[i]
        self.secilen = o
        yer = (f"Yazılacak yer: {hucre_yaz(*o.hedef)}" if o.hedef else "Yazılacak yer: yeni sayfa")
        self.ayrinti.setText(f"{o.aciklama}\n\n{o.onizleme}\n\n{yer}")
        self.uygula.setEnabled(True)

    def _onayla(self) -> None:
        if self.secilen is not None:
            self.accept()
