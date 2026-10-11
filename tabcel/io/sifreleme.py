"""Parolayla şifrelenmiş .xlsx (Excel: Dosya → Bilgi → Çalışma Kitabını Koru → Parolayla Şifrele) — Faz 8b.
Çözme/şifreleme msoffcrypto-tool (MIT) ile; Sözcük'teki `encryption.py` düzeninin Tabcel uyarlaması. Qt yok.

GİZLİLİK: çözülmüş paket yalnız bellekte (BytesIO) tutulur, diske düz yazılmaz; parola yalnız açık pencere süresince
bellekte kalır (ayarlara, son dosyalara, kurtarma kopyasına yazılmaz)."""
import io
import zipfile

import msoffcrypto
import olefile
from msoffcrypto import exceptions as crypto_errors
from msoffcrypto.format.ooxml import OOXMLFile


class YanlisParola(Exception):
    """Girilen parola dosyayı açmıyor."""


class SifrelemeHatasi(OSError):
    """Şifreli dosya okunamadı/yazılamadı; iletisi kullanıcıya gösterilebilir (Türkçe)."""


DOGRULAMA_BASARISIZ = ("Şifreli kayıt doğrulanamadı: yazılan veri aynı parolayla geri açılamadı. Dosyanın üzerine "
                       "yazılmadı; çalışma kitabınız açık duruyor. Parolayı kaldırıp kaydetmeyi deneyin.")


def sifreli_mi(yol: str) -> bool:
    """Dosya parolayla şifreli bir OOXML kabı mı. Hiçbir koşulda hata vermez; karar veremezse False (normal açma yolu
    kendi hatasını gösterir)."""
    try:
        if not olefile.isOleFile(str(yol)):
            return False                                     # ZIP paketi (şifresiz .xlsx) ya da başka biçim
        with open(yol, "rb") as h:
            ofis = msoffcrypto.OfficeFile(h)
            return bool(ofis.is_encrypted()) and ofis.format == "ooxml"
    except Exception:
        return False


def _coz_tutamac(tutamac, parola: str) -> io.BytesIO:
    ofis = msoffcrypto.OfficeFile(tutamac)
    try:
        ofis.load_key(password=parola, verify_password=True)
    except crypto_errors.InvalidKeyError as e:
        raise YanlisParola() from e
    duz = io.BytesIO()
    ofis.decrypt(duz)
    return duz


def coz(kaynak, parola: str) -> io.BytesIO:
    """Parolayı doğrular, paketi yalnız bellekte çözer; başa sarılmış BytesIO (ZIP). `kaynak`: yol ya da bayt."""
    try:
        if isinstance(kaynak, (bytes, bytearray)):
            duz = _coz_tutamac(io.BytesIO(bytes(kaynak)), parola)
        else:
            with open(kaynak, "rb") as h:
                duz = _coz_tutamac(h, parola)
    except YanlisParola:
        raise
    except OSError as e:
        raise SifrelemeHatasi("Dosya okunamadı. Başka bir programda açık ya da erişim izni olmayabilir.") from e
    except Exception as e:
        raise SifrelemeHatasi("Şifreli dosya çözülemedi. Dosya bozuk olabilir ya da bu şifreleme yöntemi "
                              "desteklenmiyor olabilir.") from e
    if not zipfile.is_zipfile(duz):
        raise SifrelemeHatasi("Parola doğru ama içinden geçerli bir çalışma kitabı çıkmadı.")
    duz.seek(0)
    return duz


def sifrele(paket: bytes, parola: str) -> bytes:
    """Bellekteki .xlsx paketini parolayla şifreler; şifreli dosyanın baytlarını döndürür."""
    try:
        cikti = io.BytesIO()
        OOXMLFile(io.BytesIO(paket)).encrypt(parola, cikti)
    except Exception as e:
        raise SifrelemeHatasi("Çalışma kitabı şifrelenemedi.") from e
    return cikti.getvalue()


def dogrula(veri: bytes, parola: str, paket: bytes) -> bool:
    """Şifreli baytlar aynı parolayla çözülünce paketin kendisi mi çıkıyor (kütüphanenin şifreleme özelliği
    "deneysel" olduğu için her şifreli kayıttan önce denetlenir)."""
    try:
        return coz(veri, parola).getvalue() == paket
    except Exception:
        return False
