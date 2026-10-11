"""Yüzen nesne etkileşimi (Faz 6 / 6e; `faz6_tasarim.md` §5.1): seçme, taşıma, boyutlandırma, silme, z sırası,
dahili pano, sağ tık menüsü, çift tık. `Izgara`ya `NesneKatmani` ile birlikte karışım olarak girer.

- Tık nesneyi seçer (hücre seçimi değişmez); nesne dışına tık / Esc seçimi bırakır.
- Sürükleme boyunca **komut yok**: önizleme dikdörtgeni çizilir; bırakınca TEK `NesneDegis` (tek geri al adımı).
- Hücre sınırı geçişleri hücre genişlik/yüksekliğiyle yapılır (`_konum_kaydir_piksel`): sayfa dışına çıkarılamaz.
"""
from typing import Optional, Tuple

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QMenu

from ..model.grafik import EN_KUCUK_BOYUT, Grafik, Konum, Resim
from ..model.komutlar import Grup, NesneDegis, NesneEkle, NesneSil, NesneSirala
from . import theme

TUTAMACLAR = ("nw", "n", "ne", "e", "se", "s", "sw", "w")
TUTAMAC = 7                      # piksel (tutamaç karesi)
SURUKLEME_ESIGI = 4              # piksel: bundan az hareket tık sayılır
_IMLEC = {"nw": Qt.SizeFDiagCursor, "se": Qt.SizeFDiagCursor, "ne": Qt.SizeBDiagCursor, "sw": Qt.SizeBDiagCursor,
          "n": Qt.SizeVerCursor, "s": Qt.SizeVerCursor, "e": Qt.SizeHorCursor, "w": Qt.SizeHorCursor}


