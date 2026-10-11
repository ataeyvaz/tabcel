"""Tablo Sağlık Kontrolü paneli (Faz 9c): tarama (donmadan, ilerleme + iptal), önem derecesine göre gruplu rapor, bulguya tıklayınca
hücreye gitme, sade Türkçe açıklama, onayla tek tıkla düzeltme (geri al yığınına girer), Yoksay (dosyayla saklanır), kontrol ayarları.
Mantık `formul/saglik.py`da. **Denetçi onay olmadan hücre değiştirmez:** yalnız “Düzelt” düğmesi komut çalıştırır."""
import time
from typing import List, Optional

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QDockWidget, QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton,
    QHBoxLayout, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from .. import APP_NAME
from ..formul import saglik
from . import theme

ROL_BULGU = Qt.UserRole
RENKLER = {saglik.KRITIK: "#c00000", saglik.UYARI: "#b45309", saglik.BILGI: "#1d4ed8"}
DILIM_MS = 12                                         # bir zamanlayıcı turunda tarama için harcanan süre


class SaglikAyarlariPenceresi(QDialog):
    """Kontrolleri ayrı ayrı aç/kapat + formülde yoksayılacak sabit sayılar."""

    def __init__(self, ayarlar: saglik.Ayarlar, ust=None):
        super().__init__(ust)
        self.setWindowTitle("Tablo Sağlığı Ayarları")
        self.setMinimumWidth(480)
        d = QVBoxLayout(self)
        d.addWidget(QLabel("Hangi kontroller yapılsın?"))
        self.kutular = {}
        for kimlik, ad, onem, aciklama in saglik.KONTROLLER:
            k = QCheckBox(f"{ad}  ({saglik.ONEM_ADLARI[onem]})")
            k.setToolTip(aciklama)
            k.setChecked(ayarlar.acik_mi(kimlik))
            d.addWidget(k)
            e = QLabel(aciklama)
            e.setStyleSheet(f"color: {theme.TEXT_MUTED}; margin-left: 22px;")
            e.setWordWrap(True)
            d.addWidget(e)
            self.kutular[kimlik] = k
        d.addWidget(QLabel("Formüllerde alarm vermeyecek sabit sayılar (virgülle ayırın):"))
        self.sabitler = QLineEdit(", ".join(_sayi_yaz(x) for x in ayarlar.sabit_yoksay))
        d.addWidget(self.sabitler)
        dugmeler = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dugmeler.button(QDialogButtonBox.Ok).setText("Tamam")
        dugmeler.button(QDialogButtonBox.Cancel).setText("İptal")
        dugmeler.accepted.connect(self.accept)
        dugmeler.rejected.connect(self.reject)
        d.addWidget(dugmeler)

    def ayarlar(self) -> saglik.Ayarlar:
        a = saglik.Ayarlar()
        a.acik = {k: c.isChecked() for k, c in self.kutular.items()}
        sayilar = []
        for parca in self.sabitler.text().replace(";", ",").split(","):
            p = parca.strip().replace(" ", "")
            if not p:
                continue
            try:
                sayilar.append(float(p.replace(",", ".")) if p.count(",") + p.count(".") <= 1 else float(p.replace(".", "").replace(",", ".")))
            except ValueError:
                continue
        a.sabit_yoksay = tuple(sayilar)
        return a


def _sayi_yaz(x: float) -> str:
    return str(int(x)) if x == int(x) else str(x).replace(".", ",")


