"""Geri al / yinele (komut deseni). Qt yok.

Aralık işlemleri tek adımdır: tek komut ya da `Grup`.
"""
from typing import Dict, List, Optional, Protocol

from .adres import MAX_COL, MAX_ROW, AdresHatasi, Aralik
from .sayfa import Anahtar, Hucre, Sayfa
from .harmanla import tr_kucuk
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
        self._ek_once = None             # Faz 5: ([(Sayfa, ek_durumu)], kitap.ad_durumu) — geri almak için

    def _formulleri_duzelt(self) -> None:
        from ..formul.kaydir import yapi_duzeltmeleri    # model → formul yalnız burada
        self._duzeltmeler = yapi_duzeltmeleri(
            self.sayfa.kitap, self.sayfa, "sutun" if self.eksen else "satir", self.nerede,
            self.adet if self.ekle else -self.adet)
        for s, degisen in self._duzeltmeler.items():
            s.toplu_yaz({k: Hucre(None, yeni) for k, (_, yeni) in degisen.items()})
        from ..formul.kaydir import ek_duzeltmeleri
        ek_duzeltmeleri(self.sayfa.kitap, self.sayfa, "sutun" if self.eksen else "satir",
                        self.nerede, self.adet if self.ekle else -self.adet)
        self._nesne_basvurularini_duzelt()

    def _nesne_basvurularini_duzelt(self) -> None:
        """Kitaptaki TÜM sayfaların grafik başvuruları (seriler) ekle-sil yapılan sayfaya bakıyorsa kayar
        (faz6_tasarim.md §2.2). Nesnelerin kendi çapaları `Sayfa._kaydir`da kaydı."""
        from .adres import MAX_COL, MAX_ROW
        from .grafik import Grafik, grafik_referanslarini_kaydir
        kitap = self.sayfa.kitap
        sinir = MAX_COL if self.eksen else MAX_ROW
        fark = self.adet if self.ekle else -self.adet
        for s in (kitap.sayfalar if kitap else [self.sayfa]):
            if not s.nesneler:
                continue
            yeni = [grafik_referanslarini_kaydir(n, self.sayfa.kimlik, self.eksen, self.nerede, fark, sinir)
                    if isinstance(n, Grafik) else n for n in s.nesneler]
            s.nesne_baglari_yaz(yeni)

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
        self._birlesim_once = self.sayfa.birlesim_durumu()
        self._yapi_once = self.sayfa.sayfa_yapisi
        kitap = self.sayfa.kitap
        self._ek_once = ([(s, s.ek_durumu()) for s in (kitap.sayfalar if kitap else [self.sayfa])],
                         kitap.ad_durumu() if kitap else None,
                         [(s, s.nesne_durumu()) for s in (kitap.sayfalar if kitap else [self.sayfa])])
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
        self.sayfa.birlesim_yukle(self._birlesim_once)
        self.sayfa.yazdirma_yaz(self._yapi_once)
        sayfa_durumlari, ad_durumu, nesne_durumlari = self._ek_once
        for s, durum in sayfa_durumlari:
            s.ek_durumu_yukle(durum)
        if ad_durumu is not None:
            self.sayfa.kitap.ad_durumu_yukle(ad_durumu)
        for s, durum in nesne_durumlari:
            s.nesne_durumu_yukle(durum)


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
        self._eski_birlesim: List = []   # [(Sayfa, birleşim listesi)] geri almak için

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
        kitap = self.kaynak.kitap
        self._ad_once = kitap.ad_durumu() if kitap is not None else None
        self._eski = [(s, s.toplu_yaz(yeni)) for s, yeni in self._plan().items()]
        if kitap is not None and kitap.adlar:
            from ..formul.kaydir import adlari_tasi           # model → formul yalnız burada
            r1, c1, _, _ = self.kutu
            adlari_tasi(kitap, self.kaynak.kimlik, self.kutu, self.hedef.kimlik,
                        self.hedef_konum[0] - r1, self.hedef_konum[1] - c1)
        self._eski_bicim = [(s, s.bicim_yaz(hucreler=yeni)) for s, yeni in self._bicim_plani()]
        self._birlesimleri_tasi()
        self._notlari_tasi()

    def _notlari_tasi(self) -> None:
        """Notlar hücreyle birlikte taşınır; hedef bölgedeki eski notlar ezilir (içerik gibi)."""
        k, h = self.kaynak, self.hedef
        self._eski_not = []
        if not k.notlar and not h.notlar:
            return
        r1, c1, r2, c2 = self.kutu
        dr, dc = self.hedef_konum[0] - r1, self.hedef_konum[1] - c1
        tasinan = {(r, c): n for (r, c), n in k.notlar.items() if r1 <= r <= r2 and c1 <= c <= c2}
        ezilen = [(r, c) for (r, c) in h.notlar if r1 + dr <= r <= r2 + dr and c1 + dc <= c <= c2 + dc]
        if not tasinan and not ezilen:
            return
        yeni_k = {a: None for a in tasinan}
        yeni_h = {a: None for a in ezilen}
        hedefe = {(r + dr, c + dc): n for (r, c), n in tasinan.items()}
        if h is k:
            yeni_k.update(yeni_h)
            yeni_k.update(hedefe)
            self._eski_not = [(k, k.notlari_yaz(yeni_k))]
        else:
            yeni_h.update(hedefe)
            self._eski_not = [(k, k.notlari_yaz(yeni_k)), (h, h.notlari_yaz(yeni_h))]

    def _birlesimleri_tasi(self) -> None:
        """Kutuya tamamen giren birleşimler hedefe taşınır; hedef bölgeyle kesişen eski birleşimler kalkar."""
        k, h = self.kaynak, self.hedef
        r1, c1, r2, c2 = self.kutu
        dr, dc = self.hedef_konum[0] - r1, self.hedef_konum[1] - c1
        kutu = Aralik(r1, c1, r2, c2)
        tasinan = [b for b in k.birlesimler if kutu.ilk_satir <= b.ilk_satir and b.son_satir <= kutu.son_satir
                   and kutu.ilk_sutun <= b.ilk_sutun and b.son_sutun <= kutu.son_sutun]
        hedef_bolge = Aralik(r1 + dr, c1 + dc, r2 + dr, c2 + dc)
        ezilen = h.birlesim_kesisen(hedef_bolge)
        if not tasinan and not ezilen:
            return
        self._eski_birlesim = [(k, k.birlesim_durumu())] + ([(h, h.birlesim_durumu())] if h is not k else [])
        yeni = [Aralik(b.ilk_satir + dr, b.ilk_sutun + dc, b.son_satir + dr, b.son_sutun + dc) for b in tasinan]
        if h is k:
            k.birlesimleri_yaz(yeni, list(dict.fromkeys(tasinan + ezilen)))
        else:
            k.birlesimleri_yaz([], tasinan)
            h.birlesimleri_yaz(yeni, ezilen)

    def geri_al(self) -> None:
        for s, eski in reversed(getattr(self, "_eski_not", [])):
            s.notlari_yaz(eski)
        for s, eski in reversed(self._eski_birlesim):
            s.birlesim_yukle(eski)
        self._eski_birlesim = []
        for s, eski in reversed(self._eski_bicim):
            s.bicim_yaz(*eski)
        for s, eski in reversed(self._eski):
            s.toplu_yaz(eski)
        if getattr(self, "_ad_once", None) is not None:
            self.kaynak.kitap.ad_durumu_yukle(self._ad_once)


