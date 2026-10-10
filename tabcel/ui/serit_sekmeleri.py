"""Giriş dışındaki şerit sekmeleri (5j-5; `faz5j_tasarim.md` §4): Sayfa Düzeni, Formüller, Veri, Gözden Geçir,
Görünüm. Yalnız yerleşimdir: düğmeler `Pencere.eylemler` kataloğundaki eylemleri kullanır; tek işlevsel
ekleme Sayfa Düzeni'ndeki ölçek/sığdır kutularıdır (`Pencere.sayfa_yapisi_degistir`)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QLabel, QSpinBox

from .serit import SeritGrubu, SeritSayfasi


class SayfaDuzeniSayfasi(SeritSayfasi):
    def __init__(self, pencere):
        super().__init__()
        self.pencere = pencere
        e = pencere.eylemler
        m = pencere._menu
        sy = SeritGrubu("Sayfa Yapısı", 5, "margins32")
        sy.buyuk(menu=m(("kenar_normal", "kenar_genis", "kenar_dar", None, "kenar_ozel")),
                 ikon="margins32", metin="Kenar\nBoşlukları")
        sy.buyuk(menu=m(("yon_dikey", "yon_yatay")), ikon="orientation32", metin="Yönlendirme")
        sy.buyuk(menu=m(tuple(k for k in e if k.startswith("kagit_"))), ikon="paper32", metin="Boyut")
        sy.buyuk(menu=m(("alan_belirle", "alan_temizle")), ikon="print_area32", metin="Yazdırma\nAlanı")
        sy.buyuk(e["baslik_yazdir"], ikon="print_titles32", metin="Başlıkları\nYazdır")
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
        sg.satirlar([[QLabel("Ölçek:"), self.olcek], [self.sigdir]])
        self.grup_ekle(sg)

        so = SeritGrubu("Sayfa Seçenekleri", 3, "print_titles32")
        so.kucukler([e["kilavuz"], e["kilavuz_yazdir"]])
        self.grup_ekle(so)
        self._esitleniyor = False

    def _olcek_girildi(self) -> None:
        if self._esitleniyor:
            return
        self.pencere.sayfa_yapisi_degistir(olcek=self.olcek.value(), sigdir_genislik=False)

    def _sigdir_tiklandi(self, secili: bool) -> None:
        self.pencere.sayfa_yapisi_degistir(sigdir_genislik=bool(secili))

    def guncelle(self) -> None:
        g = self.pencere.izgara()
        if g is None:
            return
        y = g.sayfa.sayfa_yapisi
        self._esitleniyor = True
        try:
            if not self.olcek.hasFocus():
                self.olcek.setValue(y.olcek)
            self.olcek.setEnabled(not y.sigdir_genislik)
            self.sigdir.setChecked(y.sigdir_genislik)
        finally:
            self._esitleniyor = False


class FormullerSayfasi(SeritSayfasi):
    def __init__(self, pencere):
        super().__init__()
        e = pencere.eylemler
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
        n = SeritGrubu("Notlar", 5, "note32")
        n.buyuk(e["yeni_not"])
        n.kucukler([e["notu_sil"]])
        self.grup_ekle(n)


class GorunumSayfasi(SeritSayfasi):
    def __init__(self, pencere):
        super().__init__()
        e = pencere.eylemler
        g = SeritGrubu("Göster", 3, "freeze32")
        g.kucukler([e["kilavuz"]])
        self.grup_ekle(g)
        y = SeritGrubu("Yakınlaştır", 4, "zoom100_32")
        y.buyuk(e["yakin_100"], metin="%100")
        self.grup_ekle(y)
        p = SeritGrubu("Pencere", 5, "freeze32")
        p.buyuk(menu=pencere._menu(("bolme", "ust_satir", "ilk_sutun", "coz")), ikon="freeze32",
                metin="Bölmeleri\nDondur")
        self.grup_ekle(p)
