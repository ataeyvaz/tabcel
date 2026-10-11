"""Ana pencere: yeşil başlık şeridi, ad kutusu + formül çubuğu, ızgara, sayfa sekmeleri,
durum çubuğu (mod, Ortalama · Sayım · Toplam, yakınlaştırma).

Her sayfanın kendi `Izgara`'sı vardır (seçim ve kaydırma konumu sayfada kalır); geri al
yığını çalışma kitabı genelinde ortaktır.
"""
from typing import Dict, Optional

from PySide6.QtCore import QSize, Qt, QStringListModel, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import (
    QColorDialog, QDialog, QHBoxLayout, QCompleter, QInputDialog, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox,
    QSlider, QStackedWidget, QTabBar, QToolButton, QVBoxLayout, QWidget,
)

from .. import APP_NAME
from ..model.adres import AdresHatasi, aralik_coz, hucre_yaz
from ..model.ad import AdHatasi, TanimliAd, ad_dogrula
from ..formul.ad_yardim import (
    aralik_basvurusu, basvurur_saklanan, gorunur_adlar, hedef_aralik, secimin_adi,
)
from ..formul import hata_neden, isaretleme
from .renkli import renkli_ciz
from ..formul.ceviri import hucre_metni
from ..formul.motor import Hesaplayici
from ..model.komutlar import (
    AdDegis, GeriAlYigini, SayfaEkle, SayfaSil, SayfaTasi, SayfaYenidenAdlandir,
)
from ..model.komutlar import ana_sayfa
from ..model.olay import Olay
from ..model.sayfa import CalismaKitabi, Sayfa
from . import icons, theme
from .ad_penceresi import AdTanimlaPenceresi, AdYoneticisi, GitPenceresi
from .bicim_cubugu import BicimCubugu
from .bulut_islemleri import BulutIslemleri
from .hizli_erisim import HizliErisim
from .dosya_islemleri import DosyaIslemleri
from .grafik_eylemleri import BAGLAM_SEKMESI, GrafikEylemleri
from .serit import Serit, SeritGrubu
from .grid import Izgara, goster


class _SekmeCubugu(QTabBar):
    ciftTik = Signal(int)

    def paintEvent(self, olay):
        super().paintEvent(olay)
        renkler = [self.tabData(i) for i in range(self.count())]
        if not any(renkler):
            return
        p = QPainter(self)
        for i, renk in enumerate(renkler):
            if renk:                       # Excel gibi: sekmenin altında renkli şerit
                r = self.tabRect(i)
                p.fillRect(r.left() + 2, r.bottom() - 2, r.width() - 4, 3, QColor(renk))
        p.end()

    def mouseDoubleClickEvent(self, olay):
        i = self.tabAt(olay.position().toPoint())
        if i >= 0:
            self.ciftTik.emit(i)
        else:
            super().mouseDoubleClickEvent(olay)


class _FormulCubugu(QLineEdit):
    """Enter: onayla; Esc: vazgeç."""
    onayla = Signal(str)
    vazgec = Signal()
    odakAldi = Signal()
    okIsaret = Signal(int, int, bool)       # işaret modunda ok tuşu: satır, sütun farkı, Shift

    def __init__(self, *a):
        super().__init__(*a)
        self.isaret_denetimi = None         # () -> bool (ızgara verir)

    def focusInEvent(self, olay):
        super().focusInEvent(olay)
        self.odakAldi.emit()

    def paintEvent(self, olay):
        super().paintEvent(olay)
        renkli_ciz(self, ek_x=7)         # stil sayfası: 1 px kenarlık + 6 px iç boşluk

    def keyPressEvent(self, olay):
        k = olay.key()
        oklar = {Qt.Key_Up: (-1, 0), Qt.Key_Down: (1, 0), Qt.Key_Left: (0, -1), Qt.Key_Right: (0, 1)}
        if k in (Qt.Key_Return, Qt.Key_Enter):
            self.onayla.emit(self.text())
        elif k == Qt.Key_Escape:
            self.vazgec.emit()
        elif k == Qt.Key_F4:
            yeni, imlec = isaretleme.f4(self.text(), self.cursorPosition())
            if yeni != self.text():
                self.setText(yeni)
                self.setCursorPosition(imlec)
                self.textEdited.emit(yeni)
        elif k in oklar and self.isaret_denetimi is not None and self.isaret_denetimi():
            self.okIsaret.emit(oklar[k][0], oklar[k][1], bool(olay.modifiers() & Qt.ShiftModifier))
        else:
            super().keyPressEvent(olay)


