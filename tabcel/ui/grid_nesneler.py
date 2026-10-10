"""Izgarada yüzen nesne (grafik/resim) katmanı (Faz 6 / 6d; `faz6_tasarim.md` §5). `Izgara`ya karışım (mixin) olarak girer.

- Nesneler `Izgara._boya` içinde, hücrelerin ve seçimin **üstünde** çizilir (çocuk widget yok): artımlı kaydırma,
  dondurma ve yakınlaştırma mevcut çizim yoluyla uyumlu kalır.
- Her nesne bir `QPixmap` önbelleğinden çizilir (grafik bir kez kurulur); önbellek anahtarı `(nesne, piksel boyut,
  yakınlaştırma, dpr)` — anahtar değişince eski girdi zaten kullanılmaz.
- **Canlı güncelleme:** hücre/sonuç olayları ilgili grafiği `kirli` işaretler, **30 ms'lik tek zamanlayıcı** önbelleği
  düşürüp yeniden çizer (50.000 hücrelik toplu sonuç bir kez işlenir; yazarken her tuşta yeniden kurma yok). Kirli
  grafik zamanlayıcı dolana dek eski görüntüsüyle çizilir.
- Nesne yokken ek maliyet tek `if` denetimidir.
"""
from typing import Dict, Optional, Set, Tuple

from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QImage, QPainter, QPixmap

from ..model.adres import Aralik
from ..model.grafik import Grafik, Konum, Resim, grafik_aralik_kesisir
from ..model.grafik_verisi import grafik_verisi
from .grafik_boyayici import grafik_ciz

NESNE_ERTELEME_MS = 30


