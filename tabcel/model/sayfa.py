"""Hücre, Sayfa, Çalışma Kitabı: seyrek (yalnızca dolu hücreler saklanır). Qt yok.

Formül başvurularının satır/sütun ekle-sil sonrası düzeltilmesi Faz 2'dedir;
burada yalnızca hücreler ve boyutlar kaydırılır.
"""
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Set, Tuple, Union

from .adres import MAX_COL, MAX_ROW, AdresHatasi, Aralik

Deger = Union[None, str, float, bool]
Anahtar = Tuple[int, int]


@dataclass(frozen=True, eq=False)
class Hucre:
    """Değişmez hücre. `formul` dolu ise (kanonik İngilizce, '=' ile başlar) `deger`
    son hesaplanan sonuçtur; boşsa `deger` kullanıcının girdiği sabit değerdir.

    Eşitlik değerin TÜRÜNÜ de karşılaştırır: Python'da `True == 1.0` doğrudur, ama Excel'de
    DOĞRU ile 1 farklı değerlerdir (aksi halde 1 olan hücreye DOĞRU yazmak 'değişmedi' sayılırdı).
    """
    deger: Deger = None
    formul: Optional[str] = None

    def _anahtar(self):
        return (self.deger.__class__, self.deger, self.formul)

    def __eq__(self, diger):
        if not isinstance(diger, Hucre):
            return NotImplemented
        return self._anahtar() == diger._anahtar()

    def __hash__(self):
        return hash(self._anahtar())

    def bos_mu(self) -> bool:
        return self.deger is None and self.formul is None


