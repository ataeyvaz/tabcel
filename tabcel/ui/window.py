"""Ana pencere: yeşil başlık şeridi, ad kutusu + formül çubuğu, ızgara, sayfa sekmeleri,
durum çubuğu (mod, Ortalama · Sayım · Toplam, yakınlaştırma).

Her sayfanın kendi `Izgara`'sı vardır (seçim ve kaydırma konumu sayfada kalır); geri al
yığını çalışma kitabı genelinde ortaktır.
"""
from typing import Dict, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import (
    QColorDialog, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox,
    QSlider, QStackedWidget, QTabBar, QToolButton, QVBoxLayout, QWidget,
)

from .. import APP_NAME
from ..model.adres import AdresHatasi, aralik_coz, hucre_yaz
from ..formul import isaretleme
from .renkli import renkli_ciz
from ..formul.ceviri import hucre_metni
from ..formul.motor import Hesaplayici
from ..model.komutlar import (
    GeriAlYigini, SayfaEkle, SayfaSil, SayfaTasi, SayfaYenidenAdlandir,
)
from ..model.komutlar import ana_sayfa
from ..model.olay import Olay
from ..model.sayfa import CalismaKitabi, Sayfa
from . import theme
from .bicim_cubugu import BicimCubugu
from .dosya_islemleri import DosyaIslemleri
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


