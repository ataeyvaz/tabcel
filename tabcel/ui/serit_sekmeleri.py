"""Giriş dışındaki şerit sekmeleri (5j-5; `faz5j_tasarim.md` §4): Ekle (6f), Sayfa Düzeni, Formüller, Veri,
Gözden Geçir, Görünüm ve bağlamsal Grafik (6f). Yalnız yerleşimdir: düğmeler `Pencere.eylemler` kataloğundaki eylemleri kullanır; tek işlevsel
ekleme Sayfa Düzeni'ndeki ölçek/sığdır kutularıdır (`Pencere.sayfa_yapisi_degistir`)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QLabel, QSpinBox

from ..model.grafik_islem import GALERI
from .serit import SeritGrubu, SeritSayfasi


class EkleSayfasi(SeritSayfasi):
    """Ekle sekmesi (`faz6_tasarim.md` §6.1): Grafikler ve Resimler."""

    def __init__(self, pencere):
        super().__init__()
        m = pencere._menu
        t = SeritGrubu("Tablolar", 6, "pivot32")
        t.buyuk(pencere.eylemler["ozet_tablo"], ikon="pivot32", metin="Özet\nTablo")
        self.grup_ekle(t)
        g = SeritGrubu("Grafikler", 5, "chart32")
        for tur, metin, ikon in (("sutun", "Sütun", "chart_sutun32"), ("cubuk", "Çubuk", "chart_cubuk32"),
                                 ("cizgi", "Çizgi", "chart_cizgi32")):
            g.buyuk(menu=m(tuple(f"grafik_ekle.{tur}.{a}" for a, _ in GALERI[tur])), ikon=ikon, metin=metin)
        g.buyuk(menu=m(("grafik_ekle.pasta.kumelenmis", "grafik_ekle.halka.kumelenmis")),
                ikon="chart_pasta32", metin="Pasta")
        g.buyuk(menu=m(tuple(f"grafik_ekle.alan.{a}" for a, _ in GALERI["alan"])), ikon="chart_alan32", metin="Alan")
        g.buyuk(pencere.eylemler["grafik_ekle.dagilim.kumelenmis"], ikon="chart_dagilim32", metin="Dağılım")
        self.grup_ekle(g)
        r = SeritGrubu("Resimler", 4, "picture32")
        r.buyuk(pencere.eylemler["resim_ekle"], ikon="picture32", metin="Resim")
        self.grup_ekle(r)


class GrafikSayfasi(SeritSayfasi):
    """Bağlamsal "Grafik" sekmesi: yalnız grafik seçiliyken görünür (`faz6_tasarim.md` §6.2)."""

    def __init__(self, pencere):
        super().__init__()
        e = pencere.eylemler
        m = pencere._menu
        t = SeritGrubu("Tür", 5, "chart32")
        t.buyuk(e["grafik_tur"], ikon="chart32")
        t.buyuk(e["grafik_satir_sutun"], ikon="chart_degistir32")
        t.buyuk(e["grafik_veri"], ikon="chart_veri32", metin="Veriyi\nSeç")
        self.grup_ekle(t)
        o = SeritGrubu("Grafik Öğeleri", 4, "chart_oge32")
        o.buyuk(menu=m(tuple(k for k in e if k.startswith("grafik_gosterge."))), ikon="chart_oge32", metin="Gösterge")
        o.kucukler([e["grafik_baslik"], e["grafik_eksen_basliklari"], e["grafik_veri_etiketleri"]])
        self.grup_ekle(o)
        r = SeritGrubu("Renkler", 3, "chart_renk32")
        r.buyuk(menu=m(tuple(k for k in e if k.startswith("grafik_renk."))), ikon="chart_renk32",
                metin="Renkleri\nDeğiştir")
        self.grup_ekle(r)
        d = SeritGrubu("Düzen", 2, "sirala_nesne32")
        d.buyuk(menu=m(("grafik_one_getir", "grafik_bir_one")), ikon="sirala_nesne32", metin="Öne\nGetir")
        d.buyuk(menu=m(("grafik_arkaya_gonder", "grafik_bir_arkaya")), ikon="sirala_nesne32", metin="Arkaya\nGönder")
        d.kucukler([e["grafik_ayarlar"], e["grafik_sil"]])
        self.grup_ekle(d)


class SayfaDuzeniSayfasi(SeritSayfasi):
    def __init__(self, pencere):
        super().__init__()
        self.pencere = pencere
        e = pencere.eylemler
        m = pencere._menu
        sy = SeritGrubu("Sayfa Yapısı", 6, "margins32")
        sy.buyuk(menu=m(("kenar_normal", "kenar_genis", "kenar_dar", None, "kenar_ozel")),
                 ikon="margins32", metin="Kenar\nBoşlukları")
        sy.buyuk(menu=m(("yon_dikey", "yon_yatay")), ikon="orientation32", metin="Yönlendirme")
        sy.buyuk(menu=m(tuple(k for k in e if k.startswith("kagit_"))), ikon="paper32", metin="Boyut")
        sy.buyuk(menu=m(("alan_belirle", "alan_temizle")), ikon="print_area32", metin="Yazdırma\nAlanı")
        sy.buyuk(e["baslik_yazdir"], ikon="print_titles32", metin="Başlıkları\nYazdır")
        sy.buyuk(menu=m(("sayfa_sonu_ekle", "sayfa_sonu_kaldir", None, "sayfa_sonu_sifirla")),
                 ikon="print_titles32", metin="Kesmeler")
        sy.baslatici_ekle(e["dosya.sayfa_yapisi"].trigger, "Sayfa Yapısı")
        self.grup_ekle(sy)

        sg = SeritGrubu("Sığdır", 4, "print_area32")
        self.olcek = QSpinBox()
        self.olcek.setRange(10, 400)
        self.olcek.setSuffix(" %")
        self.olcek.setValue(100)
        self.olcek.setToolTip("Yazdırma ölçeği (%10–%400)")
        self.olcek.setFocusPolicy(Qt.ClickFocus)
        self.olcek.editingFinished.connect(self._olcek_girildi)
        self.sigdir = QCheckBox("Genişliği tek sayfaya sığdır")
        self.sigdir.setFocusPolicy(Qt.NoFocus)
        self.sigdir.clicked.connect(self._sigdir_tiklandi)
        self.sigdir_yuk = QCheckBox("Yüksekliği tek sayfaya sığdır")
        self.sigdir_yuk.setFocusPolicy(Qt.NoFocus)
        self.sigdir_yuk.clicked.connect(self._sigdir_yuk_tiklandi)
        sg.satirlar([[QLabel("Ölçek:"), self.olcek], [self.sigdir], [self.sigdir_yuk]])
        self.grup_ekle(sg)

        so = SeritGrubu("Sayfa Seçenekleri", 3, "print_titles32")
        so.kucukler([e["kilavuz"], e["kilavuz_yazdir"]])
        so.buyuk(menu=m(("sira_asagi", "sira_sag")), ikon="print_titles32", metin="Sayfa\nSırası")
        self.grup_ekle(so)
        self._esitleniyor = False

    def _olcek_girildi(self) -> None:
        if self._esitleniyor:
            return
        self.pencere.sayfa_yapisi_degistir(olcek=self.olcek.value(), sigdir_genislik=False,
                                           sigdir_yukseklik=False)

    def _sigdir_tiklandi(self, secili: bool) -> None:
        self.pencere.sayfa_yapisi_degistir(sigdir_genislik=bool(secili))

    def _sigdir_yuk_tiklandi(self, secili: bool) -> None:
        self.pencere.sayfa_yapisi_degistir(sigdir_yukseklik=bool(secili))

    def guncelle(self) -> None:
        g = self.pencere.izgara()
        if g is None:
            return
        y = g.sayfa.sayfa_yapisi
        self._esitleniyor = True
        try:
            if not self.olcek.hasFocus():
                self.olcek.setValue(y.olcek)
            self.olcek.setEnabled(not (y.sigdir_genislik or y.sigdir_yukseklik))
            self.sigdir.setChecked(y.sigdir_genislik)
            self.sigdir_yuk.setChecked(y.sigdir_yukseklik)
        finally:
            self._esitleniyor = False


class FormullerSayfasi(SeritSayfasi):
    def __init__(self, pencere):
        super().__init__()
        e = pencere.eylemler
        fd = SeritGrubu("Formül Denetleme", 6, "trace32")
        fd.buyuk(e["izleme"], ikon="trace32", metin="Hesap\nİzleme")
        self.grup_ekle(fd)
        asi = SeritGrubu("Asistan", 6, "asistan32")
        asi.buyuk(e["asistan"], ikon="asistan32", metin="Ne yapmak\nistiyorsun?")
        self.grup_ekle(asi)
        ik = SeritGrubu("İşlev Kitaplığı", 5, "autosum32")
        ik.buyuk(e["otomatik_toplam"], ikon="autosum32", metin="Otomatik\nToplam")
        self.grup_ekle(ik)
        ta = SeritGrubu("Tanımlı Adlar", 4, "name_manager32")
        ta.buyuk(e["ad_yoneticisi"], metin="Ad\nYöneticisi")
        ta.kucukler([e["ad_tanimla"]])
        self.grup_ekle(ta)


class VeriSayfasi(SeritSayfasi):
    def __init__(self, pencere):
        super().__init__()
        e = pencere.eylemler
        sf = SeritGrubu("Sırala ve Filtre Uygula", 5, "sort_filter32")
        sf.kucukler([e["artan"], e["azalan"]])
        sf.buyuk(e["ozel_sirala"], metin="Sırala")
        sf.buyuk(e["filtre"], metin="Filtre")
        sf.kucukler([e["filtre_temizle"], e["filtre_yeniden"]])
        self.grup_ekle(sf)
        va = SeritGrubu("Veri Araçları", 4, "validation32")
        va.buyuk(e["dogrulama"], metin="Veri\nDoğrulama")
        self.grup_ekle(va)


class GozdenGecirSayfasi(SeritSayfasi):
    def __init__(self, pencere):
        super().__init__()
        e = pencere.eylemler
        y = SeritGrubu("Yazım", 6, "spell32")
        y.buyuk(e["yazim"], metin="Yazım\nDenetimi")
        self.grup_ekle(y)
        sg = SeritGrubu("Denetim", 6, "saglik32")
        sg.buyuk(e["saglik"], ikon="saglik32", metin="Tablo\nSağlığı")
        sg.buyuk(e["temizleyici"], ikon="temizle32", metin="Paylaşım\nTemizleyici")
        self.grup_ekle(sg)
        n = SeritGrubu("Notlar", 5, "note32")
        n.buyuk(e["yeni_not"])
        n.kucukler([e["notu_sil"]])
        self.grup_ekle(n)


class YardimSayfasi(SeritSayfasi):
    """Yardım sekmesi: Nasıl Kullanılır (F1), Klavye Kısayolları, Yenilikler, Excel'den Farklar."""

    def __init__(self, pencere):
        super().__init__()
        e = pencere.eylemler
        y = SeritGrubu("Yardım", 5, "help32")
        y.buyuk(e["yardim"], ikon="help32", metin="Nasıl\nKullanılır")
        y.buyuk(e["yardim_kisayollar"], ikon="keyboard32", metin="Klavye\nKısayolları")
        y.buyuk(e["yardim_yenilikler"], ikon="info32", metin="Yenilikler")
        y.buyuk(e["yardim_farklar"], ikon="help32", metin="Excel'den\nFarklar")
        y.buyuk(e["hakkinda"], ikon="info32", metin="Hakkında")
        self.grup_ekle(y)


class GorunumSayfasi(SeritSayfasi):
    def __init__(self, pencere):
        super().__init__()
        e = pencere.eylemler
        g = SeritGrubu("Göster", 3, "freeze32")
        g.kucukler([e["kilavuz"], e["sayfa_sonlari"]])
        self.grup_ekle(g)
        y = SeritGrubu("Yakınlaştır", 4, "zoom100_32")
        y.buyuk(e["yakin_100"], metin="%100")
        self.grup_ekle(y)
        p = SeritGrubu("Pencere", 5, "freeze32")
        p.buyuk(menu=pencere._menu(("bolme", "ust_satir", "ilk_sutun", "coz")), ikon="freeze32",
                metin="Bölmeleri\nDondur")
        self.grup_ekle(p)
