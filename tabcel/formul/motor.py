"""Hesaplama motoru: bağımlılık grafiği, kirli işaretleme, sıralı yeniden hesaplama. Qt yok.

Kitabın olaylarını dinler (faz2_tasarim.md §4):
- ``hucre``  → değişen hücreler grafikte yeniden kaydedilir; yalnız etkilenenler hesaplanır
- ``yapi``, ``sayfa`` (ekle/sil) → grafik baştan kurulur, tümü hesaplanır
- ``sayfa`` (ad/taşı) → yalnız değişken fonksiyonlu hücreler (DOLAYLI sayfa adıyla çalışır)
Hesap sırası: satır sırası + okurken erteleme (`_hesapla`). Döngüdeki hücreler 0 olur (Excel gibi)
ve `donguler` kümesine girer.
"""
from bisect import bisect_left
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Set, Tuple

from ..model import deger as D
from ..model.olay import Olay
from . import fonksiyonlar
from .agac import Ad, Cagri, Dugum, Ref, agac_kaydir, formul_ayristir
from .degerler import BEKLIYOR, ONEK_ONBELLEGI, Bekle, Dizi
from .degerlendir import AD_DERINLIK, Baglam, ad_agaci, hucre_sonucu
from .sozcuk import FormulHatasi

Anahtar = Tuple[int, int, int]                  # (sayfa kimliği, satır, sütun)
Kutu = Tuple[int, int, int, int]                # (r1, c1, r2, c2)
GENIS_SUTUN = 8                                 # bundan geniş aralık kutuları sütun indeksine girmez


class _Kayit:
    __slots__ = ("agac", "hucreler", "araliklar", "degisken")

    def __init__(self, agac, hucreler, araliklar, degisken):
        self.agac: Optional[Dugum] = agac
        self.hucreler: List[Anahtar] = hucreler
        self.araliklar: List[Tuple[int, Kutu]] = araliklar     # (kimlik, kutu)
        self.degisken: bool = degisken


def _oncul_topla(agac: Dugum, kendi: int, kitap, satir: int = 1,
                 sutun: int = 1, gizlilik: Optional[list] = None) -> Tuple[List[Anahtar], List[Tuple[int, Kutu]], bool]:
    """Ağaçtaki durağan başvurular (tek hücreler, aralıklar) ve değişken fonksiyon var mı.
    Tanımlı adlar (`Ad`) açılır: adın ağacı (hücreye göre kaydırılmış) aynı taramaya katılır."""
    hucreler, araliklar, degisken = [], [], False
    yigin = [(agac, ())]
    while yigin:
        d, adlar = yigin.pop()
        if isinstance(d, Ad):
            tanim = kitap.ad_bul(d.ad, kendi) if kitap is not None else None
            if tanim is not None and tanim.anahtar() not in adlar and len(adlar) < AD_DERINLIK:
                a = ad_agaci(tanim.formul)
                if a is not None:
                    yigin.append((agac_kaydir(a, satir - 1, sutun - 1), adlar + (tanim.anahtar(),)))
            continue
        if isinstance(d, Ref):
            b = d.basvuru
            if b.sayfa is None:
                k = kendi
            elif isinstance(b.sayfa, int):
                k = b.sayfa
            else:                                   # adla (bağlanmamış) başvuru — normalde olmaz
                s = next((s for s in kitap.sayfalar if s.ad.casefold() == b.sayfa.casefold()), None)
                if s is None:
                    continue
                k = s.kimlik
            if b.r1 == b.r2 and b.c1 == b.c2:
                hucreler.append((k, b.r1, b.c1))
            else:
                araliklar.append((k, (b.r1, b.c1, b.r2, b.c2)))
            continue
        if isinstance(d, Cagri):
            t = fonksiyonlar.bul(d.ad)
            if t is not None and (t.degisken or t.dinamik):
                degisken = True
            if t is not None and t.gizlilik and gizlilik is not None:
                gizlilik.append(True)
            yigin.extend((x, adlar) for x in d.argumanlar)
            continue
        for alan in getattr(d, "__dataclass_fields__", ()):
            v = getattr(d, alan)
            if isinstance(v, Dugum):
                yigin.append((v, adlar))
    return hucreler, araliklar, degisken


