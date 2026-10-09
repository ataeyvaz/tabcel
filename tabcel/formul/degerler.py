"""Değerlendirme sırasında dolaşan değer türleri. Qt yok.

Bir ifade şunlardan birine değerlenir:
- skaler: None (boş hücre), float, str, bool, `Hata`
- `AralikDeger`: bir sayfadaki dikdörtgen başvuru (tek hücre de olabilir); değerler gerektikçe okunur
- `Dizi`: satırlar listesi (dizi sabiti ya da öğe öğe işlem sonucu)
"""
from typing import Iterator, List, Tuple

from ..model import deger as D
from ..model.adres import MAX_COL, MAX_ROW


class _Bekliyor:
    """Motorun hesaplama sırasında henüz hesaplanmamış formül hücrelerinin sonuç deposuna koyduğu
    işaret. Okunursa `Bekle` atılır; motor o hücreyi önce hesaplar (faz2_tasarim.md §4)."""
    __slots__ = ()

    def __repr__(self):
        return "BEKLIYOR"


BEKLIYOR = _Bekliyor()

# Hesap turu önbelleği: motor tur başında {"etkin": {}} yapar, sonunda boşaltır. Tur dışında
# (doğrudan değerlendirmede) önbellek kullanılmaz — bayat değer riski olmasın.
ONEK_ONBELLEGI: dict = {}


class Bekle(BaseException):
    """Henüz hesaplanmamış hücre okundu. BaseException: fonksiyonlardaki `except Exception`
    bunu yutmasın (fonksiyon yazarken BaseException yakalanmaz)."""

    def __init__(self, sayfa, satir: int, sutun: int):
        super().__init__()
        self.sayfa, self.satir, self.sutun = sayfa, satir, sutun


class Dizi:
    __slots__ = ("satirlar",)

    def __init__(self, satirlar: List[list]):
        self.satirlar = satirlar

    @property
    def satir_sayisi(self) -> int:
        return len(self.satirlar)

    @property
    def sutun_sayisi(self) -> int:
        return len(self.satirlar[0]) if self.satirlar else 0

    def deger(self, i: int, j: int):
        return self.satirlar[i][j]

    def degerler(self) -> Iterator:
        for satir in self.satirlar:
            yield from satir

    def __eq__(self, diger):
        return isinstance(diger, Dizi) and self.satirlar == diger.satirlar

    def __repr__(self):
        return f"Dizi({self.satirlar!r})"


