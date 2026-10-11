"""Hesap izleme (Faz 9b, “Bu sayı nereden geliyor?”): bir hücrenin değerinin hangi hücrelerden/aralıklardan hesaplandığını TEMBEL ağaç
olarak sunar; ters yönde (“bu hücre nerelerde kullanılıyor”) bağımlıları listeler. Qt yok; salt okunur (hiçbir hücreyi değiştirmez).

Kaynak: motorun `onculler` / `bagimlilar` API'si (Faz 9a). Ağaç düğümleri küçük `Dugum` kayıtlarıdır; çocuklar istendikçe
(`cocuklar`) üretilir, sayfalıdır (`SAYFA_BOYUTU`) — binlerce düğüm birden üretilmez. Aralık başvurusu TEK düğümdür
(“A1:A1000 — 1.000 hücre, toplam 84.250”); açılınca dolu hücreleri sayfalı listelenir. Döngü (yol üzerinde yinelenen hücre ya da
`motor.donguler`) işaretlenir ve açılmaz; zincirde hata varsa hatanın doğduğu hücre `hata_kaynagi` olarak işaretlenir
(`hata_neden`)."""
from dataclasses import dataclass, replace
from typing import Any, Dict, List, Optional, Tuple

from ..model.adres import Aralik, aralik_yaz, hucre_yaz
from ..model.bul import gorunen_metin
from ..model.deger import Hata
from ..model.gosterim import goster
from ..model.sayfa import TasmaHucre
from . import ceviri, hata_neden
from .degerler import AralikDeger, Bekle

import heapq

SAYFA_BOYUTU = 100                    # bir seferde listelenen çocuk sayısı
OZET_SINIRI = 2_000_000               # bundan büyük aralıkta toplam hesaplanmaz (yalnız hücre sayısı)
HIZLI_OZET_SINIRI = 5_000             # bundan küçük aralığın özeti düğümle birlikte; büyüğü tembel (`ozet_tamamla`)

Anahtar = Tuple[int, int, int]        # (sayfa kimliği, satır, sütun)
Kutu = Tuple[int, int, int, int]


def _binlik(n: float) -> str:
    """`84250` → `84.250`; en çok 2 ondalık (`1234,5`)."""
    if n == int(n):
        return f"{int(n):,}".replace(",", ".")
    ust, _, alt = f"{n:,.2f}".rstrip("0").partition(".")
    return ust.replace(",", ".") + ("," + alt if alt else "")


@dataclass
class Dugum:
    tur: str                                  # "hucre" | "aralik" | "daha" (sayfalama düğmesi)
    sayfa: Any = None
    satir: int = 0
    sutun: int = 0
    kutu: Optional[Kutu] = None               # aralıkta (r1, c1, r2, c2)
    etiket: str = ""                          # adres; başka sayfadaysa `Sayfa2!B3`
    formul: Optional[str] = None              # Türkçe gösterimli formül (formül hücresiyse)
    deger: Any = None
    deger_metni: str = ""
    hata: bool = False                        # değer bir hata
    hata_kaynagi: bool = False                # zincirde hatanın doğduğu hücre
    dongu: bool = False                       # döngüsel başvuru
    ozet: str = ""                            # aralık: “1.000 hücre, toplam 84.250”
    ozet_bekliyor: bool = False               # büyük aralık: yalnız hücre sayısı biliniyor, dolu/toplam `ozet_tamamla` ile
    cocuk_var: bool = False
    tasma_sahibi: Optional[Tuple[int, int]] = None      # taşan hücre: formülün asıl hücresi
    ek: Optional[dict] = None                 # "daha": {'ana': Dugum, 'sayfa_no': int, 'kalan': int, 'yon': str}

    @property
    def anahtar(self) -> Optional[Anahtar]:
        return (self.sayfa.kimlik, self.satir, self.sutun) if self.tur == "hucre" else None

    @property
    def metin(self) -> str:
        """Tek satırlık özet (günlük/test): `D10 = =B10-C10 → 145.000 ₺`."""
        if self.tur == "aralik":
            return f"{self.etiket} — {self.ozet}"
        if self.tur == "daha":
            return self.etiket
        f = f" = {self.formul}" if self.formul else ""
        return f"{self.etiket}{f} → {self.deger_metni}"