class NotlarDegis:
    """Hücre notlarını değiştirir (ekle / düzenle / sil; tek geri al adımı). `yeni`:
    {(satır, sütun): Not | None} (None = notu sil). Hücre içeriğine dokunmaz."""

    def __init__(self, sayfa: Sayfa, yeni):
        self.sayfa = sayfa
        self.yeni = dict(yeni)
        self.eski = {}

    def bos_mu(self) -> bool:
        n = self.sayfa.notlar
        return all(n.get(a) == (v if v is not None and not v.bos_mu() else None)
                   for a, v in self.yeni.items())

    def yap(self) -> None:
        self.eski = self.sayfa.notlari_yaz(self.yeni)

    def geri_al(self) -> None:
        self.sayfa.notlari_yaz(self.eski)


class FiltreDegis:
    """Otomatik filtreyi koyar / değiştirir / kaldırır (`yeni=None`) ve satır gizliliğini baştan hesaplar
    (faz5_tasarim.md §6.2). Filtre aralığındaki (eski ve yeni) tüm veri satırlarının gizliliği baştan
    belirlenir — elle gizlenmiş satır da açılabilir (Excel de ayrım tutmaz). Tek geri al adımı."""

    def __init__(self, sayfa: Sayfa, yeni, metin_al=None):
        self.sayfa, self.yeni, self.metin_al = sayfa, yeni, metin_al
        self._eski_filtre = None
        self._eski_boyut = None
        self.gizlenen = 0                     # son uygulamada filtreyle gizlenen satır sayısı

    def yap(self) -> None:
        from .filtre import gizlenecekler, veri_satirlari
        s = self.sayfa
        self._eski_filtre, self._eski_boyut = s.filtre, s.boyut_durumu()
        etkilenen = set()
        for f in (s.filtre, self.yeni):
            if f is not None:
                etkilenen.update(veri_satirlari(f))
        gizli = (gizlenecekler(s, self.yeni) if self.metin_al is None
                 else gizlenecekler(s, self.yeni, self.metin_al)) if self.yeni is not None else set()
        self.gizlenen = len(gizli)
        s.filtre_yaz(self.yeni)                # önce filtre: ALTTOPLAM `boyut` olayında yeni aralığı görür
        s.gizli_satir = (s.gizli_satir - etkilenen) | gizli
        s.boyut_degisti()

    def geri_al(self) -> None:
        self.sayfa.filtre_yaz(self._eski_filtre)
        self.sayfa.boyut_durumu_yukle(self._eski_boyut)