class SaglikPaneli(QDockWidget):
    hucreyeGit = Signal(object, int, int)            # sayfa, satır, sütun

    def __init__(self, pencere):
        super().__init__("Tablo Sağlığı", pencere)
        self.setObjectName("saglikPaneli")
        self.pencere = pencere
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        govde = QWidget()
        d = QVBoxLayout(govde)
        d.setContentsMargins(6, 6, 6, 6)
        ust = QHBoxLayout()
        self.tara_dugmesi = QPushButton("Tara")
        self.iptal_dugmesi = QPushButton("İptal")
        self.iptal_dugmesi.setEnabled(False)
        self.ayar_dugmesi = QPushButton("Ayarlar…")
        for b in (self.tara_dugmesi, self.iptal_dugmesi, self.ayar_dugmesi):
            ust.addWidget(b)
        ust.addStretch(1)
        d.addLayout(ust)
        self.ilerleme = QProgressBar()
        self.ilerleme.setRange(0, 1000)
        self.ilerleme.setTextVisible(False)
        self.ilerleme.setMaximumHeight(8)
        d.addWidget(self.ilerleme)
        self.ozet = QLabel("Çalışma kitabını taramak için Tara'ya basın.")
        self.ozet.setWordWrap(True)
        d.addWidget(self.ozet)
        self.eski_etiketi = QLabel("Kitap değişti; sonuçlar eski olabilir — yeniden tarayın.")
        self.eski_etiketi.setStyleSheet(f"color: {RENKLER[saglik.UYARI]};")
        self.eski_etiketi.hide()
        d.addWidget(self.eski_etiketi)
        self.agac = QTreeWidget()
        self.agac.setHeaderLabels(["Bulgu", "Yer"])
        self.agac.setColumnWidth(0, 250)
        d.addWidget(self.agac, 3)
        self.ayrinti = QLabel("")
        self.ayrinti.setWordWrap(True)
        self.ayrinti.setTextFormat(Qt.PlainText)
        self.ayrinti.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.ayrinti.setMinimumHeight(110)
        d.addWidget(self.ayrinti, 1)
        alt = QHBoxLayout()
        self.duzelt_dugmesi = QPushButton("Düzelt")
        self.yoksay_dugmesi = QPushButton("Yoksay")
        self.geri_dugmesi = QPushButton("Yoksayılanları geri al")
        for b in (self.duzelt_dugmesi, self.yoksay_dugmesi, self.geri_dugmesi):
            alt.addWidget(b)
        alt.addStretch(1)
        d.addLayout(alt)
        self.duzelt_dugmesi.setEnabled(False)
        self.yoksay_dugmesi.setEnabled(False)
        self.geri_dugmesi.hide()
        self.setWidget(govde)
        self._uretec = None
        self._bulgular: List[saglik.Bulgu] = []
        self._yoksayilan = 0
        self._zamanlayici = QTimer(self)
        self._zamanlayici.setInterval(0)
        self._zamanlayici.timeout.connect(self._sur)
        self.tara_dugmesi.clicked.connect(self.tara)
        self.iptal_dugmesi.clicked.connect(self.iptal)
        self.ayar_dugmesi.clicked.connect(self.ayarlari_ac)
        self.agac.currentItemChanged.connect(self._secildi)
        self.agac.itemClicked.connect(lambda o, _k: self._git(o))
        self.duzelt_dugmesi.clicked.connect(self.duzelt)
        self.yoksay_dugmesi.clicked.connect(self.yoksay)
        self.geri_dugmesi.clicked.connect(self.yoksayilanlari_geri_al)

    # ------------------------------------------------------------------ tarama (donmadan)
    def tara(self) -> None:
        self.iptal()
        p = self.pencere
        self.agac.clear()
        self._bulgular = []
        self._yoksayilan = 0
        self.ayrinti.setText("")
        self.eski_etiketi.hide()
        self._ayar = saglik.ayarlari_oku()
        t = saglik.Tarayici(p.kitap, p.motor, self._ayar, p.kitap.saglik_yoksay)
        self._tarayici = t
        self._uretec = t.calistir()
        self.tara_dugmesi.setEnabled(False)
        self.iptal_dugmesi.setEnabled(True)
        self.ozet.setText("Taranıyor…")
        self._zamanlayici.start()

    def iptal(self) -> None:
        if self._uretec is not None:
            self._uretec.close()
            self._uretec = None
            self._zamanlayici.stop()
            self.tara_dugmesi.setEnabled(True)
            self.iptal_dugmesi.setEnabled(False)
            self.ozet.setText("Tarama iptal edildi. " + self._ozet_metni())

    def _sur(self) -> None:
        """Bir dilim: en çok DILIM_MS ms tarar, olay döngüsüne döner (arayüz donmaz)."""
        if self._uretec is None:
            return
        bitis = time.perf_counter() + DILIM_MS / 1000
        try:
            while time.perf_counter() < bitis:
                olay = next(self._uretec)
                if olay[0] == "ilerleme":
                    self.ilerleme.setValue(int(olay[1] * 1000))
                    self.ozet.setText(f"Taranıyor: {olay[2]}")
                elif olay[0] == "bulgu":
                    self._bulgu_ekle(olay[1])
                # "ritim": tarayıcı kendi zaman payını doldurdu; döngü süresine bakıp olay döngüsüne döner
        except StopIteration:
            self._uretec = None
            self._zamanlayici.stop()
            self._yoksayilan = self._tarayici.yoksayilan
            self.tara_dugmesi.setEnabled(True)
            self.iptal_dugmesi.setEnabled(False)
            self.ilerleme.setValue(1000)
            self._agaci_yenile()
            self.ozet.setText(self._ozet_metni())
        except Exception as e:                                        # denetçi programı düşürmez
            self._uretec = None
            self._zamanlayici.stop()
            self.tara_dugmesi.setEnabled(True)
            self.iptal_dugmesi.setEnabled(False)
            self.ozet.setText(f"Tarama tamamlanamadı: {e}")

    def _bulgu_ekle(self, b: saglik.Bulgu) -> None:
        self._bulgular.append(b)

    # ------------------------------------------------------------------ rapor
    def _ozet_metni(self) -> str:
        sayi = {o: sum(1 for b in self._bulgular if b.onem == o) for o in (saglik.KRITIK, saglik.UYARI, saglik.BILGI)}
        if not self._bulgular:
            m = "Sorun bulunamadı."
        else:
            m = " · ".join(f"{sayi[o]} {saglik.ONEM_ADLARI[o]}" for o in sayi)
        n = len(self.pencere.kitap.saglik_yoksay)
        self.geri_dugmesi.setVisible(n > 0)
        return m + (f"   ({n} yoksayılan bulgu)" if n else "")

    def _agaci_yenile(self) -> None:
        self.agac.clear()
        for onem in (saglik.KRITIK, saglik.UYARI, saglik.BILGI):
            liste = [b for b in self._bulgular if b.onem == onem]
            if not liste:
                continue
            grup = QTreeWidgetItem([f"{saglik.ONEM_ADLARI[onem]} ({len(liste)})"])
            f = grup.font(0)
            f.setBold(True)
            grup.setFont(0, f)
            grup.setForeground(0, QBrush(QColor(RENKLER[onem])))
            self.agac.addTopLevelItem(grup)
            for kontrol, ad, _o, _a in saglik.KONTROLLER:
                alt = [b for b in liste if b.kontrol == kontrol]
                for b in alt:
                    o = QTreeWidgetItem([f"{ad}: {b.baslik}", b.adres + (f" (+{b.adet - 1})" if b.adet > 1 else "")])
                    o.setData(0, ROL_BULGU, b)
                    o.setToolTip(0, b.aciklama)
                    grup.addChild(o)
            grup.setExpanded(True)

    def _bulgu(self, o: Optional[QTreeWidgetItem]) -> Optional[saglik.Bulgu]:
        return o.data(0, ROL_BULGU) if o is not None else None

    def _secildi(self, o, _onceki=None) -> None:
        b = self._bulgu(o)
        self.duzelt_dugmesi.setEnabled(b is not None and b.duzeltme is not None)
        self.yoksay_dugmesi.setEnabled(b is not None)
        if b is None:
            self.ayrinti.setText("")
            return
        metin = f"{b.aciklama}\n\nNeden sorun olabilir: {b.neden}"
        if b.duzeltme is not None:
            metin += f"\n\nÖnerilen düzeltme: {b.duzeltme.aciklama}\n(Düzelt'e basmadıkça hiçbir hücre değişmez; Ctrl+Z ile geri alınır.)"
        if b.adet > 1:
            metin += f"\n\nEtkilenen hücre sayısı: {b.adet}"
        self.ayrinti.setText(metin)

    def _git(self, o: QTreeWidgetItem) -> None:
        b = self._bulgu(o)
        if b is None:
            return
        sayfa = self.pencere.kitap.sayfa_kimlikle(b.sayfa_kimlik)
        if sayfa is not None:
            self.hucreyeGit.emit(sayfa, *b.konum)

    # ------------------------------------------------------------------ eylemler (yalnız kullanıcı basınca)
    def duzelt(self) -> None:
        o = self.agac.currentItem()
        b = self._bulgu(o)
        if b is None or b.duzeltme is None:
            return
        try:
            kmt = saglik.duzeltme_komutu(self.pencere.kitap, b)
            self.pencere.yigin.calistir(kmt)
        except (ValueError, KeyError) as e:
            QMessageBox.warning(self, APP_NAME, str(e))
            return
        self._bulgular.remove(b)
        self._agaci_yenile()
        self.ozet.setText("Düzeltildi (Ctrl+Z ile geri alınır). " + self._ozet_metni())
        self.eski_etiketi.show()

    def yoksay(self) -> None:
        o = self.agac.currentItem()
        b = self._bulgu(o)
        if b is None:
            return
        self.pencere.kitap.saglik_yoksay.add(b.anahtar)
        self.pencere.gorunum_degisti_isaretle()                       # yoksayma dosyayla saklanır → belge “değişti”
        self._bulgular.remove(b)
        self._agaci_yenile()
        self.ayrinti.setText("")
        self.ozet.setText(self._ozet_metni())

    def yoksayilanlari_geri_al(self) -> None:
        self.pencere.kitap.saglik_yoksay.clear()
        self.pencere.gorunum_degisti_isaretle()
        self.tara()

    def ayarlari_ac(self) -> None:
        d = SaglikAyarlariPenceresi(saglik.ayarlari_oku(), self.pencere)
        if d.exec() == QDialog.Accepted:
            saglik.ayarlari_yaz(d.ayarlar())
            self.ozet.setText("Ayarlar kaydedildi; yeniden taramak için Tara'ya basın.")

    # ------------------------------------------------------------------ pencere olayları
    def olay(self, olay) -> None:
        """Kitap değişince sonuçlar eskiyebilir (otomatik yeniden tarama yok: gürültü olur)."""
        if self._bulgular and olay.tur in ("hucre", "yapi", "sayfa"):
            self.eski_etiketi.show()
