"""Araç çubuğu ikonları (Sözcük'ün icons.py dosyasından uyarlandı; orada değişiklik yapılmaz).

Keskinlik için: şekiller 20 px ızgarada 1 px çizgiyle ve piksel merkezlerine (x,5) hizalı çizilir;
ikon istenen boyutta doğrudan çizilir (IconEngine); harfler gerçek yazı tipiyle çizilir.
"""
from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QIconEngine, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

INK = "#424242"
DISABLED = "#b8b8b8"
GRID = 20

# "text" öğeleri: (metin, piksel boyutu, kalın, italik, (x, y, genişlik, yükseklik) 20'lik ızgarada)
ICONS = {
    "undo": {"svg": "M7.5 4.5L4.5 7.5L7.5 10.5 M4.5 7.5H12A3.5 3.5 0 0 1 12 14.5H9.5"},
    "redo": {"svg": "M12.5 4.5L15.5 7.5L12.5 10.5 M15.5 7.5H8A3.5 3.5 0 0 0 8 14.5H10.5"},
    "bold": {"text": [("B", 15, True, False, (0, 1, 20, 17))]},
    "italic": {"text": [("I", 16, False, True, (0, 1, 20, 17))], "font": "Georgia"},
    "underline": {"svg": "M5.5 17.5H14.5", "text": [("U", 14, False, False, (0, 0, 20, 16))]},
    "strike": {"svg": "M2.5 10.5H17.5", "text": [("ab", 13, False, False, (0, 1, 20, 17))]},
    "font_color": {"text": [("A", 14, False, False, (0, -1, 20, 16))], "bar": True},
    # dolgu kovası: eğik kova + damla; altta seçili renk çubuğu
    "fill_color": {"svg": "M5.5 9.5L10 5 L14.5 9.5 L10 14 Z M10 5V2.5 M16.5 11.5V13.5", "bar": True},
    "grow_font": {"svg": "M13.5 6.5L15.5 4.5L17.5 6.5", "text": [("A", 15, False, False, (0, 1, 14, 18))]},
    "shrink_font": {"svg": "M13.5 4.5L15.5 6.5L17.5 4.5", "text": [("A", 12, False, False, (0, 3, 14, 16))]},
    "align_left": {"svg": "M3.5 4.5H16.5 M3.5 8.5H11.5 M3.5 12.5H16.5 M3.5 16.5H11.5"},
    "align_center": {"svg": "M3.5 4.5H16.5 M6.5 8.5H13.5 M3.5 12.5H16.5 M6.5 16.5H13.5"},
    "align_right": {"svg": "M3.5 4.5H16.5 M8.5 8.5H16.5 M3.5 12.5H16.5 M8.5 16.5H16.5"},
    # dikey hiza: kutu içinde üste / ortaya / alta yaslı çizgiler
    "valign_top": {"svg": "M3.5 3.5H16.5 M6.5 6.5H13.5 M9 9.5H11"},
    "valign_middle": {"svg": "M3.5 10.5H16.5 M6.5 7.5H13.5 M6.5 13.5H13.5"},
    "valign_bottom": {"svg": "M3.5 16.5H16.5 M6.5 13.5H13.5 M9 10.5H11"},
    "wrap": {"svg": "M3.5 5.5H16.5 M3.5 10.5H13.5A2.5 2.5 0 0 1 13.5 15.5H10.5 M12 13.5L10 15.5L12 17.5"
                    " M3.5 15.5H7.5"},
    "indent": {"svg": "M3.5 3.5H16.5 M9.5 7.5H16.5 M9.5 11.5H16.5 M3.5 15.5H16.5 M4 7L6.5 9.5L4 12"},
    "outdent": {"svg": "M3.5 3.5H16.5 M9.5 7.5H16.5 M9.5 11.5H16.5 M3.5 15.5H16.5 M6.5 7L4 9.5L6.5 12"},
    "borders": {"svg": "M3.5 3.5H16.5V16.5H3.5Z M3.5 10H16.5 M10 3.5V16.5"},
    "percent": {"text": [("%", 14, True, False, (0, 0, 20, 19))]},
    "currency": {"text": [("₺", 14, True, False, (0, 0, 20, 19))]},
    "thousands": {"text": [("000", 9, True, False, (0, 0, 20, 19))]},
    "decimal_more": {"svg": "M3.5 11.5L1.5 13.5L3.5 15.5 M1.5 13.5H6.5", "text": [("0,0", 9, False, False, (7, 3, 13, 10))]},
    "decimal_less": {"svg": "M6.5 11.5L8.5 13.5L6.5 15.5 M8.5 13.5H3.5", "text": [("0,0", 9, False, False, (7, 3, 13, 10))]},
    "chevron_down": {"svg": "M6 8L10 12L14 8"},
}

