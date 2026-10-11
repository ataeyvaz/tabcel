"""Yazım denetimi oturumu (Faz 7c) — Qt'siz. Motor (Windows Yazım Denetimi API'si, `io/yazim_motoru.py`)
dışarıdan verilir: `errors(metin) -> [(başlangıç, uzunluk, eylem, yerine)]`, `suggest(sözcük) -> [öneri]`.

Kapsam: yalnız **sabit metin** hücreleri (formül, sayı, tarih, mantıksal, hata değeri denetlenmez). Seçim birden çok
hücreyse yalnız seçim, tek hücreyse tüm sayfa; satır sırasıyla, sayfanın başından (Excel etkin hücreden başlar ve
sonda "baştan devam edilsin mi" diye sorar — bilerek fark, `surec.md`). Düzeltme `uygula` geri çağrısıyla yapılır
(arayüz geri alınabilir komutla yazar); bir hücrede birden çok hata varsa her düzeltmeden sonra hücre yeniden
taranır, böylece konumlar kaymaz."""
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple

from .adres import Aralik
from .harmanla import tr_kucuk
from .sayfa import Hucre, Sayfa


@dataclass(frozen=True)
class Bulgu:
    satir: int
    sutun: int
    metin: str            # hücrenin tüm metni
    baslangic: int
    uzunluk: int

    @property
    def sozcuk(self) -> str:
        return self.metin[self.baslangic:self.baslangic + self.uzunluk]


def hucre_sirasi(sayfa: Sayfa, aralikler: Iterable[Aralik], tum_sayfa: bool) -> List[Tuple[int, int]]:
    """Denetlenecek sabit metin hücreleri, satır sırasıyla (yinelenmeden)."""
    if tum_sayfa:
        kaynak = ((r, c, h) for r, c, h in sayfa.dolu_hucreler())
    else:
        goruldu: Dict[Tuple[int, int], Hucre] = {}
        for ar in aralikler:
            for r, c, h in sayfa.aralikta(ar):
                goruldu[(r, c)] = h
        kaynak = ((r, c, h) for (r, c), h in sorted(goruldu.items()))
    return [(r, c) for r, c, h in kaynak if h.formul is None and isinstance(h.deger, str) and h.deger.strip()]


class YazimOturumu:
    def __init__(self, sayfa: Sayfa, hucreler: List[Tuple[int, int]], motor,
                 uygula: Callable[[Sayfa, Dict[Tuple[int, int], Hucre]], None]):
        self.sayfa = sayfa
        self.hucreler = hucreler
        self.motor = motor
        self._uygula = uygula
        self.yoksayilan: Set[str] = set()
        self.tum_degisim: Dict[str, str] = {}              # tr_kucuk(sözcük) → yerine
        self._i = 0
        self._ofset = 0
        self.simdiki: Optional[Bulgu] = None
        self.degistirilen = 0
        self.denetlenen_hucre = 0

    # ------------------------------------------------------------------ tarama
    def _metin(self, r: int, c: int) -> Optional[str]:
        h = self.sayfa.hucre(r, c)
        return h.deger if h is not None and h.formul is None and isinstance(h.deger, str) else None

    def ara(self) -> Optional[Bulgu]:
        """Sıradaki yanlış sözcüğü bulur (`simdiki`); yoksa None. Yoksayılanlar atlanır, "tümünü değiştir"
        denenler kendiliğinden düzeltilir."""
        while self._i < len(self.hucreler):
            r, c = self.hucreler[self._i]
            metin = self._metin(r, c)
            hata = self._ilk_hata(metin) if metin else None
            if hata is None:
                self._i += 1
                self._ofset = 0
                self.denetlenen_hucre += 1
                continue
            bas, uzun = hata
            anahtar = tr_kucuk(metin[bas:bas + uzun])
            if anahtar in self.yoksayilan:
                self._ofset = bas + uzun
                continue
            if anahtar in self.tum_degisim:
                self._yaz(r, c, metin, bas, uzun, self.tum_degisim[anahtar])
                continue
            self.simdiki = Bulgu(r, c, metin, bas, uzun)
            return self.simdiki
        self.simdiki = None
        return None

    def _ilk_hata(self, metin: str) -> Optional[Tuple[int, int]]:
        for bas, uzun, _eylem, _yerine in sorted(self.motor.errors(metin)):
            if bas >= self._ofset and uzun > 0:
                return bas, uzun
        return None

    def oneriler(self, limit: int = 8) -> List[str]:
        if self.simdiki is None:
            return []
        try:
            return list(self.motor.suggest(self.simdiki.sozcuk, limit))
        except Exception:                                   # öneri alınamadı: denetim sürer
            return []

    # ------------------------------------------------------------------ eylemler
    def _yaz(self, r: int, c: int, metin: str, bas: int, uzun: int, yerine: str) -> None:
        yeni = metin[:bas] + yerine + metin[bas + uzun:]
        self._uygula(self.sayfa, {(r, c): Hucre(yeni) if yeni else None})
        self._ofset = bas + len(yerine)
        self.degistirilen += 1

    def degistir(self, yerine: str) -> Optional[Bulgu]:
        b = self.simdiki
        if b is not None:
            self._yaz(b.satir, b.sutun, b.metin, b.baslangic, b.uzunluk, yerine)
        return self.ara()

    def tumunu_degistir(self, yerine: str) -> Optional[Bulgu]:
        if self.simdiki is not None:
            self.tum_degisim[tr_kucuk(self.simdiki.sozcuk)] = yerine
        return self.degistir(yerine)

    def yoksay(self) -> Optional[Bulgu]:
        if self.simdiki is not None:
            self._ofset = self.simdiki.baslangic + self.simdiki.uzunluk
        return self.ara()

    def tumunu_yoksay(self) -> Optional[Bulgu]:
        if self.simdiki is not None:
            self.yoksayilan.add(tr_kucuk(self.simdiki.sozcuk))
        return self.yoksay()