@dataclass
class Sayfalama:
    dugumler: List[Dugum]
    toplam: Optional[int]                      # None: henüz bilinmiyor (büyük aralık özeti hesaplanmadı)
    sonraki: bool                              # yüklenecek başka sayfa var mı


class Izleme:
    """Bir kitap + motor için izleme. Hücre/formül değişince yeni `kok` istenir (ya da `guncelle` ile değerler tazelenir)."""

    def __init__(self, kitap, motor):
        self.kitap, self.motor = kitap, motor
        self._kok_sayfa = None
        self._hata_kaynagi: Optional[Anahtar] = None
        self._hata_metni: Optional[str] = None
        self._ozet_onbellek: Dict[Tuple[int, Kutu], Tuple[int, float, Optional[Hata]]] = {}

    # ------------------------------------------------------------------ ortak
    def _sayfa(self, kimlik: int):
        return self.kitap.sayfa_kimlikle(kimlik)

    def _etiket(self, sayfa, r: int, c: int, kutu: Optional[Kutu] = None) -> str:
        ad = hucre_yaz(r, c) if kutu is None else aralik_yaz(Aralik(*kutu))
        if self._kok_sayfa is not None and sayfa is not self._kok_sayfa:
            kisa = sayfa.ad if sayfa.ad.replace("_", "").isalnum() else "'" + sayfa.ad.replace("'", "''") + "'"
            return f"{kisa}!{ad}"
        return ad

    def _hucre_dugumu(self, sayfa, r: int, c: int, yol: Tuple[Anahtar, ...] = ()) -> Dugum:
        anahtar = (sayfa.kimlik, r, c)
        h = sayfa.hucre(r, c)
        formul = ceviri.gosterime(h.formul, self.kitap) if h is not None and h.formul is not None else None
        deger = sayfa.deger(r, c)
        metin = gorunen_metin(sayfa, r, c)
        d = Dugum("hucre", sayfa, r, c, etiket=self._etiket(sayfa, r, c), formul=formul, deger=deger,
                  deger_metni="(boş)" if metin is None else metin, hata=isinstance(deger, Hata))
        d.hata_kaynagi = anahtar == self._hata_kaynagi
        d.dongu = anahtar in yol or anahtar in self.motor.donguler
        if type(h) is TasmaHucre:
            d.tasma_sahibi = h.sahip
            d.cocuk_var = not d.dongu
        elif formul is not None and not d.dongu:
            hucreler, araliklar = self.motor.onculler(anahtar)
            d.cocuk_var = bool(hucreler or araliklar)
        return d

    def _ozet_hesapla(self, sayfa, kutu: Kutu):
        """(dolu hücre sayısı, sayıların toplamı, ilk hata | None) — TEK geçişte."""
        r1, c1, r2, c2 = kutu
        ar = AralikDeger(sayfa, r1, c1, r2, c2)
        sonuc = sayfa._sonuc
        dolu, toplam, hata = 0, 0.0, None
        for k, h in ar._dolu_hucreler():
            v = h.deger if h.formul is None else sonuc.get(k)
            if v is None or v == "":
                continue
            dolu += 1
            t = type(v)
            if t is float:
                toplam += v
            elif t is Hata and hata is None:
                hata = v
        self._ozet_onbellek[(sayfa.kimlik, kutu)] = (dolu, toplam, hata)
        return dolu, toplam, hata

    def _aralik_dugumu(self, sayfa, kutu: Kutu, tam_ozet: Optional[bool] = None) -> Dugum:
        """`tam_ozet=None`: küçük aralıkta özet hemen, büyükte tembel."""
        r1, c1, r2, c2 = kutu
        adet = (r2 - r1 + 1) * (c2 - c1 + 1)
        d = Dugum("aralik", sayfa, r1, c1, kutu=kutu, etiket=self._etiket(sayfa, r1, c1, kutu), cocuk_var=True)
        d.ozet = f"{_binlik(adet)} hücre"
        if adet > OZET_SINIRI:
            return d
        if tam_ozet is None:
            tam_ozet = adet <= HIZLI_OZET_SINIRI
        if not tam_ozet:
            d.ozet_bekliyor = True
            return d
        try:
            dolu, toplam, hata = self._ozet_hesapla(sayfa, kutu)
        except Bekle:
            return d
        d.ozet += f", {_binlik(dolu)} dolu" + (f", toplam {_binlik(toplam)}" if toplam or dolu else "")
        if hata is not None:
            d.ozet += f", hata: {goster(hata)}"
            d.hata = True
        return d

    def ozet_tamamla(self, d: Dugum) -> Dugum:
        """Tembel aralık özetini hesaplar (UI iş parçacığında tek geçiş; panel bunu olay döngüsüne bölerek çağırır)."""
        if d.tur != "aralik" or not d.ozet_bekliyor:
            return d
        return self._aralik_dugumu(d.sayfa, d.kutu, True)

    # ------------------------------------------------------------------ nereden geliyor
    def kok(self, sayfa, satir: int, sutun: int) -> Dugum:
        """Seçili hücrenin düğümü. Değeri hataysa hatanın asıl kaynağı hesaplanır (`hata_kaynagi_metni`)."""
        self._kok_sayfa = sayfa
        self._hata_kaynagi = None
        if isinstance(sayfa.deger(satir, sutun), Hata):
            zincir = hata_neden.acikla(sayfa, satir, sutun, motor=self.motor)
            if zincir:
                son = zincir[-1]
                self._hata_kaynagi = (son.sayfa.kimlik, son.satir, son.sutun)
                self._hata_metni = hata_neden.metin(zincir, sayfa)
        return self._hucre_dugumu(sayfa, satir, sutun)

    def hata_kaynagi_metni(self) -> Optional[str]:
        """Kökün değeri hataysa “#DEĞER!: B3 hücresinde …” açıklaması; değilse None."""
        return self._hata_metni if self._hata_kaynagi is not None else None

    def _cocuk_listesi(self, d: Dugum) -> List[Tuple[str, Any]]:
        """Düğümün (tür, veri) çocukları — SIRALI ve yinelenmesiz."""
        if d.tur == "hucre":
            if d.tasma_sahibi is not None:
                return [("hucre", (d.sayfa.kimlik,) + tuple(d.tasma_sahibi))]
            hucreler, araliklar = self.motor.onculler(d.anahtar)
            sira = {s.kimlik: i for i, s in enumerate(self.kitap.sayfalar)}
            ogeler = [(sira.get(k, 99), r, c, "hucre", (k, r, c)) for k, r, c in dict.fromkeys(hucreler)]
            ogeler += [(sira.get(k, 99), kt[0], kt[1], "aralik", (k, kt)) for k, kt in dict.fromkeys(araliklar)]
            ogeler.sort(key=lambda x: x[:3] + (x[3] == "aralik",))
            return [(t, v) for *_, t, v in ogeler]
        return []

    def _aralik_sayfasi(self, d: Dugum, sayfa_no: int) -> Tuple[List[Tuple[int, int]], Optional[int], bool]:
        """Aralığın DOLU hücrelerinden `sayfa_no`. sayfa ([(satır, sütun)] satır sırasıyla), toplam dolu sayısı (özet henüz hesaplanmadıysa
        ve sayfa erken bittiyse None) ve sonraki sayfa var mı. Hücre kutusu sayfanın hücre sayısından küçükse kutuyu satır satır tarar
        (tamamını sıralamaz), değilse sözlüğü süzer."""
        r1, c1, r2, c2 = d.kutu
        hucreler = d.sayfa._hucreler
        bas, son = sayfa_no * SAYFA_BOYUTU, (sayfa_no + 1) * SAYFA_BOYUTU
        alan = (r2 - r1 + 1) * (c2 - c1 + 1)
        onb = self._ozet_onbellek.get((d.sayfa.kimlik, d.kutu))
        if alan <= len(hucreler) or alan <= 50_000:
            parca, sira = [], 0
            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    if (r, c) in hucreler:
                        if bas <= sira < son:
                            parca.append((r, c))
                        sira += 1
                        if sira > son:                                   # sayfa doldu ve en az bir hücre daha var
                            return parca, (onb[0] if onb is not None else None), True
            return parca, sira, False
        anahtarlar = [k for k in hucreler if r1 <= k[0] <= r2 and c1 <= k[1] <= c2]
        return sorted(anahtarlar)[bas:son], len(anahtarlar), son < len(anahtarlar)

    def cocuklar(self, d: Dugum, yol: Tuple[Anahtar, ...] = (), sayfa_no: int = 0) -> Sayfalama:
        """`d`nin çocuklarının `sayfa_no`. sayfası. `yol`: kökten `d`ye kadarki hücre anahtarları (döngü tespiti)."""
        if d.tur == "aralik":
            hucreler, toplam, sonraki = self._aralik_sayfasi(d, sayfa_no)
            dugumler = [self._hucre_dugumu(d.sayfa, r, c, yol) for r, c in hucreler]
            return Sayfalama(dugumler, toplam, sonraki)
        liste = self._cocuk_listesi(d)
        bas = sayfa_no * SAYFA_BOYUTU
        parca = liste[bas:bas + SAYFA_BOYUTU]
        yol = yol + ((d.anahtar,) if d.tur == "hucre" else ())
        dugumler: List[Dugum] = []
        for tur, v in parca:
            if tur == "hucre":
                k, r, c = v
                s = self._sayfa(k)
                if s is not None:
                    dugumler.append(self._hucre_dugumu(s, r, c, yol))
            else:
                k, kt = v
                s = self._sayfa(k)
                if s is not None:
                    dugumler.append(self._aralik_dugumu(s, kt))
        return Sayfalama(dugumler, len(liste), bas + SAYFA_BOYUTU < len(liste))

    # ------------------------------------------------------------------ nerelerde kullanılıyor (ters yön)
    def bagimli_kok(self, sayfa, satir: int, sutun: int) -> Dugum:
        self._kok_sayfa = sayfa
        d = self._hucre_dugumu(sayfa, satir, sutun)
        d.cocuk_var = bool(self.motor.bagimlilar((sayfa.kimlik, satir, sutun)))
        return d

    def bagimli_sayisi(self, d: Dugum) -> int:
        return len(self.motor.bagimlilar(d.anahtar)) if d.tur == "hucre" else 0

    def bagimli_cocuklar(self, d: Dugum, yol: Tuple[Anahtar, ...] = (), sayfa_no: int = 0) -> Sayfalama:
        """`d` hücresini (doğrudan) okuyan formül hücreleri; her biri kendi bağımlılarıyla açılabilir."""
        sira = {s.kimlik: i for i, s in enumerate(self.kitap.sayfalar)}
        kume = self.motor.bagimlilar(d.anahtar)
        bas = sayfa_no * SAYFA_BOYUTU
        # yalnız gereken sayfaya kadar olan en küçükler (100.000 bağımlıyı tamamen sıralamaz); sıra (sayfa kimliği, satır, sütun)
        ilk = heapq.nsmallest(bas + SAYFA_BOYUTU, kume) if len(kume) > 4 * SAYFA_BOYUTU else sorted(kume)
        tum_say = len(kume)
        yol = yol + (d.anahtar,)
        dugumler = []
        for k, r, c in ilk[bas:bas + SAYFA_BOYUTU]:
            s = self._sayfa(k)
            if s is None:
                continue
            x = self._hucre_dugumu(s, r, c, yol)
            x.cocuk_var = (k, r, c) not in yol and bool(self.motor.bagimlilar((k, r, c)))
            x.dongu = (k, r, c) in yol or (k, r, c) in self.motor.donguler
            dugumler.append(x)
        return Sayfalama(dugumler, tum_say, bas + SAYFA_BOYUTU < tum_say)

    # ------------------------------------------------------------------ güncelleme
    def guncelle(self, d: Dugum) -> Dugum:
        """Düğümün değerini/özetini yeniden okur (yapı değişmediyse ağacı yeniden kurmadan tazelemek için)."""
        if d.tur == "hucre":
            y = self._hucre_dugumu(d.sayfa, d.satir, d.sutun, ())
            return replace(y, dongu=d.dongu, hata_kaynagi=d.hata_kaynagi)
        if d.tur == "aralik":
            self._ozet_onbellek.pop((d.sayfa.kimlik, d.kutu), None)
            return self._aralik_dugumu(d.sayfa, d.kutu)
        return d