_LIVE_ENGINES = []  # PySide sarmalayıcıları C++ tarafı kullanırken çöp toplanmasın


@lru_cache(maxsize=None)
def _renderer(svg_text):
    return QSvgRenderer(QByteArray(svg_text.encode()))


def _svg(path, color):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {GRID} {GRID}" width="{GRID}" height="{GRID}">'
        f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1" '
        'stroke-linecap="square" stroke-linejoin="round"/></svg>'
    )


def draw(painter, rect, name, color=INK, bar=None):
    """`name` ikonunu `rect` içine çizer. Ölçek 1 iken çizgiler tam piksele oturur."""
    spec = ICONS[name]
    scale = min(rect.width(), rect.height()) / GRID
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)
    ox = round(rect.x() + (rect.width() - GRID * scale) / 2)
    oy = round(rect.y() + (rect.height() - GRID * scale) / 2)
    painter.translate(ox, oy)
    ink = QColor(color)

    if "svg" in spec:
        _renderer(_svg(spec["svg"], ink.name())).render(painter, QRectF(0, 0, GRID * scale, GRID * scale))

    for text, px, bold, italic, (x, y, w, h) in spec.get("text", []):
        font = QFont(spec.get("font", "Segoe UI"))
        font.setPixelSize(max(6, round(px * scale)))
        font.setBold(bold)
        font.setItalic(italic)
        font.setHintingPreference(QFont.PreferFullHinting)
        painter.setFont(font)
        painter.setPen(ink)
        painter.drawText(QRectF(x * scale, y * scale, w * scale, h * scale), Qt.AlignCenter, text)

    if spec.get("bar") and bar and bar != "none":
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(bar))
        painter.drawRect(QRectF(round(3 * scale), round(15 * scale), round(14 * scale), max(3, round(4 * scale))))
    painter.restore()


class IconEngine(QIconEngine):
    def __init__(self, name, color=INK, bar=None):
        super().__init__()
        self.name, self.color, self.bar = name, color, bar

    def _color(self, mode):
        return DISABLED if mode == QIcon.Disabled else self.color

    def paint(self, painter, rect, mode, state):
        bar = self.bar if mode != QIcon.Disabled or not self.bar else DISABLED
        draw(painter, QRectF(rect), self.name, self._color(mode), bar)

    def pixmap(self, size, mode, state):
        return self.scaledPixmap(size, mode, state, 1.0)

    def scaledPixmap(self, size, mode, state, scale):
        pixmap = QPixmap(QSize(round(size.width() * scale), round(size.height() * scale)))
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        self.paint(painter, pixmap.rect(), mode, state)
        painter.end()
        pixmap.setDevicePixelRatio(scale)
        return pixmap

    def clone(self):
        engine = IconEngine(self.name, self.color, self.bar)
        _LIVE_ENGINES.append(engine)
        return engine


@lru_cache(maxsize=None)
def icon(name, color=INK, bar=None):
    engine = IconEngine(name, color, bar)
    _LIVE_ENGINES.append(engine)
    return QIcon(engine)