class AralikDeger:
    """Sayfa üzerindeki başvuru; değerler gerektikçe okunur. Formül hücresinin değeri sayfanın
    sonuç deposundan gelir (`BEKLIYOR` ise `Bekle` atılır).

    Not: hız için `Sayfa._hucreler` / `Sayfa._sonuc` doğrudan okunur (motorla aynı katman)."""
    __slots__ = ("sayfa", "r1", "c1", "r2", "c2")

    def __init__(self, sayfa, r1: int, c1: int, r2: int, c2: int):
        self.sayfa, self.r1, self.c1, self.r2, self.c2 = sayfa, r1, c1, r2, c2

    @property
    def satir_sayisi(self) -> int:
        return self.r2 - self.r1 + 1

    @property
    def sutun_sayisi(self) -> int:
        return self.c2 - self.c1 + 1

    def tek_hucre(self) -> bool:
        return self.r1 == self.r2 and self.c1 == self.c2

    def hucre_degeri(self, r: int, c: int):
        """Mutlak satır/sütundaki değer."""
        h = self.sayfa._hucreler.get((r, c))
        if h is None:
            return None
        if h.formul is None:
            return h.deger
        v = self.sayfa._sonuc.get((r, c))
        if v is BEKLIYOR:
            raise Bekle(self.sayfa, r, c)
        return v

    def deger(self, i: int, j: int):
        """Göreli (0 tabanlı) konumdaki değer."""
        return self.hucre_degeri(self.r1 + i, self.c1 + j)

    def _dolu_hucreler(self):
        """(anahtar, Hucre) çiftleri: küçük aralıkta aralığı, büyükte sözlüğü gezer."""
        hucreler = self.sayfa._hucreler
        r1, c1, r2, c2 = self.r1, self.c1, self.r2, self.c2
        if (r2 - r1 + 1) * (c2 - c1 + 1) <= len(hucreler):
            get = hucreler.get
            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    h = get((r, c))
                    if h is not None:
                        yield (r, c), h
        else:
            for k, h in hucreler.items():
                if r1 <= k[0] <= r2 and c1 <= k[1] <= c2:
                    yield k, h

    def dolu(self) -> Iterator[Tuple[int, int, object]]:
        """Dolu hücreler (sırasız): (satır, sütun, değer). Büyük aralıklarda (A:A) hızlıdır."""
        sonuc = self.sayfa._sonuc
        for k, h in self._dolu_hucreler():
            if h.formul is None:
                yield k[0], k[1], h.deger
            else:
                v = sonuc.get(k)
                if v is BEKLIYOR:
                    raise Bekle(self.sayfa, k[0], k[1])
                yield k[0], k[1], v

    def toplam(self):
        """(sayıların toplamı, sayı adedi, ilk hata | None). Tek sütunlu uzun aralıkta, hesap turu
        sırasında önek önbelleği kullanılır (birikimli toplam deseni `=TOPLA($D$1:D5000)` O(n²)
        yerine O(n)). Toplama sırası doğrudan toplamla aynıdır → sonuç birebir aynı."""
        onb = ONEK_ONBELLEGI.get("etkin")
        if onb is not None and self.c1 == self.c2 and self.r2 - self.r1 >= 32:
            return self._onekten(onb)
        liste, hata = self.sayilar()
        t = 0.0
        for v in liste:
            t += v
        return t, len(liste), hata

    def _onekten(self, onb):
        anahtar = (id(self.sayfa), self.c1, self.r1)
        kayit = onb.get(anahtar)
        if kayit is None:
            kayit = onb[anahtar] = [self.r1 - 1, [], [], []]   # son satır, toplamlar, adetler, hatalar
        son, toplamlar, adetler, hatalar = kayit
        if son < self.r2:
            hucreler, sonuc = self.sayfa._hucreler, self.sayfa._sonuc
            get = hucreler.get
            c = self.c1
            t = toplamlar[-1] if toplamlar else 0.0
            n = adetler[-1] if adetler else 0
            hata = hatalar[-1] if hatalar else None
            for r in range(son + 1, self.r2 + 1):
                k = (r, c)
                h = get(k)
                if h is not None:
                    v = h.deger if h.formul is None else sonuc.get(k)
                    tv = type(v)
                    if tv is float:
                        t += v
                        n += 1
                    elif v is BEKLIYOR:
                        kayit[0] = r - 1          # buraya kadarki önek geçerli kalır
                        raise Bekle(self.sayfa, r, c)
                    elif tv is D.Hata and hata is None:
                        hata = v
                toplamlar.append(t)
                adetler.append(n)
                hatalar.append(hata)
            kayit[0] = self.r2
        i = self.r2 - self.r1
        return toplamlar[i], adetler[i], hatalar[i]

    def sayilar(self):
        """Aralıktaki sayılar (metin/mantıksal/boş atlanır) ve ilk rastlanan hata.
        Döner: (float listesi, Hata | None). TOPLA/ORTALAMA'nın sıcak yolu: üreteçsiz sıkı döngü."""
        hucreler, sonuc = self.sayfa._hucreler, self.sayfa._sonuc
        r1, c1, r2, c2 = self.r1, self.c1, self.r2, self.c2
        cikti: list = []
        ekle = cikti.append
        hata = None
        if (r2 - r1 + 1) * (c2 - c1 + 1) <= len(hucreler):
            get = hucreler.get
            ogeler = []
            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    k = (r, c)
                    h = get(k)
                    if h is not None:
                        ogeler.append((k, h))
        else:
            ogeler = [(k, h) for k, h in hucreler.items()
                      if r1 <= k[0] <= r2 and c1 <= k[1] <= c2]
        for k, h in ogeler:
            v = h.deger if h.formul is None else sonuc.get(k)
            t = type(v)
            if t is float:
                ekle(v)
            elif v is BEKLIYOR:
                raise Bekle(self.sayfa, k[0], k[1])
            elif t is D.Hata and hata is None:
                hata = v
        return cikti, hata

    def dolu_degerler(self) -> Iterator:
        """Yalnız değerler (sırasız) — TOPLA gibi konumu önemsiz işlevler için en hızlı yol."""
        sonuc = self.sayfa._sonuc
        for k, h in self._dolu_hucreler():
            if h.formul is None:
                yield h.deger
            else:
                v = sonuc.get(k)
                if v is BEKLIYOR:
                    raise Bekle(self.sayfa, k[0], k[1])
                yield v

    def kirpilmis(self) -> Tuple[int, int, int, int]:
        """Kullanılan alanla sınırlanmış uçlar (A:A gibi tam sütunu diziye çevirirken);
        sayfa boşsa yalnız sol üst hücre."""
        kul = self.sayfa.kullanilan_aralik()
        if kul is None:
            return self.r1, self.c1, self.r1, self.c1
        r2 = max(self.r1, min(self.r2, kul[2]))
        c2 = max(self.c1, min(self.c2, kul[3]))
        return self.r1, self.c1, r2, c2

    def diziye(self) -> Dizi:
        r1, c1, r2, c2 = self.kirpilmis()
        return Dizi([[self.hucre_degeri(r, c) for c in range(c1, c2 + 1)]
                     for r in range(r1, r2 + 1)])

    def __repr__(self):
        return f"AralikDeger({getattr(self.sayfa, 'ad', '?')}!{self.r1},{self.c1}:{self.r2},{self.c2})"