class DogrulamaDegis:
    """Aralıklara veri doğrulama kuralı koyar (`dv`) ya da kaldırır (`dv=None`); eski kuralların bu
    hücrelerdeki etkisi kalkar (`dogrulama.yeni_liste`). Tek geri al adımı."""

    def __init__(self, sayfa: Sayfa, araliklar, dv=None):
        self.sayfa, self.araliklar, self.dv = sayfa, list(araliklar), dv
        self._eski = None

    def bos_mu(self) -> bool:
        from .dogrulama import yeni_liste
        return yeni_liste(self.sayfa.dogrulamalar, self.araliklar, self.dv) == self.sayfa.dogrulamalar

    def yap(self) -> None:
        from .dogrulama import yeni_liste
        self._eski = list(self.sayfa.dogrulamalar)
        self.sayfa.dogrulamalari_yaz(yeni_liste(self._eski, self.araliklar, self.dv))

    def geri_al(self) -> None:
        self.sayfa.dogrulamalari_yaz(self._eski)


class KosulluDegis:
    """Koşullu biçim kural listesini değiştirir (kural ekle/düzenle/sil/sırala/temizle; tek geri al adımı).
    `yeni`: yeni TAM liste (sıra = öncelik) ya da `yeni(eski_liste) -> liste` işlevi."""

    def __init__(self, sayfa: Sayfa, yeni):
        self.sayfa, self._yeni = sayfa, yeni
        self._eski = None

    def _hesapla(self, eski):
        return list(self._yeni(list(eski)) if callable(self._yeni) else self._yeni)

    def bos_mu(self) -> bool:
        return self._hesapla(self.sayfa.kosullu) == self.sayfa.kosullu

    def yap(self) -> None:
        self._eski = list(self.sayfa.kosullu)
        self.sayfa.kosullulari_yaz(self._hesapla(self._eski))

    def geri_al(self) -> None:
        self.sayfa.kosullulari_yaz(self._eski)