class Sayfa:
    VARSAYILAN_SUTUN_GENISLIGI = 64   # px, 100% yakınlaştırmada
    VARSAYILAN_SATIR_YUKSEKLIGI = 20

    def __init__(self, ad: str):
        self.ad = ad
        self._hucreler: Dict[Anahtar, Hucre] = {}
        self.sutun_genislik: Dict[int, int] = {}
        self.satir_yukseklik: Dict[int, int] = {}
        self.gizli_sutun: Set[int] = set()
        self.gizli_satir: Set[int] = set()
        self.sekme_rengi: Optional[str] = None     # '#rrggbb' ya da None
        self._kul: Optional[Tuple[int, int, int, int]] = None   # kullanılan aralık önbelleği

    # --- okuma / yazma ---
    def hucre(self, satir: int, sutun: int) -> Optional[Hucre]:
        return self._hucreler.get((satir, sutun))

    def deger(self, satir: int, sutun: int) -> Deger:
        h = self._hucreler.get((satir, sutun))
        return h.deger if h else None

    def ata(self, satir: int, sutun: int, hucre: Optional[Hucre]) -> Optional[Hucre]:
        """Hücreyi yazar (None/boş = siler); eski hücreyi döndürür."""
        if not (1 <= satir <= MAX_ROW and 1 <= sutun <= MAX_COL):
            raise AdresHatasi(f"Hücre aralık dışı: ({satir}, {sutun})")
        eski = self._hucreler.get((satir, sutun))
        if hucre is None or hucre.bos_mu():
            if eski is not None:
                del self._hucreler[(satir, sutun)]
                kul = self._kul
                if kul and (satir in (kul[0], kul[2]) or sutun in (kul[1], kul[3])):
                    self._kul = None             # sınırdaki hücre silindi: yeniden hesaplanır
        else:
            self._hucreler[(satir, sutun)] = hucre
            kul = self._kul
            if kul:
                self._kul = (min(kul[0], satir), min(kul[1], sutun),
                             max(kul[2], satir), max(kul[3], sutun))
        return eski

    def dolu_hucreler(self, sirali: bool = True) -> Iterator[Tuple[int, int, Hucre]]:
        """Dolu hücreler. Sıra gerekmiyorsa `sirali=False` (100.000 hücrede sıralama pahalıdır)."""
        ogeler = sorted(self._hucreler.items()) if sirali else self._hucreler.items()
        for (s, c), h in ogeler:
            yield s, c, h

    def aralikta(self, ar: Aralik) -> Iterator[Tuple[int, int, Hucre]]:
        """Aralıktaki dolu hücreler (sırasız). Küçük aralıkta aralığı, büyükte sözlüğü gezer."""
        alan = (ar.son_satir - ar.ilk_satir + 1) * (ar.son_sutun - ar.ilk_sutun + 1)
        hucreler = self._hucreler
        if alan <= len(hucreler):
            for r in range(ar.ilk_satir, ar.son_satir + 1):
                for c in range(ar.ilk_sutun, ar.son_sutun + 1):
                    h = hucreler.get((r, c))
                    if h is not None:
                        yield r, c, h
        else:
            r1, c1, r2, c2 = ar.ilk_satir, ar.ilk_sutun, ar.son_satir, ar.son_sutun
            for (r, c), h in hucreler.items():
                if r1 <= r <= r2 and c1 <= c <= c2:
                    yield r, c, h

    def kullanilan_aralik(self) -> Optional[Tuple[int, int, int, int]]:
        """(ilk_satir, ilk_sutun, son_satir, son_sutun) ya da sayfa boşsa None."""
        if not self._hucreler:
            return None
        if self._kul is None:
            satirlar = [k[0] for k in self._hucreler]
            sutunlar = [k[1] for k in self._hucreler]
            self._kul = (min(satirlar), min(sutunlar), max(satirlar), max(sutunlar))
        return self._kul

    # --- boyutlar ---
    def genislik(self, sutun: int) -> int:
        """Görünen genişlik; gizli sütun için 0 (özgün genişlik saklı kalır)."""
        if sutun in self.gizli_sutun:
            return 0
        return self.sutun_genislik.get(sutun, self.VARSAYILAN_SUTUN_GENISLIGI)

    def yukseklik(self, satir: int) -> int:
        if satir in self.gizli_satir:
            return 0
        return self.satir_yukseklik.get(satir, self.VARSAYILAN_SATIR_YUKSEKLIGI)

    def boyut_durumu(self):
        """Boyut + gizleme durumunun kopyası (geri al için)."""
        return (dict(self.sutun_genislik), dict(self.satir_yukseklik),
                set(self.gizli_sutun), set(self.gizli_satir))

    def boyut_durumu_yukle(self, durum) -> None:
        g, y, gs, gr = durum
        self.sutun_genislik, self.satir_yukseklik = dict(g), dict(y)
        self.gizli_sutun, self.gizli_satir = set(gs), set(gr)

    # --- satır / sütun ekle-sil ---
    def satir_ekle(self, nerede: int, adet: int = 1) -> None:
        """`nerede` satırından itibaren `adet` boş satır açar (aşağıdakiler kayar)."""
        self._kaydir(0, nerede, adet)

    def satir_sil(self, nerede: int, adet: int = 1) -> Dict[Anahtar, Hucre]:
        """Satırları siler, yukarı kaydırır; silinen hücreleri döndürür."""
        return self._kaydir(0, nerede, -adet)

    def sutun_ekle(self, nerede: int, adet: int = 1) -> None:
        self._kaydir(1, nerede, adet)

    def sutun_sil(self, nerede: int, adet: int = 1) -> Dict[Anahtar, Hucre]:
        return self._kaydir(1, nerede, -adet)

    def _kaydir(self, eksen: int, nerede: int, fark: int) -> Dict[Anahtar, Hucre]:
        sinir = MAX_COL if eksen else MAX_ROW
        if not 1 <= nerede <= sinir or fark == 0:
            raise AdresHatasi(f"Geçersiz konum/adet: {nerede}, {fark}")
        kul = self.kullanilan_aralik()
        if fark > 0 and kul and kul[2 + eksen] >= nerede and kul[2 + eksen] + fark > sinir:
            # Excel gibi: dolu hücre sayfanın dışına itilecekse işlem reddedilir (sessiz veri kaybı yok)
            raise AdresHatasi("Sayfanın sonundaki dolu hücreler dışarı itileceği için eklenemiyor")
        silinen: Dict[Anahtar, Hucre] = {}
        yeni: Dict[Anahtar, Hucre] = {}
        for anahtar, h in self._hucreler.items():
            k = anahtar[eksen]
            if k >= nerede:
                if fark < 0 and k < nerede - fark:
                    silinen[anahtar] = h
                    continue
                k += fark
                if k > sinir:          # ekleme sınırın dışına iter: hücre kaybolur
                    continue
                anahtar = (k, anahtar[1]) if eksen == 0 else (anahtar[0], k)
            yeni[anahtar] = h
        self._hucreler = yeni
        self._kul = None
        olcu = self.sutun_genislik if eksen else self.satir_yukseklik
        yeni_olcu = {}
        for k, v in olcu.items():
            k = self._kaydir_indeks(k, nerede, fark, sinir)
            if k is not None:
                yeni_olcu[k] = v
        olcu.clear()
        olcu.update(yeni_olcu)
        gizli = self.gizli_sutun if eksen else self.gizli_satir
        yeni_gizli = {k2 for k in gizli
                      if (k2 := self._kaydir_indeks(k, nerede, fark, sinir)) is not None}
        gizli.clear()
        gizli.update(yeni_gizli)
        return silinen

    @staticmethod
    def _kaydir_indeks(k: int, nerede: int, fark: int, sinir: int) -> Optional[int]:
        """Satır/sütun indeksinin ekle-sil sonrası yeni değeri; silinmişse/sınır dışıysa None."""
        if k < nerede:
            return k
        if fark < 0 and k < nerede - fark:
            return None
        k += fark
        return k if k <= sinir else None


