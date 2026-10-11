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
    "dialog_launcher": {"svg": "M4.5 4.5H15.5V15.5H4.5Z M10.5 14.5L14.5 10.5 M14.5 13.5V10.5H11.5"},
    "merge": {"svg": "M3.5 3.5H16.5V16.5H3.5Z M6 10H14 M11.5 7.5L14 10L11.5 12.5 M8.5 7.5L6 10L8.5 12.5"},
    # biçim boyacısı: fırça (sap + tüy bloğu)
    "format_painter": {"svg": "M4.5 3.5H14.5V7.5H4.5Z M14.5 5.5H16.5V10.5H9.5V13 M8 13H11V16.5H8Z"},
    "chevron_down": {"svg": "M6 8L10 12L14 8"},
    # --- şerit (5j-2): 20 px küçük ikonlar ---
    "cut": {"svg": "M6.5 13L13 3.5 M13.5 13L7 3.5 M3 15.5A2.5 2.5 0 1 0 8 15.5A2.5 2.5 0 1 0 3 15.5"
                   " M12 15.5A2.5 2.5 0 1 0 17 15.5A2.5 2.5 0 1 0 12 15.5"},
    "copy": {"svg": "M7.5 7.5H15.5V16.5H7.5Z M5.5 12.5H4.5V3.5H12.5V6.5"},
    "autosum": {"svg": "M14.5 4.5H5.5L10.5 10L5.5 15.5H14.5"},
    "fill": {"svg": "M10.5 3.5V13.5 M6.5 9.5L10.5 13.5L14.5 9.5 M4.5 16.5H16.5"},
    "clear": {"svg": "M3.5 11.5L10.5 4.5L16.5 10.5L12.5 14.5H7.5Z M7 8L13 14 M10.5 16.5H16.5"},
    "sort_az": {"svg": "M16.5 3.5V15.5 M14 13L16.5 15.5L19 13",
                "text": [("A", 8, True, False, (1, 2, 11, 8)), ("Z", 8, True, False, (1, 10, 11, 8))]},
    "sort_za": {"svg": "M16.5 3.5V15.5 M14 13L16.5 15.5L19 13",
                "text": [("Z", 8, True, False, (1, 2, 11, 8)), ("A", 8, True, False, (1, 10, 11, 8))]},
    "filter_clear": {"svg": "M3.5 4.5H15.5L10.5 10.5V16.5L8.5 15V10.5Z M13 12.5L17.5 17 M17.5 12.5L13 17"},
    "reapply": {"svg": "M3.5 4.5H15.5L10.5 10.5V15.5L8.5 14V10.5Z M17.5 13.5A3 3 0 1 1 15 11 M17.5 11V13.5H15"},
    "define_name": {"svg": "M3.5 3.5H10L16.5 10L10 16.5L3.5 10Z M6.5 6.5H7.5V7.5H6.5Z"},
    "note_delete": {"svg": "M3.5 3.5H13.5V12.5H8.5L5.5 15.5V12.5H3.5Z M14 14L18 18 M18 14L14 18"},
    "save": {"svg": "M3.5 3.5H14.5L16.5 5.5V16.5H3.5Z M6.5 3.5V7.5H13.5V3.5 M6.5 16.5V11.5H13.5V16.5"},
    # --- şerit (5j-2): 32 px büyük ikonlar (kendi 32'lik ızgarasında, 1 px çizgi) ---
    "paste32": {"grid": 32, "svg": "M5.5 6.5H11.5V4.5H17.5V6.5H23.5V12.5 M5.5 6.5V27.5H15.5"
                                   " M13.5 12.5H26.5V27.5H13.5Z M16.5 17.5H23.5 M16.5 21.5H23.5"},
    "cond_format32": {"grid": 32, "svg": "M4.5 5.5H27.5V26.5H4.5Z M4.5 12.5H27.5 M4.5 19.5H27.5 M15.5 5.5V26.5"
                                         " M7.5 9H12.5 M7.5 16H10.5 M7.5 23H12.5 M18.5 9H24.5 M18.5 16H22.5"},
    "insert32": {"grid": 32, "svg": "M4.5 5.5H20.5V21.5H4.5Z M4.5 11.5H20.5 M12.5 5.5V21.5 M24.5 18.5V28.5 M19.5 23.5H29.5"},
    "delete32": {"grid": 32, "svg": "M4.5 5.5H20.5V21.5H4.5Z M4.5 11.5H20.5 M12.5 5.5V21.5 M20.5 20.5L28.5 28.5 M28.5 20.5L20.5 28.5"},
    "format32": {"grid": 32, "svg": "M4.5 5.5H22.5V23.5H4.5Z M4.5 11.5H22.5 M13.5 5.5V23.5"
                                    " M18.5 27.5L26.5 19.5L28.5 21.5L20.5 29.5H18.5Z"},
    "sort_filter32": {"grid": 32, "svg": "M17.5 6.5H28.5L24 14V21.5L22 20V14Z M7.5 5.5V25.5 M4.5 22.5L7.5 25.5L10.5 22.5"
                                         " M12.5 8.5H14.5 M12.5 13.5H14.5"},
    "find32": {"grid": 32, "svg": "M5.5 13.5A8 8 0 1 0 21.5 13.5A8 8 0 1 0 5.5 13.5 M19.5 19.5L27.5 27.5"},
    "sort32": {"grid": 32, "svg": "M9.5 4.5V26.5 M5.5 22.5L9.5 26.5L13.5 22.5 M18.5 7.5H27.5 M18.5 13.5H25.5 M18.5 19.5H23.5"},
    "filter32": {"grid": 32, "svg": "M4.5 5.5H27.5L18.5 16.5V27.5L13.5 24.5V16.5Z"},
    "validation32": {"grid": 32, "svg": "M4.5 4.5H27.5V19.5H4.5Z M9.5 11.5L13 15L20.5 8 M4.5 24.5H27.5 M4.5 28.5H18.5"},
    "name_manager32": {"grid": 32, "svg": "M4.5 5.5H16L26.5 16L16 26.5L4.5 15Z M9.5 10.5H11.5V12.5H9.5Z"},
    "margins32": {"grid": 32, "svg": "M7.5 3.5H25.5V28.5H7.5Z M11.5 7.5H21.5V24.5H11.5Z M3.5 12.5H7.5 M25.5 12.5H29.5"},
    "orientation32": {"grid": 32, "svg": "M5.5 4.5H17.5V22.5H5.5Z M19.5 17.5H29.5V27.5H19.5Z"},
    "paper32": {"grid": 32, "svg": "M7.5 3.5H19.5L25.5 9.5V28.5H7.5Z M19.5 3.5V9.5H25.5 M11.5 15.5H21.5 M11.5 20.5H21.5"},
    "print_area32": {"grid": 32, "svg": "M5.5 5.5H26.5V26.5H5.5Z M10.5 10.5H21.5V21.5H10.5Z"},
    "print_titles32": {"grid": 32, "svg": "M6.5 4.5H25.5V27.5H6.5Z M6.5 11.5H25.5 M13.5 11.5V27.5 M6.5 17.5H25.5 M6.5 22.5H25.5"},
    "note32": {"grid": 32, "svg": "M4.5 5.5H27.5V21.5H15.5L9.5 27.5V21.5H4.5Z M9.5 11.5H22.5 M9.5 16.5H18.5"},
    "freeze32": {"grid": 32, "svg": "M4.5 5.5H27.5V26.5H4.5Z M4.5 12.5H27.5 M12.5 5.5V26.5 M4.5 13.5H27.5 M13.5 5.5V26.5"},
    "zoom100_32": {"grid": 32, "svg": "M5.5 13.5A8 8 0 1 0 21.5 13.5A8 8 0 1 0 5.5 13.5 M19.5 19.5L27.5 27.5",
                   "text": [("100", 8, True, False, (5.5, 9, 16, 9))]},
    "autosum32": {"grid": 32, "svg": "M24.5 6.5H8.5L16.5 16L8.5 25.5H24.5"},
    # --- grafikler (6f): Ekle sekmesi ve Grafik bağlamsal sekmesi, 32 px ---
    "chart32": {"grid": 32, "svg": "M5.5 4.5V27.5H28.5 M9.5 27.5V18.5H13.5V27.5 M16.5 27.5V10.5H20.5V27.5 M23.5 27.5V14.5H27.5V27.5"},
    "chart_sutun32": {"grid": 32, "svg": "M5.5 4.5V27.5H28.5 M9.5 27.5V16.5H14.5V27.5 M18.5 27.5V8.5H23.5V27.5"},
    "chart_cubuk32": {"grid": 32, "svg": "M5.5 4.5V27.5H28.5 M5.5 8.5H24.5V13.5H5.5 M5.5 17.5H16.5V22.5H5.5"},
    "chart_cizgi32": {"grid": 32, "svg": "M5.5 4.5V27.5H28.5 M8.5 22.5L14.5 14.5L20.5 19.5L27.5 8.5"},
    "chart_pasta32": {"grid": 32, "svg": "M5.5 16.5A11 11 0 1 0 27.5 16.5A11 11 0 1 0 5.5 16.5 M16.5 16.5V5.5 M16.5 16.5L26 22"},
    "chart_halka32": {"grid": 32, "svg": "M5.5 16.5A11 11 0 1 0 27.5 16.5A11 11 0 1 0 5.5 16.5"
                                         " M11.5 16.5A5 5 0 1 0 21.5 16.5A5 5 0 1 0 11.5 16.5 M16.5 5.5V11.5 M24.5 22.5L20 19.5"},
    "chart_alan32": {"grid": 32, "svg": "M5.5 4.5V27.5H28.5 M6.5 27.5V22.5L13.5 14.5L20.5 19.5L28.5 9.5V27.5"},
    "chart_dagilim32": {"grid": 32, "svg": "M5.5 4.5V27.5H28.5 M9.5 20.5H11.5V22.5H9.5Z M14.5 13.5H16.5V15.5H14.5Z"
                                           " M20.5 18.5H22.5V20.5H20.5Z M24.5 8.5H26.5V10.5H24.5Z"},
    "chart_degistir32": {"grid": 32, "svg": "M6.5 10.5H24.5 M20.5 6.5L24.5 10.5L20.5 14.5 M25.5 21.5H7.5 M11.5 17.5L7.5 21.5L11.5 25.5"},
    "chart_veri32": {"grid": 32, "svg": "M4.5 4.5H27.5V27.5H4.5Z M4.5 11.5H27.5 M12.5 11.5V27.5"
                                        " M16.5 24.5V18.5H19.5V24.5 M22.5 24.5V15.5H25.5V24.5"},
    "chart_renk32": {"grid": 32, "svg": "M16.5 5.5A11 11 0 1 0 16.5 27.5C19 27.5 19.5 25.5 18.5 24C17.5 22.5 18.5 21 20.5 21H24.5"
                                        "A5 5 0 0 0 27.5 16.5A11 11 0 0 0 16.5 5.5Z M10.5 14.5H12.5V16.5H10.5Z"
                                        " M15.5 10.5H17.5V12.5H15.5Z M21.5 13.5H23.5V15.5H21.5Z"},
    "chart_oge32": {"grid": 32, "svg": "M4.5 5.5H27.5V26.5H4.5Z M9.5 10.5H17.5 M9.5 22.5V15.5H13.5V22.5 M17.5 22.5V13.5H21.5V22.5"},
    "sirala_nesne32": {"grid": 32, "svg": "M4.5 4.5H18.5V18.5H4.5Z M13.5 13.5H27.5V27.5H13.5Z"},
    # --- yardım (Yardım sekmesi) ---
    "picture32": {"grid": 32, "svg": "M4.5 5.5H27.5V26.5H4.5Z M4.5 22.5L11.5 15.5L17.5 21.5L21.5 17.5L27.5 23.5 M20.5 9.5A2 2 0 1 0 24.5 9.5A2 2 0 1 0 20.5 9.5"},
    "help32": {"grid": 32, "svg": "M4.5 16.5A12 12 0 1 0 28.5 16.5A12 12 0 1 0 4.5 16.5", "text": [("?", 16, True, False, (4.5, 4.5, 24, 24))]},
    "keyboard32": {"grid": 32, "svg": "M3.5 8.5H28.5V23.5H3.5Z M7.5 12.5H9.5 M12.5 12.5H14.5 M17.5 12.5H19.5 M22.5 12.5H24.5 M7.5 16.5H9.5 M12.5 16.5H14.5 M17.5 16.5H19.5 M22.5 16.5H24.5 M10.5 20.5H21.5"},
    "spell32": {"grid": 32, "svg": "M4.5 22.5L10.5 6.5L16.5 22.5 M6.7 17.5H14.3 M16.5 23.5L21 28L29 17.5"},
    "pivot32": {"grid": 32, "svg": "M4.5 4.5H27.5V27.5H4.5Z M4.5 11.5H27.5 M11.5 4.5V27.5 M15.5 16.5H23.5 M15.5 21.5H23.5"},
    "asistan32": {"grid": 32, "svg": "M16.5 4.5V9.5 M16.5 23.5V28.5 M4.5 16.5H9.5 M23.5 16.5H28.5 M8 8L11.5 11.5 M21.5 21.5L25 25 M25 8L21.5 11.5 M11.5 21.5L8 25 M12.5 16.5A4 4 0 1 0 20.5 16.5A4 4 0 1 0 12.5 16.5"},
    "trace32": {"grid": 32, "svg": "M5.5 5.5H13.5V12.5H5.5Z M18.5 5.5H26.5V12.5H18.5Z M12.5 22.5H20.5V28.5H12.5Z M9.5 12.5V17.5H22.5V12.5 M16.5 17.5V22.5"},
    "info32": {"grid": 32, "svg": "M4.5 16.5A12 12 0 1 0 28.5 16.5A12 12 0 1 0 4.5 16.5 M16.5 14.5V23.5 M16.5 9.5V11.5"},
}

_LIVE_ENGINES = []  # PySide sarmalayıcıları C++ tarafı kullanırken çöp toplanmasın


@lru_cache(maxsize=None)
def _renderer(svg_text):
    return QSvgRenderer(QByteArray(svg_text.encode()))


def _svg(path, color, grid=GRID):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {grid} {grid}" width="{grid}" height="{grid}">'
        f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1" '
        'stroke-linecap="square" stroke-linejoin="round"/></svg>'
    )


def draw(painter, rect, name, color=INK, bar=None):
    """`name` ikonunu `rect` içine çizer. Ölçek 1 iken çizgiler tam piksele oturur."""
    spec = ICONS[name]
    grid = spec.get("grid", GRID)          # büyük (32 px) şerit ikonları kendi ızgarasında 1 px çizgiyle çizilir
    scale = min(rect.width(), rect.height()) / grid
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)
    ox = round(rect.x() + (rect.width() - grid * scale) / 2)
    oy = round(rect.y() + (rect.height() - grid * scale) / 2)
    painter.translate(ox, oy)
    ink = QColor(color)

    if "svg" in spec:
        _renderer(_svg(spec["svg"], ink.name(), grid)).render(painter, QRectF(0, 0, grid * scale, grid * scale))

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
