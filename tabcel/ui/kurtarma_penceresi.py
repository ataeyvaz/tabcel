"""Çökme sonrası kurtarma önerisi (Faz 4 / 4e)."""
import time
from typing import List, Optional, Tuple

from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QDialogButtonBox, QLabel, QListWidget, QListWidgetItem, QVBoxLayout,
)

from .. import APP_NAME
from ..io.kurtarma import Kurtarilabilir


class KurtarmaPenceresi(QDialog):
    """`eylem()`: "ac" | "sil" | "sonra"; `secilenler()`: seçili kopyalar (varsayılan hepsi)."""

    def __init__(self, liste: List[Kurtarilabilir], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Belge Kurtarma — {APP_NAME}")
        self.resize(480, 320)
        self._liste = liste
        self._eylem = "sonra"
        self.liste_kutusu = QListWidget()
        self.liste_kutusu.setSelectionMode(QAbstractItemView.ExtendedSelection)
        for k in liste:
            zaman = time.strftime("%d.%m.%Y %H:%M", time.localtime(k.zaman))
            oge = QListWidgetItem(f"{k.ad} — {zaman}")
            oge.setToolTip(k.yol or "Kaydedilmemiş belge")
            self.liste_kutusu.addItem(oge)
        self.liste_kutusu.selectAll()
        d = QVBoxLayout(self)
        d.addWidget(QLabel(f"{APP_NAME} beklenmedik şekilde kapanmış. Kaydedilmemiş değişiklikleri "
                           "içeren belgeler kurtarılabilir:"))
        d.addWidget(self.liste_kutusu, 1)
        dugmeler = QDialogButtonBox()
        self.ac_dugmesi = dugmeler.addButton("Seçilenleri Aç", QDialogButtonBox.AcceptRole)
        self.sil_dugmesi = dugmeler.addButton("Seçilenleri Sil", QDialogButtonBox.DestructiveRole)
        self.sonra_dugmesi = dugmeler.addButton("Sonra Sor", QDialogButtonBox.RejectRole)
        self.ac_dugmesi.clicked.connect(lambda: self._bitir("ac"))
        self.sil_dugmesi.clicked.connect(lambda: self._bitir("sil"))
        self.sonra_dugmesi.clicked.connect(lambda: self._bitir("sonra"))
        d.addWidget(dugmeler)

    def _bitir(self, eylem: str) -> None:
        self._eylem = eylem
        self.accept() if eylem != "sonra" else self.reject()

    def eylem(self) -> str:
        return self._eylem

    def secilenler(self) -> List[Kurtarilabilir]:
        satirlar = {self.liste_kutusu.row(i) for i in self.liste_kutusu.selectedItems()}
        return [k for i, k in enumerate(self._liste) if i in satirlar]
