""".csv aç/kaydet (Faz 4 / 4c). Qt yok.

Okuma: kodlama (UTF-8 BOM / UTF-8 / Windows-1254) ve ayraç (`;` `,` sekme `|`) otomatik tanınır; alanlar
hücreye elle yazılmış gibi çözülür (sayı, yüzde, tarih, formül — Türkçe Excel'in CSV açışı gibi), istenirse
hepsi metin kalır. Yazma: etkin sayfa, hücrelerin **görünen** metni (Excel gibi), varsayılan `;` ve UTF-8 BOM
(Türkçe Excel'in doğrudan açtığı biçim).
"""
import csv
import io
from typing import Iterable, List, Optional, Tuple

from ..formul import ceviri
from ..formul.sozcuk import FormulHatasi
from ..model.deger import Hata
from ..model.gosterim import goster
from ..model.sayfa import CalismaKitabi, Hucre, Sayfa, sayfa_adi_dogrula
from ..model.sayi_bicimi import BicimHatasi, bicimle
from ..model.stil import StilYama

AYRACLAR = {"Noktalı virgül (;)": ";", "Virgül (,)": ",", "Sekme": "\t", "Dikey çizgi (|)": "|"}
KODLAMALAR = {"UTF-8 (BOM'lu)": "utf-8-sig", "UTF-8": "utf-8", "Windows-1254 (Türkçe)": "cp1254"}
ONIZLEME_SATIR = 200
MAKS_SATIR = 1_048_576
MAKS_SUTUN = 16_384


class CsvHatasi(Exception):
    """Dosya okunamadı/yazılamadı (kullanıcıya gösterilecek ileti)."""


def kodlama_tani(veri: bytes) -> str:
    """BOM → `utf-8-sig`; geçerli UTF-8 → `utf-8`; aksi `cp1254` (Türkçe Windows)."""
    if veri.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    try:
        veri.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "cp1254"


def coz(veri: bytes, kodlama: str) -> str:
    try:
        return veri.decode(kodlama)
    except UnicodeDecodeError:
        return veri.decode(kodlama, errors="replace")
    except LookupError as e:
        raise CsvHatasi(f"Bilinmeyen kodlama: {kodlama}") from e


def ayrac_tani(metin: str) -> str:
    """İlk ~30 dolu satırda tırnak dışındaki her adayın sayısına bakar: en tutarlı (her satırda aynı
    sayıda, ≥1) aday seçilir; eşitlikte `;` `,` sekme `|` sırası (Türkçe Excel `;` kullanır).
    Hiçbiri yoksa `;`."""
    satirlar = [s for s in _mantiksal_satirlar(metin, 30) if s.strip()]
    en_iyi, en_puan = ";", (0, 0)
    for aday in (";", ",", "\t", "|"):
        sayilar = [_tirnak_disi_say(s, aday) for s in satirlar]
        if not sayilar or max(sayilar) == 0:
            continue
        ortak = max(set(sayilar), key=sayilar.count)       # en sık görülen sayı
        if ortak == 0:
            continue
        uyan = sayilar.count(ortak)
        puan = (uyan, ortak)
        if puan > en_puan:
            en_iyi, en_puan = aday, puan
    return en_iyi


def _mantiksal_satirlar(metin: str, sinir: int) -> List[str]:
    """Tırnak içindeki satır sonlarını bölmeden ilk `sinir` mantıksal satır."""
    satirlar, kisim, tirnak = [], [], False
    for ch in metin:
        if ch == '"':
            tirnak = not tirnak
        if ch in "\r\n" and not tirnak:
            if kisim:
                satirlar.append("".join(kisim))
                kisim = []
                if len(satirlar) >= sinir:
                    return satirlar
            continue
        kisim.append(ch)
    if kisim and len(satirlar) < sinir:
        satirlar.append("".join(kisim))
    return satirlar


def _tirnak_disi_say(satir: str, ayrac: str) -> int:
    n, tirnak = 0, False
    for ch in satir:
        if ch == '"':
            tirnak = not tirnak
        elif ch == ayrac and not tirnak:
            n += 1
    return n


def satirlari_oku(metin: str, ayrac: str) -> List[List[str]]:
    """Metni satır/alan listesine ayırır (RFC 4180 tırnaklama). Aşırı büyükse CsvHatasi."""
    csv.field_size_limit(1 << 28)
    try:
        satirlar = []
        for s in csv.reader(io.StringIO(metin, newline=""), delimiter=ayrac, quotechar='"'):
            satirlar.append(s)
            if len(satirlar) > MAKS_SATIR:
                raise CsvHatasi(f"Dosya {MAKS_SATIR:,} satırdan uzun; yalnızca ilk {MAKS_SATIR:,} satır alınabilirdi.")
    except csv.Error as e:
        raise CsvHatasi(f"CSV okunamadı: {e}") from e
    return satirlar