class AdDegis:
    """Tanımlı ad ekler / düzenler / yeniden adlandırır / siler (tek geri al adımı).
    `eski_anahtar`: düzenlenen/silinen adın anahtarı (yeni ad için None); `yeni`: yeni `TanimliAd`
    (silmede None). Yeniden adlandırma kitaptaki formüllerdeki (hücre + doğrulama + koşullu biçim +
    diğer adlar) o ada çözülen ad sözcüklerini de yeni adla yazar; silmede formüller metni korur ve
    `#AD?` hesaplanır (Excel). Geçersiz ad/yinelenen ad kurulurken `AdHatasi` verir."""

    def __init__(self, kitap, eski_anahtar, yeni):
        from .ad import ad_kontrol
        if yeni is not None:
            ad_kontrol(kitap, yeni, eski_anahtar)
        self.kitap, self.eski_anahtar, self.yeni = kitap, eski_anahtar, yeni
        self._ad_once = None
        self._ek_once = None
        self._duzeltmeler = {}

    def yap(self) -> None:
        kitap = self.kitap
        self._ad_once = kitap.ad_durumu()
        self._ek_once = [(s, s.ek_durumu()) for s in kitap.sayfalar]
        hedef = kitap.adlar.get(self.eski_anahtar) if self.eski_anahtar is not None else None
        self._duzeltmeler = {}
        if (hedef is not None and self.yeni is not None
                and tr_kucuk(hedef.ad) != tr_kucuk(self.yeni.ad)):
            from ..formul.kaydir import ad_yeniden_adlandir   # model → formul yalnız burada
            self._duzeltmeler = ad_yeniden_adlandir(kitap, hedef, self.yeni.ad)
            for s, degisen in self._duzeltmeler.items():
                s.toplu_yaz({k: Hucre(None, yeni) for k, (_, yeni) in degisen.items()})
        kitap.ad_yaz(self.yeni, self.eski_anahtar)

    def geri_al(self) -> None:
        for s, degisen in self._duzeltmeler.items():
            s.toplu_yaz({k: Hucre(None, eski) for k, (eski, _) in degisen.items()})
        for s, durum in self._ek_once:
            s.ek_durumu_yukle(durum)
        self.kitap.ad_durumu_yukle(self._ad_once)


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
            elif tam_satir:                      # tüm sayfa: biçimli satırların kendi stili de değişir
                for r, k in sayfa.satir_stil.items():
                    satir[r] = uygula(k)
            else:
                raise AdresHatasi("Seçimde çok sayıda biçimli satır var; daha az sütun seçin")
        elif tam_satir:
            for r in range(r1, r2 + 1):
                satir[r] = uygula(sayfa.satir_stil.get(r, 0))
            for (r, c), k in sayfa._stil.items():
                if r1 <= r <= r2:
                    hucre[(r, c)] = uygula(k)
            # biçimli sütunlarla kesişim: satır stili sütun stilini örtmesin (tam sütun dalının simetriği)
            if len(sayfa.sutun_stil) * (r2 - r1 + 1) > BICIM_KESISIM_SINIRI:
                raise AdresHatasi("Seçimde çok sayıda biçimli sütun var; daha az satır seçin")
            for c in sayfa.sutun_stil:
                for r in range(r1, r2 + 1):
                    if (r, c) not in hucre:
                        hucre[(r, c)] = uygula(sayfa.stil_kimligi(r, c))
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


class BirlesimDegis:
    """Birleşim ekler/kaldırır (tek adım). Hücre içeriği ve biçimine dokunmaz; genelde `birlesim_komutu`."""

    def __init__(self, sayfa: Sayfa, ekle, kaldir):
        self.sayfa, self.ekle, self.kaldir = sayfa, list(ekle), list(kaldir)

    def bos_mu(self) -> bool:
        return not (self.ekle or self.kaldir)

    def yap(self) -> None:
        self.sayfa.birlesimleri_yaz(self.ekle, self.kaldir)

    def geri_al(self) -> None:
        self.sayfa.birlesimleri_yaz(self.kaldir, self.ekle)


BIRLESIM_TURLERI = ("birlestir", "ortala", "satirlar", "coz")


def birlesim_hedefleri(aralik: Aralik, tur: str) -> List[Aralik]:
    """Birleştirilecek aralıklar: `satirlar` her satırı ayrı birleştirir; tek hücreli sonuç atlanır."""
    if tur == "satirlar":
        hedefler = [Aralik(r, aralik.ilk_sutun, r, aralik.son_sutun)
                    for r in range(aralik.ilk_satir, aralik.son_satir + 1)]
    else:
        hedefler = [aralik]
    return [h for h in hedefler if h.ilk_satir != h.son_satir or h.ilk_sutun != h.son_sutun]


def birlesim_veri_kaybi(sayfa: Sayfa, aralik: Aralik, tur: str) -> bool:
    """Birleştirme sol üst dışında dolu hücre silecek mi (arayüz Excel'deki gibi uyarır)?"""
    for h in birlesim_hedefleri(aralik, tur):
        for r, c, hu in sayfa.aralikta(h):
            if (r, c) != (h.ilk_satir, h.ilk_sutun) and not hu.bos_mu():
                return True
    return False


