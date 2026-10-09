"""Geri al / yinele (komut deseni). Qt yok.

Aralık işlemleri tek adımdır: tek komut ya da `Grup`.
"""
from typing import Dict, List, Optional, Protocol

from .adres import MAX_COL, MAX_ROW, AdresHatasi, Aralik
from .sayfa import Anahtar, Hucre, Sayfa
from .stil import StilYama


class Komut(Protocol):
    def yap(self) -> None: ...
    def geri_al(self) -> None: ...


class HucrelerDegis:
    """Birden çok hücreyi tek adımda değiştirir. `yeni`: {(satır, sütun): Hucre | None}."""

    def __init__(self, sayfa: Sayfa, yeni: Dict[Anahtar, Optional[Hucre]]):
        self.sayfa = sayfa
        self.yeni = dict(yeni)
        self.eski: Dict[Anahtar, Optional[Hucre]] = {}

    def yap(self) -> None:
        self.eski = self.sayfa.toplu_yaz(self.yeni)

    def geri_al(self) -> None:
        self.sayfa.toplu_yaz(self.eski)


class _SatirSutun:
    """Satır/sütun ekle-sil + kitaptaki formül başvurularının düzeltilmesi (tek geri al adımı).

    yap: kaydır → formül metinlerini yeniden yaz (eskileri sakla).
    geri_al: önce formül metinlerini geri yükle → sonra kaydırmayı geri al.
    """
    eksen = 0

    def __init__(self, sayfa: Sayfa, nerede: int, adet: int, ekle: bool):
        self.sayfa, self.nerede, self.adet, self.ekle = sayfa, nerede, adet, ekle
        self._silinen: Dict[Anahtar, Hucre] = {}
        self._olcu_once = None
        self._bicim_silinen = None       # silinen bandın ham stil kayıtları (silmeyi geri almak için)
        self._duzeltmeler = {}           # {Sayfa: {anahtar: (eski formül, yeni formül)}}

    def _formulleri_duzelt(self) -> None:
        from ..formul.kaydir import yapi_duzeltmeleri    # model → formul yalnız burada
        self._duzeltmeler = yapi_duzeltmeleri(
            self.sayfa.kitap, self.sayfa, "sutun" if self.eksen else "satir", self.nerede,
            self.adet if self.ekle else -self.adet)
        for s, degisen in self._duzeltmeler.items():
            s.toplu_yaz({k: Hucre(None, yeni) for k, (_, yeni) in degisen.items()})

    def _formulleri_geri_yukle(self) -> None:
        for s, degisen in self._duzeltmeler.items():
            s.toplu_yaz({k: Hucre(None, eski) for k, (eski, _) in degisen.items()})

    def _ekle(self) -> None:
        (self.sayfa.sutun_ekle if self.eksen else self.sayfa.satir_ekle)(self.nerede, self.adet)

    def _sil(self) -> Dict[Anahtar, Hucre]:
        return (self.sayfa.sutun_sil if self.eksen else self.sayfa.satir_sil)(
            self.nerede, self.adet)

    def yap(self) -> None:
        self._olcu_once = self.sayfa.boyut_durumu()
        if self.ekle:
            self._ekle()
        else:
            self._bicim_silinen = self.sayfa.bicim_silinecek(self.eksen, self.nerede, self.adet)
            self._silinen = self._sil()
        self._formulleri_duzelt()

    def geri_al(self) -> None:
        self._formulleri_geri_yukle()
        if self.ekle:
            self._sil()
        else:
            self._ekle()
            for (s, c), h in self._silinen.items():
                self.sayfa.ata(s, c, h)
            self.sayfa.bicim_geri_koy(self.eksen, self.nerede, self.adet, self._bicim_silinen)
        self.sayfa.boyut_durumu_yukle(self._olcu_once)


class SatirEkleSil(_SatirSutun):
    eksen = 0


class SutunEkleSil(_SatirSutun):
    eksen = 1


