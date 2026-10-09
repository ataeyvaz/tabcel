"""Görsel tema renkleri. Sözcük'ün theme.py dosyası örnek alınır; Excel yeşili vurgu.

Stil sayfası ve başlık çubuğu rengi pencere işiyle birlikte eklenecek.
"""

ACCENT = "#217346"
ACCENT_DARK = "#1a5c38"
TEXT = "#242424"
TEXT_MUTED = "#616161"
WINDOW = "#f3f3f3"
SURFACE = "#ffffff"
BORDER = "#e0e0e0"

# ızgara
GRID_LINE = "#d4d4d4"
HEADER_BG = "#f0f0f0"
HEADER_BG_SELECTED = "#d2e6da"
HEADER_TEXT = "#444444"
HEADER_TEXT_SELECTED = ACCENT_DARK
SELECTION_FILL = "#217346"   # yarı saydam çizilir

UYARI = "#b45309"            # durum çubuğu uyarısı (ör. döngüsel başvuru)

HOVER = "#f0f0f0"
PRESSED = "#e0e0e0"


def stylesheet() -> str:
    return f"""
QMainWindow, #central {{ background: {WINDOW}; }}
QToolTip {{ background: {SURFACE}; color: {TEXT}; border: 1px solid {BORDER};
    padding: 5px 8px; border-radius: 4px; }}

#header {{ background: {ACCENT}; }}
#header QLabel {{ color: #ffffff; }}
#header #docTitle {{ font-weight: 600; }}
#header QToolButton {{ color: #ffffff; border: none; border-radius: 4px;
    padding: 4px 10px; background: transparent; }}
#header QToolButton:hover {{ background: rgba(255,255,255,0.14); }}
#header QToolButton:pressed {{ background: rgba(255,255,255,0.24); }}
#header QToolButton:disabled {{ color: rgba(255,255,255,0.45); }}
#header #fileButton {{ font-weight: 600; }}
#header #fileButton::menu-indicator {{ image: none; }}

#formulaBar {{ background: {SURFACE}; border-bottom: 1px solid {BORDER}; }}
#formulaBar QLineEdit {{ border: 1px solid {BORDER}; border-radius: 3px;
    padding: 2px 6px; background: {SURFACE}; color: {TEXT}; }}
#formulaBar QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
#formulaBar QLabel {{ color: {TEXT_MUTED}; font-style: italic; padding: 0 4px; }}

#sheetBar {{ background: {WINDOW}; border-top: 1px solid {BORDER}; }}
#sheetBar QToolButton {{ border: none; border-radius: 4px; padding: 2px 8px;
    font-size: 14pt; color: {TEXT_MUTED}; }}
#sheetBar QToolButton:hover {{ background: {HOVER}; }}
QTabBar::tab {{ background: transparent; color: {TEXT_MUTED}; padding: 4px 14px;
    border: none; border-top: 2px solid transparent; }}
QTabBar::tab:selected {{ background: {SURFACE}; color: {ACCENT_DARK}; font-weight: 600;
    border-top: 2px solid {ACCENT}; }}
QTabBar::tab:hover:!selected {{ background: {HOVER}; }}

QStatusBar {{ background: {WINDOW}; color: {TEXT_MUTED}; border-top: 1px solid {BORDER}; }}
QStatusBar::item {{ border: none; }}
QSlider::groove:horizontal {{ height: 3px; background: {BORDER}; border-radius: 1px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 1px; }}
QSlider::handle:horizontal {{ background: {ACCENT}; width: 12px; margin: -5px 0;
    border-radius: 6px; }}
QMenu {{ background: {SURFACE}; border: 1px solid {BORDER}; padding: 4px; }}
QMenu::item {{ padding: 5px 22px; border-radius: 3px; }}
QMenu::item:selected {{ background: {HEADER_BG_SELECTED}; color: {TEXT}; }}
"""


def baslik_cubugu_rengi(pencere, renk: str = ACCENT) -> None:
    """Windows 11'de başlık çubuğunu vurgu rengine boyar (DWM); başka sistemlerde sessizce geçer."""
    import sys
    if sys.platform != "win32":
        return
    try:
        import ctypes
        r, g, b = (int(renk[i:i + 2], 16) for i in (1, 3, 5))
        colorref = ctypes.c_int(r | (g << 8) | (b << 16))
        beyaz = ctypes.c_int(0x00FFFFFF)
        hwnd = int(pencere.winId())
        dwm = ctypes.windll.dwmapi
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(colorref), 4)   # DWMWA_CAPTION_COLOR
        dwm.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(beyaz), 4)      # DWMWA_TEXT_COLOR
    except Exception:
        pass