def birlesim_komutu(sayfa: Sayfa, araliklar, tur: str):
    """Seçimden birleştirme komutu; yapılacak iş yoksa None.

    - `birlestir`: seçimi tek hücre yapar; `ortala`: + sol üst hücre yatay ortalanır; `satirlar`: her
      satırı ayrı birleştirir; `coz`: seçimle kesişen tüm birleşimleri kaldırır.
    - Sol üst dışındaki hücrelerin içeriği silinir (biçimleri kalır); hedef içinde tamamen kalan eski
      birleşimler çözülür. Hedefi kısmen kesen birleşim ValueError (arayüz seçimi önce genişletir).
    - Çoklu aralıkta birleştirilmez (Excel de reddeder).
    """
    if tur not in BIRLESIM_TURLERI:
        raise ValueError(f"Bilinmeyen birleştirme türü: {tur!r}")
    if tur == "coz":
        kaldir = []
        for ar in araliklar:
            for b in sayfa.birlesim_kesisen(ar):
                if b not in kaldir:
                    kaldir.append(b)
        return Grup([BirlesimDegis(sayfa, [], kaldir)]) if kaldir else None
    if len(araliklar) != 1:
        raise ValueError("Birden çok aralık birleştirilemez")
    hedefler = birlesim_hedefleri(araliklar[0], tur)
    if not hedefler:
        return None
    kaldir, silinecek = [], {}
    for h in hedefler:
        for b in sayfa.birlesim_kesisen(h):
            if not (h.ilk_satir <= b.ilk_satir and b.son_satir <= h.son_satir
                    and h.ilk_sutun <= b.ilk_sutun and b.son_sutun <= h.son_sutun):
                raise ValueError("Seçim, birleşik bir hücreyi kısmen kapsıyor")
            if b not in kaldir:
                kaldir.append(b)
        for r, c, _ in sayfa.aralikta(h):
            if (r, c) != (h.ilk_satir, h.ilk_sutun):
                silinecek[(r, c)] = None
    komutlar = []
    if silinecek:
        komutlar.append(HucrelerDegis(sayfa, silinecek))
    if tur == "ortala":
        ust_sol = [Aralik(h.ilk_satir, h.ilk_sutun, h.ilk_satir, h.ilk_sutun) for h in hedefler]
        komutlar.append(bicim_komutu(sayfa, ust_sol, StilYama(yatay="orta")))
    komutlar.append(BirlesimDegis(sayfa, hedefler, kaldir))
    return Grup(komutlar)


class BicimPlani:
    """Sıralı yama listesini tek adımda uygular: `plan = [(aralıklar, StilYama), …]`.

    Her adım bir öncekinin SONUCUNU görerek kurulur (köşe hücrede üst + sol kenarlık gibi
    örtüşen yamalar birbirini ezmesin); bu yüzden komutlar `yap()` anında üretilir. Geri al
    hepsini ters sırayla çözer."""

    def __init__(self, sayfa: Sayfa, plan):
        self.sayfa = sayfa
        self.plan = list(plan)
        self._komutlar: List[BicimDegis] = []

    def bos_mu(self) -> bool:
        return not self.plan

    def yap(self) -> None:
        self._komutlar = []
        for araliklar, yama in self.plan:
            k = bicim_komutu(self.sayfa, araliklar, yama)
            k.yap()
            self._komutlar.append(k)

    def geri_al(self) -> None:
        for k in reversed(self._komutlar):
            k.geri_al()


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
    if hasattr(komut, "ana_sayfa_ver"):                    # kendi geçiş sayfasını bilen komutlar (Özet Tablo vb.)
        return komut.ana_sayfa_ver(geri_al)
    if isinstance(komut, Grup):
        for k in komut.komutlar:
            s = ana_sayfa(k, geri_al)
            if s is not None:
                return s
        return None
    return getattr(komut, "sayfa", None) if isinstance(
        komut, (HucrelerDegis, _SatirSutun, OlcuDegis, BicimDegis, BicimPlani, BirlesimDegis, Sirala,
                NotlarDegis, FiltreDegis, DogrulamaDegis, KosulluDegis, NesneEkle, NesneSil, NesneDegis,
                NesneSirala)) else None