class HucreTasi:
    """Kes-yapıştır = taşıma (tek geri al adımı). `kaynak` sayfadaki `kutu` (r1, c1, r2, c2)
    `hedef` sayfada sol üst köşesi `hedef_konum` olacak biçimde taşınır. Kitaptaki tüm formüllerin
    taşınan bölgeye işaret eden başvuruları yeni yere kayar (`formul.kaydir.tasi`); taşınan
    formüllerin kendi başvuruları kaymaz."""

    def __init__(self, kaynak: Sayfa, kutu, hedef: Sayfa, hedef_konum: Anahtar):
        self.kaynak, self.kutu, self.hedef, self.hedef_konum = kaynak, tuple(kutu), hedef, hedef_konum
        self._eski: List = []            # [(Sayfa, {anahtar: eski Hucre})] uygulama sırasıyla
        self._eski_bicim: List = []      # [(Sayfa, bicim_yaz'ın eski kayıtları)] uygulama sırasıyla

    def _plan(self) -> Dict[Sayfa, Dict[Anahtar, Optional[Hucre]]]:
        from ..formul.kaydir import tasi                  # model → formul yalnız burada
        r1, c1, r2, c2 = self.kutu
        dr, dc = self.hedef_konum[0] - r1, self.hedef_konum[1] - c1
        ki, hi = self.kaynak.kimlik, self.hedef.kimlik
        kitap = self.kaynak.kitap
        sayfalar = kitap.sayfalar if kitap is not None else list({self.kaynak, self.hedef})

        def hedefte(s, r, c):
            return s is self.hedef and r1 + dr <= r <= r2 + dr and c1 + dc <= c <= c2 + dc

        plan: Dict[Sayfa, Dict[Anahtar, Optional[Hucre]]] = {s: {} for s in sayfalar}
        # 1) taşınan hücreler: kaynak boşalır, hedefe (formülü düzeltilmiş) yazılır
        tasinan = list(self.kaynak.aralikta(Aralik(r1, c1, r2, c2)))
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                plan[self.kaynak][(r, c)] = None
        for r in range(r1 + dr, r2 + dr + 1):
            for c in range(c1 + dc, c2 + dc + 1):
                plan[self.hedef][(r, c)] = None
        for r, c, h in tasinan:
            if h.formul is not None:
                yeni = tasi(h.formul, ki, hi, ki, self.kutu, hi, dr, dc)
                if yeni is not None:
                    h = Hucre(None, yeni)
            plan[self.hedef][(r + dr, c + dc)] = h
        # 2) diğer formüller: taşınan bölgeye işaret edenler kayar
        for s in sayfalar:
            for r, c, h in s.dolu_hucreler(sirali=False):
                if h.formul is None:
                    continue
                if s is self.kaynak and r1 <= r <= r2 and c1 <= c <= c2:
                    continue                              # taşınan formül (yukarıda)
                if hedefte(s, r, c):
                    continue                              # üzerine yazılıyor
                yeni = tasi(h.formul, s.kimlik, s.kimlik, ki, self.kutu, hi, dr, dc)
                if yeni is not None:
                    plan[s][(r, c)] = Hucre(None, yeni)
        return {s: d for s, d in plan.items() if d}

    def _bicim_plani(self):
        """Biçim de taşınır: taşınan her hücrenin ETKİN stili hedefe yazılır, kaynak varsayılana döner.
        Kaynak/hedef sayfada hiç biçim yoksa boş. Döner: [(Sayfa, {anahtar: kimlik})] uygulama sırasıyla."""
        k, h = self.kaynak, self.hedef
        if not (k._stil or k.satir_stil or k.sutun_stil or h._stil or h.satir_stil or h.sutun_stil):
            return []
        r1, c1, r2, c2 = self.kutu
        dr, dc = self.hedef_konum[0] - r1, self.hedef_konum[1] - c1
        tasinan = {(r + dr, c + dc): k.stil_kimligi(r, c)
                   for r in range(r1, r2 + 1) for c in range(c1, c2 + 1)}
        temizle = {(r, c): 0 for r in range(r1, r2 + 1) for c in range(c1, c2 + 1)}
        if k is h:
            temizle.update(tasinan)
            return [(k, temizle)]
        return [(k, temizle), (h, tasinan)]

    def yap(self) -> None:
        self._eski = [(s, s.toplu_yaz(yeni)) for s, yeni in self._plan().items()]
        self._eski_bicim = [(s, s.bicim_yaz(hucreler=yeni)) for s, yeni in self._bicim_plani()]

    def geri_al(self) -> None:
        for s, eski in reversed(self._eski_bicim):
            s.bicim_yaz(*eski)
        for s, eski in reversed(self._eski):
            s.toplu_yaz(eski)


class BicimDegis:
    """Hücre/satır/sütun biçimini tek adımda değiştirir (K4: girdiye dokunmaz, formül yeniden hesaplanmaz).
    `hucreler`/`satirlar`/`sutunlar`: yeni HAM stil kayıtları ({anahtar: kimlik | None}); eski kayıtlar
    saklanır, geri al yükler. Genelde `bicim_komutu` ile kurulur."""

    def __init__(self, sayfa: Sayfa, hucreler=None, satirlar=None, sutunlar=None):
        self.sayfa = sayfa
        self.hucreler = dict(hucreler or {})
        self.satirlar = dict(satirlar or {})
        self.sutunlar = dict(sutunlar or {})
        self._eski = ({}, {}, {})

    def bos_mu(self) -> bool:
        return not (self.hucreler or self.satirlar or self.sutunlar)

    def yap(self) -> None:
        self._eski = self.sayfa.bicim_yaz(self.hucreler, self.satirlar, self.sutunlar)

    def geri_al(self) -> None:
        self.sayfa.bicim_yaz(*self._eski)