def _sutun_satirlari(anahtarlar: Iterable[Anahtar]) -> Dict[int, Dict[int, List[int]]]:
    """{kimlik: {sütun: sıralı satırlar}} — aralık–hücre kesişimini ikili aramayla bulmak için."""
    d: Dict[int, Dict[int, List[int]]] = defaultdict(lambda: defaultdict(list))
    for k, r, c in anahtarlar:
        d[k][c].append(r)
    for sutunlar in d.values():
        for satirlar in sutunlar.values():
            satirlar.sort()
    return d


def _kutudakiler(sutunlar: Dict[int, List[int]], sutun_sirasi: List[int], kutu: Kutu):
    """`sutunlar` içinde kutuya düşen (satır, sütun)'lar."""
    r1, c1, r2, c2 = kutu
    i = bisect_left(sutun_sirasi, c1)
    while i < len(sutun_sirasi) and sutun_sirasi[i] <= c2:
        c = sutun_sirasi[i]
        satirlar = sutunlar[c]
        j = bisect_left(satirlar, r1)
        while j < len(satirlar) and satirlar[j] <= r2:
            yield satirlar[j], c
            j += 1
        i += 1


def _kutuda_var_mi(sutunlar, sutun_sirasi, kutu: Kutu) -> bool:
    return next(_kutudakiler(sutunlar, sutun_sirasi, kutu), None) is not None


