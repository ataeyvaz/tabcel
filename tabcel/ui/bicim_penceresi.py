"""Hücreleri Biçimlendir (Ctrl+1): Sayı, Hizalama, Yazı Tipi, Kenarlık, Dolgu (Faz 3 / 3e).

Pencere etkin hücrenin stiliyle açılır; Tamam'da yalnız KULLANICININ DEĞİŞTİRDİĞİ alanlar plan olarak
döner (çok hücreli seçimde dokunulmayan alanlar hücrelerin kendi değerinde kalır — Excel gibi).
Saklanan sayı kodu kanoniktir; Özel alanında Türkçe yazımla gösterilir/girilir (`yerele`/`kanonige`).
"""
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFontComboBox, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton, QSpinBox, QTabWidget,
    QVBoxLayout, QWidget,
)

from .. import APP_NAME
from ..model import bicim_islem as bi
from ..model import bicim_kodlari as bk
from ..model.sayi_bicimi import BicimHatasi, yerele
from ..model.stil import ALTI_CIZILI, KENAR_YONLERI, Stil, StilYama

YATAY_ADLARI = (("genel", "Genel"), ("sol", "Sola (Girinti)"), ("orta", "Ortala"), ("sag", "Sağa (Girinti)"),
                ("doldur", "Doldur"), ("iki_yana", "İki Yana Yasla"), ("secim_ortasi", "Seçimi Ortala"))
DIKEY_ADLARI = (("ust", "Üst"), ("orta", "Orta"), ("alt", "Alt"))
CIZGI_ADLARI = (("ince", "İnce"), ("orta", "Orta"), ("kalin", "Kalın"), ("kesikli", "Kesikli"),
                ("noktali", "Noktalı"), ("cift", "Çift"), ("sac", "Saç teli"))
ALTI_CIZILI_ADLARI = (("yok", "Yok"), ("tek", "Tek"), ("cift", "Çift"))
KENAR_ADLARI = (("ust", "Üst"), ("alt", "Alt"), ("sol", "Sol"), ("sag", "Sağ"))


class _RenkSecici(QWidget):
    """Renk düğmesi + "Yok/Otomatik" onay kutusu. `deger()`: '#RRGGBB' ya da None."""

    def __init__(self, yok_metni: str, baslangic: Optional[str], varsayilan: str):
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        self._renk = baslangic or varsayilan
        self.yok = QCheckBox(yok_metni)
        self.yok.setChecked(baslangic is None)
        self.dugme = QPushButton()
        self.dugme.setFixedWidth(60)
        self.dugme.clicked.connect(self._sec)
        h.addWidget(self.yok)
        h.addWidget(self.dugme)
        h.addStretch(1)
        self._boya()

    def _boya(self):
        self.dugme.setStyleSheet(f"QPushButton {{ background: {self._renk}; border: 1px solid #888; }}")

    def _sec(self):
        r = QColorDialog.getColor(QColor(self._renk), self, "Renk seç")
        if r.isValid():
            self.renk_ata(r.name())

    def renk_ata(self, renk: str) -> None:
        self._renk = renk.upper()
        self.yok.setChecked(False)
        self._boya()

    def deger(self) -> Optional[str]:
        return None if self.yok.isChecked() else self._renk.upper()