class _BosArguman:
    """Atlanmış argüman (EĞER(A1;;1)). Fonksiyon kendi varsayılanını uygular."""
    __slots__ = ()

    def __repr__(self):
        return "BOS_ARG"


BOS_ARG = _BosArguman()


def hata_mi(v) -> bool:
    return isinstance(v, D.Hata)


def skalere(v, satir: int, sutun: int):
    """Tek değer beklenen yerde aralık/dizi → tek değer (Excel'in örtük kesişimi).
    Aralık: tek hücreyse o; tek sütunsa formül satırındaki, tek satırsa formül sütunundaki hücre;
    kesişmiyorsa #DEĞER!. Dizi: sol üst öğe. `satir`/`sutun`: formül hücresinin konumu."""
    if isinstance(v, AralikDeger):
        if v.tek_hucre():
            return v.hucre_degeri(v.r1, v.c1)
        if v.c1 == v.c2 and v.r1 <= satir <= v.r2:
            return v.hucre_degeri(satir, v.c1)
        if v.r1 == v.r2 and v.c1 <= sutun <= v.c2:
            return v.hucre_degeri(v.r1, sutun)
        return D.DEGER_HATASI
    if isinstance(v, Dizi):
        return v.satirlar[0][0] if v.satirlar and v.satirlar[0] else None
    if v is BOS_ARG:
        return None
    return v


# --- öğe öğe işlemler için ortak yardımcılar (degerlendir.py ve fonksiyonlar kullanır) ---
def _boyut(v):
    if isinstance(v, AralikDeger):
        r1, c1, r2, c2 = v.kirpilmis() if (v.r2 == MAX_ROW or v.c2 == MAX_COL) else (
            v.r1, v.c1, v.r2, v.c2)
        return r2 - r1 + 1, c2 - c1 + 1
    if isinstance(v, Dizi):
        return v.satir_sayisi, v.sutun_sayisi
    return None


def _okuyucu(v):
    if isinstance(v, AralikDeger):
        if v.tek_hucre():
            x = v.hucre_degeri(v.r1, v.c1)
            return lambda i, j: x
        if v.r2 == MAX_ROW or v.c2 == MAX_COL:
            r1, c1, _, _ = v.kirpilmis()
        else:
            r1, c1 = v.r1, v.c1
        return lambda i, j: v.hucre_degeri(r1 + i, c1 + j)
    if isinstance(v, Dizi):
        return v.deger
    x = None if v is BOS_ARG else v
    return lambda i, j: x


def _yay(okuyucu, boyut, R, C):
    """Excel 365 yayma kuralı: 1 satırlı/sütunlu taraf genişletilir; boyu yetmeyen yerde #YOK."""
    if boyut is None:
        return okuyucu
    r, c = boyut

    def oku(i, j):
        if (r != 1 and i >= r) or (c != 1 and j >= c):
            return D.YOK
        return okuyucu(0 if r == 1 else i, 0 if c == 1 else j)
    return oku