class Hesaplayici:
    def __init__(self, kitap):
        self.kitap = kitap
        self.donguler: Set[Anahtar] = set()
        self._agac_onb: Dict[str, Optional[Dugum]] = {}
        self._kayit: Dict[Anahtar, _Kayit] = {}
        self._hucre_bag: Dict[Anahtar, Set[Anahtar]] = defaultdict(set)
        # aralık bağımlılıkları: dar kutular (≤ GENIS_SUTUN sütun) sütuna göre indekslenir; yeniden
        # hesapta yalnız değişen sütunlara değen kutular taranır (satır sayısı × düzey karesi yok)
        self._aralik_sutun: Dict[int, Dict[int, Dict[Anahtar, List[Kutu]]]] = defaultdict(
            lambda: defaultdict(dict))
        self._aralik_genis: Dict[int, Dict[Anahtar, List[Kutu]]] = defaultdict(dict)
        self._degisken: Set[Anahtar] = set()
        self._gizlilik: Set[Anahtar] = set()          # ALTTOPLAM gibi satır gizliliğine bağlı hücreler
        self._sayfalar: Dict[int, object] = {}
        self._yaziyor = False
        self._tasma_alan: Dict[Anahtar, Kutu] = {}       # taşmayı deneyen formül hücresi → istenen alan (engelli olsa da)
        self._tasma_derinlik = 0
        self.tumunu_hesapla()
        self._birak = kitap.dinle(self._olay)

    def kapat(self) -> None:
        self._birak()

    # ------------------------------------------------------------------ grafik
    def _agac(self, formul: str) -> Optional[Dugum]:
        if formul not in self._agac_onb:
            try:
                self._agac_onb[formul] = formul_ayristir(formul)
            except FormulHatasi:
                self._agac_onb[formul] = None
            if len(self._agac_onb) > 200_000:            # bellek sınırı: önbelleği sıfırla
                self._agac_onb = {formul: self._agac_onb[formul]}
        return self._agac_onb[formul]

    def agac(self, anahtar: Anahtar, formul: str) -> Optional[Dugum]:
        """Hücrenin ayrıştırılmış formül ağacı: kayıttan (motor olaylarla güncel tutar), yoksa önbellekten."""
        k = self._kayit.get(anahtar)
        if k is not None and k.agac is not None:
            return k.agac
        return self._agac(formul)

    def _kaydi_sil(self, anahtar: Anahtar) -> None:
        k = self._kayit.pop(anahtar, None)
        if k is None:
            return
        for h in k.hucreler:
            bag = self._hucre_bag.get(h)
            if bag is not None:
                bag.discard(anahtar)
                if not bag:
                    del self._hucre_bag[h]
        for kimlik, (_, c1, _, c2) in k.araliklar:
            if c2 - c1 + 1 > GENIS_SUTUN:
                self._aralik_genis[kimlik].pop(anahtar, None)
            else:
                sutunlar = self._aralik_sutun[kimlik]
                for c in range(c1, c2 + 1):
                    sutunlar[c].pop(anahtar, None)
        self._degisken.discard(anahtar)
        self._gizlilik.discard(anahtar)

    def _kaydet(self, anahtar: Anahtar, formul: str) -> None:
        agac = self._agac(formul)
        if agac is None:
            self._kayit[anahtar] = _Kayit(None, [], [], False)
            return
        gizlilik: list = []
        hucreler, araliklar, degisken = _oncul_topla(agac, anahtar[0], self.kitap, anahtar[1], anahtar[2], gizlilik)
        self._kayit[anahtar] = _Kayit(agac, hucreler, araliklar, degisken)
        for h in hucreler:
            self._hucre_bag[h].add(anahtar)
        for kimlik, kutu in araliklar:
            c1, c2 = kutu[1], kutu[3]
            if c2 - c1 + 1 > GENIS_SUTUN:
                self._aralik_genis[kimlik].setdefault(anahtar, []).append(kutu)
            else:
                sutunlar = self._aralik_sutun[kimlik]
                for c in range(c1, c2 + 1):
                    sutunlar[c].setdefault(anahtar, []).append(kutu)
        if degisken:
            self._degisken.add(anahtar)
        if gizlilik:
            self._gizlilik.add(anahtar)

    def _hucreyi_yenile(self, sayfa, r: int, c: int) -> None:
        anahtar = (sayfa.kimlik, r, c)
        self._kaydi_sil(anahtar)
        h = sayfa.hucre(r, c)
        if h is not None and h.formul is not None:
            self._kaydet(anahtar, h.formul)

    def _grafigi_kur(self) -> None:
        self._kayit.clear()
        self._hucre_bag.clear()
        self._aralik_sutun.clear()
        self._aralik_genis.clear()
        self._degisken.clear()
        self._gizlilik.clear()
        self._sayfalar = {s.kimlik: s for s in self.kitap.sayfalar}
        for s in self.kitap.sayfalar:
            for r, c, h in s.dolu_hucreler(sirali=False):
                if h.formul is not None:
                    self._kaydet((s.kimlik, r, c), h.formul)

    # ------------------------------------------------------------------ olaylar
    def _olay(self, olay: Olay) -> None:
        if self._yaziyor:
            return
        t = olay.tur
        if t == "hucre":
            sayfa = olay.sayfa
            self._sayfalar[sayfa.kimlik] = sayfa
            degisen = []
            for (r, c) in olay["degisiklikler"]:
                self._hucreyi_yenile(sayfa, r, c)
                degisen.append((sayfa.kimlik, r, c))
                if (r, c) in sayfa.tasma:                 # taşan formül silindi ya da sabit değerle değişti
                    h = sayfa.hucre(r, c)
                    if h is None or h.formul is None:
                        kal = sayfa.tasma_kaldir((r, c))
                        self._tasma_alan.pop((sayfa.kimlik, r, c), None)
                        if kal:
                            sayfa._bildir("sonuc", degisiklikler=dict(kal))
                            degisen.extend((sayfa.kimlik,) + k for k in kal)
            degisen.extend(self._tasma_etkilenenler(sayfa.kimlik, olay["degisiklikler"]))
            self._yeniden_hesapla(degisen)
        elif t == "yapi":
            self.tumunu_hesapla()
        elif t == "boyut":                # satır gizle/göster/filtre: yalnız gizliliğe bağlı hücreler
            if self._gizlilik:
                self._yeniden_hesapla([], self._gizlilik)
        elif t == "ad":                    # tanımlı ad değişti (olay.sayfa None): seyrek, basit ve doğru
            self.tumunu_hesapla()
        elif t == "sayfa":
            if olay["islem"] in ("ekle", "sil"):
                self.tumunu_hesapla()
            else:
                self._yeniden_hesapla([])

    # ------------------------------------------------------------------ hesaplama
    def tumunu_hesapla(self) -> None:
        self._tasma_alan.clear()
        for s in self.kitap.sayfalar:
            s.tasma_hepsini_kaldir()                      # taşma hücreleri türetilmiştir: baştan üretilir
        self._grafigi_kur()
        self._hesapla(set(self._kayit))

    def _tasma_etkilenenler(self, kimlik: int, degisen_hucreler) -> List[Anahtar]:
        """Değişen hücrelerden biri bir taşma alanına (istenen alan; engelli olanlar dahil) düşüyorsa o taşmayı üreten formül
        hücresi yeniden hesaplanmalı (alan doldu → #TAŞMA!, boşaldı → yeniden taşar)."""
        sonuc: List[Anahtar] = []
        aday = [(a, k) for a, k in self._tasma_alan.items() if a[0] == kimlik]
        if not aday:
            return sonuc
        if len(aday) * len(degisen_hucreler) > 5_000_000:             # dev yapıştırma: hepsini yeniden hesapla
            return [a for a, _ in aday]
        for a, (r1, c1, r2, c2) in aday:
            for (r, c) in degisen_hucreler:
                if r1 <= r <= r2 and c1 <= c <= c2 and (r, c) != (a[1], a[2]):
                    sonuc.append(a)
                    break
        return sonuc

    def _bagimlilar(self, oncu: Set[Anahtar], kirli: Set[Anahtar]) -> Set[Anahtar]:
        """`oncu` kümesindeki hücrelere (doğrudan) bağlı formül hücreleri; `kirli`dekiler atlanır."""
        sonuc: Set[Anahtar] = set()
        hb = self._hucre_bag
        for a in oncu:
            bag = hb.get(a)
            if bag:
                sonuc |= bag
        if self._aralik_sutun or self._aralik_genis:
            for kimlik, sutunlar in _sutun_satirlari(oncu).items():
                dar = self._aralik_sutun.get(kimlik)
                if dar:
                    for c, satirlar in sutunlar.items():
                        kayitlar = dar.get(c)
                        if not kayitlar:
                            continue
                        for bagimli, kutular in kayitlar.items():
                            if bagimli in sonuc or bagimli in kirli:
                                continue
                            for r1, _, r2, _ in kutular:
                                j = bisect_left(satirlar, r1)
                                if j < len(satirlar) and satirlar[j] <= r2:
                                    sonuc.add(bagimli)
                                    break
                genis = self._aralik_genis.get(kimlik)
                if genis:
                    sira = sorted(sutunlar)
                    for bagimli, kutular in genis.items():
                        if bagimli in sonuc or bagimli in kirli:
                            continue
                        for kutu in kutular:
                            if _kutuda_var_mi(sutunlar, sira, kutu):
                                sonuc.add(bagimli)
                                break
        return sonuc

    def _yeniden_hesapla(self, degisen: List[Anahtar], ek: Iterable[Anahtar] = ()) -> None:
        tohum = set(degisen) | self._degisken | set(ek)
        kirli = {a for a in tohum if a in self._kayit}
        sinir = tohum
        while sinir:
            yeni = self._bagimlilar(sinir, kirli) - kirli
            kirli |= yeni
            sinir = yeni
        # değişen ama artık formül olmayan hücrelerin eski döngü işareti kalkar
        self.donguler -= set(degisen)
        if kirli:
            self._hesapla(kirli)

    def _hesapla(self, kirli: Set[Anahtar]) -> None:
        """Kirli hücreleri sayfa/satır/sütun sırasıyla hesaplar. Henüz hesaplanmamış bir hücre
        okunursa (`Bekle`) o hücre öne alınır (Excel'in hesap zinciri gibi: kenar listesi
        çıkarılmaz, okuma sırasında düzelir). Bekleme yığınında zaten olan hücre yeniden
        istenirse döngüdür: yığının o kısmı 0 olur (Excel gibi) ve `donguler`e girer."""
        sayfa_sira = {s.kimlik: i for i, s in enumerate(self.kitap.sayfalar)}
        sira = sorted((a for a in kirli if a[0] in sayfa_sira and a in self._kayit),
                      key=lambda a: (sayfa_sira[a[0]], a[1], a[2]))
        sayfalar = self._sayfalar
        for k, r, c in sira:
            sayfalar[k]._sonuc[(r, c)] = BEKLIYOR
        bekleyen = set(sira)
        hesaplanan: Dict[Anahtar, object] = {}
        self.donguler -= kirli

        ONEK_ONBELLEGI["etkin"] = {}           # tur boyunca geçerli önek toplamları

        tasan: Dict[Anahtar, Dizi] = {}
        tasma_degisen: Set[Anahtar] = set()

        def koy(a, v):
            if type(v) is Dizi:                      # çok hücreli dizi: sol üst öğe hücrede, tamamı taşar (aşağıda)
                tasan[a] = v
                v = v.satirlar[0][0]
                v = 0.0 if v is None else v
            sayfalar[a[0]]._sonuc[(a[1], a[2])] = v
            hesaplanan[a] = v
            bekleyen.discard(a)

        try:
            for a in sira:
                if a not in bekleyen:
                    continue
                yigin, yiginda = [a], {a}
                while yigin:
                    x = yigin[-1]
                    if x not in bekleyen:
                        yigin.pop()
                        yiginda.discard(x)
                        continue
                    try:
                        v = self._degerle(x)
                    except Bekle as b:
                        y = (b.sayfa.kimlik, b.satir, b.sutun)
                        if y in yiginda:                      # döngü
                            for z in yigin[yigin.index(y):]:
                                koy(z, 0.0)
                                self.donguler.add(z)
                            continue
                        if y not in bekleyen:                 # olmamalı: bayat işaret
                            koy(y, None)
                            continue
                        yigin.append(y)
                        yiginda.add(y)
                        continue
                    koy(x, v)
                    yigin.pop()
                    yiginda.discard(x)
        finally:
            ONEK_ONBELLEGI.pop("etkin", None)
            for k, r, c in bekleyen:                          # yarıda kaldıysa işaret kalmasın
                sayfalar[k]._sonuc.pop((r, c), None)
            tasma_degisen = self._tasmalari_isle(hesaplanan, tasan)
            self._sonuclari_yaz(hesaplanan)
        if tasma_degisen and self._tasma_derinlik < 8:        # taşan/boşalan hücreleri okuyan formüller yeniden hesaplanır
            self._tasma_derinlik += 1
            try:
                self._yeniden_hesapla(list(tasma_degisen))
            finally:
                self._tasma_derinlik -= 1

    def _tasmalari_isle(self, hesaplanan: Dict[Anahtar, object], tasan: Dict[Anahtar, Dizi]) -> Set[Anahtar]:
        """Hesaplanan formül hücrelerinin taşmasını sayfaya yazar/kaldırır; engel varsa hücre `#TAŞMA!` olur.
        Dönen: değeri değişen taşma hücreleri (bağımlıları yeniden hesaplanmalı)."""
        degisen: Set[Anahtar] = set()
        olaylar: Dict[int, Dict[Tuple[int, int], object]] = defaultdict(dict)
        for a in list(hesaplanan):
            sayfa = self._sayfalar.get(a[0])
            if sayfa is None:
                continue
            ank = (a[1], a[2])
            dizi = tasan.get(a)
            if dizi is None:
                self._tasma_alan.pop(a, None)
                kal = sayfa.tasma_kaldir(ank) if ank in sayfa.tasma else {}
                degisen.update((a[0],) + k for k in kal)
                olaylar[a[0]].update(kal)
                continue
            R, C = dizi.satir_sayisi, dizi.sutun_sayisi
            self._tasma_alan[a] = (ank[0], ank[1], ank[0] + R - 1, ank[1] + C - 1)
            if sayfa.tasma_engeli(ank, R, C):
                kal = sayfa.tasma_kaldir(ank)
                degisen.update((a[0],) + k for k in kal)
                olaylar[a[0]].update(kal)
                hesaplanan[a] = D.TASMA
                sayfa._sonuc[ank] = D.TASMA
            else:
                yaz = sayfa.tasma_yaz(ank, dizi.satirlar)
                degisen.update((a[0],) + k for k in yaz)
                olaylar[a[0]].update(yaz)
        for k, ol in olaylar.items():
            if ol:
                self._sayfalar[k]._bildir("sonuc", degisiklikler=dict(ol))
        return degisen

    def _degerle(self, a: Anahtar):
        kayit = self._kayit[a]
        if kayit.agac is None:
            return D.AD
        try:
            return hucre_sonucu(kayit.agac, Baglam(self._sayfalar[a[0]], a[1], a[2], self.kitap), True)
        except RecursionError:
            return D.SAYI                    # çok derin iç içe formül
        except Exception:                    # fonksiyon hatası programı düşürmesin
            return D.DEGER_HATASI

    def _sonuclari_yaz(self, hesaplanan: Dict[Anahtar, object]) -> None:
        sayfa_basina: Dict[int, Dict[Tuple[int, int], object]] = defaultdict(dict)
        for (k, r, c), v in hesaplanan.items():
            sayfa_basina[k][(r, c)] = v
        self._yaziyor = True
        try:
            for k, sonuclar in sayfa_basina.items():
                sayfa = self._sayfalar.get(k)
                if sayfa is not None and sayfa.kitap is self.kitap:
                    sayfa.sonuclari_yaz(sonuclar)
        finally:
            self._yaziyor = False