class GeriAlYigini:
    def __init__(self, sinir: int = 100):
        self.sinir = sinir
        self.son_komut = None            # en son geri alınan/yinelenen komut
        self.son_geri_al = False
        self._geri: List[Komut] = []
        self._ileri: List[Komut] = []

    def damga(self):
        """Geri al yığınının anlık durumu (kayıt noktası işareti): geri alıp aynı noktaya dönülürse eşit olur."""
        return (len(self._geri), self._geri[-1] if self._geri else None)

    @staticmethod
    def damga_esit(a, b) -> bool:
        return a[0] == b[0] and a[1] is b[1]

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


class SayfaYapisiDegis:
    """Sayfanın yazdırma ayarlarını değiştirir (geri alınabilir; Excel'de geri alınamaz — bilerek fark:
    kayıt noktası işaretini ("değişti") doğru tutmak için komut)."""

    def __init__(self, sayfa: Sayfa, yeni):
        self.sayfa, self.yeni, self.eski = sayfa, yeni, sayfa.sayfa_yapisi

    def bos_mu(self) -> bool:
        return self.yeni == self.eski

    def yap(self) -> None:
        self.sayfa.yazdirma_yaz(self.yeni)

    def geri_al(self) -> None:
        self.sayfa.yazdirma_yaz(self.eski)


class NesneEkle:
    """Yüzen nesne (grafik/resim) ekler (tek geri al adımı). İlk `yap`ta kimlik atanır; yinelemede aynı
    kimlikle aynı sıraya geri konur. `nesne` ekledikten sonra sayfada saklanan (kimlikli) halidir."""

    def __init__(self, sayfa: Sayfa, nesne, indeks: Optional[int] = None):
        self.sayfa, self.nesne, self.indeks = sayfa, nesne, indeks

    def yap(self) -> None:
        self.nesne = self.sayfa.nesne_ekle(self.nesne, self.indeks)
        self.indeks = self.sayfa.nesneler.index(self.nesne)

    def geri_al(self) -> None:
        self.sayfa.nesne_sil(self.nesne.kimlik)


class NesneSil:
    """Nesneyi siler (tek geri al adımı; geri alınca aynı kimlik ve z sırasıyla döner)."""

    def __init__(self, sayfa: Sayfa, kimlik: int):
        self.sayfa, self.kimlik = sayfa, kimlik
        self._nesne = None
        self._indeks = 0

    def yap(self) -> None:
        self._nesne, self._indeks = self.sayfa.nesne_sil(self.kimlik)

    def geri_al(self) -> None:
        self.sayfa.nesne_ekle(self._nesne, self._indeks)


class NesneDegis:
    """Aynı kimlikli nesneyi `yeni` ile değiştirir: taşıma, boyutlandırma, tür/başlık/seri değişimi (tek
    geri al adımı). Sürüklerken canlı önizleme komutsuz yapılır; bırakınca BU komut çalışır."""

    def __init__(self, sayfa: Sayfa, yeni):
        self.sayfa, self.yeni = sayfa, yeni
        self.eski = sayfa.nesne(yeni.kimlik)

    def bos_mu(self) -> bool:
        return self.eski is None or self.eski == self.yeni

    def yap(self) -> None:
        self.eski = self.sayfa.nesne_degistir(self.yeni)

    def geri_al(self) -> None:
        self.sayfa.nesne_degistir(self.eski)


class NesneSirala:
    """Nesneyi z sırasında taşır. `yon`: `one_getir` | `arkaya_gonder` | `bir_one` | `bir_arkaya`."""
    YONLER = ("one_getir", "arkaya_gonder", "bir_one", "bir_arkaya")

    def __init__(self, sayfa: Sayfa, kimlik: int, yon: str):
        if yon not in self.YONLER:
            raise ValueError(f"yön şunlardan biri olmalı: {self.YONLER}")
        self.sayfa, self.kimlik, self.yon = sayfa, kimlik, yon
        self._eski = None

    def _hedef(self) -> int:
        n = len(self.sayfa.nesneler)
        i = next(i for i, x in enumerate(self.sayfa.nesneler) if x.kimlik == self.kimlik)
        return {"one_getir": n - 1, "arkaya_gonder": 0, "bir_one": min(i + 1, n - 1),
                "bir_arkaya": max(i - 1, 0)}[self.yon]

    def bos_mu(self) -> bool:
        return self.sayfa.nesne(self.kimlik) is None or self._hedef() == next(
            i for i, x in enumerate(self.sayfa.nesneler) if x.kimlik == self.kimlik)

    def yap(self) -> None:
        self._eski = self.sayfa.nesne_sirala(self.kimlik, self._hedef())

    def geri_al(self) -> None:
        self.sayfa.nesne_sirala(self.kimlik, self._eski)