class Pencere(DosyaIslemleri, QMainWindow):
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
        self._mod = "Hazır"
        self.setStyleSheet(theme.stylesheet())
        self._kur()
        self._dosya_kur()
        self._sekmeleri_esitle(self.kitap.sayfalar[0])
        self.kitap.dinle(self._kitap_olayi)           # sayfa ekle/sil/ad/taşı + geri al/yinele buradan yansır
        self._baslik_guncelle()
        self.resize(1100, 700)

    # ------------------------------------------------------------------ kurulum
    def _kur(self):
        merkez = QWidget()
        merkez.setObjectName("central")
        dikey = QVBoxLayout(merkez)
        dikey.setContentsMargins(0, 0, 0, 0)
        dikey.setSpacing(0)
        self.setCentralWidget(merkez)

        # başlık şeridi
        baslik = QWidget()
        baslik.setObjectName("header")
        h = QHBoxLayout(baslik)
        h.setContentsMargins(8, 6, 8, 6)
        self.dosya_dugmesi = QToolButton()
        self.dosya_dugmesi.setObjectName("fileButton")
        self.dosya_dugmesi.setText("Dosya")
        self.dosya_dugmesi.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self.dosya_dugmesi)
        self._dosya_menusu_doldur(menu)
        self.dosya_dugmesi.setMenu(menu)
        self.gorunum_dugmesi = QToolButton()
        self.gorunum_dugmesi.setObjectName("fileButton")
        self.gorunum_dugmesi.setText("Görünüm")
        self.gorunum_dugmesi.setPopupMode(QToolButton.InstantPopup)
        gm = QMenu(self.gorunum_dugmesi)
        self.gorunum_eylemleri = {}
        for anahtar, metin in (("bolme", "Bölmeleri Dondur"), ("ust_satir", "Üst Satırı Dondur"),
                               ("ilk_sutun", "İlk Sütunu Dondur"), ("coz", "Bölmelerin Dondurmasını Kaldır")):
            self.gorunum_eylemleri[anahtar] = gm.addAction(
                metin, lambda t=anahtar: self.izgara().dondur_ayarla(t))
        gm.addSeparator()
        self.kilavuz_eylemi = gm.addAction("Kılavuz Çizgileri")
        self.kilavuz_eylemi.setCheckable(True)
        self.kilavuz_eylemi.setChecked(True)
        self.kilavuz_eylemi.toggled.connect(lambda v: self.izgara().kilavuz_goster(v))
        gm.aboutToShow.connect(self._gorunum_menusu_hazirla)
        self.gorunum_dugmesi.setMenu(gm)
        self.duzen_dugmesi, self.duzen_eylemleri = self._menu_iskeleti("Düzen", (
            ("bul", "Bul…"), ("degistir", "Değiştir…"), ("git", "Git…")))
        self.veri_dugmesi, self.veri_eylemleri = self._menu_iskeleti("Veri", (
            ("artan", "Artan Sırala"), ("azalan", "Azalan Sırala"), ("ozel_sirala", "Özel Sıralama…"),
            None, ("filtre", "Filtre"), ("filtre_temizle", "Filtreyi Temizle"),
            ("filtre_yeniden", "Yeniden Uygula"),
            None, ("dogrulama", "Veri Doğrulama…"),
            None, ("ad_tanimla", "Ad Tanımla…"), ("ad_yoneticisi", "Ad Yöneticisi")))
        self.geri_dugmesi = QToolButton()
        self.geri_dugmesi.setText("Geri Al")
        self.geri_dugmesi.setToolTip("Geri Al (Ctrl+Z)")
        self.geri_dugmesi.clicked.connect(lambda: self.izgara().geri_al())
        self.yinele_dugmesi = QToolButton()
        self.yinele_dugmesi.setText("Yinele")
        self.yinele_dugmesi.setToolTip("Yinele (Ctrl+Y)")
        self.yinele_dugmesi.clicked.connect(lambda: self.izgara().yinele())
        self.belge_etiketi = QLabel()
        self.belge_etiketi.setObjectName("docTitle")
        h.addWidget(self.dosya_dugmesi)
        h.addWidget(self.gorunum_dugmesi)
        h.addWidget(self.duzen_dugmesi)
        h.addWidget(self.veri_dugmesi)
        h.addWidget(self.geri_dugmesi)
        h.addWidget(self.yinele_dugmesi)
        h.addStretch(1)
        h.addWidget(self.belge_etiketi)
        h.addStretch(1)
        dikey.addWidget(baslik)
        self.bilgi_cubugu = self._bilgi_cubugu_olustur()      # açılan dosyada korunamayan öğe uyarısı
        dikey.addWidget(self.bilgi_cubugu)

        # biçim araç çubuğu (3d)
        self.bicim_cubugu = BicimCubugu(self.izgara)
        dikey.addWidget(self.bicim_cubugu)

        # ad kutusu + formül çubuğu
        cubuk = QWidget()
        cubuk.setObjectName("formulaBar")
        f = QHBoxLayout(cubuk)
        f.setContentsMargins(6, 4, 6, 4)
        self.ad_kutusu = QLineEdit()
        self.ad_kutusu.setFixedWidth(110)
        self.ad_kutusu.setToolTip("Ad Kutusu: hücre/aralık adresi yazıp Enter'a basın (ör. B7 veya A1:C5)")
        self.ad_kutusu.returnPressed.connect(self._ad_kutusundan_git)
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
        self.izgara_yigini = QStackedWidget()
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
        sb.addPermanentWidget(self.ozet_etiketi)
        sb.addPermanentWidget(self.yakin_kaydirici)
        sb.addPermanentWidget(self.yakin_etiketi)

        self.bul_penceresi = None
        for eylem, kisayol, islev in (
                ("bul", "Ctrl+F", lambda: self.bul_ac(False)),
                ("degistir", "Ctrl+H", lambda: self.bul_ac(True)),
                ("git", "Ctrl+G", self.git_ac)):
            self.duzen_eylemleri[eylem].setEnabled(True)
            self.duzen_eylemleri[eylem].setText(self.duzen_eylemleri[eylem].text() + "	" + kisayol)   # yalnız gösterim; kısayol QShortcut'ta (çift tanım belirsizlik yaratır)
            self.duzen_eylemleri[eylem].triggered.connect(lambda _=False, f=islev: f())
            QShortcut(QKeySequence(kisayol), self, activated=islev)
        QShortcut(QKeySequence("F5"), self, activated=self.git_ac)
        QShortcut(QKeySequence("Shift+F4"), self, activated=lambda: self.sonrakini_bul(False))
        QShortcut(QKeySequence("Ctrl+Shift+F4"), self, activated=lambda: self.sonrakini_bul(True))
        QShortcut(QKeySequence("Ctrl+PgDown"), self, activated=lambda: self._sekme_git(1))
        QShortcut(QKeySequence("Ctrl+PgUp"), self, activated=lambda: self._sekme_git(-1))

    def _menu_iskeleti(self, baslik: str, ogeler):
        """Başlık şeridine menü düğmesi ekler; `ogeler`: (anahtar, metin) ya da None (ayırıcı). Eylemler
        başlangıçta kapalıdır: Faz 5'in ilgili alt işi (5b…5g) kendi eylemini bağlayıp açar.
        Döner: (düğme, {anahtar: eylem})."""
        dugme = QToolButton()
        dugme.setObjectName("fileButton")
        dugme.setText(baslik)
        dugme.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(dugme)
        eylemler = {}
        for oge in ogeler:
            if oge is None:
                menu.addSeparator()
                continue
            anahtar, metin = oge
            eylem = menu.addAction(metin)
            eylem.setEnabled(False)
            eylemler[anahtar] = eylem
        dugme.setMenu(menu)
        return dugme, eylemler

    def _gorunum_menusu_hazirla(self) -> None:
        """Menü açılırken: kılavuz onayı sayfaya uyar; dondurma açıkken 'Dondurmayı Kaldır' ad değişimi yok."""
        g = self.izgara()
        self.kilavuz_eylemi.blockSignals(True)
        self.kilavuz_eylemi.setChecked(g.sayfa.kilavuz)
        self.kilavuz_eylemi.blockSignals(False)
        self.gorunum_eylemleri["coz"].setEnabled(g.sayfa.dondur is not None)

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
        g.boyaciDegisti.connect(lambda _a: self._arayuzu_guncelle())
        g.yakinlastirmaDegisti.connect(self._yakinlastirma_degisti)
        g.uyari.connect(self._uyari)
        g.uzakOnay.connect(self._uzak_onayla)
        g.veri_kaybi_onayi = self._birlestirme_onayi
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
        if olay.tur == "sonuc":
            g = self._izgaralar.get(olay.sayfa)
            if g is not None and olay.sayfa is self._secili_sayfa:
                g._oto_gecersiz()              # metin sonucu değiştiyse kaydırılmış satır yüksekliği de
                g._sayfa_adimlari()
                g.viewport().update()          # başka hücreden tetiklenen yeniden hesaplama
            self._dongu_etiketi_guncelle()
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
            self.ad_kutusu.setText(hucre_yaz(*g.aktif))
        isaretleniyor = g.dis_duzenleyici is not None and g._isaret is not None
        if (not g.duzenleniyor() and not self.formul.hasFocus() and not isaretleniyor
                and self._uzak is None):
            self._formul_isareti_kapat()
            self.formul.setText(g.aktif_duzenleme_metni())
        self._ozet_planla()
        self._dongu_etiketi_guncelle()
        self.bicim_cubugu.guncelle()

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

    def git_ac(self):
        metin, tamam = QInputDialog.getText(self, "Git", "Başvuru:", text="")
        if tamam and metin.strip():
            self._adrese_git(metin)

    def _ad_kutusundan_git(self):
        self._adrese_git(self.ad_kutusu.text())

    def _adrese_git(self, metin: str):
        g = self.izgara()
        try:
            ar = aralik_coz(metin)
        except AdresHatasi:
            QMessageBox.warning(self, APP_NAME, "Başvuru geçerli değil.")
            self._arayuzu_guncelle()
            g.setFocus()
            return
        tam = ar.son_satir - ar.ilk_satir > 1000 or ar.son_sutun - ar.ilk_sutun > 100
        g.sec((ar.ilk_satir, ar.ilk_sutun), (ar.son_satir, ar.son_sutun), kaydir=not tam)
        if tam:
            g._gorunur_yap((ar.ilk_satir, ar.ilk_sutun))
        g.setFocus()
        self._arayuzu_guncelle()

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
