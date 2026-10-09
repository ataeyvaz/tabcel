"""Biçim araç çubuğu (Faz 3 / 3d): yazı tipi, boyut, K/İ/A, yazı ve dolgu rengi, kenarlık, hizalama,
metni kaydır, girinti, sayı biçimi. Mantık `model/bicim_islem.py`'de (Qt'siz); burası düğme kabuğu.

Çubuk etkin hücrenin biçimini yansıtır (`guncelle`); düğmeler etkin hücreye bakıp sonucu TÜM seçime
uygular (Excel gibi). Her düğme `izgara_al()` ile verilen o anki sayfanın ızgarasına yazar; biçim
tek geri al adımıdır.
"""
from typing import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFontComboBox, QFrame, QHBoxLayout, QMenu, QToolButton, QWidget,
)

from ..model import bicim_islem as bi
from ..model.sayi_bicimi import HAZIR
from ..model.stil import StilYama
from . import icons
from .bicim_penceresi import BicimPenceresi
from .widgets import RenkDugmesi

KENAR_METINLERI = (
    ("alt", "Alt Kenarlık"), ("ust", "Üst Kenarlık"), ("sol", "Sol Kenarlık"), ("sag", "Sağ Kenarlık"),
    (None, None),
    ("tum", "Tüm Kenarlıklar"), ("dis", "Dış Kenarlıklar"), ("kalin_dis", "Kalın Dış Kenarlık"),
    ("cift_alt", "Çift Alt Kenarlık"),
    (None, None),
    ("yok", "Kenarlık Yok"),
)


class _Ayirac(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.VLine)
        self.setStyleSheet("color: #d0d0d0;")
        self.setFixedHeight(20)


