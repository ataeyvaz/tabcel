"""Excel ölçü birimleri ⇄ piksel (100% yakınlaştırma). Qt yok.

Sütun genişliği Excel'de "karakter" (Calibri 11'de bir rakamın genişliği ≈ 7 px, +5 px dolgu):
8,43 karakter ≈ 64 px. Satır yüksekliği punto: 15 pt = 20 px (96 dpi → 1 pt = 4/3 px).
Birebir değil, yaklaşık dönüşümdür; .xlsx G/Ç'de (Faz 4) kesin değerler sınanacak.
"""

SUTUN_PX_KARAKTER = 7
SUTUN_DOLGU_PX = 5
MIN_GENISLIK_PX = 3
MAX_GENISLIK_PX = 1790       # ≈ 255 karakter
MIN_YUKSEKLIK_PX = 3
MAX_YUKSEKLIK_PX = 545       # ≈ 409 pt


def karakter_px(karakter: float) -> int:
    return round(karakter * SUTUN_PX_KARAKTER + SUTUN_DOLGU_PX)


def px_karakter(px: float) -> float:
    return round((px - SUTUN_DOLGU_PX) / SUTUN_PX_KARAKTER, 2)


def punto_px(punto: float) -> int:
    return round(punto * 4 / 3)


def px_punto(px: float) -> float:
    return round(px * 3 / 4, 2)


def genislik_sinirla(px: float) -> int:
    return int(min(max(round(px), MIN_GENISLIK_PX), MAX_GENISLIK_PX))


def yukseklik_sinirla(px: float) -> int:
    return int(min(max(round(px), MIN_YUKSEKLIK_PX), MAX_YUKSEKLIK_PX))
