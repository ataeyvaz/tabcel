"""Veri Doğrulama penceresi (Faz 5 / 5g; faz5_tasarim.md §7.3). Sekmeler: Ayarlar, Giriş İletisi, Hata Uyarısı.

Kaynak/değer alanları Türkçe yazılır: liste ayırıcı `;` (`Evet;Hayır` → saklanan `"Evet,Hayır"`), formül
`=$A$1:$A$5` / `=Sayfa2!$A:$A` (işaretleme modu yok). Formüller etkin hücreye göre yazılır; saklanan biçime
çevirip kural çapasına kaydırmayı çağıran yapar (`window.dogrulama_ac`).
"""
import re
from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from ..formul import ceviri
from ..formul.sozcuk import FormulHatasi
from ..model.dogrulama import Dogrulama, liste_sabiti_ogeleri, liste_sabiti_yaz

IZIN = (("her_deger", "Herhangi Bir Değer"), ("tam_sayi", "Tam Sayı"), ("ondalik", "Ondalık"),
        ("liste", "Liste"), ("tarih", "Tarih"), ("saat", "Saat"), ("metin_uzunlugu", "Metin Uzunluğu"),
        ("ozel", "Özel"))
VERI = (("arasinda", "arasında"), ("arasinda_degil", "arasında değil"), ("esit", "eşit"),
        ("esit_degil", "eşit değil"), ("buyuk", "büyük"), ("kucuk", "küçük"),
        ("buyuk_esit", "büyük veya eşit"), ("kucuk_esit", "küçük veya eşit"))
STIL = (("durdur", "Durdur"), ("uyari", "Uyarı"), ("bilgi", "Bilgi"))
VARSAYILAN_IL = "Bu değer, bu hücre için tanımlanan veri doğrulama kısıtlamalarıyla eşleşmiyor."
_SAYI = re.compile(r"^=-?[\d.,E+-]+$")