class BicimCubugu(QWidget):
    def __init__(self, izgara_al: Callable, parent=None):
        super().__init__(parent)
        self.setObjectName("formatBar")
        self._izgara_al = izgara_al
        self._guncelleniyor = False
        h = QHBoxLayout(self)
        h.setContentsMargins(6, 3, 6, 3)
        h.setSpacing(2)

        # yazı tipi + boyut
        self.yazi_tipi = QFontComboBox()
        self.yazi_tipi.setFixedWidth(150)
        self.yazi_tipi.setToolTip("Yazı Tipi")
        self.yazi_tipi.activated.connect(self._yazi_tipi_secildi)
        self.boyut = QComboBox()
        self.boyut.setEditable(True)
        self.boyut.setFixedWidth(56)
        self.boyut.setToolTip("Yazı Boyutu")
        self.boyut.addItems([str(b) for b in bi.BOYUTLAR])
        self.boyut.setInsertPolicy(QComboBox.NoInsert)
        self.boyut.activated.connect(lambda _i: self._boyut_girildi())
        self.boyut.lineEdit().editingFinished.connect(self._boyut_girildi)
        self.buyut = self._dugme("grow_font", "Yazı Tipini Büyüt", lambda: self._boyut_adim(+1))
        self.kucult = self._dugme("shrink_font", "Yazı Tipini Küçült", lambda: self._boyut_adim(-1))
        for w in (self.yazi_tipi, self.boyut, self.buyut, self.kucult):
            h.addWidget(w)
        h.addWidget(_Ayirac())

        # karakter biçimi
        self.kalin = self._dugme("bold", "Kalın (Ctrl+B)", lambda: self._degistir(bi.kalin_yamasi), True)
        self.italik = self._dugme("italic", "İtalik (Ctrl+I)", lambda: self._degistir(bi.italik_yamasi), True)
        self.altcizili = self._dugme("underline", "Altı Çizili (Ctrl+U)",
                                     lambda: self._degistir(bi.alti_cizili_yamasi), True)
        self.yazi_rengi = RenkDugmesi("font_color", "Yazı Rengi", "#FF0000", "Otomatik")
        self.yazi_rengi.renkSecildi.connect(self._yazi_rengi_secildi)
        self.dolgu = RenkDugmesi("fill_color", "Dolgu Rengi", "#FFFF00", "Dolgu Yok")
        self.dolgu.renkSecildi.connect(self._dolgu_secildi)
        self.kenarlik = QToolButton()
        self.kenarlik.setIcon(icons.icon("borders"))
        self.kenarlik.setToolTip("Kenarlıklar")
        self.kenarlik.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self.kenarlik)
        self.kenar_eylemleri = {}
        for anahtar, metin in KENAR_METINLERI:
            if anahtar is None:
                menu.addSeparator()
            else:
                self.kenar_eylemleri[anahtar] = menu.addAction(
                    metin, lambda a=anahtar: self.kenarlik_uygula(a))
        self.kenarlik.setMenu(menu)
        for w in (self.kalin, self.italik, self.altcizili, self.yazi_rengi, self.dolgu, self.kenarlik):
            h.addWidget(w)
        h.addWidget(_Ayirac())

        # hizalama
        self.dikey = {
            "ust": self._dugme("valign_top", "Üste Hizala", lambda: self._dikey("ust"), True),
            "orta": self._dugme("valign_middle", "Ortaya Hizala (Dikey)", lambda: self._dikey("orta"), True),
            "alt": self._dugme("valign_bottom", "Alta Hizala", lambda: self._dikey("alt"), True),
        }
        self.yatay = {
            "sol": self._dugme("align_left", "Sola Hizala", lambda: self._yatay("sol"), True),
            "orta": self._dugme("align_center", "Ortala", lambda: self._yatay("orta"), True),
            "sag": self._dugme("align_right", "Sağa Hizala", lambda: self._yatay("sag"), True),
        }
        self.kaydir = self._dugme("wrap", "Metni Kaydır", lambda: self._degistir(bi.kaydir_yamasi), True)
        self.girinti_azalt = self._dugme("outdent", "Girintiyi Azalt", lambda: self._girinti(-1))
        self.girinti_artir = self._dugme("indent", "Girintiyi Artır", lambda: self._girinti(+1))
        for w in (*self.dikey.values(), *self.yatay.values(), self.kaydir,
                  self.girinti_azalt, self.girinti_artir):
            h.addWidget(w)
        h.addWidget(_Ayirac())

        # sayı
        self.sayi_bicimi = QComboBox()
        self.sayi_bicimi.setFixedWidth(150)
        self.sayi_bicimi.setToolTip("Sayı Biçimi")
        self.sayi_bicimi.addItems(list(HAZIR))
        self.sayi_bicimi.addItem("Özel")
        self.sayi_bicimi.activated.connect(self._sayi_bicimi_secildi)
        self.para = self._dugme("currency", "Para Birimi Biçimi (Ctrl+Shift+4)",
                                lambda: self._sayi_kodu(bi.PARA))
        self.yuzde = self._dugme("percent", "Yüzde Stili (Ctrl+Shift+5)", lambda: self._sayi_kodu(bi.YUZDE))
        self.binlik = self._dugme("thousands", "Binlik Ayracı (Ctrl+Shift+1)",
                                  lambda: self._sayi_kodu(bi.BINLIK))
        self.ondalik_artir = self._dugme("decimal_more", "Ondalık Basamak Artır", lambda: self._ondalik(+1))
        self.ondalik_azalt = self._dugme("decimal_less", "Ondalık Basamak Azalt", lambda: self._ondalik(-1))
        for w in (self.sayi_bicimi, self.para, self.yuzde, self.binlik, self.ondalik_artir,
                  self.ondalik_azalt):
            h.addWidget(w)
        self.pencere_dugmesi = self._dugme("dialog_launcher", "Hücreleri Biçimlendir (Ctrl+1)",
                                           lambda: self.penceresi_ac())
        h.addStretch(1)
        h.addWidget(self.pencere_dugmesi)

        # klavye kısayolları. Türkçe Excel'deki karşılıkları doğrulanana dek Sözcük'teki kararla aynı
        # (Ctrl+B/I/U; §8b-44). Gizlenen/kısa pencerede de çalışsın diye pencereye bağlı
        for tus, islem in (("Ctrl+B", bi.kalin_yamasi), ("Ctrl+I", bi.italik_yamasi),
                           ("Ctrl+U", bi.alti_cizili_yamasi), ("Ctrl+5", bi.ustu_cizili_yamasi)):
            QShortcut(QKeySequence(tus), self, activated=lambda f=islem: self._degistir(f),
                      context=Qt.WindowShortcut)
        QShortcut(QKeySequence("Ctrl+1"), self, activated=lambda: self.penceresi_ac(),
                  context=Qt.WindowShortcut)
        for tus, kod in (("Ctrl+Shift+4", bi.PARA), ("Ctrl+Shift+5", bi.YUZDE),
                         ("Ctrl+Shift+1", bi.BINLIK)):
            QShortcut(QKeySequence(tus), self, activated=lambda k=kod: self._sayi_kodu(k),
                      context=Qt.WindowShortcut)

    # ------------------------------------------------------------------ yapı taşları
    def _dugme(self, ikon: str, ipucu: str, islem: Callable, isaretli: bool = False) -> QToolButton:
        d = QToolButton()
        d.setIcon(icons.icon(ikon))
        d.setIconSize(QSize(20, 20))
        d.setToolTip(ipucu)
        d.setFocusPolicy(Qt.NoFocus)
        d.setCheckable(isaretli)
        d.clicked.connect(lambda _=False: islem())
        return d

    def _g(self):
        return self._izgara_al()

    def _etkin_stil(self):
        g = self._g()
        return g.sayfa.stil(*g.aktif)

    def _uygula(self, yama_ya_da_plan) -> None:
        g = self._g()
        g.bicim_uygula(yama_ya_da_plan)
        odak = QApplication.focusWidget()
        if odak is None or self.isAncestorOf(odak):     # düzenleme/formül çubuğundaki odak çalınmaz
            g.setFocus()
        self.guncelle()                  # işaretli düğmeler komutun gerçek sonucuna dönsün

    def _degistir(self, yama_uretici: Callable) -> None:
        self._uygula(yama_uretici(self._etkin_stil()))

    # ------------------------------------------------------------------ düğme işlemleri
    def _yazi_tipi_secildi(self, _i: int) -> None:
        self._uygula(StilYama(yazi_tipi=self.yazi_tipi.currentFont().family()))

    def _boyut_girildi(self) -> None:
        if self._guncelleniyor:
            return
        v = bi.boyut_coz(self.boyut.currentText())
        if v is None:                    # geçersiz: eski değere dön
            self.guncelle()
            return
        self._uygula(StilYama(boyut=v))

    def _boyut_adim(self, yon: int) -> None:
        self._uygula(StilYama(boyut=bi.sonraki_boyut(bi.etkin_boyut(self._etkin_stil()), yon)))

    def _yazi_rengi_secildi(self, renk) -> None:
        self._uygula(StilYama(yazi_rengi=renk.name() if renk else None))

    def _dolgu_secildi(self, renk) -> None:
        self._uygula(StilYama(dolgu=renk.name() if renk else None))

    def kenarlik_uygula(self, secenek: str) -> None:
        self._uygula(bi.kenarlik_plani(self._g().secimler, secenek))

    def _yatay(self, hiza: str) -> None:
        self._uygula(bi.yatay_yamasi(self._etkin_stil(), hiza))

    def _dikey(self, hiza: str) -> None:
        self._uygula(bi.dikey_yamasi(self._etkin_stil(), hiza))

    def _girinti(self, fark: int) -> None:
        yama = bi.girinti_yamasi(self._etkin_stil(), fark)
        if yama is not None:
            self._uygula(yama)

    def _sayi_kodu(self, kod: str) -> None:
        self._uygula(bi.sayi_bicimi_yamasi(kod))

    def _sayi_bicimi_secildi(self, _i: int) -> None:
        ad = self.sayi_bicimi.currentText()
        if ad in HAZIR:
            self._sayi_kodu(HAZIR[ad])
        else:
            self.guncelle()
            self.penceresi_ac(0)         # "Özel": kodu Hücreleri Biçimlendir'de yazılır

    def penceresi_ac(self, sekme: int = 0) -> bool:
        """Hücreleri Biçimlendir (Ctrl+1). Tamam'da yalnız değişen alanlar tüm seçime uygulanır."""
        g = self._g()
        r, c = g.aktif
        h = g.sayfa.hucre(r, c)
        deger = None
        if h is not None:
            deger = h.deger if h.formul is None else g.sayfa.sonuc(r, c)
        p = BicimPenceresi(self._etkin_stil(), deger, self.window(), sekme)
        if p.exec() != QDialog.Accepted:
            g.setFocus()
            self.guncelle()
            return False
        plan = p.plan(g.secimler)
        if plan:
            g.bicim_uygula(plan)
        g.setFocus()
        self.guncelle()
        return bool(plan)

    def _ondalik(self, fark: int) -> None:
        g = self._g()
        r, c = g.aktif
        h = g.sayfa.hucre(r, c)
        deger = None
        if h is not None:
            deger = h.deger if h.formul is None else g.sayfa.sonuc(r, c)
        yama = bi.ondalik_yamasi(self._etkin_stil(), fark, deger)
        if yama is not None:
            self._uygula(yama)

    # ------------------------------------------------------------------ durum
    def guncelle(self) -> None:
        """Düğme ve kutuları etkin hücrenin biçimine göre eşitler (sinyal yaymadan)."""
        if self._izgara_al() is None:
            return
        s = self._etkin_stil()
        self._guncelleniyor = True
        try:
            self.kalin.setChecked(s.kalin)
            self.italik.setChecked(s.italik)
            self.altcizili.setChecked(s.alti_cizili != "yok")
            self.kaydir.setChecked(s.kaydir)
            for ad, d in self.yatay.items():
                d.setChecked(s.yatay == ad)
            for ad, d in self.dikey.items():
                d.setChecked(s.dikey == ad)
            self.yazi_tipi.setCurrentFont(QFont(s.yazi_tipi or self.font().family()))
            self.boyut.setEditText(f"{bi.etkin_boyut(s):g}")
            self.sayi_bicimi.setCurrentText(bi.hazir_adi(s.sayi_bicimi))
        finally:
            self._guncelleniyor = False
