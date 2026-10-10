"""Resim dosyasından `Resim` nesnesi (Faz 6 / 6g; `faz6_tasarim.md` §9). Qt yok; Pillow (HPND) yalnız doğrulama
ve boyut için kullanılır — baytlar aynen saklanır (.xlsx'e kayıpsız yazılsın)."""
import io
import os
from typing import Tuple

from .grafik import Konum, Resim, nesne_baslangic_olcusu

EN_BUYUK_BAYT = 25 * 1024 * 1024
BICIMLER = {"PNG", "JPEG", "GIF", "BMP"}
UZANTILAR = "*.png *.jpg *.jpeg *.gif *.bmp"
HATA_ACILAMADI = "Bu dosya resim olarak açılamadı"


def resim_coz(veri: bytes) -> Tuple[int, int]:
    """Baytlardan (genişlik, yükseklik) piksel; desteklenmeyen/bozuk içerikte `ValueError`."""
    from PIL import Image
    if not veri:
        raise ValueError(HATA_ACILAMADI)
    if len(veri) > EN_BUYUK_BAYT:
        raise ValueError("Resim çok büyük (en çok 25 MB)")
    try:
        with Image.open(io.BytesIO(veri)) as im:
            bicim = im.format
            im.verify()
            g, y = im.size
    except Exception:
        raise ValueError(HATA_ACILAMADI) from None
    if bicim not in BICIMLER or g < 1 or y < 1:
        raise ValueError("Desteklenen resim türleri: PNG, JPEG, GIF, BMP")
    return g, y


def resim_olustur(veri: bytes, ad: str = "", konum: Konum = Konum()) -> Resim:
    """Baytlardan `Resim` (kimliksiz): doğal boyut (96 dpi), en çok 600 px genişlik, oran korunur."""
    g, y = resim_coz(veri)
    return Resim(veri=veri, ad=ad, konum=konum, boyut=nesne_baslangic_olcusu(g, y))


def resim_yukle(yol: str, konum: Konum = Konum()) -> Resim:
    """Dosyadan `Resim`; okunamayan/çok büyük/bozuk dosyada `ValueError` (iletisi kullanıcıya gösterilir)."""
    try:
        if os.path.getsize(yol) > EN_BUYUK_BAYT:
            raise ValueError("Resim çok büyük (en çok 25 MB)")
        with open(yol, "rb") as f:
            veri = f.read()
    except OSError:
        raise ValueError(HATA_ACILAMADI) from None
    return resim_olustur(veri, os.path.basename(yol), konum)
