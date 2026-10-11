"""Özet Tablo (pivot) — Faz 8d. Qt yok.

**Anlık görüntü** (değer tablosu): kaynak aralığın ilk satırı alan başlıkları, geri kalanı kayıtlardır. Bir satır alanı, bir
sütun alanı (ikisi de isteğe bağlı) ve bir ya da birkaç değer alanı (Toplam / Sayı / Ortalama / Maks / Min) seçilir; sonuç sade
bir hücre aralığı olarak yazılır (biçimli başlık satırı/sütunu, "Genel Toplam"). Kaynak değişince tablo **kendiliğinden
güncellenmez** (Excel'in canlı Özet Tablosundan bilinçli fark; yeniden oluşturulur) ve .xlsx'e düz değerler olarak kaydedilir.

Gruplama Türkçe harf kurallarıyla büyük/küçük harf duyarsızdır (`Çay` = `ÇAY`); sıralama Excel sırasıdır (sayı < metin <
mantıksal < hata; boş en sonda, "(boş)" etiketiyle). Toplam/Ortalama/Maks/Min yalnız sayıları katar, Sayı boş olmayanları sayar;
bir değerde hata varsa o hücrenin sonucu o hatadır."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .adres import Aralik
from .deger import Hata
from .gosterim import goster
from .harmanla import deger_anahtari, tr_kucuk
from .komutlar import BicimDegis, HucrelerDegis, SayfaEkle, bicim_komutu
from .sayfa import CalismaKitabi, Hucre, Sayfa
from .stil import StilYama

ISLEVLER = ("Toplam", "Sayı", "Ortalama", "Maks", "Min")
BOS_ETIKET = "(boş)"
GENEL_TOPLAM = "Genel Toplam"
BASLIK_DOLGU = "#D2E6DA"                 # tema: HEADER_BG_SELECTED


class OzetHatasi(ValueError):
    """Kaynak/seçenek geçersiz (kullanıcıya gösterilecek Türkçe ileti)."""


@dataclass(frozen=True)
class DegerAlani:
    alan: str
    islev: str = "Toplam"

    def __post_init__(self):
        if self.islev not in ISLEVLER:
            raise OzetHatasi(f"Bilinmeyen özetleme işlevi: {self.islev}")

    @property
    def etiket(self) -> str:
        return f"{self.islev} - {self.alan}"


@dataclass(frozen=True)
class OzetTanimi:
    satir: Optional[str] = None            # satır alanı adı
    sutun: Optional[str] = None            # sütun alanı adı
    degerler: Tuple[DegerAlani, ...] = ()
    satir_toplami: bool = True             # sağda "Genel Toplam" sütunu (sütun alanı varsa)
    sutun_toplami: bool = True             # altta "Genel Toplam" satırı (satır alanı varsa)


@dataclass
class OzetSonucu:
    """`matris[0]` başlık satırı; satır sayısı = 1 + gövde (+ genel toplam satırı)."""
    matris: List[List[Any]]
    ust_sol: str = ""
    toplam_satiri: bool = False            # son satır "Genel Toplam"
    toplam_sutunlari: int = 0              # sağdaki "Genel Toplam" sütunu sayısı
    kayit_sayisi: int = 0
    uyarilar: List[str] = field(default_factory=list)

    @property
    def boyut(self) -> Tuple[int, int]:
        return len(self.matris), max((len(s) for s in self.matris), default=0)


# ------------------------------------------------------------------ kaynak
def baslik_oku(sayfa: Sayfa, kaynak: Aralik) -> List[str]:
    """İlk satırdaki alan başlıkları (boş → `Sütun N`, yineleyen → `Ad2`)."""
    sonuc, gorulen = [], {}
    for n, c in enumerate(range(kaynak.ilk_sutun, kaynak.son_sutun + 1), 1):
        ad = goster(sayfa.deger(kaynak.ilk_satir, c)).strip() or f"Sütun {n}"
        anahtar = tr_kucuk(ad)
        gorulen[anahtar] = gorulen.get(anahtar, 0) + 1
        sonuc.append(ad if gorulen[anahtar] == 1 else f"{ad}{gorulen[anahtar]}")
    return sonuc


def _kayitlar(sayfa: Sayfa, kaynak: Aralik) -> List[List[Any]]:
    kayit = []
    for r in range(kaynak.ilk_satir + 1, kaynak.son_satir + 1):
        satir = [sayfa.deger(r, c) for c in range(kaynak.ilk_sutun, kaynak.son_sutun + 1)]
        if any(v is not None for v in satir):                    # tamamen boş satır kayıt değil
            kayit.append(satir)
    return kayit


# ------------------------------------------------------------------ özetleme
def _ozetle(degerler: List[Any], islev: str):
    for v in degerler:
        if isinstance(v, Hata):
            return v
    sayilar = [float(v) for v in degerler if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if islev == "Sayı":
        return float(sum(1 for v in degerler if v is not None))
    if islev == "Toplam":
        return float(sum(sayilar))
    if islev == "Ortalama":
        return sum(sayilar) / len(sayilar) if sayilar else Hata("#DIV/0!")
    if islev == "Maks":
        return max(sayilar) if sayilar else 0.0
    return min(sayilar) if sayilar else 0.0                      # Min


def _anahtar(v: Any):
    """Gruplama anahtarı: metin büyük/küçük harf duyarsız (Türkçe), sayı/mantıksal/hata/boş kendi türünde."""
    if v is None:
        return ("b",)
    if isinstance(v, bool):
        return ("l", v)
    if isinstance(v, (int, float)):
        return ("n", float(v))
    if isinstance(v, Hata):
        return ("h", v.kod)
    return ("s", tr_kucuk(str(v)))


def _sirali(anahtarlar: Dict[Any, Any]) -> List[Tuple[Any, Any]]:
    """[(anahtar, gösterilecek özgün değer)] — Excel sırasına göre."""
    return sorted(anahtarlar.items(), key=lambda kv: deger_anahtari(kv[1]))


def hesapla(sayfa: Sayfa, kaynak: Aralik, tanim: OzetTanimi) -> OzetSonucu:
    """Özet tablo matrisini hesaplar (sayfaya yazmaz)."""
    if kaynak.son_satir <= kaynak.ilk_satir:
        raise OzetHatasi("Kaynakta başlık satırının altında veri yok.")
    basliklar = baslik_oku(sayfa, kaynak)
    sira = {tr_kucuk(b): i for i, b in enumerate(basliklar)}

    def indeks(alan: Optional[str]) -> Optional[int]:
        if alan is None:
            return None
        i = sira.get(tr_kucuk(alan))
        if i is None:
            raise OzetHatasi(f"“{alan}” alanı kaynakta yok.")
        return i
    if not tanim.degerler:
        raise OzetHatasi("En az bir değer alanı seçin.")
    ri, ci = indeks(tanim.satir), indeks(tanim.sutun)
    if ri is not None and ri == ci:
        raise OzetHatasi("Satır ve sütun alanı aynı olamaz.")
    vi = [indeks(d.alan) for d in tanim.degerler]
    kayitlar = _kayitlar(sayfa, kaynak)
    if not kayitlar:
        raise OzetHatasi("Kaynakta veri satırı yok.")

    satir_anahtarlari: Dict[Any, Any] = {}
    sutun_anahtarlari: Dict[Any, Any] = {}
    hucre: Dict[Tuple[Any, Any], List[List[Any]]] = {}
    for k in kayitlar:
        rv = k[ri] if ri is not None else None
        cv = k[ci] if ci is not None else None
        ra = _anahtar(rv) if ri is not None else ("hepsi",)
        ca = _anahtar(cv) if ci is not None else ("hepsi",)
        satir_anahtarlari.setdefault(ra, rv)
        sutun_anahtarlari.setdefault(ca, cv)
        kutu = hucre.setdefault((ra, ca), [[] for _ in vi])
        for j, i in enumerate(vi):
            kutu[j].append(k[i])
    satirlar = _sirali(satir_anahtarlari) if ri is not None else [(("hepsi",), None)]
    sutunlar = _sirali(sutun_anahtarlari) if ci is not None else [(("hepsi",), None)]

    def etiket(v):
        return BOS_ETIKET if v is None else v if isinstance(v, (str, float, bool, Hata)) else float(v)

    def topla(ra_list, ca_list, j):
        toplanan = []
        for ra in ra_list:
            for ca in ca_list:
                toplanan += (hucre.get((ra, ca)) or [[] for _ in vi])[j]
        return toplanan
    r_tum = [a for a, _ in satirlar]
    c_tum = [a for a, _ in sutunlar]
    uyarilar = []
    n = len(tanim.degerler)
    # başlık satırı
    ust_sol = tanim.satir or ("Özet" if ri is None else "")
    baslik: List[Any] = [ust_sol]
    sutun_dilimleri: List[Tuple[Optional[Any], int]] = []        # (sütun anahtarı | None=toplam, değer indeksi)
    if ci is None:
        for j, d in enumerate(tanim.degerler):
            baslik.append(d.etiket)
            sutun_dilimleri.append((c_tum[0], j))
    else:
        for ca, v in sutunlar:
            for j, d in enumerate(tanim.degerler):
                e = etiket(v)
                baslik.append(e if n == 1 else f"{e} - {d.etiket}")
                sutun_dilimleri.append((ca, j))
    toplam_sutun = ci is not None and tanim.satir_toplami
    if toplam_sutun:
        for j, d in enumerate(tanim.degerler):
            baslik.append(GENEL_TOPLAM if n == 1 else f"{GENEL_TOPLAM} - {d.etiket}")
    matris: List[List[Any]] = [baslik]
    for ra, rv in satirlar:
        satir: List[Any] = [etiket(rv) if ri is not None else "Toplam"]
        for ca, j in sutun_dilimleri:
            kutu = hucre.get((ra, ca))
            satir.append(_ozetle(kutu[j], tanim.degerler[j].islev) if kutu else None)
        if toplam_sutun:
            for j, d in enumerate(tanim.degerler):
                satir.append(_ozetle(topla([ra], c_tum, j), d.islev))
        matris.append(satir)
    toplam_satiri = ri is not None and tanim.sutun_toplami
    if toplam_satiri:
        satir = [GENEL_TOPLAM]
        for ca, j in sutun_dilimleri:
            satir.append(_ozetle(topla(r_tum, [ca], j), tanim.degerler[j].islev))
        if toplam_sutun:
            for j, d in enumerate(tanim.degerler):
                satir.append(_ozetle(topla(r_tum, c_tum, j), d.islev))
        matris.append(satir)
    if len(matris) * len(baslik) > 2_000_000:
        raise OzetHatasi("Özet tablo çok büyük olurdu; daha az benzersiz değeri olan bir alan seçin.")
    return OzetSonucu(matris, ust_sol, toplam_satiri, len(tanim.degerler) if toplam_sutun else 0,
                      len(kayitlar), uyarilar)


# ------------------------------------------------------------------ yazma (geri alınabilir komut)
def hedef_hucreleri(sonuc: OzetSonucu, ust_sol: Tuple[int, int]) -> Dict[Tuple[int, int], Hucre]:
    r0, c0 = ust_sol
    yeni = {}
    for i, satir in enumerate(sonuc.matris):
        for j, v in enumerate(satir):
            if v is None or v == "":
                continue
            yeni[(r0 + i, c0 + j)] = Hucre(v)
    return yeni


def _bicim_araliklari(sonuc: OzetSonucu, ust_sol: Tuple[int, int]):
    r0, c0 = ust_sol
    satir, sutun = sonuc.boyut
    baslik = Aralik(r0, c0, r0, c0 + sutun - 1)
    ilk_sutun = Aralik(r0 + 1, c0, r0 + satir - 1, c0) if satir > 1 else None
    toplam_satir = Aralik(r0 + satir - 1, c0, r0 + satir - 1, c0 + sutun - 1) if sonuc.toplam_satiri else None
    toplam_sutun = (Aralik(r0, c0 + sutun - sonuc.toplam_sutunlari, r0 + satir - 1, c0 + sutun - 1)
                    if sonuc.toplam_sutunlari else None)
    return baslik, ilk_sutun, toplam_satir, toplam_sutun


class OzetEkle:
    """Özet tabloyu `hedef_sayfa`ya (None: kitabın sonuna yeni sayfa `yeni_ad` adıyla) `ust_sol` hücresinden başlayarak yazar;
    tek geri al adımı. Sonuç oluşturulurken hesaplanır (`OzetHatasi` oluşturanda fırlar)."""

    def __init__(self, kitap: CalismaKitabi, kaynak_sayfa: Sayfa, kaynak: Aralik, tanim: OzetTanimi,
                 hedef_sayfa: Optional[Sayfa] = None, ust_sol: Tuple[int, int] = (1, 1),
                 yeni_ad: Optional[str] = None):
        self.kitap, self.kaynak_sayfa, self.ust_sol = kitap, kaynak_sayfa, ust_sol
        self.sonuc = hesapla(kaynak_sayfa, kaynak, tanim)
        self.hedef_sayfa, self.yeni_ad = hedef_sayfa, yeni_ad
        self._ekle: Optional[SayfaEkle] = None
        self._alt: List[Any] = []
        satir, sutun = self.sonuc.boyut
        if ust_sol[0] + satir - 1 > 1_048_576 or ust_sol[1] + sutun - 1 > 16_384:
            raise OzetHatasi("Özet tablo hedefe sığmıyor (sayfa sınırı aşılır).")

    @property
    def sayfa(self) -> Optional[Sayfa]:
        return self.hedef_sayfa

    def ana_sayfa_ver(self, geri_al: bool = False) -> Optional[Sayfa]:
        """Geri alınca kaynak, yinelenince özetin yazıldığı sayfa (yeni sayfa kalkmış olabilir)."""
        return self.kaynak_sayfa if geri_al else self.hedef_sayfa

    def yap(self) -> None:
        if self.yeni_ad is not None or self._ekle is not None:
            if self._ekle is None:
                self._ekle = SayfaEkle(self.kitap, self.yeni_ad)
            self._ekle.yap()
            self.hedef_sayfa = self._ekle.sayfa
        if not self._alt:
            hs = self.hedef_sayfa
            self._alt.append(HucrelerDegis(hs, hedef_hucreleri(self.sonuc, self.ust_sol)))
            baslik, ilk_sutun, toplam_satir, toplam_sutun = _bicim_araliklari(self.sonuc, self.ust_sol)
            self._alt.append(bicim_komutu(hs, [baslik], StilYama(kalin=True, dolgu=BASLIK_DOLGU)))
            if ilk_sutun is not None:
                self._alt.append(bicim_komutu(hs, [ilk_sutun], StilYama(kalin=True)))
            for a in (toplam_satir, toplam_sutun):
                if a is not None:
                    self._alt.append(bicim_komutu(hs, [a], StilYama(kalin=True, dolgu=BASLIK_DOLGU)))
        for k in self._alt:
            k.yap()

    def geri_al(self) -> None:
        for k in reversed(self._alt):
            k.geri_al()
        if self._ekle is not None:
            self._ekle.geri_al()