class Pencere(DosyaIslemleri, BulutIslemleri, HizliErisim, QMainWindow):
    def __init__(self, kitap: Optional[CalismaKitabi] = None):
        super().__init__()
        self.kitap = kitap or CalismaKitabi()
        self.motor = Hesaplayici(self.kitap)          # pencereden önce dinler: sonuçlar hazır olur
        self.yigin = GeriAlYigini()
        self.belge_adi = "Adsız"
        self._izgaralar: Dict[Sayfa, Izgara] = {}
        self._saklanan: Dict[Sayfa, Izgara] = {}      # kitaptan çıkan sayfaların ızgarası (geri al için)
        self._secili_sayfa: Optional[Sayfa] = None
        self._uzak: Optional[dict] = None     # başka sayfaya geçilirken devredilen hücre düzenlemesi
        self._son_indeks = 0
        self._gecmis_islemi = False
        self._dongu_bilinen = set()                   # son denetimde döngüde olan hücreler (yeni döngüyü ayırt eder)
        self._hata_onb: Dict[tuple, str] = {}         # T8: (sayfa kimliği, r, c) → hata açıklaması; her olayda düşer
        self._mod = "Hazır"
        self.setStyleSheet(theme.stylesheet())
        self._kur()
        self._dosya_kur()
        self._sekmeleri_esitle(self.kitap.sayfalar[0])
        self.kitap.dinle(self._kitap_olayi)           # sayfa ekle/sil/ad/taşı + geri al/yinele buradan yansır
        self.kitap.dinle(lambda _olay: self._hata_onb.clear())   # motordan sonra: açıklamalar yeni sonuçlarla
        self._baslik_guncelle()
        self.resize(1100, 700)

    # ------------------------------------------------------------------ kurulum
    def _kur(self):
        self._eylemleri_kur()
        self.grafik_eylemleri = GrafikEylemleri(self)
        self._yardim_eylemleri_kur()
        merkez = QWidget()
        merkez.setObjectName("central")
        dikey = QVBoxLayout(merkez)
        dikey.setContentsMargins(0, 0, 0, 0)
        dikey.setSpacing(0)
        self.setCentralWidget(merkez)

        self.izgara_yigini = QStackedWidget()          # şerit/Giriş sayfası ızgarayı bu yığından okur (erken kurulur)

        # başlık şeridi: hızlı erişim (Kaydet, Geri Al, Yinele) + belge adı
        baslik = QWidget()
        baslik.setObjectName("header")
        h = QHBoxLayout(baslik)
        h.setContentsMargins(8, 6, 8, 6)
        self.kaydet_dugmesi = QToolButton()
        self.kaydet_dugmesi.setIcon(icons.icon("save", "#ffffff"))
        self.kaydet_dugmesi.setToolTip("Kaydet (Ctrl+S)")
        self.kaydet_dugmesi.clicked.connect(lambda _=False: self.kaydet())
        self.geri_dugmesi = QToolButton()
        self.geri_dugmesi.setDefaultAction(self.eylemler["geri_al"])
        self.geri_dugmesi.setIcon(icons.icon("undo", "#ffffff"))
        self.yinele_dugmesi = QToolButton()
        self.yinele_dugmesi.setDefaultAction(self.eylemler["yinele"])
        self.yinele_dugmesi.setIcon(icons.icon("redo", "#ffffff"))
        for d in (self.kaydet_dugmesi, self.geri_dugmesi, self.yinele_dugmesi):
            d.setIconSize(QSize(20, 20))
            d.setToolButtonStyle(Qt.ToolButtonIconOnly)
            d.setFocusPolicy(Qt.NoFocus)
        self.belge_etiketi = QLabel()
        self.belge_etiketi.setObjectName("docTitle")
        h.addWidget(self.kaydet_dugmesi)
        h.addWidget(self.geri_dugmesi)
        h.addWidget(self.yinele_dugmesi)
        self._hizli_kutu = QWidget()                   # kullanıcının eklediği komutlar (Hızlı Erişim, sağ tık)
        hk = QHBoxLayout(self._hizli_kutu)
        hk.setContentsMargins(0, 0, 0, 0)
        hk.setSpacing(2)
        h.addWidget(self._hizli_kutu)
        h.addStretch(1)
        h.addWidget(self.belge_etiketi)
        h.addStretch(1)
        dikey.addWidget(baslik)
        self._hizli_kur()

        # eski menü sözlükleri: katalogla aynı nesneler (testler ve kodun geri kalanı bunlara dayanır)
        self.gorunum_eylemleri = {k: self.eylemler[k] for k in ("bolme", "ust_satir", "ilk_sutun", "coz")}
        self.kilavuz_eylemi = self.eylemler["kilavuz"]
        self.duzen_eylemleri = {k: self.eylemler[k] for k in ("bul", "degistir", "git")}
        self.veri_eylemleri = {k: self.eylemler[k] for k in (
            "artan", "azalan", "ozel_sirala", "filtre", "filtre_temizle", "filtre_yeniden", "dogrulama",
            "ad_tanimla", "ad_yoneticisi")}

        # sekmeli şerit (5j): Dosya (açılır menü) + Giriş (biçim çubuğu sayfası) …
        self.serit = Serit()
        self.bicim_cubugu = BicimCubugu(self.izgara)
        self._giris_gruplari_ekle()
        self.dosya_menusu = QMenu(self)
        self._dosya_menusu_doldur(self.dosya_menusu)
        self.serit.sekme_ekle("Giriş", self.bicim_cubugu)
        from .serit_sekmeleri import (EkleSayfasi, FormullerSayfasi, GorunumSayfasi, GozdenGecirSayfasi,
                                      GrafikSayfasi, SayfaDuzeniSayfasi, VeriSayfasi, YardimSayfasi)
        for ad, sinif in (("Ekle", EkleSayfasi), ("Sayfa Düzeni", SayfaDuzeniSayfasi),
                          ("Formüller", FormullerSayfasi), ("Veri", VeriSayfasi),
                          ("Gözden Geçir", GozdenGecirSayfasi), ("Görünüm", GorunumSayfasi),
                          ("Yardım", YardimSayfasi),
                          (BAGLAM_SEKMESI, GrafikSayfasi)):          # bağlamsal sekme SON kalır (tema `:last` kuralı)
            self.serit.sekme_ekle(ad, sinif(self))
        self.serit.sekme_goster(BAGLAM_SEKMESI, False)
        self.serit.dosya_sekmesi_ekle(self.dosya_menusu)
        dikey.addWidget(self.serit)
        self.bilgi_cubugu = self._bilgi_cubugu_olustur()      # açılan dosyada korunamayan öğe uyarısı
        dikey.addWidget(self.bilgi_cubugu)

        # ad kutusu + formül çubuğu
        cubuk = QWidget()
        cubuk.setObjectName("formulaBar")
        f = QHBoxLayout(cubuk)
        f.setContentsMargins(6, 4, 6, 4)
        self.ad_kutusu = QLineEdit()
        self.ad_kutusu.setFixedWidth(110)
        self.ad_kutusu.setToolTip("Ad Kutusu: hücre/aralık adresi yazıp Enter'a basın (ör. B7 veya A1:C5)")
        self.ad_kutusu.returnPressed.connect(self._ad_kutusundan_git)
        self._ad_model = QStringListModel(self)
        self.ad_tamamlayici = QCompleter(self._ad_model, self)         # tanımlı adlar (Excel'in açılır listesi)
        self.ad_tamamlayici.setCaseSensitivity(Qt.CaseInsensitive)
        self.ad_tamamlayici.activated.connect(self._ad_secildi)
        self.ad_kutusu.setCompleter(self.ad_tamamlayici)
        fx = QLabel("fx")
        self.formul = _FormulCubugu()
        self.formul.onayla.connect(self._formul_onayla)
        self.formul.vazgec.connect(self._formul_vazgec)
        self.formul.odakAldi.connect(self._formul_odak)
        self.formul.textEdited.connect(self._formul_duzenlendi)
        self.formul.okIsaret.connect(self._formul_isaret_ok)
        f.addWidget(self.ad_kutusu)
        f.addWidget(fx)
        f.addWidget(self.formul, 1)
        dikey.addWidget(cubuk)

        # ızgaralar
        dikey.addWidget(self.izgara_yigini, 1)

        # sayfa sekmeleri
        alt = QWidget()
        alt.setObjectName("sheetBar")
        a = QHBoxLayout(alt)
        a.setContentsMargins(6, 0, 6, 0)
        self.sekmeler = _SekmeCubugu()
        self.sekmeler.setShape(QTabBar.RoundedSouth)
        self.sekmeler.setMovable(True)
        self.sekmeler.setDrawBase(False)
        self.sekmeler.setExpanding(False)
        self.sekmeler.setContextMenuPolicy(Qt.CustomContextMenu)
        self.sekmeler.currentChanged.connect(self._sekme_degisti)
        self.sekmeler.tabMoved.connect(self._sekme_tasindi)
        self.sekmeler.ciftTik.connect(self.sayfa_yeniden_adlandir)
        self.sekmeler.customContextMenuRequested.connect(self._sekme_menusu)
        ekle = QToolButton()
        ekle.setText("+")
        ekle.setToolTip("Yeni sayfa")
        ekle.clicked.connect(self.sayfa_ekle)
        a.addWidget(self.sekmeler)
        a.addWidget(ekle)
        a.addStretch(1)
        dikey.addWidget(alt)

        # durum çubuğu
        self.mod_etiketi = QLabel("Hazır")
        self.mod_etiketi.setMinimumWidth(60)
        self.ozet_etiketi = QLabel("")
        self._ozet_zamanlayici = QTimer(self)         # büyük seçimde özet çizimi beklemesin (50 ms ertelenir)
        self._ozet_zamanlayici.setSingleShot(True)
        self._ozet_zamanlayici.timeout.connect(self._ozet_guncelle)
        self.dongu_etiketi = QLabel("")               # "Döngüsel Başvurular: A1" (yalnız döngü varken)
        self.dongu_etiketi.setStyleSheet(f"color: {theme.UYARI}; font-weight: 600; padding: 0 8px;")
        self.dongu_etiketi.hide()
        self.hata_etiketi = QLabel("")                # T8: etkin hücredeki hatanın açıklaması
        self.hata_etiketi.setStyleSheet("padding: 0 8px;")
        self.hata_etiketi.hide()
        self.yakin_etiketi = QLabel("100%")
        self.yakin_etiketi.setMinimumWidth(40)
        self.yakin_etiketi.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.yakin_kaydirici = QSlider(Qt.Horizontal)
        self.yakin_kaydirici.setRange(10, 400)
        self.yakin_kaydirici.setValue(100)
        self.yakin_kaydirici.setFixedWidth(120)
        self.yakin_kaydirici.valueChanged.connect(self._kaydirici_degisti)
        sb = self.statusBar()
        sb.setSizeGripEnabled(False)
        sb.addWidget(self.mod_etiketi)
        sb.addWidget(self.dongu_etiketi)
        sb.addWidget(self.hata_etiketi, 1)
        sb.addPermanentWidget(self.ozet_etiketi)
        sb.addPermanentWidget(self.yakin_kaydirici)
        sb.addPermanentWidget(self.yakin_etiketi)

        self.bul_penceresi = None
        for tus, islev in (("Ctrl+F", lambda: self.bul_ac(False)), ("Ctrl+H", lambda: self.bul_ac(True)),
                           ("Ctrl+G", self.git_ac), ("F5", self.git_ac),
                           ("Ctrl+Shift+L", self.filtre_ac_kapat), ("Ctrl+Alt+L", self.filtre_yeniden_uygula),
                           ("Ctrl+F3", self.ad_yoneticisi_ac),
                           ("Shift+F4", lambda: self.sonrakini_bul(False)),
                           ("Ctrl+Shift+F4", lambda: self.sonrakini_bul(True)),
                           ("Ctrl+PgDown", lambda: self._sekme_git(1)), ("Ctrl+PgUp", lambda: self._sekme_git(-1))):
            QShortcut(QKeySequence(tus), self, activated=islev)      # kısayol eyleme konmaz (belirsiz kısayol); ipucunda gösterilir
        for k, a in self.kosullu_eylemleri.items():
            self.eylemler["kosullu." + k] = a

    def _kosullu_menusu(self, dugme) -> QMenu:
        """Koşullu Biçimlendirme menüsü (faz5_tasarim.md §8.4); Giriş ▸ Stiller grubunda açılır."""
        def pen(ad, *a, **kw):
            return lambda: getattr(self, ad)(*a, **kw)
        m = QMenu(dugme)
        self.kosullu_eylemleri = {}

        def ekle(menu, anahtar, metin, islev):
            self.kosullu_eylemleri[anahtar] = menu.addAction(metin, islev)
        hm = m.addMenu("Hücre Kurallarını Vurgula")
        for anahtar, metin, tur, islec in (
                ("buyuk", "Büyüktür…", "hucre_degeri", "buyuk"), ("kucuk", "Küçüktür…", "hucre_degeri", "kucuk"),
                ("arasinda", "Arasında…", "hucre_degeri", "arasinda"), ("esit", "Eşittir…", "hucre_degeri", "esit"),
                ("metin", "Metin İçerir…", "metin", "icerir"), ("yinelenen", "Yinelenen Değerler…", "yinelenen", None)):
            ekle(hm, anahtar, metin, pen("kosullu_kural_ac", tur, islec))
        im = m.addMenu("İlk/Son Kuralları")
        for anahtar, metin, tur, yuzde in (
                ("ilk10", "İlk 10 Öğe…", "ilk", False), ("ilk10y", "İlk %10…", "ilk", True),
                ("son10", "Son 10 Öğe…", "son", False), ("son10y", "Son %10…", "son", True),
                ("ort_ustu", "Ortalamanın Üstünde…", "ortalama_ustu", False),
                ("ort_alti", "Ortalamanın Altında…", "ortalama_alti", False)):
            ekle(im, anahtar, metin, pen("kosullu_kural_ac", tur, None, yuzde))
        vm = m.addMenu("Veri Çubukları")
        for baslik, onek in (("Gradyan Dolgu", ""), ("Düz Dolgu", "duz_")):
            vm.addSection(baslik)
            for k, ad in (("mavi", "Mavi"), ("yesil", "Yeşil"), ("kirmizi", "Kırmızı"), ("turuncu", "Turuncu"),
                          ("acik_mavi", "Açık Mavi"), ("mor", "Mor")):
                ekle(vm, f"cubuk_{onek}{k}", f"{ad} Veri Çubuğu", pen("kosullu_hazir", "veri_cubugu", onek + k))
        rm = m.addMenu("Renk Ölçekleri")
        for k, ad in (("yesil_sari_kirmizi", "Yeşil - Sarı - Kırmızı Renk Ölçeği"),
                      ("kirmizi_sari_yesil", "Kırmızı - Sarı - Yeşil Renk Ölçeği"),
                      ("yesil_beyaz", "Yeşil - Beyaz Renk Ölçeği"), ("beyaz_kirmizi", "Beyaz - Kırmızı Renk Ölçeği")):
            ekle(rm, f"olcek_{k}", ad, pen("kosullu_hazir", "renk_olcegi", k))
        m.addSeparator()
        ekle(m, "yeni", "Yeni Kural…", pen("kosullu_kural_ac", "hucre_degeri", None, False, False))
        tm = m.addMenu("Kuralları Temizle")
        ekle(tm, "temizle_secim", "Seçili Hücrelerden Kuralları Temizle", pen("kosullu_temizle", False))
        ekle(tm, "temizle_sayfa", "Tüm Sayfadan Kuralları Temizle", pen("kosullu_temizle", True))
        ekle(m, "yonet", "Kuralları Yönet…", pen("kosullu_yonet"))
        return m

    def _yardim_eylemleri_kur(self) -> None:
        """Yardım sekmesinin eylemleri; F1 pencere düzeyinde kısayol (eyleme konmaz, bkz. `_eylemleri_kur`)."""
        for anahtar, metin, konu, ipucu in (
                ("yardim", "Nasıl Kullanılır", None, "Yardım ve Nasıl Kullanılır (F1)"),
                ("yardim_kisayollar", "Klavye Kısayolları", "kisayollar", None),
                ("yardim_yenilikler", "Yenilikler", "yenilikler", None),
                ("yardim_farklar", "Excel'den Farklar", "farklar", None)):
            a = QAction(metin, self)
            a.setToolTip(ipucu or metin)
            a.triggered.connect(lambda _=False, k=konu: self.yardim_ac(k))
            self.eylemler[anahtar] = a
        h = QAction(f"{APP_NAME} Hakkında", self)
        h.setToolTip("Sürüm, künye ve kullanılan açık kaynak bileşenler")
        h.triggered.connect(lambda _=False: self.hakkinda_ac())
        self.eylemler["hakkinda"] = h
        QShortcut(QKeySequence("F1"), self, activated=lambda: self.yardim_ac(None))
        QShortcut(QKeySequence("F7"), self, activated=lambda: self.yazim_denetle(), context=Qt.WindowShortcut)

    # --- Gözden Geçir: Yazım Denetimi (Faz 7c) ---
    def _yazim_motoru(self):
        """Windows Yazım Denetimi API'si; kullanılamıyorsa None ve ileti. Testlerde yamalanır."""
        from ..io.yazim_motoru import SpellEngine, SpellEngineUnavailable
        try:
            return SpellEngine()
        except SpellEngineUnavailable as e:
            QMessageBox.information(self, APP_NAME, str(e))
            return None

    def yazim_denetle(self) -> bool:
        """Seçili hücreleri (tek hücre seçiliyse tüm sayfayı) denetler; yanlış bulunduysa pencere açılır."""
        from ..model.komutlar import HucrelerDegis
        from ..model.yazim import YazimOturumu, hucre_sirasi
        from .yazim_penceresi import YazimPenceresi
        g = self.izgara()
        motor = self._yazim_motoru()
        if motor is None:
            return False
        secimler = g.secimler
        tek = len(secimler) == 1 and secimler[0].ilk_satir == secimler[0].son_satir             and secimler[0].ilk_sutun == secimler[0].son_sutun
        sira = hucre_sirasi(g.sayfa, secimler, tek)
        oturum = YazimOturumu(g.sayfa, sira, motor,
                              lambda sayfa, yeni: g.yigin.calistir(HucrelerDegis(sayfa, yeni)))
        d = YazimPenceresi(oturum, self, git=lambda r, c: g.sec((r, c)))
        if d.baslat():
            d.exec()
        else:
            QMessageBox.information(self, APP_NAME, "Yazım denetimi tamamlandı: yanlış sözcük bulunamadı.")
        return True

    def hakkinda_ac(self) -> None:
        from .hakkinda_penceresi import HakkindaPenceresi
        HakkindaPenceresi(self).exec()

    def yardim_ac(self, konu=None):
        """Yardım penceresini açar (tek örnek); `konu` verilirse o konuya gider."""
        from .yardim import yardim_goster
        return yardim_goster(self, konu)

    def _menu(self, ogeler) -> QMenu:
        """Katalog anahtarlarından açılır menü; `None` ayırıcı, `(ad, [alt öğeler])` alt menü."""
        m = QMenu(self)
        for o in ogeler:
            if o is None:
                m.addSeparator()
            elif isinstance(o, tuple):
                alt = self._menu(o[1])
                alt.setTitle(o[0])
                m.addMenu(alt)
            else:
                m.addAction(self.eylemler[o])
        return m

    def _giris_gruplari_ekle(self) -> None:
        """Giriş sekmesinin Pano / Stiller / Hücreler / Düzenleme grupları (Yazı Tipi, Hizalama, Sayı
        `BicimCubugu`da kurulur). Sıra Excel gibi: Pano, Yazı Tipi, Hizalama, Sayı, Stiller, Hücreler,
        Düzenleme."""
        e = self.eylemler
        pano = SeritGrubu("Pano", 3, "paste32")
        pano.buyuk(e["yapistir"])
        pano.kucukler([e["kes"], e["kopyala"], self.bicim_cubugu.boyaci])
        stiller = SeritGrubu("Stiller", 5, "cond_format32")
        stiller.buyuk(menu=self._kosullu_menusu(self), ikon="cond_format32", metin="Koşullu\nBiçimlendirme")
        hucreler = SeritGrubu("Hücreler", 4, "insert32")
        hucreler.buyuk(menu=self._menu(("satir_ekle", "sutun_ekle", "sayfa_ekle")), ikon="insert32", metin="Ekle")
        hucreler.buyuk(menu=self._menu(("satir_sil", "sutun_sil", "sayfa_sil")), ikon="delete32", metin="Sil")
        hucreler.buyuk(menu=self._menu((
            "satir_yukseklik", "satir_sigdir", "sutun_genislik", "sutun_sigdir", None,
            ("Gizle ve Göster", ("satir_gizle", "satir_goster", "sutun_gizle", "sutun_goster")), None,
            "sayfa_adlandir", "sekme_rengi", None, "hucre_bicimi")), ikon="format32", metin="Biçim")
        duzenleme = SeritGrubu("Düzenleme", 2, "autosum")
        duzenleme.kucukler([
            e["otomatik_toplam"],
            (e["doldur"], self._menu(("doldur_asagi", "doldur_saga"))),
            (e["temizle"], self._menu(("temizle_hepsi", "temizle_bicim", "temizle_icerik", "temizle_not")))])
        duzenleme.buyuk(menu=self._menu((
            "artan", "azalan", "ozel_sirala", None, "filtre", "filtre_temizle", "filtre_yeniden")),
            ikon="sort_filter32", metin="Sırala ve\nFiltre")
        duzenleme.buyuk(menu=self._menu(("bul", "degistir", "git")), ikon="find32", metin="Bul ve\nSeç")
        for g, konum in ((pano, 0), (stiller, 4), (hucreler, 5), (duzenleme, 6)):
            self.bicim_cubugu.grup_ekle(g, konum)
        for d in self.bicim_cubugu.findChildren(QToolButton):
            d.setFocusPolicy(Qt.NoFocus)             # şerit düğmeleri düzenleme/formül çubuğu odağını çalmaz

    def _eylemleri_kur(self) -> None:
        """Eylem kataloğu (5j-3): her komut TEK `QAction`; menüler ve şerit aynı nesneyi kullanır.
        Kısayollar eyleme konmaz (aynı tuş iki yerde tanımlanınca Qt 'belirsiz kısayol' verir):
        `QShortcut`lar ayrı kurulur, burada yalnız ipucunda gösterilir. Eylemler çağrıldığında etkin
        sayfanın ızgarasına bakar (`self.izgara()`)."""
        self.eylemler: Dict[str, QAction] = {}

        def e(anahtar, metin, islev, kisayol="", ikon=None, isaretli=False):
            a = QAction(metin, self)
            if ikon:
                a.setIcon(icons.icon(ikon))
                a.setProperty("ikonAdi", ikon)
            a.setToolTip(metin.rstrip("…") + (f" ({kisayol})" if kisayol else ""))
            if isaretli:
                a.setCheckable(True)
            if islev is not None:
                a.triggered.connect(lambda _=False, f=islev: f())
            self.eylemler[anahtar] = a
            return a
        g = self.izgara
        sayfa_i = lambda: self.sekmeler.currentIndex()
        # geri al / yinele
        e("geri_al", "Geri Al", lambda: g().geri_al(), "Ctrl+Z", "undo")
        e("yinele", "Yinele", lambda: g().yinele(), "Ctrl+Y", "redo")
        # pano
        e("yapistir", "Yapıştır", lambda: g().yapistir(), "Ctrl+V", "paste32")
        e("kes", "Kes", lambda: g().kes(), "Ctrl+X", "cut")
        e("kopyala", "Kopyala", lambda: g().kopyala(), "Ctrl+C", "copy")
        # düzenleme
        e("otomatik_toplam", "Otomatik Toplam", lambda: g().otomatik_toplam(), "Alt+=", "autosum")
        e("doldur", "Doldur", lambda: None, "", "fill")                 # yalnız menü düğmesinin başlığı
        e("doldur_asagi", "Aşağı", lambda: g().asagi_doldur(), "Ctrl+D")
        e("doldur_saga", "Sağa", lambda: g().saga_doldur(), "Ctrl+R")
        e("temizle", "Temizle", lambda: None, "", "clear")              # yalnız menü düğmesinin başlığı
        e("temizle_hepsi", "Tümünü Temizle", lambda: g().tumunu_temizle())
        e("temizle_bicim", "Biçimleri Temizle", lambda: g().bicimleri_temizle())
        e("temizle_icerik", "İçeriği Temizle", lambda: g().secimi_temizle(), "Delete")
        e("temizle_not", "Notları Temizle", lambda: g().notlari_temizle())
        e("bul", "Bul…", lambda: self.bul_ac(False), "Ctrl+F", "find32")
        e("degistir", "Değiştir…", lambda: self.bul_ac(True), "Ctrl+H")
        e("git", "Git…", lambda: self.git_ac(), "Ctrl+G")
        # hücreler
        e("satir_ekle", "Sayfa Satırları Ekle", lambda: g().satirlari_ekle(), "", "insert32")
        e("sutun_ekle", "Sayfa Sütunları Ekle", lambda: g().sutunlari_ekle())
        e("sayfa_ekle", "Sayfa Ekle", lambda: self.sayfa_ekle())
        e("satir_sil", "Sayfa Satırlarını Sil", lambda: g().satirlari_sil(), "", "delete32")
        e("sutun_sil", "Sayfa Sütunlarını Sil", lambda: g().sutunlari_sil())
        e("sayfa_sil", "Sayfayı Sil", lambda: self.sayfa_sil(sayfa_i()))
        e("satir_yukseklik", "Satır Yüksekliği…", lambda: g()._satir_yuksekligi_sor(), "", "format32")
        e("satir_sigdir", "Satır Yüksekliğini Otomatik Sığdır", lambda: g().satir_otomatik_sigdir())
        e("sutun_genislik", "Sütun Genişliği…", lambda: g()._sutun_genisligi_sor())
        e("sutun_sigdir", "Sütun Genişliğini Otomatik Sığdır", lambda: g().sutun_otomatik_sigdir())
        e("satir_gizle", "Satırları Gizle", lambda: g().satirlari_gizle(), "Ctrl+9")
        e("satir_goster", "Satırları Göster", lambda: g().satirlari_goster(), "Ctrl+Shift+9")
        e("sutun_gizle", "Sütunları Gizle", lambda: g().sutunlari_gizle(), "Ctrl+0")
        e("sutun_goster", "Sütunları Göster", lambda: g().sutunlari_goster(), "Ctrl+Shift+0")
        e("sayfa_adlandir", "Sayfayı Yeniden Adlandır…", lambda: self.sayfa_yeniden_adlandir(sayfa_i()))
        e("sekme_rengi", "Sekme Rengi…", lambda: self._sekme_rengi_sor(sayfa_i()))
        e("hucre_bicimi", "Hücreleri Biçimlendir…", lambda: self.bicim_cubugu.penceresi_ac(), "Ctrl+1")
        # veri
        e("artan", "Artan Sırala", lambda: self.sirala_hizli(True), "", "sort_az")
        e("azalan", "Azalan Sırala", lambda: self.sirala_hizli(False), "", "sort_za")
        e("ozel_sirala", "Özel Sıralama…", lambda: self.sirala_ozel(), "", "sort32")
        e("filtre", "Filtre", lambda: self.filtre_ac_kapat(), "Ctrl+Shift+L", "filter32", isaretli=True)
        e("filtre_temizle", "Filtreyi Temizle", lambda: self.filtre_temizle(), "", "filter_clear")
        e("filtre_yeniden", "Yeniden Uygula", lambda: self.filtre_yeniden_uygula(), "Ctrl+Alt+L", "reapply")
        e("dogrulama", "Veri Doğrulama…", lambda: self.dogrulama_ac(), "", "validation32")
        e("ad_tanimla", "Ad Tanımla…", lambda: self.ad_tanimla_ac(), "", "define_name")
        e("ad_yoneticisi", "Ad Yöneticisi", lambda: self.ad_yoneticisi_ac(), "Ctrl+F3", "name_manager32")
        # notlar
        e("yazim", "Yazım Denetimi…", lambda: self.yazim_denetle(), "F7", "spell32")
        e("yeni_not", "Yeni Not", lambda: g().not_duzenle(), "Shift+F2", "note32")
        e("notu_sil", "Notu Sil", lambda: g().notu_sil(), "", "note_delete")
        # görünüm
        for k, metin in (("bolme", "Bölmeleri Dondur"), ("ust_satir", "Üst Satırı Dondur"),
                         ("ilk_sutun", "İlk Sütunu Dondur"), ("coz", "Bölmelerin Dondurmasını Kaldır")):
            e(k, metin, lambda t=k: g().dondur_ayarla(t), "", "freeze32" if k == "bolme" else None)
        kl = e("kilavuz", "Kılavuz Çizgileri", None, isaretli=True)
        kl.setChecked(True)
        kl.toggled.connect(lambda v: g().kilavuz_goster(v))
        e("yakin_100", "%100", lambda: g().yakinlastir(1.0), "", "zoom100_32")
        # sayfa düzeni (5j-5): hepsi `sayfa_yapisi_degistir` (geri alınabilir) ya da Sayfa Yapısı penceresi
        from ..model.sayfa_yapisi import KAGITLAR, KENAR_HAZIR
        for k, ad in (("normal", "Normal"), ("genis", "Geniş"), ("dar", "Dar")):
            u, a, so, sa = KENAR_HAZIR[k]
            e("kenar_" + k, f"{ad}  (üst/alt {u:g}, sol/sağ {so:g} cm)".replace(".", ","),
              lambda u=u, a=a, so=so, sa=sa: self.sayfa_yapisi_degistir(ust=u, alt=a, sol=so, sag=sa))
        e("kenar_ozel", "Özel Kenar Boşlukları…", lambda: self.sayfa_yapisi_ac())
        e("yon_dikey", "Dikey", lambda: self.sayfa_yapisi_degistir(yon="dikey"))
        e("yon_yatay", "Yatay", lambda: self.sayfa_yapisi_degistir(yon="yatay"))
        for k, (kg, ky) in KAGITLAR.items():
            e("kagit_" + k, f"{k}  ({kg:g} × {ky:g} cm)".replace(".", ","),
              lambda k=k: self.sayfa_yapisi_degistir(kagit=k))
        e("alan_belirle", "Yazdırma Alanını Belirle", lambda: self.sayfa_yapisi_degistir(alan=g().secim))
        e("alan_temizle", "Yazdırma Alanını Temizle", lambda: self.sayfa_yapisi_degistir(alan=None))
        e("baslik_yazdir", "Başlıkları Yazdır", lambda: self.sayfa_yapisi_ac(), "", "print_titles32")
        e("sayfa_sonu_ekle", "Sayfa Sonu Ekle", lambda: self.sayfa_sonu_ekle())
        e("sayfa_sonu_kaldir", "Sayfa Sonunu Kaldır", lambda: self.sayfa_sonu_kaldir())
        e("sayfa_sonu_sifirla", "Tüm Sayfa Sonlarını Sıfırla", lambda: self.sayfa_sonlarini_sifirla())
        e("sira_asagi", "Önce aşağı, sonra sağa", lambda: self.sayfa_yapisi_degistir(sayfa_sirasi="asagi_sonra_sag"),
          isaretli=True)
        e("sira_sag", "Önce sağa, sonra aşağı", lambda: self.sayfa_yapisi_degistir(sayfa_sirasi="sag_sonra_asagi"),
          isaretli=True)
        sb = e("sayfa_sonlari", "Sayfa Sonlarını Göster", None, isaretli=True)
        sb.toggled.connect(lambda v: g().sayfa_sonlari_goster(v))
        e("kilavuz_yazdir", "Kılavuz Çizgilerini Yazdır",
          lambda: self.sayfa_yapisi_degistir(kilavuz=not g().sayfa.sayfa_yapisi.kilavuz), isaretli=True)

    def _gorunum_menusu_hazirla(self) -> None:
        self._eylem_durumlari()

    def _eylem_durumlari(self) -> None:
        """Etkin sayfaya bağlı eylem durumları (işaret/etkinlik/metin); `_arayuzu_guncelle` her seçim
        değişiminde çağırır, bu yüzden ucuz tutulur."""
        g = self.izgara()
        if g is None:
            return
        e = self.eylemler
        y = g.sayfa.sayfa_yapisi
        for anahtar, deger in (("kilavuz", g.sayfa.kilavuz), ("filtre", g.sayfa.filtre is not None),
                               ("kilavuz_yazdir", y.kilavuz), ("sayfa_sonlari", g.sayfa.sayfa_sonlari),
                               ("sira_asagi", y.sayfa_sirasi == "asagi_sonra_sag"),
                               ("sira_sag", y.sayfa_sirasi == "sag_sonra_asagi")):
            a = e[anahtar]
            a.blockSignals(True)
            a.setChecked(bool(deger))
            a.blockSignals(False)
        e["coz"].setEnabled(g.sayfa.dondur is not None)
        r, c = g._aktif                                      # sayfa sonları: etkin hücrenin üstü ve solu
        e["sayfa_sonu_ekle"].setEnabled((r >= 2 and r not in y.satir_kesmeleri)
                                        or (c >= 2 and c not in y.sutun_kesmeleri))
        e["sayfa_sonu_kaldir"].setEnabled(r in y.satir_kesmeleri or c in y.sutun_kesmeleri)
        e["sayfa_sonu_sifirla"].setEnabled(bool(y.satir_kesmeleri or y.sutun_kesmeleri))
        var = g.not_var_mi()
        e["notu_sil"].setEnabled(var)
        e["yeni_not"].setText("Notu Düzenle" if var else "Yeni Not")

    def closeEvent(self, olay):
        olay.ignore()                                        # yalnız başarıyla kapanabilirse kabul edilir
        try:
            kapanir = self._kapanabilir_mi()
        except Exception as e:                               # kayıt sırasında beklenmeyen hata: pencere AÇIK kalır
            QMessageBox.critical(self, APP_NAME, f"Kapatılamadı: {e}")
            kapanir = False
        if kapanir:
            self._pencere_kapandi()
            olay.accept()

    def showEvent(self, olay):
        super().showEvent(olay)
        theme.baslik_cubugu_rengi(self)

    # ------------------------------------------------------------------ yardımcılar
    def izgara(self) -> Izgara:
        return self.izgara_yigini.currentWidget()

    def _baslik_guncelle(self):
        ad = self.belge_adi + (" *" if self.degisti_mi() else "")
        self.setWindowTitle(f"{ad} - {APP_NAME}")
        self.belge_etiketi.setText(f"{ad} — {APP_NAME}")

    # ------------------------------------------------------------------ sayfalar
    def _izgara_olustur(self, sayfa: Sayfa) -> Izgara:
        g = Izgara(sayfa, yigin=self.yigin)
        g.aktifDegisti.connect(self._arayuzu_guncelle)
        g.secimDegisti.connect(self._arayuzu_guncelle)
        g.degisti.connect(self._icerik_degisti)
        g.modDegisti.connect(self._mod_degisti)
        g.duzenlemeMetniDegisti.connect(self._duzenleme_aynala)
        g.suruklemeBitti.connect(self._arayuzu_guncelle)
        g.nesneSecimiDegisti.connect(self._arayuzu_guncelle)     # Ad Kutusu seçili nesnenin adını gösterir
        g.nesneAyarIstendi.connect(self.grafik_eylemleri.ayar_istendi)
        g.boyaciDegisti.connect(lambda _a: self._arayuzu_guncelle())
        g.yakinlastirmaDegisti.connect(self._yakinlastirma_degisti)
        g.uyari.connect(self._uyari)
        g.uzakOnay.connect(self._uzak_onayla)
        g.filtreDugmesi.connect(self.filtre_paneli_ac)
        g.veri_kaybi_onayi = self._birlestirme_onayi
        g.hata_aciklayici = self.hata_aciklamasi
        g.gecmisIslemi.connect(self._gecmis_islemi_ayarla)
        self._izgaralar[sayfa] = g
        self.izgara_yigini.addWidget(g)
        return g

    def _birlestirme_onayi(self) -> bool:
        """Excel'deki uyarı: birleştirmede yalnız sol üst hücrenin değeri kalır."""
        c = QMessageBox.warning(
            self, APP_NAME, "Hücreleri birleştirmek yalnızca sol üstteki değeri korur ve diğer "
            "değerleri siler. Devam edilsin mi?", QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok)
        return c == QMessageBox.Ok

    def _gecmis_islemi_ayarla(self, basladi: bool):
        self._gecmis_islemi = basladi
        if basladi:
            return
        # geri al/yinele bitti: asıl değişiklik başka sayfadaysa o sayfaya geç (Excel gibi). Hedef
        # olaylardan değil komuttan alınır: başka sayfalardaki formül düzeltmeleri (yan etki) geçiş
        # yaptırmaz (6f)
        hedef = ana_sayfa(self.yigin.son_komut, self.yigin.son_geri_al)
        if hedef is not None and hedef is not self._secili_sayfa and hedef in self.kitap.sayfalar:
            self.sekmeler.setCurrentIndex(self.kitap.sayfalar.index(hedef))

    def _sekmeleri_esitle(self, secilecek: Optional[Sayfa] = None):
        """Izgaraları ve sekme çubuğunu kitabın güncel sayfa listesine göre eşitler.

        Kitaptan çıkan sayfanın ızgarası atılmaz, saklanır (silmeyi geri alınca seçim/kaydırma/
        yakınlaştırma korunur)."""
        sayfalar = self.kitap.sayfalar
        for s in [s for s in self._izgaralar if s not in sayfalar]:
            g = self._izgaralar.pop(s)
            self.izgara_yigini.removeWidget(g)
            g.hide()
            self._saklanan[s] = g
        for s in sayfalar:
            if s not in self._izgaralar:
                g = self._saklanan.pop(s, None)
                if g is None:
                    self._izgara_olustur(s)
                else:
                    self._izgaralar[s] = g
                    self.izgara_yigini.addWidget(g)
        adlar = [s.ad for s in sayfalar]
        if [self.sekmeler.tabText(i) for i in range(self.sekmeler.count())] != adlar:
            self.sekmeler.blockSignals(True)         # (sürüklemeden gelen olayda zaten eşit: yeniden kurulmaz)
            while self.sekmeler.count():
                self.sekmeler.removeTab(0)
            for ad in adlar:
                self.sekmeler.addTab(ad)
            self.sekmeler.blockSignals(False)
        for i, s in enumerate(sayfalar):
            self.sekmeler.setTabData(i, s.sekme_rengi)
        if secilecek not in sayfalar:
            secilecek = (self._secili_sayfa if self._secili_sayfa in sayfalar
                         else sayfalar[min(self._son_indeks, len(sayfalar) - 1)])
        i = sayfalar.index(secilecek)
        self.sekmeler.blockSignals(True)
        self.sekmeler.setCurrentIndex(i)
        self.sekmeler.blockSignals(False)
        self.sekmeler.update()
        self._sekme_degisti(i)

    def _kitap_olayi(self, olay: Olay):
        """Modeldeki değişikliklere arayüz tepkisi (doğrudan yazım, geri al ve yinele aynı yoldan gelir)."""
        if olay.tur in ("hucre", "sonuc", "yapi", "ek", "sayfa"):
            kuralli = False
            for g in self._izgaralar.values():
                g._kosullu_gecersiz()                  # koşullu biçim başka sayfaya da bakabilir: hepsi
                kuralli = kuralli or bool(g.sayfa.kosullu)
            gorunen = self._izgaralar.get(self._secili_sayfa)
            if kuralli and gorunen is not None and olay.sayfa is not self._secili_sayfa:
                gorunen.viewport().update()            # başka sayfadaki değişiklik görünen sayfanın biçimini değiştirebilir
            if olay.tur == "ek" and olay.ayrinti.get("alan") in ("kosullu", "hepsi"):
                ig = self._izgaralar.get(olay.sayfa)
                if ig is not None:
                    ig.viewport().update()
        if olay.tur == "sonuc":
            g = self._izgaralar.get(olay.sayfa)
            if g is not None and olay.sayfa is self._secili_sayfa:
                g._oto_gecersiz()              # metin sonucu değiştiyse kaydırılmış satır yüksekliği de
                g._sayfa_adimlari()
                g.viewport().update()          # başka hücreden tetiklenen yeniden hesaplama
            self._dongu_etiketi_guncelle()
            return
        if olay.tur == "ad":
            self._ad_listesini_yenile()
            self._arayuzu_guncelle()               # ad kutusu seçimin adını gösterir
            return
        if olay.tur == "sayfa":
            if olay["islem"] == "sil":
                self._son_indeks = olay["indeks"]
            self._sekmeleri_esitle(olay.sayfa if olay["islem"] == "ekle" else None)

    def sayfa_ekle(self):
        self.yigin.calistir(SayfaEkle(self.kitap))

    def sayfa_sil(self, i: int):
        sayfa = self.kitap.sayfalar[i]
        if len(self.kitap.sayfalar) == 1:
            QMessageBox.information(self, APP_NAME, "Çalışma kitabındaki son sayfa silinemez.")
            return
        if sayfa.kullanilan_aralik() is not None:
            c = QMessageBox.question(
                self, APP_NAME,
                f"“{sayfa.ad}” sayfası ve içindeki veriler silinecek (Ctrl+Z ile geri alınabilir). "
                "Devam edilsin mi?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if c != QMessageBox.Yes:
                return
        Izgara._pano_durumu = None        # kesilen/kopyalanan sayfa silinmiş olabilir
        self.yigin.calistir(SayfaSil(self.kitap, sayfa))

    def sayfa_yeniden_adlandir(self, i: int, yeni: Optional[str] = None):
        sayfa = self.kitap.sayfalar[i]
        if yeni is None:
            yeni, tamam = QInputDialog.getText(self, "Sayfayı yeniden adlandır", "Sayfa adı:",
                                               text=sayfa.ad)
            if not tamam:
                return
        if yeni == sayfa.ad:
            return
        try:
            self.yigin.calistir(SayfaYenidenAdlandir(self.kitap, sayfa, yeni))
        except ValueError as e:
            QMessageBox.warning(self, APP_NAME, str(e))

    def sekme_rengi_ata(self, i: int, renk: Optional[str]):
        self.kitap.sayfalar[i].sekme_rengi = renk
        self.gorunum_degisti_isaretle()
        self.sekmeler.setTabData(i, renk)
        self.sekmeler.update()

    def _sekme_rengi_sor(self, i: int):
        mevcut = self.kitap.sayfalar[i].sekme_rengi
        r = QColorDialog.getColor(QColor(mevcut) if mevcut else QColor(theme.ACCENT), self,
                                  "Sekme rengi")
        if r.isValid():
            self.sekme_rengi_ata(i, r.name())

    def sekme_menusu_olustur(self, nokta) -> QMenu:
        i = self.sekmeler.tabAt(nokta)
        m = QMenu(self)
        m.addAction("Yeni sayfa", self.sayfa_ekle)
        if i >= 0:
            m.addAction("Yeniden adlandır…", lambda: self.sayfa_yeniden_adlandir(i))
            m.addAction("Sekme rengi…", lambda: self._sekme_rengi_sor(i))
            if self.kitap.sayfalar[i].sekme_rengi:
                m.addAction("Sekme rengini kaldır", lambda: self.sekme_rengi_ata(i, None))
            m.addAction("Sil", lambda: self.sayfa_sil(i))
        return m

    def _sekme_menusu(self, nokta):
        self.sekme_menusu_olustur(nokta).exec(self.sekmeler.mapToGlobal(nokta))

    def _sekme_tasindi(self, kaynak: int, hedef: int):
        self.yigin.calistir(SayfaTasi(self.kitap, self.kitap.sayfalar[kaynak], hedef))

    def _sekme_git(self, yon: int):
        n = self.sekmeler.count()
        self.sekmeler.setCurrentIndex((self.sekmeler.currentIndex() + yon) % n)

    def _sekme_degisti(self, i: int):
        if i < 0 or i >= len(self.kitap.sayfalar):
            return
        eski = self._izgaralar.get(self._secili_sayfa)
        yeni_sayfa = self.kitap.sayfalar[i]
        if (eski is not None and self._uzak is None and yeni_sayfa is not self._secili_sayfa
                and eski.duzenleniyor() and eski._isaret_modu()):
            self._duzenlemeyi_devret(eski)
        if eski is not None and yeni_sayfa is not self._secili_sayfa:
            eski.boyaci_iptal()                  # biçim boyacısı sayfaya özel: sayfa değişince biter
        self._secili_sayfa = yeni_sayfa
        g = self._izgaralar[self._secili_sayfa]
        self.izgara_yigini.setCurrentWidget(g)
        if self._uzak is not None:
            self._uzak_baglan(g)
        self.yakin_kaydirici.blockSignals(True)
        self.yakin_kaydirici.setValue(round(g.yakinlastirma * 100))
        self.yakin_kaydirici.blockSignals(False)
        self.yakin_etiketi.setText(f"{round(g.yakinlastirma * 100)}%")
        self._arayuzu_guncelle()
        if self._uzak is not None:
            self.formul.setFocus()
        else:
            g.setFocus()

    # ------------------------------------------------------------------ başka sayfadan başvuru (K7)
    def _duzenlemeyi_devret(self, g: Izgara):
        """Formül yazarken başka sayfa sekmesine tıklandı: hücre içi düzenleme formül çubuğuna devredilir
        (düzenleyici kendi sayfasının ızgarasında yaşar, sekme değişince gizlenir). Enter formülü
        ilk hücreye yazar ve o sayfaya döner; Esc vazgeçer."""
        e = g._duzenleyici
        self._uzak = {"izgara": g, "hucre": g._duzenlenen}
        self.formul.setText(e.text())
        self.formul.setCursorPosition(e.cursorPosition())
        g.duzenlemeyi_bitir(False)
        self._mod_degisti("Gir")
        self.mod_etiketi.setText("Gir")

    def _uzak_onayla(self):
        """Devredilen düzenleme sürerken işaret dışı tıklama: formül ilk hücreye onaylanır (Enter gibi);
        hatalıysa uyarı verilir ve düzenleme açık kalır."""
        if self._uzak is not None:
            self._formul_onayla(self.formul.text())

    def _uzak_baglan(self, g: Izgara):
        for x in self._izgaralar.values():
            x.dis_duzenleyici = None
            x.uzak_sayfa = self._uzak["izgara"].sayfa
        g.dis_duzenleyici = self.formul
        self.formul.isaret_denetimi = g._isaret_modu

    def _uzak_bitir(self):
        """Devredilen düzenleme bitti: kaynak sayfaya dön. Kaynak ızgarayı verir."""
        u, self._uzak = self._uzak, None
        for x in self._izgaralar.values():
            x.uzak_sayfa = None
        if u["izgara"].sayfa in self.kitap.sayfalar:
            self.sekmeler.setCurrentIndex(self.kitap.sayfalar.index(u["izgara"].sayfa))
        return u

    # ------------------------------------------------------------------ ad kutusu / formül çubuğu
    def _arayuzu_guncelle(self, *_):
        self._baslik_guncelle()
        g = self.izgara()
        kaynak = self.sender()
        if kaynak is not g and kaynak in self._izgaralar.values():
            return       # arka plandaki sayfanın sinyali
        sec = g.secim
        coklu = (sec.ilk_satir, sec.ilk_sutun) != (sec.son_satir, sec.son_sutun)
        if g.suruklenuyor() and coklu:
            self.ad_kutusu.setText(f"{sec.son_satir - sec.ilk_satir + 1}S x "
                                   f"{sec.son_sutun - sec.ilk_sutun + 1}Sü")
        else:
            ad = secimin_adi(self.kitap, g.sayfa, sec) if self.kitap.adlar else None
            nesne = g.sayfa.nesne(g.secili_nesne) if g.secili_nesne is not None else None
            self.ad_kutusu.setText(nesne.etiket if nesne is not None else (ad or hucre_yaz(*g.aktif)))
        isaretleniyor = g.dis_duzenleyici is not None and g._isaret is not None
        if (not g.duzenleniyor() and not self.formul.hasFocus() and not isaretleniyor
                and self._uzak is None):
            self._formul_isareti_kapat()
            self.formul.setText(g.aktif_duzenleme_metni())
        self._ozet_planla()
        self._dongu_etiketi_guncelle()
        self._hata_etiketi_guncelle()
        self.serit.guncelle()
        self._eylem_durumlari()
        self.grafik_eylemleri.sekmeyi_esitle()

    # ------------------------------------------------------------------ hata açıklamaları (T8)
    def hata_aciklamasi(self, sayfa: Sayfa, satir: int, sutun: int) -> str:
        """Hücredeki hatanın Türkçe açıklaması (hata yoksa ""); kitapta bir olay olana dek önbellekte."""
        anahtar = (sayfa.kimlik, satir, sutun)
        m = self._hata_onb.get(anahtar)
        if m is None:
            m = self._hata_onb[anahtar] = hata_neden.metin(
                hata_neden.acikla(sayfa, satir, sutun, motor=self.motor))
        return m

    def _hata_etiketi_guncelle(self):
        """Durum çubuğu: tek hücre (ya da tek birleşik hücre) seçiliyken etkin hücredeki hatanın açıklaması."""
        g = self.izgara()
        sec = g.secim
        tek = (sec.ilk_satir, sec.ilk_sutun) == (sec.son_satir, sec.son_sutun) or g.sayfa.birlesim(*g.aktif) == sec
        metin = self.hata_aciklamasi(g.sayfa, *g.aktif) if tek and not g._ekler else ""
        if not metin:
            self.hata_etiketi.hide()
            return
        genislik = max(200, self.width() // 2)
        self.hata_etiketi.setText(self.hata_etiketi.fontMetrics().elidedText(metin, Qt.ElideRight, genislik))
        self.hata_etiketi.setToolTip(metin)
        self.hata_etiketi.show()

    def _uyari(self, metin: str):
        self.statusBar().showMessage(metin, 6000)
        QMessageBox.warning(self, APP_NAME, metin)

    def _icerik_degisti(self):
        for g in self._izgaralar.values():
            g.viewport().update()
        self._arayuzu_guncelle()
        self._dongu_denetle()

    # ------------------------------------------------------------------ döngüsel başvuru (6e)
    def _dongu_etiketi_guncelle(self):
        """Durum çubuğu: seçili sayfadaki döngü hücrelerinden ilki (Excel gibi); yalnız başka
        sayfada varsa adressiz "Döngüsel Başvurular"."""
        dongu = self.motor.donguler
        if not dongu:
            self.dongu_etiketi.hide()
            return
        kimlik = self._secili_sayfa.kimlik if self._secili_sayfa is not None else None
        burada = sorted((r, c) for k, r, c in dongu if k == kimlik)
        self.dongu_etiketi.setText("Döngüsel Başvurular: " + hucre_yaz(*burada[0]) if burada
                                   else "Döngüsel Başvurular")
        self.dongu_etiketi.show()

    def _dongu_denetle(self):
        """Yeni bir döngü oluştuysa (formül girişi, yapıştırma…) bir kez uyarır. Geri al/yinele
        sırasında uyarmaz; etiket her durumda güncellenir."""
        simdiki = set(self.motor.donguler)
        yeni = simdiki - self._dongu_bilinen
        self._dongu_bilinen = simdiki
        self._dongu_etiketi_guncelle()
        if yeni and not self._gecmis_islemi:
            QMessageBox.warning(
                self, APP_NAME,
                "Bu formül döngüsel başvuru içeriyor: bir formül kendi hücresine doğrudan ya da "
                "dolaylı olarak başvuruyor. Döngüdeki hücreler 0 olarak hesaplanır; sonuçlar yanlış "
                "olabilir.")

    # --- Düzen menüsü: Bul / Değiştir / Git (Faz 5 / 5b) ---
    def bul_ac(self, degistir: bool = False):
        from .bul_penceresi import BulPenceresi
        if self.bul_penceresi is None:
            self.bul_penceresi = BulPenceresi(self)
        self.bul_penceresi.ac(degistir)

    def sonrakini_bul(self, ters: bool = False):
        """Shift+F4 / Ctrl+Shift+F4: pencere kapalıyken de son arananı bulur."""
        if self.bul_penceresi is None or not self.bul_penceresi.bul_metni.text():
            self.bul_ac(False)
            return
        self.bul_penceresi.sonrakini_bul(ters)

    # --- Veri menüsü: Sırala (Faz 5 / 5c) ---
    def _siralama_uyarisi(self) -> Optional[bool]:
        """Excel "Sıralama Uyarısı": True = seçimi genişlet, False = geçerli seçimle devam, None = vazgeç."""
        kutu = QMessageBox(self)
        kutu.setWindowTitle("Sıralama Uyarısı")
        kutu.setIcon(QMessageBox.Warning)
        kutu.setText("Seçimin yanında da veri bulundu. Bu veriler seçime dahil edilmediği için "
                     "sıralanmayacak. Ne yapmak istersiniz?")
        genislet = kutu.addButton("Seçimi genişlet", QMessageBox.AcceptRole)
        devam = kutu.addButton("Geçerli seçimle devam et", QMessageBox.ActionRole)
        kutu.addButton("İptal", QMessageBox.RejectRole)
        kutu.setDefaultButton(genislet)
        kutu.exec()
        tik = kutu.clickedButton()
        return True if tik is genislet else False if tik is devam else None

    def _siralama_alani(self, genislet=None):
        """Sıralanacak alan: (veri aralığı başlık dahil, başlık var mı, anahtar sütunu) ya da None.
        Tek hücre seçiliyse etkin hücrenin bitişik bölgesi; tek sütun seçimi yanında veri varsa
        Excel uyarısı sorulur (`genislet` None ise sorulur; True/False ise sorulmaz)."""
        from ..model.adres import Aralik, bitisik_bolge
        from ..model.sirala import baslik_tahmin, veri_kutusu
        g = self.izgara()
        sec = g.secimler
        if len(sec) > 1:
            QMessageBox.warning(self, APP_NAME, "Bu komut çoklu seçimde kullanılamaz.")
            return None
        ar = sec[0]
        tek = ar.ilk_satir == ar.son_satir and ar.ilk_sutun == ar.son_sutun
        if tek:
            ar = bitisik_bolge(g.sayfa, *g.aktif)
        else:
            ar = veri_kutusu(g.sayfa, ar) or ar
            bolge = bitisik_bolge(g.sayfa, *g.aktif)
            disari = (bolge.ilk_sutun < ar.ilk_sutun or bolge.son_sutun > ar.son_sutun
                      or bolge.ilk_satir < ar.ilk_satir or bolge.son_satir > ar.son_satir)
            if ar.ilk_sutun == ar.son_sutun and disari:
                if genislet is None:
                    genislet = self._siralama_uyarisi()
                    if genislet is None:
                        return None
                if genislet:
                    ar = bolge
        return ar, baslik_tahmin(g.sayfa, ar), g.aktif[1]

    def _siralama_uygula(self, aralik, anahtarlar, baslik, buyuk_kucuk=False, yon="satir") -> bool:
        from ..model.adres import Aralik
        from ..model.komutlar import Sirala
        from ..model.sirala import siralama_plani
        g = self.izgara()
        try:
            plan = siralama_plani(g.sayfa, aralik, anahtarlar, baslik=baslik, buyuk_kucuk=buyuk_kucuk, yon=yon)
        except ValueError as e:
            QMessageBox.warning(self, APP_NAME, str(e))
            return False
        if not plan:
            return False
        if yon == "satir":
            veri = Aralik(aralik.ilk_satir + (1 if baslik else 0), aralik.ilk_sutun,
                          aralik.son_satir, aralik.son_sutun)
        else:
            veri = Aralik(aralik.ilk_satir, aralik.ilk_sutun + (1 if baslik else 0),
                          aralik.son_satir, aralik.son_sutun)
        self.yigin.calistir(Sirala(g.sayfa, veri, plan, yon))
        g._guncelle()
        return True

    def sirala_hizli(self, artan: bool, genislet=None) -> bool:
        """A→Z / Z→A: anahtar etkin hücrenin sütunu; başlık satırı tahmin edilir."""
        from ..model.sirala import SiralamaAnahtari
        alan = self._siralama_alani(genislet)
        if alan is None:
            return False
        aralik, baslik, sutun = alan
        if not aralik.ilk_sutun <= sutun <= aralik.son_sutun:
            sutun = aralik.ilk_sutun
        return self._siralama_uygula(aralik, [SiralamaAnahtari(sutun, artan)], baslik)

    def sirala_ozel(self, sonuc=None) -> bool:
        """Özel Sıralama penceresi. `sonuc`: testler için pencereyi atlayan (anahtarlar, başlık, büyük/küçük,
        yön) demeti."""
        from .sirala_penceresi import SiralaPenceresi
        alan = self._siralama_alani(True)
        if alan is None:
            return False
        aralik, baslik, sutun = alan
        if sonuc is None:
            pen = SiralaPenceresi(self.izgara().sayfa, aralik, sutun, self, baslik)
            if pen.exec() != QDialog.Accepted:
                return False
            sonuc = (pen.anahtarlar(), pen.baslik(), pen.buyuk_kucuk(), pen.yon())
        anahtarlar, baslik, bk, yon = sonuc
        return self._siralama_uygula(aralik, anahtarlar, baslik, bk, yon)

    # ------------------------------------------------------------------ koşullu biçim (5h)
    def kosullu_kural_ac(self, tur: str = "hucre_degeri", islec=None, yuzde: bool = False,
                         tur_sabit: bool = True, sonuc=None) -> bool:
        """Hızlı kural ya da Yeni Kural penceresi; Tamam kuralı seçime en yüksek öncelikle ekler. `sonuc`: testler
        için pencereyi atlayan `KosulluKural` (formüller etkin hücreye göre yazılmış sayılır)."""
        from .kosullu_pencereleri import KuralPenceresi
        g = self.izgara()
        if sonuc is None:
            pen = KuralPenceresi(self.kitap, self, tur=tur, islec=islec, tur_sabit=tur_sabit)
            if yuzde:
                pen.yuzde.setChecked(True)
            if pen.exec() != QDialog.Accepted:
                return False
            sonuc = pen.kural()
        return g.kosullu_kural_ekle(sonuc)

    def kosullu_hazir(self, tur: str, ad: str) -> bool:
        """Veri çubuğu (`ad`: mavi… ya da `duz_mavi`…) ya da renk ölçeği (`ad`: RENK_OLCEKLERI anahtarı) doğrudan eklenir."""
        from ..model.kosullu import KosulluKural, RENK_OLCEKLERI, VERI_CUBUGU_RENKLERI
        if tur == "veri_cubugu":
            duz = ad.startswith("duz_")
            kural = KosulluKural((), tur="veri_cubugu", bicim=None, gradyan=not duz,
                                 renk=VERI_CUBUGU_RENKLERI[ad[4:] if duz else ad])
        else:
            kural = KosulluKural((), tur="renk_olcegi", bicim=None, noktalar=RENK_OLCEKLERI[ad])
        return self.izgara().kosullu_kural_ekle(kural)

    def kosullu_yonet(self, sonuc=None) -> bool:
        """Kuralları Yönet. `sonuc`: testler için pencereyi atlayan yeni TAM kural listesi."""
        from .kosullu_pencereleri import KuralYoneticisi
        g = self.izgara()
        if sonuc is None:
            pen = KuralYoneticisi(self.kitap, g.sayfa, g.secimler, g.aktif, self)
            if pen.exec() != QDialog.Accepted:
                return False
            sonuc = pen.liste()
        return g.kosullu_listesi_yaz(sonuc)

    def kosullu_temizle(self, tum_sayfa: bool = False) -> bool:
        return self.izgara().kosullu_temizle(tum_sayfa)

    # ------------------------------------------------------------------ veri doğrulama (5g)
    def _dogrulama_karisik_onayi(self) -> bool:
        c = QMessageBox.question(
            self, APP_NAME,
            "Seçim, veri doğrulama ayarları olmayan ya da farklı olan hücreler içeriyor. "
            "Doğrulama ayarlarını bu hücrelere de uygulamak istiyor musunuz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        return c == QMessageBox.Yes

    def _dogrulama_kapsami(self, g):
        """(etkin hücrenin kuralı, seçim farklı/kuralsız hücreler içeriyor mu). Seçimde hiç kural yoksa karışık
        sayılmaz; kural varsa ve seçimin tamamı etkin hücrenin kuralıyla kaplı değilse karışıktır."""
        from ..model.adres import aralik_cikar
        mevcut = g.sayfa.dogrulama(*g.aktif)
        kesen = [dv for dv in g.sayfa.dogrulamalar
                 if any(not (a.son_satir < s.ilk_satir or a.ilk_satir > s.son_satir
                             or a.son_sutun < s.ilk_sutun or a.ilk_sutun > s.son_sutun)
                        for a in dv.araliklar for s in g.secimler)]
        if not kesen:
            return mevcut, False
        if any(dv is not mevcut for dv in kesen):
            return mevcut, True
        kalan = list(g.secimler)
        for a in mevcut.araliklar:
            kalan = [p for k in kalan for p in aralik_cikar(k, a)]
        return mevcut, bool(kalan)

    def dogrulama_ac(self, sonuc=None) -> bool:
        """Veri ▸ Veri Doğrulama…: etkin hücrenin kuralıyla açılır; Tamam seçimin tüm aralıklarına uygular.
        Seçim farklı/kuralsız hücreler içeriyorsa önce Excel gibi sorulur. `sonuc`: testler için pencereyi atlayan
        `Dogrulama` (ya da None = temizle); formüller etkin hücreye göre yazılmış sayılır."""
        from dataclasses import replace
        from .dogrulama_penceresi import DogrulamaPenceresi
        from ..formul.kaydir import kopyala
        g = self.izgara()
        mevcut, karisik = self._dogrulama_kapsami(g)
        if karisik and not self._dogrulama_karisik_onayi():
            return False
        if sonuc is None:
            pen = DogrulamaPenceresi(self.kitap, mevcut, self)
            if pen.exec() != QDialog.Accepted:
                return False
            dv = pen.sonuc()
        else:
            dv = None if sonuc == "temizle" else sonuc
        if dv is not None:
            # formüller etkin hücreye göre yazıldı; kural çapası = ilk aralığın sol üstü
            cr, cc = g.secimler[0].ilk_satir, g.secimler[0].ilk_sutun
            fr, fc = cr - g.aktif[0], cc - g.aktif[1]
            if (fr, fc) != (0, 0):
                kay = lambda f: kopyala(f, fr, fc) if f is not None and f.startswith("=") else f
                dv = replace(dv, formul1=kay(dv.formul1), formul2=kay(dv.formul2))
        return g.dogrulama_uygula(dv)

    # ------------------------------------------------------------------ filtre (5f)
    def filtre_ac_kapat(self) -> bool:
        """Ctrl+Shift+L: sayfada filtre varsa kaldırır; yoksa seçimin (tek hücreyse bitişik bölgenin)
        başlık satırına filtre koyar."""
        from ..model.adres import bitisik_bolge
        from ..model.filtre import Filtre
        g = self.izgara()
        if g.sayfa.filtre is not None:
            return self._filtre_uygula(None)
        ar = g.secim
        if ar.ilk_satir == ar.son_satir and ar.ilk_sutun == ar.son_sutun:
            ar = bitisik_bolge(g.sayfa, *g.aktif)
        if g.sayfa.kullanilan_aralik() is None:
            return False
        return self._filtre_uygula(Filtre(ar), bildir=False)

    def filtre_temizle(self) -> bool:
        """Tüm sütun koşullarını kaldırır; filtre düğmeleri kalır, gizli satırlar açılır."""
        from ..model.filtre import Filtre
        f = self.izgara().sayfa.filtre
        if f is None or not f.kosullar:
            return False
        return self._filtre_uygula(Filtre(f.aralik, {}), genislet=False, bildir=False)

    def filtre_yeniden_uygula(self) -> bool:
        """Ctrl+Alt+L: koşullar değişen veriye göre yeniden uygulanır (aralık alttaki yeni satırlara uzar)."""
        f = self.izgara().sayfa.filtre
        return f is not None and self._filtre_uygula(f)

    def _filtre_uygula(self, yeni, genislet: bool = True, bildir: bool = True) -> bool:
        from ..model.filtre import Filtre, aralik_genislet, veri_satirlari
        from ..model.komutlar import FiltreDegis
        g = self.izgara()
        if yeni is not None and genislet:
            yeni = Filtre(aralik_genislet(g.sayfa, yeni.aralik), yeni.kosullar)
        if yeni == g.sayfa.filtre and not (yeni is not None and yeni.kosullar):
            return False
        kmt = FiltreDegis(g.sayfa, yeni)
        self.yigin.calistir(kmt)
        g._guncelle(pano_iptal=False)
        self._eylem_durumlari()
        if bildir and yeni is not None and yeni.kosullar:
            n = len(veri_satirlari(yeni))
            self.statusBar().showMessage(f"{n} kayıttan {n - kmt.gizlenen} kayıt bulundu", 6000)
        return True

    def filtre_paneli_ac(self, sutun: int):
        from .filtre_paneli import FiltrePaneli
        g = self.izgara()
        f = g.sayfa.filtre
        if f is None:
            return None
        from ..model.filtre import Filtre, aralik_genislet
        genis = Filtre(aralik_genislet(g.sayfa, f.aralik), f.kosullar)     # liste yeni satırları da görsün
        pan = FiltrePaneli(g.sayfa, genis, sutun, self)
        pan.kosulSecildi.connect(lambda k, s=sutun: self.filtre_kosulu_uygula(s, k))
        pan.sirala.connect(lambda artan, s=sutun: self._filtre_sirala(s, artan))
        d = g._filtre_dugmesi_dikdortgeni(sutun)
        if d is not None:
            pan.move(g.viewport().mapToGlobal(d.bottomLeft()))
        self._filtre_paneli = pan
        pan.show()
        return pan

    def filtre_kosulu_uygula(self, sutun: int, kosul) -> bool:
        """`sutun`un koşulunu değiştirir (None = temizle); diğer sütunların koşulları korunur."""
        from ..model.filtre import Filtre
        f = self.izgara().sayfa.filtre
        if f is None:
            return False
        kosullar = dict(f.kosullar)
        if kosul is None:
            kosullar.pop(sutun, None)
        else:
            kosullar[sutun] = kosul
        return self._filtre_uygula(Filtre(f.aralik, kosullar))

    def _filtre_sirala(self, sutun: int, artan: bool):
        """Panelden A→Z / Z→A: filtre aralığının veri satırları bu sütuna göre sıralanır (başlık sabit)."""
        from ..model.sirala import SiralamaAnahtari
        g = self.izgara()
        f = g.sayfa.filtre
        if f is not None:
            self._siralama_uygula(f.aralik, [SiralamaAnahtari(sutun, artan)], True)

    def git_ac(self):
        pen = GitPenceresi(self, [t.ad for t in gorunur_adlar(self.kitap, self.izgara().sayfa)])
        if pen.exec() == QDialog.Accepted and pen.metin():
            self._adrese_git(pen.metin())

    def _ad_kutusundan_git(self):
        self._adrese_git(self.ad_kutusu.text(), tanimla=True)

    def _ad_secildi(self, metin: str):
        self.ad_kutusu.setText(metin)
        self._adrese_git(metin, tanimla=True)

    def _ad_listesini_yenile(self):
        kitap = self.kitap
        self._ad_model.setStringList(sorted({t.ad for t in gorunur_adlar(kitap)}, key=str.casefold))

    def _adrese_git(self, metin: str, tanimla: bool = False):
        """Adres/aralık ya da tanımlı ad yazılan yere gider. `tanimla` (Ad Kutusu): ad yoksa geçerli bir
        adsa seçim bu adla tanımlanır (kitap kapsamı, Excel gibi)."""
        g = self.izgara()
        metin = metin.strip()
        try:
            ar = aralik_coz(metin)
        except AdresHatasi:
            self._ada_git(metin, tanimla)
            return
        tam = ar.son_satir - ar.ilk_satir > 1000 or ar.son_sutun - ar.ilk_sutun > 100
        g.sec((ar.ilk_satir, ar.ilk_sutun), (ar.son_satir, ar.son_sutun), kaydir=not tam)
        if tam:
            g._gorunur_yap((ar.ilk_satir, ar.ilk_sutun))
        g.setFocus()
        self._arayuzu_guncelle()

    def _ada_git(self, ad: str, tanimla: bool):
        g = self.izgara()
        tanim = self.kitap.ad_bul(ad, g.sayfa.kimlik) if ad else None
        if tanim is not None:
            hedef = hedef_aralik(self.kitap, tanim, g.sayfa)
            if hedef is None:
                QMessageBox.warning(self, APP_NAME, "Bu ad bir hücre aralığına başvurmuyor.")
            else:
                sayfa, ar = hedef
                if sayfa is not g.sayfa and sayfa in self.kitap.sayfalar:
                    self.sekmeler.setCurrentIndex(self.kitap.sayfalar.index(sayfa))
                    g = self.izgara()
                g.sec((ar.ilk_satir, ar.ilk_sutun), (ar.son_satir, ar.son_sutun))
        elif not tanimla:
            QMessageBox.warning(self, APP_NAME, "Başvuru geçerli değil.")
        else:
            try:
                ad_dogrula(ad)
            except AdHatasi as e:
                QMessageBox.warning(self, APP_NAME, str(e))
            else:
                sec = g.secim
                try:
                    formul = basvurur_saklanan(self.kitap, aralik_basvurusu(g.sayfa, sec), g.sayfa)
                except Exception:
                    formul = None
                if formul is not None:
                    self._ad_uygula(None, TanimliAd(ad, formul))
        self._arayuzu_guncelle()
        self.izgara().setFocus()

    def ad_tanimla_ac(self, duzenlenen: Optional[TanimliAd] = None) -> bool:
        """Ad Tanımla / Ad Düzenle penceresi; Tamam'da geri alınabilir `AdDegis` çalışır."""
        g = self.izgara()
        pen = AdTanimlaPenceresi(self.kitap, g.sayfa, g.secim, duzenlenen, self)
        if pen.exec() != QDialog.Accepted or pen.tanim is None:
            return False
        return self._ad_uygula(pen.eski_anahtar, pen.tanim)

    def _ad_uygula(self, eski_anahtar, tanim) -> bool:
        try:
            self.yigin.calistir(AdDegis(self.kitap, eski_anahtar, tanim))
        except AdHatasi as e:
            QMessageBox.warning(self, APP_NAME, str(e))
            return False
        return True

    def ad_sil(self, tanim: TanimliAd) -> None:
        self.yigin.calistir(AdDegis(self.kitap, tanim.anahtar(), None))

    def ad_yoneticisi_ac(self) -> None:
        AdYoneticisi(self).exec()

    def _formul_odak(self):
        """Formül çubuğuna girilince ızgara başvuru işaretlemeyi buraya yönlendirir (K7)."""
        g = self.izgara()
        g.dis_duzenleyici = self.formul
        self.formul.isaret_denetimi = g._isaret_modu

    def _formul_duzenlendi(self, _metin: str):
        g = self.izgara()
        g.dis_duzenleyici = self.formul
        self.formul.isaret_denetimi = g._isaret_modu
        g._metin_degisti()

    def _formul_isaret_ok(self, dr: int, dc: int, shift: bool):
        self.izgara()._isaret_ok(dr, dc, shift)

    def _formul_isareti_kapat(self):
        for g in self._izgaralar.values():
            etkindi = g.dis_duzenleyici is not None or g._isaret is not None or g._isaret_yaziyor
            g.dis_duzenleyici = None
            g.isaret_sifirla()
            if etkindi:          # her seçim değişiminde çağrılır: boşuna tüm ızgarayı yeniden çizme
                g.viewport().update()

    def _formul_onayla(self, metin: str):
        if self._uzak is not None:
            kaynak, (r, c) = self._uzak["izgara"], self._uzak["hucre"]
            if not kaynak.hucre_gir(r, c, metin):
                return                              # formül hatalı: formül çubuğunda kalınır
            self._uzak_bitir()
            self._formul_isareti_kapat()
            kaynak.sec((r, c))
            kaynak.setFocus()
            kaynak.sec((r + 1, c))
            return
        g = self.izgara()
        if not g.hucre_gir(*g.aktif, metin):
            return                                  # formül hatalı: formül çubuğunda kalınır
        self._formul_isareti_kapat()
        g.setFocus()
        g.sec((g.aktif[0] + 1, g.aktif[1]))

    def _formul_vazgec(self):
        if self._uzak is not None:
            self._uzak_bitir()
        g = self.izgara()
        self._formul_isareti_kapat()
        self.formul.setText(g.aktif_duzenleme_metni())
        g.setFocus()

    def _duzenleme_aynala(self, metin: str):
        if self.sender() is self.izgara() and self.formul.text() != metin:
            self.formul.setText(metin)

    # ------------------------------------------------------------------ durum çubuğu
    def _mod_degisti(self, mod: str):
        self._mod = mod
        self.mod_etiketi.setText(mod)
        if mod == "Hazır":
            self._arayuzu_guncelle()

    OZET_ERTELEME_ALANI = 5000       # bundan büyük seçimde özet zamanlayıcıyla ertelenir

    def _ozet_planla(self):
        g = self.izgara()
        alan = sum((a.son_satir - a.ilk_satir + 1) * (a.son_sutun - a.ilk_sutun + 1)
                   for a in g.secimler)
        if alan <= self.OZET_ERTELEME_ALANI:
            self._ozet_zamanlayici.stop()
            self._ozet_guncelle()
        else:
            self._ozet_zamanlayici.start(50)

    def _ozet_guncelle(self):
        """Seçimde Ortalama · Sayım · Toplam (Excel gibi; yalnızca dolu hücreler gezilir)."""
        g = self.izgara()
        sec = g.secim
        if not g._ekler and (sec.ilk_satir, sec.ilk_sutun) == (sec.son_satir, sec.son_sutun):
            self.ozet_etiketi.setText("")
            return
        sayilar, dolu = [], 0
        aralik_listesi = g.secimler
        sonuc_al = g.sayfa.sonuc
        gorulen = set() if len(aralik_listesi) > 1 else None   # üst üste binen aralıklarda hücre bir kez sayılır
        for a in aralik_listesi:
            for r, c, h in g.sayfa.aralikta(a):
                if g.filtreyle_gizli(r):
                    continue                       # Excel: filtreyle gizlenen satırlar özete girmez
                if gorulen is not None:
                    if (r, c) in gorulen:
                        continue
                    gorulen.add((r, c))
                dolu += 1
                v = h.deger if h.formul is None else sonuc_al(r, c)
                if isinstance(v, float):
                    sayilar.append(v)
        if not sayilar:
            self.ozet_etiketi.setText(f"Sayım: {dolu}  " if dolu else "")
            return
        toplam = sum(sayilar)
        self.ozet_etiketi.setText(
            f"Ortalama: {goster(toplam / len(sayilar))}    Sayım: {dolu}    "
            f"Toplam: {goster(toplam)}    ")

    # ------------------------------------------------------------------ yakınlaştırma
    def _kaydirici_degisti(self, v: int):
        self.izgara().yakinlastir(v / 100)

    def _yakinlastirma_degisti(self, oran: float):
        if self.sender() is not self.izgara():
            return
        self.yakin_etiketi.setText(f"{round(oran * 100)}%")
        self.yakin_kaydirici.blockSignals(True)
        self.yakin_kaydirici.setValue(round(oran * 100))
        self.yakin_kaydirici.blockSignals(False)