BICIM_ALAN_SINIRI = 5_000_000        # tam satır/sütun olmayan tek aralıkta en çok hücre
BICIM_KESISIM_SINIRI = 200_000       # tam sütun × biçimli satır kesişimi için en çok açık hücre kaydı


def bicim_komutu(sayfa: Sayfa, araliklar, yama: Optional[StilYama] = None, sifirla: bool = False) -> BicimDegis:
    """Seçimdeki (çoklu aralık dahil) her hücreye `yama`yı uygulayan komut. `sifirla=True`: yama yerine
    biçimi varsayılana döndürür ("Biçimleri temizle"; satır/sütun stilleri de kalkar).

    - Tam satır seçimi satır stiline, tam sütun seçimi sütun stiline yazılır (1 milyon hücre değil);
      aralıkta zaten açık stil kaydı olan hücrelere de yama uygulanır (Excel gibi).
    - Tam sütun seçiminde, biçimli satırların kesişimleri satır stilini ezmesin diye o hücrelere açık
      kayıt yazılır (son uygulanan kazanır). Tüm sayfa seçimi sütun yolunu kullanır.
    - Sıradan aralık: yalnız etkin stili DEĞİŞEN hücreler yazılır.
    """
    havuz = sayfa.havuz
    if sifirla:
        def uygula(k):
            return 0
    else:
        def uygula(k, _h=havuz.yama_uygula):
            return _h(k, yama)
    hucre: Dict[Anahtar, Optional[int]] = {}
    satir: Dict[int, Optional[int]] = {}
    sutun: Dict[int, Optional[int]] = {}
    for ar in araliklar:
        r1, c1, r2, c2 = ar.ilk_satir, ar.ilk_sutun, ar.son_satir, ar.son_sutun
        tam_sutun = r1 == 1 and r2 == MAX_ROW
        tam_satir = c1 == 1 and c2 == MAX_COL
        if tam_sutun:
            for c in range(c1, c2 + 1):
                sutun[c] = uygula(sayfa.sutun_stil.get(c, 0))
            for (r, c), k in sayfa._stil.items():
                if c1 <= c <= c2:
                    hucre[(r, c)] = uygula(k)
            if len(sayfa.satir_stil) * (c2 - c1 + 1) <= BICIM_KESISIM_SINIRI:
                for r in sayfa.satir_stil:
                    for c in range(c1, c2 + 1):
                        if (r, c) not in hucre:
                            hucre[(r, c)] = uygula(sayfa.stil_kimligi(r, c))
        elif tam_satir:
            for r in range(r1, r2 + 1):
                satir[r] = uygula(sayfa.satir_stil.get(r, 0))
            for (r, c), k in sayfa._stil.items():
                if r1 <= r <= r2:
                    hucre[(r, c)] = uygula(k)
        else:
            if (r2 - r1 + 1) * (c2 - c1 + 1) > BICIM_ALAN_SINIRI:
                raise AdresHatasi("Seçim biçimlendirme için çok büyük; tam satır/sütun seçin")
            stil_kimligi = sayfa.stil_kimligi
            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    k = stil_kimligi(r, c)
                    yeni = uygula(k)
                    if yeni != k:
                        hucre[(r, c)] = yeni
    return BicimDegis(sayfa, hucre, satir, sutun)


class OlcuDegis:
    """Sütun genişliği / satır yüksekliği / gizleme değişikliği (tek adım).

    İki kullanım: `uygula(sayfa)` işlevi verilir (yap() çağırır), ya da değişiklik zaten
    uygulanmışsa (fare sürüklemesi) `eski` ve `yeni` durumlar verilir.
    """

    def __init__(self, sayfa: Sayfa, uygula=None, eski=None, yeni=None):
        self.sayfa, self.uygula, self.eski, self.yeni = sayfa, uygula, eski, yeni

    def yap(self) -> None:
        if self.yeni is not None:
            self.sayfa.boyut_durumu_yukle(self.yeni)
            return
        self.eski = self.sayfa.boyut_durumu()
        self.uygula(self.sayfa)
        self.yeni = self.sayfa.boyut_durumu()
        self.sayfa.boyut_degisti()

    def geri_al(self) -> None:
        self.sayfa.boyut_durumu_yukle(self.eski)