SAYFA_ADI_YASAK = set("\\/?*[]:")


def sayfa_adi_dogrula(ad: str) -> None:
    """Excel kuralları: boş olamaz, en çok 31 karakter, ters/düz bölü, ? * [ ] : içeremez,
    başta/sonda kesme işareti olamaz. Geçersizse Türkçe iletiyle ValueError."""
    if not ad.strip():
        raise ValueError("Sayfa adı boş olamaz")
    if len(ad) > 31:
        raise ValueError("Sayfa adı en çok 31 karakter olabilir")
    kotu = sorted(set(ad) & SAYFA_ADI_YASAK)
    if kotu:
        raise ValueError("Sayfa adı şu karakterleri içeremez: " + " ".join(kotu))
    if ad.startswith("'") or ad.endswith("'"):
        raise ValueError("Sayfa adı kesme işaretiyle başlayıp bitemez")


class CalismaKitabi:
    def __init__(self):
        self.sayfalar: List[Sayfa] = [Sayfa("Sayfa1")]

    def sayfa_ekle(self, ad: Optional[str] = None) -> Sayfa:
        ad = ad or self._yeni_ad()
        sayfa_adi_dogrula(ad)
        if self.ad_var_mi(ad):
            raise ValueError(f"Bu adda bir sayfa zaten var: {ad}")
        s = Sayfa(ad)
        self.sayfalar.append(s)
        return s

    def ad_var_mi(self, ad: str) -> bool:
        return any(s.ad.casefold() == ad.casefold() for s in self.sayfalar)

    def _yeni_ad(self) -> str:
        n = len(self.sayfalar) + 1
        while self.ad_var_mi(f"Sayfa{n}"):
            n += 1
        return f"Sayfa{n}"

    def sayfa_sil(self, sayfa: Sayfa) -> None:
        if len(self.sayfalar) == 1:
            raise ValueError("Son sayfa silinemez")
        self.sayfalar.remove(sayfa)

    def yeniden_adlandir(self, sayfa: Sayfa, ad: str) -> None:
        sayfa_adi_dogrula(ad)
        if any(s is not sayfa and s.ad.casefold() == ad.casefold() for s in self.sayfalar):
            raise ValueError(f"Bu adda bir sayfa zaten var: {ad}")
        sayfa.ad = ad

    def sayfa_tasi(self, sayfa: Sayfa, yeni_indeks: int) -> None:
        """Sayfayı sekme sırasında `yeni_indeks` konumuna taşır."""
        if not 0 <= yeni_indeks < len(self.sayfalar):
            raise ValueError(f"Geçersiz sıra: {yeni_indeks}")
        self.sayfalar.remove(sayfa)
        self.sayfalar.insert(yeni_indeks, sayfa)
