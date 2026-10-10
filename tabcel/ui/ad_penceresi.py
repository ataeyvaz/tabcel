"""Ad Tanımla, Ad Yöneticisi ve Git penceresi (Faz 5 / 5d; faz5_tasarim.md §4.5).

Başvurur alanında başvuru işaretleme (K7) yoktur (tasarım §11): formül metni elle yazılır.
"""
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from .. import APP_NAME
from ..formul.ad_yardim import (
    aralik_basvurusu, basvurur_gosterim, basvurur_saklanan, deger_metni, gorunur_adlar,
)
from ..formul.sozcuk import FormulHatasi
from ..model.ad import AdHatasi, TanimliAd, ad_kontrol

KITAP_KAPSAMI = "Çalışma Kitabı"


class AdTanimlaPenceresi(QDialog):
    """Yeni ad tanımlar ya da `duzenlenen` adı düzenler. Tamam'da `tanim` ve `eski_anahtar` dolar."""

    def __init__(self, kitap, aktif_sayfa, secim=None, duzenlenen: Optional[TanimliAd] = None,
                 parent=None, ad_onerisi: str = ""):
        super().__init__(parent)
        self.kitap, self.aktif_sayfa, self.duzenlenen = kitap, aktif_sayfa, duzenlenen
        self.tanim: Optional[TanimliAd] = None
        self.eski_anahtar = duzenlenen.anahtar() if duzenlenen is not None else None
        self.setWindowTitle("Ad Düzenle" if duzenlenen is not None else "Yeni Ad")
        self.ad_kutusu = QLineEdit(duzenlenen.ad if duzenlenen is not None else ad_onerisi)
        self.kapsam_kutusu = QComboBox()
        self.kapsam_kutusu.addItem(KITAP_KAPSAMI, None)
        for s in kitap.sayfalar:
            self.kapsam_kutusu.addItem(s.ad, s.kimlik)
        self.aciklama_kutusu = QLineEdit(duzenlenen.aciklama if duzenlenen is not None else "")
        self.basvurur_kutusu = QLineEdit()
        if duzenlenen is not None:
            self.basvurur_kutusu.setText(basvurur_gosterim(kitap, duzenlenen))
            self.kapsam_kutusu.setCurrentIndex(self.kapsam_kutusu.findData(duzenlenen.kapsam))
            self.kapsam_kutusu.setEnabled(False)               # Excel: kapsam sonradan değişmez
        elif secim is not None:
            self.basvurur_kutusu.setText(aralik_basvurusu(aktif_sayfa, secim))
        self.ileti = QLabel("")
        self.ileti.setStyleSheet("color: #C00000;")
        self.ileti.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Ad:", self.ad_kutusu)
        form.addRow("Kapsam:", self.kapsam_kutusu)
        form.addRow("Açıklama:", self.aciklama_kutusu)
        form.addRow("Başvurur:", self.basvurur_kutusu)
        dugmeler = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dugmeler.accepted.connect(self.accept)
        dugmeler.rejected.connect(self.reject)
        yerlesim = QVBoxLayout(self)
        yerlesim.addLayout(form)
        yerlesim.addWidget(self.ileti)
        yerlesim.addWidget(dugmeler)
        self.setMinimumWidth(420)

    def kapsam(self) -> Optional[int]:
        return self.kapsam_kutusu.currentData()

    def tanim_olustur(self) -> TanimliAd:
        """Alanlardan `TanimliAd` kurar ve doğrular; geçersizse `AdHatasi`/`FormulHatasi`."""
        kapsam = self.kapsam()
        bagla = (self.kitap.sayfa_kimlikle(kapsam) if kapsam is not None else None) or self.aktif_sayfa
        formul = basvurur_saklanan(self.kitap, self.basvurur_kutusu.text(), bagla)
        tanim = TanimliAd(self.ad_kutusu.text().strip(), formul, kapsam, self.aciklama_kutusu.text().strip(),
                          self.duzenlenen.gizli if self.duzenlenen is not None else False)
        ad_kontrol(self.kitap, tanim, self.eski_anahtar)
        return tanim

    def accept(self):
        try:
            self.tanim = self.tanim_olustur()
        except AdHatasi as e:
            self.ileti.setText(str(e))
            return
        except FormulHatasi as e:
            self.ileti.setText(f"Başvurur geçerli değil: {e}")
            return
        super().accept()


