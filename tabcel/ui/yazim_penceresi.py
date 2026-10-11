"""Yazım Denetimi penceresi (Faz 7c, F7): yanlış sözcük bağlamıyla gösterilir; öneri listesi, Değiştir / Tümünü
Değiştir / Yoksay / Tümünü Yoksay. Mantık `model/yazim.YazimOturumu`da; burası yalnız arayüz."""
import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, QVBoxLayout,
)

from .. import APP_NAME
from ..model.adres import hucre_yaz
from ..model.yazim import Bulgu, YazimOturumu
from . import theme


class YazimPenceresi(QDialog):
    def __init__(self, oturum: YazimOturumu, ust=None, git=None):
        super().__init__(ust)
        self.oturum = oturum
        self._git = git                                    # (satır, sütun) → ızgarada o hücreye git
        self.setWindowTitle("Yazım Denetimi")
        self.setMinimumWidth(480)
        d = QVBoxLayout(self)
        self.konum = QLabel()
        self.konum.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        d.addWidget(self.konum)
        self.baglam = QLabel()
        self.baglam.setWordWrap(True)
        self.baglam.setTextFormat(Qt.RichText)
        d.addWidget(self.baglam)
        self.yerine = QLineEdit()
        self.yerine.setPlaceholderText("Yerine konacak sözcük")
        d.addWidget(self.yerine)
        self.oneri_listesi = QListWidget()
        self.oneri_listesi.setMaximumHeight(120)
        self.oneri_listesi.currentTextChanged.connect(lambda t: t and self.yerine.setText(t))
        self.oneri_listesi.itemDoubleClicked.connect(lambda _i: self._degistir(False))
        d.addWidget(self.oneri_listesi)
        sira = QHBoxLayout()
        self.dugmeler = {}
        for ad, islev in (("Yoksay", lambda: self._sonuc(self.oturum.yoksay())),
                          ("Tümünü Yoksay", lambda: self._sonuc(self.oturum.tumunu_yoksay())),
                          ("Değiştir", lambda: self._degistir(False)),
                          ("Tümünü Değiştir", lambda: self._degistir(True))):
            b = QPushButton(ad)
            b.clicked.connect(lambda _=False, f=islev: f())
            self.dugmeler[ad] = b
            sira.addWidget(b)
        d.addLayout(sira)
        kapat = QPushButton("Kapat")
        kapat.clicked.connect(self.reject)
        d.addWidget(kapat)
        self.bitti = False

    def baslat(self) -> bool:
        """İlk yanlışı bulur; hiç yoksa bildirir ve False döner (pencere açılmaz)."""
        self._sonuc(self.oturum.ara())
        return not self.bitti

    def _degistir(self, tumu: bool) -> None:
        yerine = self.yerine.text()
        if not yerine:
            return
        self._sonuc(self.oturum.tumunu_degistir(yerine) if tumu else self.oturum.degistir(yerine))

    def _sonuc(self, b) -> None:
        if b is None:
            self.bitti = True
            self.konum.setText("")
            self.baglam.setText("Yazım denetimi tamamlandı.")
            self.oneri_listesi.clear()
            self.yerine.clear()
            for d in self.dugmeler.values():
                d.setEnabled(False)
            return
        self._goster(b)

    def _goster(self, b: Bulgu) -> None:
        self.konum.setText(f"{hucre_yaz(b.satir, b.sutun)} hücresinde")
        on = html.escape(b.metin[:b.baslangic])
        so = html.escape(b.metin[b.baslangic + b.uzunluk:])
        self.baglam.setText(f"{on}<span style='color:#c00000;font-weight:bold'>{html.escape(b.sozcuk)}</span>{so}")
        oneriler = self.oturum.oneriler()
        self.oneri_listesi.blockSignals(True)
        self.oneri_listesi.clear()
        self.oneri_listesi.addItems(oneriler)
        self.oneri_listesi.blockSignals(False)
        self.yerine.setText(oneriler[0] if oneriler else b.sozcuk)
        self.yerine.selectAll()
        for ad in ("Değiştir", "Tümünü Değiştir"):
            self.dugmeler[ad].setEnabled(True)
        if self._git:
            self._git(b.satir, b.sutun)
