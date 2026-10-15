"""Sayfa Yapısı penceresi (Faz 4 / 4d)."""
from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLineEdit, QMessageBox, QRadioButton, QSpinBox, QVBoxLayout,
)

from .. import APP_NAME
from ..model.adres import AdresHatasi, aralik_coz, aralik_yaz
from ..model.sayfa_yapisi import KAGITLAR, SayfaYapisi


def baslik_satirlari_coz(metin: str) -> Optional[tuple]:
    """`1:2`, `$1:$2` ya da `3` → (ilk, son); boş → None; geçersizse ValueError."""
    m = metin.strip().replace("$", "")
    if not m:
        return None
    a, _, b = m.partition(":")
    try:
        ilk, son = int(a), int(b or a)
    except ValueError:
        raise ValueError("Yinelenecek satırlar “1:2” biçiminde yazılmalı.")
    if not 1 <= ilk <= son <= 1_048_576:
        raise ValueError("Yinelenecek satırlar geçersiz.")
    return ilk, son


def baslik_satirlari_yaz(v: Optional[tuple]) -> str:
    return "" if v is None else f"${v[0]}:${v[1]}"


class SayfaYapisiPenceresi(QDialog):
    def __init__(self, yapi: SayfaYapisi, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sayfa Yapısı")
        self._yapi = yapi
        self.dikey = QRadioButton("Dikey")
        self.yatay = QRadioButton("Yatay")
        (self.yatay if yapi.yon == "yatay" else self.dikey).setChecked(True)
        yon = QHBoxLayout()
        yon.addWidget(self.dikey)
        yon.addWidget(self.yatay)
        self.kagit = QComboBox()
        self.kagit.addItems(list(KAGITLAR))
        self.kagit.setCurrentText(yapi.kagit)
        self.olcek = QSpinBox()
        self.olcek.setRange(10, 400)
        self.olcek.setSuffix(" %")
        self.olcek.setValue(yapi.olcek)
        self.sigdir = QCheckBox("Tüm sütunları tek sayfa genişliğine sığdır")
        self.sigdir.setChecked(yapi.sigdir_genislik)
        self.sigdir_yuk = QCheckBox("Tüm satırları tek sayfa yüksekliğine sığdır")
        self.sigdir_yuk.setChecked(yapi.sigdir_yukseklik)
        for kutu in (self.sigdir, self.sigdir_yuk):
            kutu.toggled.connect(self._olcek_durumu)
        self.olcek.setEnabled(not (yapi.sigdir_genislik or yapi.sigdir_yukseklik))
        self.sira = QComboBox()
        self.sira.addItem("Önce aşağı, sonra sağa", "asagi_sonra_sag")
        self.sira.addItem("Önce sağa, sonra aşağı", "sag_sonra_asagi")
        self.sira.setCurrentIndex(0 if yapi.sayfa_sirasi == "asagi_sonra_sag" else 1)
        self.kenarlar = {}
        kenar = QFormLayout()
        for ad, etiket in (("ust", "Üst (cm)"), ("alt", "Alt (cm)"), ("sol", "Sol (cm)"), ("sag", "Sağ (cm)")):
            sp = QDoubleSpinBox()
            sp.setRange(0, 10)
            sp.setDecimals(2)
            sp.setSingleStep(0.1)
            sp.setValue(getattr(yapi, ad))
            self.kenarlar[ad] = sp
            kenar.addRow(etiket, sp)
        self.ortala = QCheckBox("Yatay ortala")
        self.ortala.setChecked(yapi.yatay_ortala)
        self.alan = QLineEdit(aralik_yaz(yapi.alan) if yapi.alan else "")
        self.alan.setPlaceholderText("boş = hepsi")                 # kısa: %125/%150 ölçekte kırpılıyordu (elle test 2026-10-15)
        self.alan.setToolTip("Boş bırakılırsa kullanılan alanın tamamı yazdırılır (örn. A1:F40)")
        self.baslik = QLineEdit(baslik_satirlari_yaz(yapi.baslik_satirlari))
        self.baslik.setPlaceholderText("örn. $1:$2")
        self.kilavuz = QCheckBox("Kılavuz çizgilerini yazdır")
        self.kilavuz.setChecked(yapi.kilavuz)

        sayfa_kutu = QGroupBox("Sayfa")
        f1 = QFormLayout(sayfa_kutu)
        f1.addRow("Yön:", yon)
        f1.addRow("Kağıt:", self.kagit)
        f1.addRow("Ölçek:", self.olcek)
        f1.addRow(self.sigdir)
        f1.addRow(self.sigdir_yuk)
        f1.addRow("Sayfa sırası:", self.sira)
        kenar_kutu = QGroupBox("Kenar boşlukları")
        kenar_kutu.setLayout(kenar)
        kenar.addRow(self.ortala)
        sayfa_kutu2 = QGroupBox("Yazdırılacak")
        f3 = QFormLayout(sayfa_kutu2)
        f3.addRow("Yazdırma alanı:", self.alan)
        f3.addRow("Her sayfada yinelenen satırlar:", self.baslik)
        f3.addRow(self.kilavuz)
        dugmeler = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dugmeler.button(QDialogButtonBox.Ok).setText("Tamam")
        dugmeler.button(QDialogButtonBox.Cancel).setText("İptal")
        dugmeler.accepted.connect(self._tamam)
        dugmeler.rejected.connect(self.reject)
        d = QVBoxLayout(self)
        for w in (sayfa_kutu, kenar_kutu, sayfa_kutu2, dugmeler):
            d.addWidget(w)
        self._sonuc: Optional[SayfaYapisi] = None

    def _olcek_durumu(self) -> None:
        self.olcek.setEnabled(not (self.sigdir.isChecked() or self.sigdir_yuk.isChecked()))

    def _tamam(self) -> None:
        try:
            alan = aralik_coz(self.alan.text()) if self.alan.text().strip() else None
            baslik = baslik_satirlari_coz(self.baslik.text())
            self._sonuc = self._yapi.degistir(
                yon="yatay" if self.yatay.isChecked() else "dikey", kagit=self.kagit.currentText(),
                olcek=self.olcek.value(), sigdir_genislik=self.sigdir.isChecked(),
                sigdir_yukseklik=self.sigdir_yuk.isChecked(), sayfa_sirasi=self.sira.currentData(),
                yatay_ortala=self.ortala.isChecked(), alan=alan, baslik_satirlari=baslik,
                kilavuz=self.kilavuz.isChecked(), **{k: v.value() for k, v in self.kenarlar.items()})
        except (AdresHatasi, ValueError) as e:
            QMessageBox.warning(self, APP_NAME, str(e))
            return
        self.accept()

    def sonuc(self) -> Optional[SayfaYapisi]:
        return self._sonuc
