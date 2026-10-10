"""Grafik eylemleri (Faz 6 / 6f): Ekle sekmesi galerisi + "Grafik" bağlamsal sekmesi komutları ve Grafik
Ayarları penceresinin açılışı. Eylemler `Pencere.eylemler` kataloğuna girer (şerit ve menüler aynı nesneyi
kullanır); hepsi seçili grafiği etkin sayfanın ızgarasından okur."""
from typing import Optional, Tuple

from PySide6.QtGui import QAction, QActionGroup

from ..model.grafik import VARSAYILAN_BOYUT, Grafik
from ..model.grafik_islem import GALERI, RENK_SEMALARI, grafik_kur, renk_sema_uygula, satir_sutun_degistir
from . import icons
from .grafik_pencereleri import GOSTERGE_ADLARI, GrafikAyarlariPenceresi

BAGLAM_SEKMESI = "Grafik"
VARSAYILAN_BASLIK = "Grafik Başlığı"
VARSAYILAN_EKSEN_BASLIGI = "Eksen Başlığı"


class GrafikEylemleri:
    def __init__(self, pencere):
        self.pencere = pencere
        e = pencere.eylemler
        self._gosterge_grubu = QActionGroup(pencere)

        def yeni(anahtar, metin, islev, ikon=None, isaretli=False, ipucu=None):
            a = QAction(metin, pencere)
            if ikon:
                a.setIcon(icons.icon(ikon))
            a.setToolTip(ipucu or metin.rstrip("…"))
            a.setCheckable(isaretli)
            a.triggered.connect(lambda _=False, f=islev: f())
            e[anahtar] = a
            return a

        # Ekle sekmesi galerisi: her (tür, alt tür) bir eylem
        for tur, ogeler in GALERI.items():
            for alt, ad in ogeler:
                yeni(f"grafik_ekle.{tur}.{alt}", ad, lambda t=tur, a=alt: self.ekle(t, a))
        # bağlamsal sekme
        yeni("grafik_tur", "Grafik Türünü\nDeğiştir", lambda: self.ayar_penceresi("tur"), "chart32",
             ipucu="Grafik Türünü Değiştir")
        yeni("grafik_satir_sutun", "Satır/Sütun\nDeğiştir", self.satir_sutun_degistir, "chart_degistir32",
             ipucu="Satır/Sütun Değiştir")
        yeni("grafik_veri", "Veriyi Seç…", lambda: self.ayar_penceresi("veri"), "chart_veri32")
        yeni("grafik_ayarlar", "Grafik Ayarları…", lambda: self.ayar_penceresi(None))
        yeni("grafik_baslik", "Grafik Başlığı", self.baslik_degistir, isaretli=True)
        yeni("grafik_eksen_basliklari", "Eksen Başlıkları", self.eksen_basliklari_degistir, isaretli=True)
        yeni("grafik_veri_etiketleri", "Veri Etiketleri", self.veri_etiketleri_degistir, isaretli=True)
        for deger, ad in GOSTERGE_ADLARI:
            a = yeni(f"grafik_gosterge.{deger or 'yok'}", ad, lambda d=deger: self.gosterge_ayarla(d), isaretli=True)
            self._gosterge_grubu.addAction(a)
        for ad in RENK_SEMALARI:
            yeni(f"grafik_renk.{ad}", ad, lambda n=ad: self.renk_ayarla(n))
        for anahtar, metin, yon in (("grafik_one_getir", "Öne Getir", "one_getir"),
                                    ("grafik_bir_one", "Bir Öne Getir", "bir_one"),
                                    ("grafik_arkaya_gonder", "Arkaya Gönder", "arkaya_gonder"),
                                    ("grafik_bir_arkaya", "Bir Arkaya Gönder", "bir_arkaya")):
            yeni(anahtar, metin, lambda y=yon: self.sirala(y))
        yeni("grafik_sil", "Grafiği Sil", self.sil)

    # ------------------------------------------------------------------ yardımcılar
    def secili(self) -> Optional[Tuple[object, Grafik]]:
        """(ızgara, seçili grafik) ya da None (nesne yok / resim)."""
        g = self.pencere.izgara()
        if g is None or g.secili_nesne is None:
            return None
        n = g.sayfa.nesne(g.secili_nesne)
        return (g, n) if isinstance(n, Grafik) else None

    def _uygula(self, islev) -> bool:
        s = self.secili()
        if s is None:
            return False
        g, n = s
        yeni = islev(n)
        return bool(yeni is not None and g.nesne_uygula(yeni))

    # ------------------------------------------------------------------ ekleme
    def ekle(self, tur: str, alt_tur: str = "kumelenmis") -> bool:
        """Seçili aralıktan grafik ekler (görünen alanın ortasına); yeni grafik seçilir, Grafik sekmesine geçilir."""
        p = self.pencere
        g = p.izgara()
        try:
            grafik = grafik_kur(g.sayfa, g.secim, tur, alt_tur)
        except ValueError as hata:
            p._uyari(str(hata))
            return False
        g.nesne_ekle(grafik.degistir(konum=g.nesne_yerlesim_konumu(VARSAYILAN_BOYUT)))
        self.sekmeyi_esitle()
        p.serit.sec(BAGLAM_SEKMESI)
        return True

    # ------------------------------------------------------------------ bağlamsal komutlar
    def satir_sutun_degistir(self) -> bool:
        try:
            return self._uygula(satir_sutun_degistir)
        except ValueError as hata:
            self.pencere._uyari(str(hata))
            return False

    def baslik_degistir(self) -> bool:
        return self._uygula(lambda n: n.degistir(baslik=None if n.baslik is not None else VARSAYILAN_BASLIK))

    def eksen_basliklari_degistir(self) -> bool:
        def f(n):
            if n.tur in ("pasta", "halka"):
                return None
            b = None if (n.x_baslik is not None or n.y_baslik is not None) else VARSAYILAN_EKSEN_BASLIGI
            return n.degistir(x_baslik=b, y_baslik=b)
        return self._uygula(f)

    def veri_etiketleri_degistir(self) -> bool:
        return self._uygula(lambda n: n.degistir(deger_etiketi=not n.deger_etiketi))

    def gosterge_ayarla(self, konum: Optional[str]) -> bool:
        return self._uygula(lambda n: n.degistir(gosterge=konum))

    def renk_ayarla(self, sema: str) -> bool:
        return self._uygula(lambda n: renk_sema_uygula(n, sema))

    def sirala(self, yon: str) -> bool:
        s = self.secili()
        return bool(s) and s[0].nesne_sirala(yon)

    def sil(self) -> bool:
        s = self.secili()
        return bool(s) and s[0].nesne_sil()

    # ------------------------------------------------------------------ pencere
    def ayar_penceresi(self, odak: Optional[str] = None) -> bool:
        s = self.secili()
        if s is None:
            return False
        g, n = s
        d = GrafikAyarlariPenceresi(self.pencere.kitap, g.sayfa, n, self.pencere, odak)
        if d.exec() and d.sonuc is not None:
            g.nesne_uygula(d.sonuc)
        return True

    def ayar_istendi(self, kimlik: int, istek: str) -> None:
        """Izgaranın `nesneAyarIstendi` sinyali ('ayarlar' | 'veri' | 'tur'); resimde bir şey yapılmaz."""
        g = self.pencere.izgara()
        if g is None or not isinstance(g.sayfa.nesne(kimlik), Grafik):
            return
        if g.secili_nesne != kimlik:
            g.nesne_sec(kimlik)
        self.ayar_penceresi({"veri": "veri", "tur": "tur"}.get(istek))

    # ------------------------------------------------------------------ durum
    def sekmeyi_esitle(self) -> None:
        """Grafik sekmesi yalnız grafik seçiliyken görünür; işaretli eylemler seçili grafiğe uyar."""
        p = self.pencere
        s = self.secili()
        p.serit.sekme_goster(BAGLAM_SEKMESI, s is not None)
        if s is None:
            return
        n = s[1]
        e = p.eylemler
        durum = {"grafik_baslik": n.baslik is not None,
                 "grafik_eksen_basliklari": n.x_baslik is not None or n.y_baslik is not None,
                 "grafik_veri_etiketleri": n.deger_etiketi}
        for deger, _ in GOSTERGE_ADLARI:
            durum[f"grafik_gosterge.{deger or 'yok'}"] = n.gosterge == deger
        for anahtar, v in durum.items():
            a = e[anahtar]
            a.blockSignals(True)
            a.setChecked(v)
            a.blockSignals(False)
        tek = n.tur in ("pasta", "halka")
        e["grafik_eksen_basliklari"].setEnabled(not tek)
        e["grafik_satir_sutun"].setEnabled(not tek)