class NesneEtkilesimi:
    """Karışım: `Izgara` sağlayıcıdır (`sayfa`, `yigin`, `yakinlastirma`, `_gen/_yuk`, `viewport()`, `degisti`, `_aktif`);
    `nesneSecimiDegisti(int)` ve `nesneAyarIstendi(int, str)` sinyalleri `Izgara`da tanımlıdır."""

    _nesne_panosu = None         # (nesne, kesildi, kaynak sayfa) — yalnız bu uygulama içinde; hücre kopyası temizler

    def _etkilesim_kur(self) -> None:
        self._secili_nesne: Optional[int] = None
        self._nesne_surukle_durum: Optional[dict] = None
        self._nesne_onizleme: Optional[Tuple[int, QRect]] = None          # (kimlik, görüntü penceresi dikdörtgeni)
        self._onizleme_gercek_boyut = None
        self._onizleme_zamanlayici = QTimer(self)
        self._onizleme_zamanlayici.setSingleShot(True)
        self._onizleme_zamanlayici.setInterval(60)
        self._onizleme_zamanlayici.timeout.connect(self._onizleme_gercekle)

    # ------------------------------------------------------------------ seçim
    @property
    def secili_nesne(self) -> Optional[int]:
        return self._secili_nesne

    def nesne_sec(self, kimlik: Optional[int]) -> None:
        if kimlik is not None and self.sayfa.nesne(kimlik) is None:
            kimlik = None
        if kimlik == self._secili_nesne:
            return
        self._secili_nesne = kimlik
        self.nesneSecimiDegisti.emit(kimlik or 0)
        self.viewport().update()

    def _nesne_secim_dogrula(self) -> None:
        if self._secili_nesne is not None and self.sayfa.nesne(self._secili_nesne) is None:
            self._secili_nesne = None
            self.nesneSecimiDegisti.emit(0)

    # ------------------------------------------------------------------ geometri
    def _gorunen_nesne_dikdortgeni(self, n) -> Optional[Tuple[QRect, QRect]]:
        """(dikdörtgen, bölme) — sürükleme sürerken önizleme dikdörtgeni kullanılır."""
        s = self._nesne_dikdortgeni(n)
        if self._nesne_onizleme is not None and self._nesne_onizleme[0] == n.kimlik:
            pencere = s[1] if s is not None else self.viewport().rect()
            return self._nesne_onizleme[1], pencere
        return s

    @staticmethod
    def _tutamac_dikdortgenleri(d: QRect) -> dict:
        t, y = TUTAMAC, TUTAMAC // 2
        xs = {"w": d.left() - y, "e": d.right() - y + 1, "": d.center().x() - y}
        ys = {"n": d.top() - y, "s": d.bottom() - y + 1, "": d.center().y() - y}
        sonuc = {}
        for ad in TUTAMACLAR:
            sonuc[ad] = QRect(xs["w" if "w" in ad else "e" if "e" in ad else ""],
                              ys["n" if "n" in ad else "s" if "s" in ad else ""], t, t)
        return sonuc

    def _nesne_isabet(self, p: QPoint) -> Optional[Tuple[int, str]]:
        """(kimlik, 'govde' ya da tutamaç adı); seçili nesnenin tutamaçları önce, sonra üstten alta nesneler."""
        if self._secili_nesne is not None:
            n = self.sayfa.nesne(self._secili_nesne)
            s = self._gorunen_nesne_dikdortgeni(n) if n is not None else None
            if s is not None:
                for ad, r in self._tutamac_dikdortgenleri(s[0]).items():
                    if r.adjusted(-1, -1, 1, 1).contains(p) and s[1].adjusted(-4, -4, 4, 4).contains(p):
                        return n.kimlik, ad
        for n in reversed(self.sayfa.nesneler):
            s = self._gorunen_nesne_dikdortgeni(n)
            if s is not None and s[0].intersected(s[1]).contains(p):
                return n.kimlik, "govde"
        return None

    def _konum_kaydir_piksel(self, k: Konum, ddx: float, ddy: float) -> Konum:
        """Çapayı piksel (yakınlaştırılmış) farkı kadar hücre sınırlarından geçirerek kaydırır; (1, 1)'in
        gerisine geçmez."""
        z = self.yakinlastirma
        sutun, satir = k.sutun, k.satir
        ox, oy = k.dx * z + ddx, k.dy * z + ddy
        while True:
            g = self._gen(sutun)
            if ox >= g and sutun < 16384 and g > 0:
                ox -= g
                sutun += 1
            elif ox >= g and g == 0 and sutun < 16384:
                sutun += 1
            else:
                break
        while ox < 0 and sutun > 1:
            sutun -= 1
            ox += self._gen(sutun)
        while True:
            h = self._yuk(satir)
            if oy >= h and satir < 1048576 and h > 0:
                oy -= h
                satir += 1
            elif oy >= h and h == 0 and satir < 1048576:
                satir += 1
            else:
                break
        while oy < 0 and satir > 1:
            satir -= 1
            oy += self._yuk(satir)
        return Konum(satir, sutun, max(0, round(ox / z)), max(0, round(oy / z)))

    # ------------------------------------------------------------------ fare
    def _nesne_fare_bas(self, p: QPoint) -> bool:
        """Sol tık nesne üzerindeyse sürüklemeyi başlatır; döner: tık tüketildi mi. Nesne dışı tık seçimi bırakır."""
        if not self.sayfa.nesneler:
            return False
        h = self._nesne_isabet(p)
        if h is None:
            self.nesne_sec(None)
            return False
        kimlik, bolge = h
        n = self.sayfa.nesne(kimlik)
        d = self._nesne_dikdortgeni(n)
        if d is None:
            return False
        self.nesne_sec(kimlik)
        self._surukleme = "nesne"
        self._nesne_surukle_durum = {"kimlik": kimlik, "bolge": bolge, "p0": QPoint(p), "dik0": QRect(d[0]),
                                     "n0": n, "basladi": False}
        self.setFocus()
        return True

    def _nesne_fare_hareket(self, p: QPoint, shift: bool) -> None:
        d = self._nesne_surukle_durum
        if d is None:
            return
        ddx, ddy = p.x() - d["p0"].x(), p.y() - d["p0"].y()
        if not d["basladi"]:
            if abs(ddx) < SURUKLEME_ESIGI and abs(ddy) < SURUKLEME_ESIGI:
                return
            d["basladi"] = True
        n0, r0, z = d["n0"], d["dik0"], self.yakinlastirma
        if d["bolge"] == "govde":
            if shift:                                         # Shift: baskın eksene kilitle
                if abs(ddx) >= abs(ddy):
                    ddy = 0
                else:
                    ddx = 0
            self._nesne_onizleme = (d["kimlik"], QRect(r0).translated(ddx, ddy))
        else:
            self._nesne_onizleme = (d["kimlik"], self._boyut_dikdortgeni(d["bolge"], r0, ddx, ddy, n0, shift))
        self._onizleme_gercek_boyut = None
        self._onizleme_zamanlayici.start()
        self.viewport().update()

    def _boyut_dikdortgeni(self, bolge: str, r0: QRect, ddx: int, ddy: int, n0, shift: bool) -> QRect:
        z = self.yakinlastirma
        sol, ust, sag, alt = r0.left(), r0.top(), r0.right() + 1, r0.bottom() + 1
        if "w" in bolge:
            sol += ddx
        if "e" in bolge:
            sag += ddx
        if "n" in bolge:
            ust += ddy
        if "s" in bolge:
            alt += ddy
        en_kucuk_g, en_kucuk_y = round(EN_KUCUK_BOYUT[0] * z), round(EN_KUCUK_BOYUT[1] * z)
        if sag - sol < en_kucuk_g:
            if "w" in bolge:
                sol = sag - en_kucuk_g
            else:
                sag = sol + en_kucuk_g
        if alt - ust < en_kucuk_y:
            if "n" in bolge:
                ust = alt - en_kucuk_y
            else:
                alt = ust + en_kucuk_y
        kose = len(bolge) == 2
        oran_koru = kose and ((isinstance(n0, Resim) and not shift) or (isinstance(n0, Grafik) and shift))
        if oran_koru and r0.width() > 0:
            oran = r0.height() / r0.width()
            g = sag - sol
            h = max(en_kucuk_y, round(g * oran))
            if "n" in bolge:
                ust = alt - h
            else:
                alt = ust + h
        return QRect(sol, ust, sag - sol, alt - ust)

    def _nesne_fare_birak(self) -> None:
        d, self._nesne_surukle_durum = self._nesne_surukle_durum, None
        onizleme, self._nesne_onizleme = self._nesne_onizleme, None
        self._onizleme_zamanlayici.stop()
        self._onizleme_gercek_boyut = None
        self._surukleme = None
        if d is None or onizleme is None or not d["basladi"]:
            self.viewport().update()
            return
        n0, r0, yeni = d["n0"], d["dik0"], onizleme[1]
        z = self.yakinlastirma
        konum = self._konum_kaydir_piksel(n0.konum, yeni.left() - r0.left(), yeni.top() - r0.top())
        boyut = (max(EN_KUCUK_BOYUT[0], round(yeni.width() / z)), max(EN_KUCUK_BOYUT[1], round(yeni.height() / z)))
        if d["bolge"] == "govde":
            boyut = n0.boyut
        self.nesne_uygula(n0.degistir(konum=konum, boyut=boyut))
        self.viewport().update()

    def nesne_uygula(self, yeni) -> bool:
        """`yeni` (aynı kimlikli) nesneyi TEK geri al adımıyla uygular; değişen yoksa False."""
        kmt = NesneDegis(self.sayfa, yeni)
        if kmt.bos_mu():
            return False
        self.yigin.calistir(kmt)
        self.degisti.emit()
        return True

    def _nesne_imleci(self, p: QPoint):
        h = self._nesne_isabet(p)
        if h is None:
            return None
        return Qt.SizeAllCursor if h[1] == "govde" else _IMLEC[h[1]]

    def _onizleme_gercekle(self) -> None:
        if self._nesne_onizleme is not None:
            self._onizleme_gercek_boyut = self._nesne_onizleme[1].size()
            self.viewport().update()

    # ------------------------------------------------------------------ klavye
    def _nesne_klavye(self, olay) -> bool:
        """Nesne seçiliyken: Delete sil, Esc bırak, ok 1 px (Ctrl 10 px), Ctrl+C/X/V; başka tuş seçimi bırakır
        ve normal işlenir (False)."""
        k, m = olay.key(), olay.modifiers()
        ctrl = bool(m & Qt.ControlModifier)
        if k == Qt.Key_Delete:
            self.nesne_sil()
            return True
        if k == Qt.Key_Escape:
            self.nesne_sec(None)
            return True
        yon = {Qt.Key_Up: (0, -1), Qt.Key_Down: (0, 1), Qt.Key_Left: (-1, 0), Qt.Key_Right: (1, 0)}.get(k)
        if yon is not None and not (m & (Qt.ShiftModifier | Qt.AltModifier)):
            adim = 10 if ctrl else 1
            self.nesne_oteleme(yon[0] * adim, yon[1] * adim)
            return True
        if ctrl and k == Qt.Key_C:
            self.nesne_kopyala(False)
            return True
        if ctrl and k == Qt.Key_X:
            self.nesne_kopyala(True)
            return True
        if ctrl and k == Qt.Key_V:
            self.nesne_yapistir()
            return True
        if k in (Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_Meta):
            return False
        self.nesne_sec(None)
        return False

    def nesne_oteleme(self, dx: int, dy: int) -> bool:
        """Seçili nesneyi model pikseli (%100) `dx, dy` kaydırır (klavye)."""
        n = self.sayfa.nesne(self._secili_nesne) if self._secili_nesne is not None else None
        if n is None:
            return False
        z = self.yakinlastirma
        return self.nesne_uygula(n.degistir(konum=self._konum_kaydir_piksel(n.konum, dx * z, dy * z)))

    # ------------------------------------------------------------------ komutlar
    def nesne_sil(self) -> bool:
        if self._secili_nesne is None or self.sayfa.nesne(self._secili_nesne) is None:
            return False
        kimlik = self._secili_nesne
        self.yigin.calistir(NesneSil(self.sayfa, kimlik))
        self.nesne_sec(None)
        self.degisti.emit()
        return True

    def nesne_ekle(self, nesne) -> int:
        """`nesne`yi (kimliksiz) sayfaya ekler ve seçer; TEK geri al adımı. Döner: atanan kimlik."""
        kmt = NesneEkle(self.sayfa, nesne)
        self.yigin.calistir(kmt)
        self.nesne_sec(kmt.nesne.kimlik)
        self.degisti.emit()
        return kmt.nesne.kimlik

    def nesne_kopyala(self, kesilen: bool) -> bool:
        n = self.sayfa.nesne(self._secili_nesne) if self._secili_nesne is not None else None
        if n is None:
            return False
        from .grid import Izgara
        Izgara._pano_durumu = None                            # hücre kopyası/kes işareti kalkar
        Izgara._nesne_panosu = (n, kesilen, self.sayfa)
        self.viewport().update()
        return True

    def nesne_yapistir(self) -> bool:
        """Dahili panodaki nesneyi etkin hücreye yapıştırır (kes ise kaynaktan silinir; TEK geri al adımı).
        Başka bir çalışma kitabına: grafik reddedilir (başvurular kitaba özgü), resim KOPYA olarak yapışır ve
        kaynak kitaba dokunulmaz (iki geri al yığını karışmasın)."""
        from .grid import Izgara
        pano = Izgara._nesne_panosu
        if pano is None:
            return False
        n, kesilen, kaynak = pano
        baska_kitap = kaynak.kitap is not self.sayfa.kitap
        if baska_kitap and isinstance(n, Grafik):
            # grafik başvuruları kitaba ait sayfa kimlikleriyle tutulur: başka kitapta yanlış veriyi gösterirdi
            self.uyari.emit("Grafik başka bir çalışma kitabına yapıştırılamaz: veri başvuruları kendi kitabına "
                            "aittir. Önce verisini de bu kitaba taşıyıp grafiği burada oluşturun.")
            return False
        yeni = n.degistir(kimlik=0, konum=Konum(self._aktif[0], self._aktif[1]))
        ekle = NesneEkle(self.sayfa, yeni)
        if kesilen and not baska_kitap and kaynak.nesne(n.kimlik) is not None:
            self.yigin.calistir(Grup([NesneSil(kaynak, n.kimlik), ekle]))
            Izgara._nesne_panosu = None
        else:
            self.yigin.calistir(ekle)
        self.nesne_sec(ekle.nesne.kimlik)
        self.degisti.emit()
        return True

    def nesne_sirala(self, yon: str) -> bool:
        if self._secili_nesne is None:
            return False
        kmt = NesneSirala(self.sayfa, self._secili_nesne, yon)
        if kmt.bos_mu():
            return False
        self.yigin.calistir(kmt)
        self.degisti.emit()
        return True

    # ------------------------------------------------------------------ menü / çift tık
    def nesne_menusu(self, p: QPoint) -> Optional[QMenu]:
        if not self.sayfa.nesneler:
            return None
        h = self._nesne_isabet(p)
        if h is None:
            return None
        self.nesne_sec(h[0])
        n = self.sayfa.nesne(h[0])
        m = QMenu(self)
        m.addAction("Kes", lambda: self.nesne_kopyala(True))
        m.addAction("Kopyala", lambda: self.nesne_kopyala(False))
        m.addAction("Sil", self.nesne_sil)
        m.addSeparator()
        one = m.addMenu("Öne Getir")
        one.addAction("Öne Getir", lambda: self.nesne_sirala("one_getir"))
        one.addAction("Bir Adım Öne", lambda: self.nesne_sirala("bir_one"))
        geri = m.addMenu("Arkaya Gönder")
        geri.addAction("Arkaya Gönder", lambda: self.nesne_sirala("arkaya_gonder"))
        geri.addAction("Bir Adım Arkaya", lambda: self.nesne_sirala("bir_arkaya"))
        if isinstance(n, Grafik):
            m.addSeparator()
            for metin, istek in (("Veriyi Seç…", "veri"), ("Grafik Türünü Değiştir…", "tur"),
                                 ("Grafik Ayarları…", "ayarlar")):
                m.addAction(metin, lambda i=istek, k=n.kimlik: self.nesneAyarIstendi.emit(k, i))
        return m

    def _nesne_cift_tik(self, p: QPoint) -> bool:
        h = self._nesne_isabet(p) if self.sayfa.nesneler else None
        if h is None:
            return False
        n = self.sayfa.nesne(h[0])
        self.nesne_sec(h[0])
        if isinstance(n, Grafik):
            self.nesneAyarIstendi.emit(n.kimlik, "ayarlar")
        return True

    # ------------------------------------------------------------------ seçim görünümü
    def _nesne_secim_ciz(self, p: QPainter, dik: QRect, kirp: QRect) -> None:
        p.setClipRect(kirp)
        p.setPen(QPen(QColor(theme.ACCENT), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(dik.adjusted(0, 0, -1, -1))
        for r in self._tutamac_dikdortgenleri(dik).values():
            p.setPen(QPen(QColor(theme.ACCENT), 1))
            p.setBrush(QColor("#FFFFFF"))
            p.drawRect(r.adjusted(0, 0, -1, -1))
