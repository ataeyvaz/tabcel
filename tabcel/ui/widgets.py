"""Özel bileşenler: renk seçici düğme (Sözcük'ün widgets.py dosyasından uyarlandı)."""
from PySide6.QtCore import QSize, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog, QGridLayout, QHBoxLayout, QLabel, QMenu, QPushButton, QToolButton, QVBoxLayout,
    QWidget, QWidgetAction,
)

from . import icons, theme

THEME_COLORS = ["#FFFFFF", "#000000", "#E7E6E6", "#44546A", "#4472C4",
                "#ED7D31", "#A5A5A5", "#FFC000", "#5B9BD5", "#70AD47"]
STANDARD_COLORS = ["#C00000", "#FF0000", "#FFC000", "#FFFF00", "#92D050",
                   "#00B050", "#00B0F0", "#0070C0", "#002060", "#7030A0"]


def _tint(hex_color: str, amount: float) -> str:
    """amount > 0 açar, < 0 koyulaştırır (Office tema paleti gibi)."""
    c = QColor(hex_color)
    kanallar = [c.red(), c.green(), c.blue()]
    if amount > 0:
        kanallar = [round(v + (255 - v) * amount) for v in kanallar]
    else:
        kanallar = [round(v * (1 + amount)) for v in kanallar]
    return QColor(*kanallar).name()


class _Ornek(QToolButton):
    def __init__(self, renk: str, boyut: int = 16, parent=None):
        super().__init__(parent)
        self.renk = renk
        self.setFixedSize(boyut + 4, boyut + 4)
        self.setToolTip(renk.upper())
        self.setStyleSheet(
            f"QToolButton {{ background: {renk}; border: 1px solid #d0d0d0; border-radius: 0; margin: 1px; }}"
            f"QToolButton:hover {{ border: 1px solid {theme.ACCENT}; }}")


class _Baslik(QLabel):
    def __init__(self, metin: str):
        super().__init__(metin)
        self.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-weight: 600; padding: 4px 2px 2px 2px;")


class RenkDugmesi(QToolButton):
    """Tıklayınca son rengi uygular; ok kısmı renk paletini açar.

    `renkSecildi`: QColor, ya da "renk yok" (Otomatik / Dolgu yok) için None.
    """
    renkSecildi = Signal(object)

    def __init__(self, ikon: str, ipucu: str, varsayilan: str, yok_metni: str, parent=None):
        super().__init__(parent)
        self.ikon = ikon
        self.simdiki = varsayilan
        self.setToolTip(ipucu)
        self.setPopupMode(QToolButton.MenuButtonPopup)
        self.setIconSize(QSize(20, 20))
        self.clicked.connect(lambda: self.renkSecildi.emit(QColor(self.simdiki) if self.simdiki else None))

        menu = QMenu(self)
        panel = QWidget()
        d = QVBoxLayout(panel)
        d.setContentsMargins(8, 6, 8, 8)
        d.setSpacing(2)
        d.addWidget(self._metin_dugmesi(yok_metni, menu, None))
        d.addWidget(_Baslik("Tema Renkleri"))
        izgara = QGridLayout()
        izgara.setSpacing(0)
        for sutun, taban in enumerate(THEME_COLORS):
            izgara.addWidget(self._ornek(taban, menu), 0, sutun)
            tonlar = ([0.8, 0.6, 0.4, -0.25, -0.5] if taban not in ("#FFFFFF", "#000000") else
                      ([-0.05, -0.15, -0.25, -0.35, -0.5] if taban == "#FFFFFF" else
                       [0.5, 0.35, 0.25, 0.15, 0.05]))
            for satir, miktar in enumerate(tonlar, start=1):
                izgara.addWidget(self._ornek(_tint(taban, miktar), menu), satir, sutun)
        d.addLayout(izgara)
        d.addWidget(_Baslik("Standart Renkler"))
        s = QHBoxLayout()
        s.setSpacing(0)
        for renk in STANDARD_COLORS:
            s.addWidget(self._ornek(renk, menu))
        d.addLayout(s)
        d.addWidget(self._metin_dugmesi("Diğer Renkler…", menu, "daha"))
        eylem = QWidgetAction(menu)
        eylem.setDefaultWidget(panel)
        menu.addAction(eylem)
        self.setMenu(menu)
        self._ikonu_yenile()

    def _ornek(self, renk: str, menu) -> _Ornek:
        o = _Ornek(renk)
        o.clicked.connect(lambda: self.sec(QColor(renk), menu))
        return o

    def _metin_dugmesi(self, metin: str, menu, tur) -> QPushButton:
        b = QPushButton(metin)
        b.setFlat(True)
        b.setStyleSheet(
            "QPushButton { text-align: left; border: none; padding: 5px 6px; border-radius: 4px; min-width: 0; }"
            f"QPushButton:hover {{ background: {theme.HOVER}; }}")
        if tur == "daha":
            b.clicked.connect(lambda: self._daha(menu))
        else:
            b.clicked.connect(lambda: self.sec(None, menu))
        return b

    def _daha(self, menu):
        menu.close()
        renk = QColorDialog.getColor(QColor(self.simdiki or "#000000"), self.window(), "Renk seç")
        if renk.isValid():
            self.sec(renk, None)

    def sec(self, renk, menu=None):
        """Rengi seçer (None = renk yok), ikonu günceller ve `renkSecildi` yayar."""
        if menu:
            menu.close()
        self.simdiki = renk.name().upper() if renk else None
        self._ikonu_yenile()
        self.renkSecildi.emit(renk)

    def _ikonu_yenile(self):
        self.setIcon(icons.icon(self.ikon, bar=self.simdiki or "none"))