class AdYoneticisi(QDialog):
    """Ad listesi (Ad, Değer, Başvurur, Kapsam, Açıklama) + Yeni/Düzenle/Sil. Gizli adlar gösterilmez.
    Eylemler `pencere`nin `ad_tanimla_ac` / `ad_sil` yöntemlerine gider (geri alınabilir komutlar)."""

    def __init__(self, pencere):
        super().__init__(pencere)
        self.pencere = pencere
        self.setWindowTitle("Ad Yöneticisi")
        self.tablo = QTableWidget(0, 5)
        self.tablo.setHorizontalHeaderLabels(["Ad", "Değer", "Başvurur", "Kapsam", "Açıklama"])
        self.tablo.horizontalHeader().setStretchLastSection(True)
        for i, g in enumerate((130, 90, 200, 110)):
            self.tablo.setColumnWidth(i, g)
        self.tablo.setSelectionBehavior(QTableWidget.SelectRows)
        self.tablo.setSelectionMode(QTableWidget.SingleSelection)
        self.tablo.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tablo.itemDoubleClicked.connect(lambda _: self.duzenle())
        yeni, duzenle, sil, kapat = (QPushButton(m) for m in ("Yeni…", "Düzenle…", "Sil", "Kapat"))
        yeni.clicked.connect(self.yeni)
        duzenle.clicked.connect(self.duzenle)
        sil.clicked.connect(self.sil)
        kapat.clicked.connect(self.accept)
        dugmeler = QHBoxLayout()
        for d in (yeni, duzenle, sil):
            dugmeler.addWidget(d)
        dugmeler.addStretch(1)
        dugmeler.addWidget(kapat)
        yerlesim = QVBoxLayout(self)
        yerlesim.addWidget(self.tablo)
        yerlesim.addLayout(dugmeler)
        self.resize(720, 360)
        self.yenile()

    def yenile(self, secilecek=None) -> None:
        kitap = self.pencere.kitap
        adlar = gorunur_adlar(kitap)
        self.tablo.setRowCount(len(adlar))
        self._adlar = adlar
        for i, t in enumerate(adlar):
            kapsam = KITAP_KAPSAMI if t.kapsam is None else kitap.sayfa_kimlikle(t.kapsam).ad
            for j, metin in enumerate((t.ad, deger_metni(kitap, t), basvurur_gosterim(kitap, t), kapsam,
                                       t.aciklama)):
                self.tablo.setItem(i, j, QTableWidgetItem(metin))
            if secilecek is not None and t.anahtar() == secilecek:
                self.tablo.selectRow(i)

    def secili(self) -> Optional[TanimliAd]:
        satir = self.tablo.currentRow()
        return self._adlar[satir] if 0 <= satir < len(self._adlar) else None

    def yeni(self) -> None:
        if self.pencere.ad_tanimla_ac():
            self.yenile()

    def duzenle(self) -> None:
        t = self.secili()
        if t is not None and self.pencere.ad_tanimla_ac(t):
            self.yenile()

    def sil(self) -> None:
        t = self.secili()
        if t is not None:
            self.pencere.ad_sil(t)
            self.yenile()


class GitPenceresi(QDialog):
    """Git: başvuru yazın ya da tanımlı adlar listesinden seçin (çift tık = git)."""

    def __init__(self, parent, adlar):
        super().__init__(parent)
        self.setWindowTitle("Git")
        self.liste = QListWidget()
        self.liste.addItems(adlar)
        self.liste.currentTextChanged.connect(lambda m: self.basvuru.setText(m) if m else None)
        self.liste.itemDoubleClicked.connect(lambda _: self.accept())
        self.basvuru = QLineEdit()
        dugmeler = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dugmeler.accepted.connect(self.accept)
        dugmeler.rejected.connect(self.reject)
        yerlesim = QVBoxLayout(self)
        yerlesim.addWidget(QLabel("Git:"))
        yerlesim.addWidget(self.liste)
        yerlesim.addWidget(QLabel("Başvuru:"))
        yerlesim.addWidget(self.basvuru)
        yerlesim.addWidget(dugmeler)
        self.basvuru.setFocus()
        self.resize(300, 320)

    def metin(self) -> str:
        return self.basvuru.text().strip()