class NesneKatmani:
    """`Izgara` karışımı: `self.sayfa`, `self.yakinlastirma`, `_baslik_g/_baslik_y`, `_gen/_yuk`, `_donuk_olcu`,
    `_kayan_ilk_sutun/_satir`, `ilk_sutun/ilk_satir`, `viewport()` sağlayıcıdan beklenir."""

    def _nesne_kur(self) -> None:
        self._nesne_onb: Dict[int, tuple] = {}            # kimlik → (anahtar, QPixmap)
        self._resim_onb: Dict[int, tuple] = {}            # kimlik → (bayt nesnesi, çözülmüş QImage)
        self._nesne_kirli: Set[int] = set()               # veri değişti, görüntü zamanlayıcı dolana dek eski kalır
        self._nesne_zamanlayici = QTimer(self)
        self._nesne_zamanlayici.setSingleShot(True)
        self._nesne_zamanlayici.setInterval(NESNE_ERTELEME_MS)
        self._nesne_zamanlayici.timeout.connect(self._nesne_kirlileri_yenile)
        kitap = self.sayfa.kitap
        if kitap is not None:
            birak = kitap.dinle(self._nesne_olayi)
            self.destroyed.connect(lambda *_: birak())

    # ------------------------------------------------------------------ olaylar
    def _nesne_olayi(self, olay) -> None:
        try:
            self._nesne_olayi_isle(olay)
        except RuntimeError:                              # C++ nesnesi silinmiş (pencere kapanırken)
            pass

    def _nesne_olayi_isle(self, olay) -> None:
        t = olay.tur
        if t == "nesne":
            if olay.sayfa is not self.sayfa:
                return
            kimlik = olay.ayrinti.get("kimlik")
            if kimlik is None:
                self._nesne_onb.clear()
                self._resim_onb.clear()
                self._nesne_kirli.clear()
            else:
                self._nesne_onb.pop(kimlik, None)
                if olay.ayrinti.get("islem") == "sil":      # taşıma/boyut değişiminde çözülmüş resim yeniden çözülmez
                    self._resim_onb.pop(kimlik, None)
                self._nesne_kirli.discard(kimlik)
            self._nesne_secim_dogrula()
            self.viewport().update()
            return
        if t not in ("hucre", "sonuc", "yapi", "boyut", "bicim", "sayfa", "ek"):
            return
        if not self.sayfa.nesneler:
            return
        aralik = None
        if t in ("hucre", "sonuc") and olay.sayfa is not None:
            anahtarlar = olay.ayrinti.get("degisiklikler")
            if anahtarlar:
                r = [a[0] for a in anahtarlar]
                c = [a[1] for a in anahtarlar]
                aralik = Aralik(min(r), min(c), max(r), max(c))
            kimlik_sayfa = olay.sayfa.kimlik
        else:
            kimlik_sayfa = None                           # yapı/boyut/biçim/sayfa: her grafik olabilir
        degisen = False
        for n in self.sayfa.nesneler:
            if not isinstance(n, Grafik):
                continue
            if aralik is not None and not grafik_aralik_kesisir(n, kimlik_sayfa, aralik):
                continue
            self._nesne_kirli.add(n.kimlik)
            degisen = True
        if degisen and not self._nesne_zamanlayici.isActive():
            self._nesne_zamanlayici.start()

    def _nesne_kirlileri_yenile(self) -> None:
        for k in self._nesne_kirli:
            self._nesne_onb.pop(k, None)
        self._nesne_kirli.clear()
        self.viewport().update()

    def _nesne_secim_dogrula(self) -> None:
        """`NesneEtkilesimi` geçersiz kılar (seçili nesne silinmişse seçimi bırakır)."""

    def _gorunen_nesne_dikdortgeni(self, n):
        return self._nesne_dikdortgeni(n)

    # ------------------------------------------------------------------ konum
    def _nesne_boyutu(self, n) -> Tuple[int, int]:
        return self._z(n.boyut[0]), self._z(n.boyut[1])

    def _nesne_dikdortgeni(self, n) -> Optional[Tuple[QRect, QRect]]:
        """`(nesnenin görüntü penceresindeki dikdörtgeni, çapa bölmesinin kırpma dikdörtgeni)` ya da kesinlikle
        görünmüyorsa None. Dikdörtgen negatif koordinatlı olabilir (kısmen kaydırılmış). Çapa hücresi uzaksa hücre
        toplamı yapılmaz: yalnız nesnenin boyu kadar geriye gidilir."""
        w, h = self._nesne_boyutu(n)
        k = n.konum
        dx, dy = round(k.dx * self.yakinlastirma), round(k.dy * self.yakinlastirma)
        bg, bh = self._baslik_g(), self._baslik_y()
        donuk_g, donuk_y = self._donuk_olcu()
        vp = self.viewport()
        x = self._nesne_eksen(k.sutun, dx, w, bg, donuk_g, self._kayan_ilk_sutun,
                              max(self.ilk_sutun, self._kayan_ilk_sutun), self._gen, vp.width())
        y = self._nesne_eksen(k.satir, dy, h, bh, donuk_y, self._kayan_ilk_satir,
                              max(self.ilk_satir, self._kayan_ilk_satir), self._yuk, vp.height())
        if x is None or y is None:
            return None
        sol, sag = (bg, bg + donuk_g) if k.sutun < self._kayan_ilk_sutun else (bg + donuk_g, vp.width())
        ust, alt = (bh, bh + donuk_y) if k.satir < self._kayan_ilk_satir else (bh + donuk_y, vp.height())
        pencere = QRect(sol, ust, max(0, sag - sol), max(0, alt - ust))
        dik = QRect(x, y, w, h)
        if not dik.intersects(pencere):
            return None
        return dik, pencere

    @staticmethod
    def _nesne_eksen(indeks: int, kayma: int, boy: int, baslik: int, donuk: int, kayan_ilk: int, ilk: int,
                     olcu, vp_boy: int) -> Optional[int]:
        """Çapa hücresinin bu eksendeki piksel konumu + kayma; görünürlük dışı kesinse None."""
        if indeks < kayan_ilk:                            # dondurulmuş bölme: sayfa başından
            return baslik + sum(olcu(i) for i in range(1, indeks)) + kayma
        if indeks >= ilk:
            x = baslik + donuk
            i = ilk
            while i < indeks:
                x += olcu(i)
                i += 1
                if x >= vp_boy:                           # pencerenin ötesinde: görünmez
                    return None
            return x + kayma
        s, i = 0, ilk - 1                                 # kaydırılıp çıkmış satır/sütun: yukarıdan/soldan taşan
        while i >= indeks:
            s += olcu(i)
            i -= 1
            if s - kayma >= boy:                          # nesne tamamen pencere dışında kaldı
                return None
        return baslik + donuk - s + kayma

    # ------------------------------------------------------------------ çizim
    def _nesne_pixmap(self, n, w: int, h: int) -> QPixmap:
        dpr = self.devicePixelRatioF()
        anahtar = (n, w, h, round(self.yakinlastirma, 4), dpr)
        giris = self._nesne_onb.get(n.kimlik)
        if giris is not None and (n.kimlik in self._nesne_kirli or giris[0] == anahtar):
            return giris[1]
        pm = self._nesne_olustur(n, w, h, dpr)
        self._nesne_onb[n.kimlik] = (anahtar, pm)
        return pm

    def _resim_goruntusu(self, n: Resim) -> QImage:
        """Çözülmüş resim (baytlar değişmedikçe yeniden çözülmez; yeniden boyutlandırmada her seferinde çözmek yavaş)."""
        giris = self._resim_onb.get(n.kimlik)
        if giris is not None and giris[0] is n.veri:
            return giris[1]
        img = QImage.fromData(n.veri)
        self._resim_onb[n.kimlik] = (n.veri, img)
        return img

    def _nesne_olustur(self, n, w: int, h: int, dpr: float) -> QPixmap:
        pm = QPixmap(max(1, round(w * dpr)), max(1, round(h * dpr)))
        pm.setDevicePixelRatio(dpr)
        pm.fill(Qt.transparent if isinstance(n, Resim) else Qt.white)
        if isinstance(n, Resim):
            img = self._resim_goruntusu(n)
            if not img.isNull():
                p = QPainter(pm)
                try:
                    p.setRenderHint(QPainter.SmoothPixmapTransform)
                    p.drawImage(QRectF(0, 0, w, h), img)
                finally:
                    p.end()
        elif isinstance(n, Grafik):
            p = QPainter(pm)
            try:
                veri = grafik_verisi(self.sayfa.kitap, n)
                grafik_ciz(p, veri, n, (w, h), olcek=self.yakinlastirma, aile=self._yazi_tipi().family())
            finally:
                p.end()
        return pm

    def _nesneleri_ciz(self, p: QPainter, kirp: QRect) -> None:
        """`_boya` içinden: z sırasıyla her nesnenin görünen kısmını çizer; sürükleme sürerken önizleme
        dikdörtgeni kullanılır (boyutlandırmada önce eski görüntü ölçeklenir, 60 ms durulunca gerçek boyutta kurulur);
        seçili nesnenin çerçevesi ve tutamaçları en üstte."""
        secili_dik = None
        for n in self.sayfa.nesneler:
            sonuc = self._gorunen_nesne_dikdortgeni(n)
            if sonuc is None:
                continue
            dik, pencere = sonuc
            if n.kimlik == self._secili_nesne:
                secili_dik = dik
            kirpma = dik.intersected(pencere).intersected(kirp)
            if kirpma.isEmpty():
                continue
            w, h = self._nesne_boyutu(n)
            p.setClipRect(kirpma)
            if dik.size() == QSize(w, h):
                p.drawPixmap(dik.topLeft(), self._nesne_pixmap(n, w, h))
            elif self._onizleme_gercek_boyut == dik.size():
                z = self.yakinlastirma
                n2 = n.degistir(boyut=(max(1, round(dik.width() / z)), max(1, round(dik.height() / z))))
                p.drawPixmap(dik.topLeft(), self._nesne_pixmap(n2, dik.width(), dik.height()))
            else:
                giris = self._nesne_onb.get(n.kimlik)
                pm = giris[1] if giris is not None else self._nesne_pixmap(n, w, h)
                p.drawPixmap(dik, pm)                     # eski görüntü yeni boyuta gerilir
        if secili_dik is not None:
            self._nesne_secim_ciz(p, secili_dik, kirp)
        p.setClipRect(kirp)

    def nesne_dikdortgeni(self, kimlik: int) -> Optional[QRect]:
        """Nesnenin görüntü penceresindeki dikdörtgeni (kırpılmamış); görünmüyorsa None (test/etkileşim için)."""
        n = self.sayfa.nesne(kimlik)
        if n is None:
            return None
        s = self._nesne_dikdortgeni(n)
        return s[0] if s else None

    def nesne_yerlesim_konumu(self, boyut) -> Konum:
        """Yeni nesne için konum: `boyut` (model pikseli) görünen alanın ortasına gelecek biçimde, en yakın
        hücreye çapalı; başlıkların ve (1, 1)'in gerisine taşmaz (`faz6_tasarim.md` §6.1)."""
        z = self.yakinlastirma
        vp = self.viewport().rect()
        x0, y0 = self._baslik_g(), self._baslik_y()
        x = max(x0 + 1, vp.center().x() - round(boyut[0] * z / 2))
        y = max(y0 + 1, vp.center().y() - round(boyut[1] * z / 2))
        satir, sutun = self._noktadan(QPoint(x, y))
        r = self.hucre_dikdortgeni(satir, sutun) if satir and sutun else None
        if r is None:
            return Konum(self.ilk_satir, self.ilk_sutun)
        return Konum(satir, sutun, max(0, round((x - r.left()) / z)), max(0, round((y - r.top()) / z)))