class BicimPenceresi(QDialog):
    def __init__(self, stil: Stil, deger=None, parent=None, sekme: int = 0):
        super().__init__(parent)
        self.setWindowTitle("Hücreleri Biçimlendir")
        self._ilk = stil
        self._deger = deger
        self._kod = stil.sayi_bicimi                  # kanonik, çalışma kopyası
        d = QVBoxLayout(self)
        self.sekmeler = QTabWidget()
        d.addWidget(self.sekmeler)
        self._sayi_sekmesi()
        self._hizalama_sekmesi()
        self._yazi_tipi_sekmesi()
        self._kenarlik_sekmesi()
        self._dolgu_sekmesi()
        self.sekmeler.setCurrentIndex(sekme)
        self.dugmeler = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.dugmeler.button(QDialogButtonBox.Ok).setText("Tamam")
        self.dugmeler.button(QDialogButtonBox.Cancel).setText("İptal")
        self.dugmeler.accepted.connect(self._tamam)
        self.dugmeler.rejected.connect(self.reject)
        d.addWidget(self.dugmeler)
        self.resize(540, 500)

    # ------------------------------------------------------------------ Sayı
    def _sayi_sekmesi(self):
        w = QWidget()
        h = QHBoxLayout(w)
        sol = QVBoxLayout()
        sol.addWidget(QLabel("Kategori:"))
        self.kategori = QListWidget()
        self.kategori.addItems(bk.KATEGORILER)
        self.kategori.setMaximumWidth(150)
        sol.addWidget(self.kategori)
        h.addLayout(sol)
        sag = QVBoxLayout()
        self.onizleme = QLabel()
        self.onizleme.setFrameShape(QLabel.Box)
        self.onizleme.setMinimumHeight(28)
        sag.addWidget(QLabel("Örnek:"))
        sag.addWidget(self.onizleme)
        form = QFormLayout()
        self.ondalik = QSpinBox()
        self.ondalik.setRange(0, 30)
        self.binlik = QCheckBox("1000 Ayracı (.) Kullan")
        self.sembol = QComboBox()
        self.sembol.addItems(bk.SEMBOLLER)
        self.tip = QListWidget()
        self.tip.setMaximumHeight(120)
        self.ozel = QLineEdit()
        form.addRow("Ondalık basamak:", self.ondalik)
        form.addRow("", self.binlik)
        form.addRow("Simge:", self.sembol)
        form.addRow("Tür:", self.tip)
        form.addRow("Biçim kodu:", self.ozel)
        self._form = form
        sag.addLayout(form)
        sag.addStretch(1)
        h.addLayout(sag, 1)
        self.sekmeler.addTab(w, "Sayı")

        c = bk.kategori_coz(self._kod)
        self._yukleniyor = True
        self.ondalik.setValue(c["ondalik"])
        self.binlik.setChecked(c["binlik"])
        self.sembol.setCurrentText(c["sembol"])
        self.kategori.setCurrentRow(bk.KATEGORILER.index(c["kategori"]))
        self._tip_doldur(c["tip"])
        self.ozel.setText(yerele(self._kod))
        self._yukleniyor = False
        self._kategori_gorunumu()
        self._onizle()
        self.kategori.currentRowChanged.connect(self._kategori_degisti)
        self.ondalik.valueChanged.connect(self._secenek_degisti)
        self.binlik.toggled.connect(self._secenek_degisti)
        self.sembol.currentTextChanged.connect(self._secenek_degisti)
        self.tip.currentRowChanged.connect(self._secenek_degisti)
        self.ozel.textEdited.connect(self._ozel_yazildi)

    def _kategori_adi(self) -> str:
        return bk.KATEGORILER[max(0, self.kategori.currentRow())]

    def _tip_doldur(self, secili: Optional[str] = None):
        liste = {"Tarih": bk.TARIH_TIPLERI, "Saat": bk.SAAT_TIPLERI,
                 "Kesir": bk.KESIR_TIPLERI}.get(self._kategori_adi(), ())
        self.tip.blockSignals(True)
        self.tip.clear()
        for kod in liste:
            ornek = bk.ORNEK["Tarih" if self._kategori_adi() == "Tarih" else "Saat"] \
                if self._kategori_adi() != "Kesir" else 0.3333
            self.tip.addItem(f"{bk.onizleme(kod, ornek)}   [{yerele(kod)}]")
        self.tip.setCurrentRow(liste.index(secili) if secili in liste else 0)
        self.tip.blockSignals(False)

    def _kategori_gorunumu(self):
        k = self._kategori_adi()
        goster = {
            self.ondalik: k in ("Sayı", "Para Birimi", "Muhasebe", "Yüzde", "Bilimsel"),
            self.binlik: k == "Sayı",
            self.sembol: k in ("Para Birimi", "Muhasebe"),
            self.tip: k in ("Tarih", "Saat", "Kesir"),
            self.ozel: True,
        }
        for w, g in goster.items():
            w.setVisible(g)
            e = self._form.labelForField(w)
            if e is not None:
                e.setVisible(g)
        self.binlik.setVisible(k == "Sayı")

    def _kategori_degisti(self, _i: int):
        if self._yukleniyor:
            return
        if self._kategori_adi() == "Özel":
            self._onizle()
            return
        self._tip_doldur()
        self._kategori_gorunumu()
        self._kod_kur()

    def _secenek_degisti(self, *_):
        if not self._yukleniyor:
            self._kod_kur()

    def _kod_kur(self):
        k = self._kategori_adi()
        if k == "Özel":
            return
        liste = {"Tarih": bk.TARIH_TIPLERI, "Saat": bk.SAAT_TIPLERI, "Kesir": bk.KESIR_TIPLERI}.get(k)
        tip = liste[max(0, self.tip.currentRow())] if liste else None
        self._kod = bk.kod_olustur(k, self.ondalik.value(), self.binlik.isChecked(),
                                   self.sembol.currentText(), tip)
        self.ozel.setText(yerele(self._kod))
        self._onizle()

    def _ozel_yazildi(self, metin: str):
        """Biçim kodu alanına yazıldı: kategori Özel'e geçer; kod Tamam'da doğrulanır."""
        self._yukleniyor = True
        self.kategori.setCurrentRow(bk.KATEGORILER.index("Özel"))
        self._yukleniyor = False
        self._kategori_gorunumu()
        try:
            self._kod = bk.ozel_kodu_coz(metin)
            self._onizle()
        except BicimHatasi:
            self.onizleme.setText("")

    def _onizle(self):
        d = self._deger
        if d is None or isinstance(d, bool):
            d = bk.ORNEK["Genel"]
        self.onizleme.setText(bk.onizleme(self._kod, d))

    # ------------------------------------------------------------------ Hizalama
    def _hizalama_sekmesi(self):
        w = QWidget()
        f = QFormLayout(w)
        s = self._ilk
        self.yatay = QComboBox()
        for _, ad in YATAY_ADLARI:
            self.yatay.addItem(ad)
        self.yatay.setCurrentIndex([k for k, _ in YATAY_ADLARI].index(s.yatay))
        self.dikey = QComboBox()
        for _, ad in DIKEY_ADLARI:
            self.dikey.addItem(ad)
        self.dikey.setCurrentIndex([k for k, _ in DIKEY_ADLARI].index(s.dikey))
        self.girinti = QSpinBox()
        self.girinti.setRange(0, 15)
        self.girinti.setValue(s.girinti)
        self.kaydir = QCheckBox("Metni Kaydır")
        self.kaydir.setChecked(s.kaydir)
        f.addRow("Yatay:", self.yatay)
        f.addRow("Girinti:", self.girinti)
        f.addRow("Dikey:", self.dikey)
        f.addRow("", self.kaydir)
        self.sekmeler.addTab(w, "Hizalama")

    # ------------------------------------------------------------------ Yazı tipi
    def _yazi_tipi_sekmesi(self):
        w = QWidget()
        f = QFormLayout(w)
        s = self._ilk
        self.yazi_tipi = QFontComboBox()
        self.yazi_tipi.setCurrentFont(QFont(s.yazi_tipi or self.font().family()))
        self._yazi_tipi_ilk = self.yazi_tipi.currentFont().family()
        self.boyut = QComboBox()
        self.boyut.setEditable(True)
        self.boyut.addItems([str(b) for b in bi.BOYUTLAR])
        self.boyut.setEditText(f"{bi.etkin_boyut(s):g}")
        self.kalin = QCheckBox("Kalın")
        self.kalin.setChecked(s.kalin)
        self.italik = QCheckBox("İtalik")
        self.italik.setChecked(s.italik)
        self.alti_cizili = QComboBox()
        for _, ad in ALTI_CIZILI_ADLARI:
            self.alti_cizili.addItem(ad)
        self.alti_cizili.setCurrentIndex(list(ALTI_CIZILI).index(s.alti_cizili))
        self.ustu_cizili = QCheckBox("Üstü Çizili")
        self.ustu_cizili.setChecked(s.ustu_cizili)
        self.yazi_rengi = _RenkSecici("Otomatik", s.yazi_rengi, "#FF0000")
        f.addRow("Yazı tipi:", self.yazi_tipi)
        f.addRow("Boyut:", self.boyut)
        f.addRow("", self.kalin)
        f.addRow("", self.italik)
        f.addRow("Altı çizili:", self.alti_cizili)
        f.addRow("", self.ustu_cizili)
        f.addRow("Renk:", self.yazi_rengi)
        self.sekmeler.addTab(w, "Yazı Tipi")

    # ------------------------------------------------------------------ Kenarlık
    def _kenarlik_sekmesi(self):
        w = QWidget()
        f = QFormLayout(w)
        s = self._ilk
        self.cizgi = QComboBox()
        for _, ad in CIZGI_ADLARI:
            self.cizgi.addItem(ad)
        self.kenar_rengi = _RenkSecici("Otomatik (siyah)", None, "#000000")
        self.kenar = {}
        for y, ad in KENAR_ADLARI:
            c = QCheckBox(f"{ad} kenarlık")
            c.setChecked(bool(getattr(s.kenar, y)))
            self.kenar[y] = c
        self._kenar_ilk = {y: bool(getattr(s.kenar, y)) for y in KENAR_YONLERI}
        self.ic = QCheckBox("İç çizgiler (seçimdeki tüm hücre kenarları)")
        self.ic.setTristate(False)
        self._ic_dokunuldu = False
        self.ic.clicked.connect(lambda _=False: setattr(self, "_ic_dokunuldu", True))
        pre = QHBoxLayout()
        self.on_ayar = {}
        for ad, anahtar in (("Yok", "yok"), ("Dış", "dis")):
            b = QPushButton(ad)
            b.clicked.connect(lambda _=False, a=anahtar: self.on_ayar_uygula(a))
            self.on_ayar[anahtar] = b
            pre.addWidget(b)
        pre.addStretch(1)
        f.addRow("Çizgi:", self.cizgi)
        f.addRow("Renk:", self.kenar_rengi)
        f.addRow("Hazır:", pre)
        for c in self.kenar.values():
            f.addRow("", c)
        f.addRow("", self.ic)
        self.sekmeler.addTab(w, "Kenarlık")

    def on_ayar_uygula(self, anahtar: str) -> None:
        """"Yok": tüm kenar ve iç çizgiler kalkar; "Dış": dört dış kenar açılır."""
        for c in self.kenar.values():
            c.setChecked(anahtar == "dis")
        if anahtar == "yok":
            self.ic.setChecked(False)
            self._ic_dokunuldu = True

    # ------------------------------------------------------------------ Dolgu
    def _dolgu_sekmesi(self):
        w = QWidget()
        f = QFormLayout(w)
        self.dolgu = _RenkSecici("Dolgu Yok", self._ilk.dolgu, "#FFFF00")
        f.addRow("Arka plan rengi:", self.dolgu)
        self.sekmeler.addTab(w, "Dolgu")

    # ------------------------------------------------------------------ sonuç
    def _tamam(self):
        if self._kategori_adi() == "Özel" or self.ozel.text().strip():
            try:
                self._kod = bk.ozel_kodu_coz(self.ozel.text()) if self._kategori_adi() == "Özel" \
                    else self._kod
            except BicimHatasi as e:
                QMessageBox.warning(self, APP_NAME, f"Girdiğiniz sayı biçimi geçerli değil: {e}")
                self.sekmeler.setCurrentIndex(0)
                return
        if bi.boyut_coz(self.boyut.currentText()) is None:
            QMessageBox.warning(self, APP_NAME, "Yazı boyutu 1 ile 409 arasında olmalı.")
            self.sekmeler.setCurrentIndex(2)
            return
        self.accept()

    def _kenar_cizgisi(self):
        ad = CIZGI_ADLARI[self.cizgi.currentIndex()][0]
        return (ad, self.kenar_rengi.deger() or "#000000")

    def yama(self) -> StilYama:
        """Kenarlık dışındaki değişen alanlar."""
        s, alan = self._ilk, {}
        if self._kod != s.sayi_bicimi:
            alan["sayi_bicimi"] = self._kod
        yatay = YATAY_ADLARI[self.yatay.currentIndex()][0]
        if yatay != s.yatay:
            alan["yatay"] = yatay
        dikey = DIKEY_ADLARI[self.dikey.currentIndex()][0]
        if dikey != s.dikey:
            alan["dikey"] = dikey
        if self.girinti.value() != s.girinti:
            alan["girinti"] = self.girinti.value()
        if self.kaydir.isChecked() != s.kaydir:
            alan["kaydir"] = self.kaydir.isChecked()
        fam = self.yazi_tipi.currentFont().family()
        if fam != self._yazi_tipi_ilk:
            alan["yazi_tipi"] = fam
        boyut = bi.boyut_coz(self.boyut.currentText())
        if boyut is not None and boyut != bi.etkin_boyut(s):
            alan["boyut"] = boyut
        if self.kalin.isChecked() != s.kalin:
            alan["kalin"] = self.kalin.isChecked()
        if self.italik.isChecked() != s.italik:
            alan["italik"] = self.italik.isChecked()
        alti = ALTI_CIZILI_ADLARI[self.alti_cizili.currentIndex()][0]
        if alti != s.alti_cizili:
            alan["alti_cizili"] = alti
        if self.ustu_cizili.isChecked() != s.ustu_cizili:
            alan["ustu_cizili"] = self.ustu_cizili.isChecked()
        if self.yazi_rengi.deger() != s.yazi_rengi:
            alan["yazi_rengi"] = self.yazi_rengi.deger()
        if self.dolgu.deger() != s.dolgu:
            alan["dolgu"] = self.dolgu.deger()
        return StilYama(**alan)

    def plan(self, araliklar) -> List:
        """Seçime uygulanacak plan (`Izgara.bicim_uygula`); değişiklik yoksa boş liste."""
        plan = []
        y = self.yama()
        if not y.bos_mu():
            plan.append((list(araliklar), y))
        degisen = {}
        cizgi = self._kenar_cizgisi()
        for yon, c in self.kenar.items():
            if c.isChecked() != self._kenar_ilk[yon]:
                degisen[yon] = cizgi if c.isChecked() else None
        ic = (cizgi if self.ic.isChecked() else None) if self._ic_dokunuldu else bi.DEGISMEDI
        if degisen or ic is not bi.DEGISMEDI:
            plan += bi.kenar_ayar_plani(araliklar, degisen, ic)
        return plan