class SayfaEkle:
    """Kitabın sonuna yeni sayfa ekler. Geri alınca sayfa (verisiyle) kitaptan çıkar; yinelenince
    aynı nesne/kimlikle geri gelir."""

    def __init__(self, kitap, ad=None):
        self.kitap, self.ad = kitap, ad
        self.sayfa = None
        self.indeks = None

    def yap(self) -> None:
        if self.sayfa is None:
            self.sayfa = self.kitap.sayfa_ekle(self.ad)
        else:
            self.kitap.sayfa_geri_koy(self.sayfa, self.indeks)

    def geri_al(self) -> None:
        self.indeks = self.kitap.sayfa_sil(self.sayfa)


class SayfaSil:
    """Sayfayı kitaptan çıkarır; nesnesi ve verisi komutta saklanır, geri alınca aynı yere döner."""

    def __init__(self, kitap, sayfa):
        self.kitap, self.sayfa = kitap, sayfa
        self.indeks = None

    def yap(self) -> None:
        self.indeks = self.kitap.sayfa_sil(self.sayfa)

    def geri_al(self) -> None:
        self.kitap.sayfa_geri_koy(self.sayfa, self.indeks)


class SayfaYenidenAdlandir:
    def __init__(self, kitap, sayfa, ad: str):
        self.kitap, self.sayfa, self.ad = kitap, sayfa, ad
        self.eski_ad = None

    def yap(self) -> None:
        self.eski_ad = self.sayfa.ad
        self.kitap.yeniden_adlandir(self.sayfa, self.ad)

    def geri_al(self) -> None:
        self.kitap.yeniden_adlandir(self.sayfa, self.eski_ad)


class SayfaTasi:
    def __init__(self, kitap, sayfa, yeni_indeks: int):
        self.kitap, self.sayfa, self.yeni_indeks = kitap, sayfa, yeni_indeks
        self.eski_indeks = None

    def yap(self) -> None:
        self.eski_indeks = self.kitap.sayfalar.index(self.sayfa)
        self.kitap.sayfa_tasi(self.sayfa, self.yeni_indeks)

    def geri_al(self) -> None:
        self.kitap.sayfa_tasi(self.sayfa, self.eski_indeks)


class Grup:
    """Birden çok komutu geri al yığınında tek adım yapar."""

    def __init__(self, komutlar: List[Komut]):
        self.komutlar = list(komutlar)

    def yap(self) -> None:
        for k in self.komutlar:
            k.yap()

    def geri_al(self) -> None:
        for k in reversed(self.komutlar):
            k.geri_al()


def ana_sayfa(komut, geri_al: bool = False):
    """Komutun asıl değişikliği yaptığı sayfa (başka sayfalardaki formül düzeltmeleri yan etkidir);
    sayfa işlemlerinde ya da bilinmiyorsa None. Geri al/yinele sonrası arayüz o sayfaya geçer.
    Taşımada geri alırken kaynak, yinelerken hedef sayfa."""
    if isinstance(komut, HucreTasi):
        return komut.kaynak if geri_al else komut.hedef
    if isinstance(komut, Grup):
        for k in komut.komutlar:
            s = ana_sayfa(k, geri_al)
            if s is not None:
                return s
        return None
    return getattr(komut, "sayfa", None) if isinstance(
        komut, (HucrelerDegis, _SatirSutun, OlcuDegis, BicimDegis)) else None


class GeriAlYigini:
    def __init__(self, sinir: int = 100):
        self.sinir = sinir
        self.son_komut = None            # en son geri alınan/yinelenen komut
        self.son_geri_al = False
        self._geri: List[Komut] = []
        self._ileri: List[Komut] = []

    def calistir(self, komut: Komut) -> None:
        komut.yap()
        self._geri.append(komut)
        if len(self._geri) > self.sinir:
            del self._geri[0]
        self._ileri.clear()

    def geri_alinabilir(self) -> bool:
        return bool(self._geri)

    def yinelenebilir(self) -> bool:
        return bool(self._ileri)

    def geri_al(self) -> bool:
        if not self._geri:
            return False
        k = self._geri.pop()
        k.geri_al()
        self._ileri.append(k)
        self.son_komut, self.son_geri_al = k, True
        return True

    def yinele(self) -> bool:
        if not self._ileri:
            return False
        k = self._ileri.pop()
        k.yap()
        self._geri.append(k)
        self.son_komut, self.son_geri_al = k, False
        return True

    def temizle(self) -> None:
        self._geri.clear()
        self._ileri.clear()