class Sirala:
    """Satırları (yon="satir") ya da sütunları (yon="sutun") `kaynaklar` düzenine göre yer değiştirir
    (faz5_tasarim.md §3.2). `aralik`: başlık hariç VERİ aralığı; `kaynaklar[i]`: o aralığın `i`.
    konumuna gelecek kaynak satırın (sütunun) mutlak numarası (`sirala.siralama_plani`).

    Formüller kopyala gibi kayar (`=B2*C2` 5. satıra gidince `=B5*C5`); dışarıdan bu hücrelere işaret
    eden başvurular değişmez (Excel gibi). Girdi, hücre stili (ham kayıt) ve not taşınır; satır
    yüksekliği, satır stili, doğrulama, koşullu biçim ve birleşimler yerinde kalır. Tek geri al adımı."""

    def __init__(self, sayfa: Sayfa, aralik: Aralik, kaynaklar: List[int], yon: str = "satir"):
        self.sayfa, self.aralik, self.kaynaklar, self.yon = sayfa, aralik, list(kaynaklar), yon
        self._eski_hucre = None
        self._eski_stil = None
        self._ek_once = None

    def _cizgiler(self):
        a = self.aralik
        return (range(a.ilk_sutun, a.son_sutun + 1) if self.yon == "satir"
                else range(a.ilk_satir, a.son_satir + 1))

    def yap(self) -> None:
        from ..formul.kaydir import kopyala             # model → formul yalnız burada
        s, a = self.sayfa, self.aralik
        satir = self.yon == "satir"
        ilk = a.ilk_satir if satir else a.ilk_sutun
        hucreler = s._hucreler
        yeni_h: Dict[Anahtar, Optional[Hucre]] = {}
        yeni_stil: Dict[Anahtar, Optional[int]] = {}
        yeni_not = dict(s.notlar)
        tasinan = [(ilk + i, k) for i, k in enumerate(self.kaynaklar) if k != ilk + i]
        cizgiler = list(self._cizgiler())
        stil_var = bool(s._stil)                         # ham stil kaydı yoksa stil taşıma işi de yok
        notlar_var = bool(s.notlar)
        if notlar_var:
            for hedef, _ in tasinan:                    # taşınan hedeflerin eski notları silinir
                for d in cizgiler:
                    yeni_not.pop((hedef, d) if satir else (d, hedef), None)
        hget = hucreler.get
        for hedef, kaynak in tasinan:
            fark = hedef - kaynak
            for d in cizgiler:
                ks, hs = ((kaynak, d), (hedef, d)) if satir else ((d, kaynak), (d, hedef))
                h = hget(ks)
                if h is not None and h.formul is not None:
                    yeni_f = kopyala(h.formul, fark, 0) if satir else kopyala(h.formul, 0, fark)
                    h = Hucre(None, yeni_f)
                if h is not None or hs in hucreler:       # boş → boş için yazım gerekmez
                    yeni_h[hs] = h
                if stil_var:
                    yeni_stil[hs] = s.ham_stil_kimligi(*ks)
                if notlar_var:
                    n = s.notlar.get(ks)
                    if n is not None:
                        yeni_not[hs] = n
        self._ek_once = s.ek_durumu()
        self._eski_hucre = s.toplu_yaz(yeni_h)
        self._eski_stil = s.bicim_yaz(hucreler=yeni_stil)[0] if yeni_stil else {}
        if yeni_not != s.notlar:
            s.ek_durumu_yukle((yeni_not,) + self._ek_once[1:])

    def geri_al(self) -> None:
        s = self.sayfa
        s.toplu_yaz(self._eski_hucre)
        s.bicim_yaz(hucreler=self._eski_stil)
        s.ek_durumu_yukle(self._ek_once)