def dosya_oku(yol: str, kodlama: Optional[str] = None, ayrac: Optional[str] = None
              ) -> Tuple[List[List[str]], str, str]:
    """(satırlar, kodlama, ayraç); kodlama/ayraç verilmezse tanınır."""
    try:
        with open(yol, "rb") as f:
            veri = f.read()
    except FileNotFoundError as e:
        raise CsvHatasi(f"Dosya bulunamadı: {yol}") from e
    except PermissionError as e:
        raise CsvHatasi("Dosya okunamadı: başka bir uygulama kullanıyor olabilir.") from e
    except OSError as e:
        raise CsvHatasi(f"Dosya açılamadı: {e.strerror or e}") from e
    kodlama = kodlama or kodlama_tani(veri)
    metin = coz(veri, kodlama)
    ayrac = ayrac or ayrac_tani(metin)
    return satirlari_oku(metin, ayrac), kodlama, ayrac


# ------------------------------------------------------------------ kitap
def sayfa_adi_uret(yol: str) -> str:
    import os
    ad = os.path.splitext(os.path.basename(yol))[0]
    for k in '\\/?*[]:':
        ad = ad.replace(k, "_")
    ad = ad.strip("'")[:31].strip()
    try:
        sayfa_adi_dogrula(ad)
    except ValueError:
        return "Sayfa1"
    return ad


def kitap_olustur(satirlar: Iterable[List[str]], ad: str = "Sayfa1", metin_olarak: bool = False
                  ) -> Tuple[CalismaKitabi, List[str]]:
    """Satırlardan tek sayfalı kitap. `metin_olarak=True`: hiçbir alan sayıya/tarihe çevrilmez.
    Dönen liste kullanıcıya bildirilecek uyarılar (kırpılan sütunlar vb.)."""
    kitap = CalismaKitabi()
    sayfa = kitap.sayfalar[0]
    try:
        kitap.yeniden_adlandir(sayfa, ad)
    except ValueError:
        pass
    uyarilar: List[str] = []
    yeni = {}
    stiller = {}
    havuz = sayfa.havuz
    kod_kimlik = {}
    kirpildi = False
    for r, alanlar in enumerate(satirlar, start=1):
        if r > MAKS_SATIR:
            break
        if len(alanlar) > MAKS_SUTUN:
            kirpildi = True
            alanlar = alanlar[:MAKS_SUTUN]
        for c, a in enumerate(alanlar, start=1):
            if a == "":
                continue
            if metin_olarak:
                yeni[(r, c)] = Hucre(a)
                continue
            try:
                h, kod = ceviri.hucre_girdisi_akilli(a, kitap)
            except FormulHatasi:
                h, kod = Hucre(a), None                # bozuk formül metin kalır
            if h is None:
                continue
            yeni[(r, c)] = h
            if kod and kod != "General":
                k = kod_kimlik.get(kod)
                if k is None:
                    k = kod_kimlik[kod] = havuz.yama_uygula(0, StilYama(sayi_bicimi=kod))
                stiller[(r, c)] = k
    if kirpildi:
        uyarilar.append(f"{MAKS_SUTUN:,} sütundan fazlası alınamadı; fazlalık atıldı.")
    sayfa.toplu_yaz(yeni)
    if stiller:
        sayfa.bicim_yaz(stiller)
    return kitap, uyarilar


# ------------------------------------------------------------------ yazma
def hucre_metni(sayfa: Sayfa, r: int, c: int) -> str:
    """Hücrenin görünen metni (sayı biçimi uygulanmış; formülde sonuç)."""
    h = sayfa.hucre(r, c)
    if h is None:
        return ""
    v = sayfa.sonuc(r, c) if h.formul is not None else h.deger
    if v is None:
        return ""
    if isinstance(v, (Hata, bool, str)):
        return goster(v)
    kod = sayfa.stil(r, c).sayi_bicimi
    if kod != "General":
        try:
            s = bicimle(v, kod)
            if not s.diyez:
                return s.metin
        except (BicimHatasi, ArithmeticError, ValueError, OverflowError):
            pass
    return goster(v)


def metin_yaz(sayfa: Sayfa, ayrac: str = ";") -> str:
    """Etkin sayfa → CSV metni (satır sonu CRLF; kullanılan alanın üst-sol A1'den başlar)."""
    kul = sayfa.kullanilan_aralik()
    cikti = io.StringIO(newline="")
    w = csv.writer(cikti, delimiter=ayrac, quotechar='"', lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
    if kul is not None:
        son_r, son_c = kul[2], kul[3]
        for r in range(1, son_r + 1):
            w.writerow([hucre_metni(sayfa, r, c) for c in range(1, son_c + 1)])
    return cikti.getvalue()


def dosya_yaz(sayfa: Sayfa, yol: str, ayrac: str = ";", kodlama: str = "utf-8-sig") -> None:
    """Önce geçici dosyaya, sonra yerine koyma (CLAUDE.md kural 8)."""
    import os
    metin = metin_yaz(sayfa, ayrac)
    gecici = f"{yol}.{os.getpid()}.tmp"
    try:
        with open(gecici, "w", encoding=kodlama, newline="", errors="replace") as f:
            f.write(metin)
        os.replace(gecici, yol)
    except PermissionError as e:
        raise CsvHatasi("Dosya başka bir uygulamada açık olabilir; kapatıp yeniden deneyin.") from e
    except OSError as e:
        raise CsvHatasi(f"Dosya kaydedilemedi: {e.strerror or e}") from e
    finally:
        if os.path.exists(gecici):
            try:
                os.remove(gecici)
            except OSError:
                pass