class DogrulamaPenceresi(QDialog):
    """`sonuc()` → `Dogrulama` (araliklar boş demet: çağıran doldurur) ya da None (kural yok / temizle).
    `temizlendi`: Tümünü Temizle'ye basıldı."""

    def __init__(self, kitap, mevcut: Optional[Dogrulama] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Veri Doğrulama")
        self.kitap = kitap
        self.temizlendi = False
        self._sonuc: Optional[Dogrulama] = None

        # --- Ayarlar ---
        self.izin = QComboBox()
        for k, ad in IZIN:
            self.izin.addItem(ad, k)
        self.veri = QComboBox()
        for k, ad in VERI:
            self.veri.addItem(ad, k)
        self.etiket1, self.etiket2 = QLabel("En Az:"), QLabel("En Çok:")
        self.alan1, self.alan2 = QLineEdit(), QLineEdit()
        self.bos_yoksay = QCheckBox("Boşluğu yoksay")
        self.bos_yoksay.setChecked(True)
        self.acilir = QCheckBox("Hücre içi açılır liste")
        self.acilir.setChecked(True)
        ayar = QWidget()
        f = QFormLayout(ayar)
        f.addRow("İzin Verilen:", self.izin)
        f.addRow(self.bos_yoksay)
        f.addRow("Veri:", self.veri)
        f.addRow(self.etiket1, self.alan1)
        f.addRow(self.etiket2, self.alan2)
        f.addRow(self.acilir)
        self.izin.currentIndexChanged.connect(self._duzeni_ayarla)
        self.veri.currentIndexChanged.connect(self._duzeni_ayarla)

        # --- Giriş iletisi ---
        self.giris_goster = QCheckBox("Hücre seçildiğinde giriş iletisini göster")
        self.giris_goster.setChecked(True)
        self.giris_baslik, self.giris_ileti = QLineEdit(), QPlainTextEdit()
        giris = QWidget()
        g = QFormLayout(giris)
        g.addRow(self.giris_goster)
        g.addRow("Başlık:", self.giris_baslik)
        g.addRow("Giriş iletisi:", self.giris_ileti)

        # --- Hata uyarısı ---
        self.hata_goster = QCheckBox("Geçersiz veri girildikten sonra hata uyarısını göster")
        self.hata_goster.setChecked(True)
        self.hata_stil = QComboBox()
        for k, ad in STIL:
            self.hata_stil.addItem(ad, k)
        self.hata_baslik, self.hata_ileti = QLineEdit(), QPlainTextEdit()
        hata = QWidget()
        h = QFormLayout(hata)
        h.addRow(self.hata_goster)
        h.addRow("Stil:", self.hata_stil)
        h.addRow("Başlık:", self.hata_baslik)
        h.addRow("Hata iletisi:", self.hata_ileti)

        self.sekmeler = QTabWidget()
        self.sekmeler.addTab(ayar, "Ayarlar")
        self.sekmeler.addTab(giris, "Giriş İletisi")
        self.sekmeler.addTab(hata, "Hata Uyarısı")
        temizle = QPushButton("Tümünü Temizle")
        temizle.clicked.connect(self._temizle)
        dugmeler = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dugmeler.button(QDialogButtonBox.Ok).setText("Tamam")
        dugmeler.button(QDialogButtonBox.Cancel).setText("İptal")
        dugmeler.addButton(temizle, QDialogButtonBox.ResetRole)
        dugmeler.accepted.connect(self._tamam)
        dugmeler.rejected.connect(self.reject)
        v = QVBoxLayout(self)
        v.addWidget(self.sekmeler)
        v.addWidget(dugmeler)
        if mevcut is not None:
            self._yukle(mevcut)
        self._duzeni_ayarla()

    # --- düzen ---
    def tur(self) -> str:
        return self.izin.currentData()

    def islec(self) -> str:
        return self.veri.currentData()

    def _duzeni_ayarla(self) -> None:
        tur, iki = self.tur(), self.islec() in ("arasinda", "arasinda_degil")
        sayisal = tur not in ("her_deger", "liste", "ozel")
        self.veri.setEnabled(sayisal)
        self.alan1.setEnabled(tur != "her_deger")
        self.alan2.setVisible(sayisal and iki)
        self.etiket2.setVisible(sayisal and iki)
        self.acilir.setEnabled(tur == "liste")
        self.etiket1.setText("Kaynak:" if tur == "liste" else "Formül:" if tur == "ozel"
                             else "En Az:" if iki else "Değer:")

    # --- dönüşümler ---
    def _formul_goster(self, f: Optional[str], tur: str) -> str:
        if f is None:
            return ""
        if tur == "liste" and not f.startswith("="):
            return ";".join(liste_sabiti_ogeleri(f))
        g = ceviri.gosterime(f, self.kitap)
        return g[1:] if tur != "ozel" and _SAYI.match(g) else g

    def _formul_cevir(self, metin: str, tur: str, ad: str) -> str:
        from ..model.girdi import akilli_coz
        metin = metin.strip()
        if metin == "":
            raise ValueError(f"{ad} boş bırakılamaz.")
        if tur == "liste" and not metin.startswith("="):
            ogeler = [o.strip() for o in metin.split(";")]
            if any("," in o for o in ogeler):
                raise ValueError("Liste öğeleri virgül içeremez; öğeleri ';' ile ayırın.")
            return liste_sabiti_yaz(ogeler)
        try:
            if metin.startswith("=") or tur == "ozel":
                return ceviri.girdiden(metin if metin.startswith("=") else "=" + metin, self.kitap)
            h, _ = akilli_coz(metin)
        except FormulHatasi as e:
            raise ValueError(f"Bu formülde bir sorun var: {e}") from e
        if h is None or h.formul is not None or isinstance(h.deger, bool) or not isinstance(h.deger, (int, float)):
            raise ValueError("Girdiğiniz değer geçerli değil.")
        return "=" + format(float(h.deger), ".15g")

    def dogrulama_olustur(self) -> Optional[Dogrulama]:
        """Alanlardan kural (araliklar boş demet). Geçersiz alan → `ValueError` (iletisi Türkçe)."""
        tur = self.tur()
        giris = (self.giris_goster.isChecked(), self.giris_baslik.text(), self.giris_ileti.toPlainText())
        hata = (self.hata_goster.isChecked(), self.hata_stil.currentData(), self.hata_baslik.text(),
                self.hata_ileti.toPlainText())
        f1 = f2 = None
        islec = self.islec()
        if tur != "her_deger":
            f1 = self._formul_cevir(self.alan1.text(), tur, "Kaynak" if tur == "liste" else "Formül" if tur == "ozel"
                                    else "En Az" if islec in ("arasinda", "arasinda_degil") else "Değer")
            if tur not in ("liste", "ozel") and islec in ("arasinda", "arasinda_degil"):
                f2 = self._formul_cevir(self.alan2.text(), tur, "En Çok")
        if tur in ("liste", "ozel", "her_deger"):
            islec = "arasinda"
        return Dogrulama((), tur=tur, islec=islec, formul1=f1, formul2=f2,
                         bos_yoksay=self.bos_yoksay.isChecked(), acilir_liste=self.acilir.isChecked(),
                         giris=giris, hata=hata)

    def _yukle(self, dv: Dogrulama) -> None:
        self.izin.setCurrentIndex(self.izin.findData(dv.tur))
        self.veri.setCurrentIndex(self.veri.findData(dv.islec))
        self.alan1.setText(self._formul_goster(dv.formul1, dv.tur))
        self.alan2.setText(self._formul_goster(dv.formul2, dv.tur))
        self.bos_yoksay.setChecked(dv.bos_yoksay)
        self.acilir.setChecked(dv.acilir_liste)
        self.giris_goster.setChecked(dv.giris[0])
        self.giris_baslik.setText(dv.giris[1])
        self.giris_ileti.setPlainText(dv.giris[2])
        self.hata_goster.setChecked(dv.hata[0])
        self.hata_stil.setCurrentIndex(self.hata_stil.findData(dv.hata[1]))
        self.hata_baslik.setText(dv.hata[2])
        self.hata_ileti.setPlainText(dv.hata[3])

    def _tamam(self) -> None:
        try:
            self._sonuc = self.dogrulama_olustur()
        except ValueError as e:
            QMessageBox.warning(self, "Veri Doğrulama", str(e))
            return
        self.accept()

    def _temizle(self) -> None:
        self.temizlendi = True
        self._sonuc = None
        self.accept()

    def sonuc(self) -> Optional[Dogrulama]:
        return self._sonuc
