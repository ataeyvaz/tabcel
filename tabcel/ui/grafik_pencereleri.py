"""Grafik Ayarları penceresi (Faz 6 / 6f; `faz6_tasarim.md` §6.3). "Veriyi Seç" ve "Grafik Türünü Değiştir"
aynı pencereyi ilgili alana odaklanmış açar. Tamam'da `sonuc` yeni `Grafik` olur (kimlik/konum/boyut korunur);
geçersiz aralıkta pencere kapanmaz, uyarı gösterir."""
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from ..model.grafik import Grafik, Seri
from ..model.grafik_islem import GALERI, TEK_SERILI, TUR_ADLARI, alt_tur_gecerli, referans_coz, referans_yaz
from ..model.grafik_cizim import palet_rengi

GOSTERGE_ADLARI = (("sag", "Sağ"), ("sol", "Sol"), ("ust", "Üst"), ("alt", "Alt"), (None, "Yok"))
SUTUNLAR = ("Seri adı", "Değerler", "Kategori / X değerleri", "Renk")
AD_SUTUNU, DEGER_SUTUNU, KATEGORI_SUTUNU, RENK_SUTUNU = range(4)


def sayi_coz(metin: str, alan: str) -> Optional[float]:
    """Boş → None (otomatik). Ondalık ayırıcı `,` ya da `.`; geçersiz → ValueError."""
    m = metin.strip().replace(" ", "")
    if not m:
        return None
    try:
        return float(m.replace(",", "."))
    except ValueError:
        raise ValueError(f"{alan}: sayı değil ({metin.strip()})") from None


def sayi_yaz(v: Optional[float]) -> str:
    if v is None:
        return ""
    return str(int(v)) if float(v).is_integer() else str(v).replace(".", ",")


class GrafikAyarlariPenceresi(QDialog):
    def __init__(self, kitap, sayfa, grafik: Grafik, parent=None, odak: Optional[str] = None):
        super().__init__(parent)
        self.kitap, self.sayfa, self.grafik = kitap, sayfa, grafik
        self.sonuc: Optional[Grafik] = None
        self.setWindowTitle("Grafik Ayarları")
        self.setMinimumWidth(640)

        self.tur = QComboBox()
        for tur, ad in TUR_ADLARI.items():
            self.tur.addItem(ad, tur)
        self.alt_tur = QComboBox()
        self.tur.setCurrentIndex(self.tur.findData(grafik.tur))
        self._alt_turleri_doldur(grafik.alt_tur)
        self.tur.currentIndexChanged.connect(lambda _i: self._alt_turleri_doldur(None))

        self.baslik = QLineEdit(grafik.baslik or "")
        self.baslik.setPlaceholderText("(başlık yok)")
        self.gosterge = QComboBox()
        for deger, ad in GOSTERGE_ADLARI:
            self.gosterge.addItem(ad, deger)
        self.gosterge.setCurrentIndex(self.gosterge.findData(grafik.gosterge))
        self.x_baslik = QLineEdit(grafik.x_baslik or "")
        self.y_baslik = QLineEdit(grafik.y_baslik or "")
        self.deger_etiketi = QCheckBox("Değer etiketlerini göster")
        self.deger_etiketi.setChecked(grafik.deger_etiketi)
        self.y_min = QLineEdit(sayi_yaz(grafik.y_min))
        self.y_max = QLineEdit(sayi_yaz(grafik.y_max))
        for k in (self.y_min, self.y_max):
            k.setPlaceholderText("Otomatik")

        genel = QFormLayout()
        genel.addRow("Grafik türü:", self.tur)
        genel.addRow("Alt tür:", self.alt_tur)
        genel.addRow("Grafik başlığı:", self.baslik)
        genel.addRow("Gösterge:", self.gosterge)
        genel.addRow("Yatay eksen başlığı:", self.x_baslik)
        genel.addRow("Dikey eksen başlığı:", self.y_baslik)
        genel.addRow("", self.deger_etiketi)
        sinir = QHBoxLayout()
        sinir.addWidget(QLabel("En küçük:"))
        sinir.addWidget(self.y_min)
        sinir.addWidget(QLabel("En büyük:"))
        sinir.addWidget(self.y_max)
        genel.addRow("Dikey eksen sınırları:", sinir)

        self.tablo = QTableWidget(0, len(SUTUNLAR))
        self.tablo.setHorizontalHeaderLabels(SUTUNLAR)
        self.tablo.horizontalHeader().setStretchLastSection(False)
        self.tablo.horizontalHeader().setSectionResizeMode(AD_SUTUNU, QHeaderView.Stretch)
        self.tablo.horizontalHeader().setSectionResizeMode(DEGER_SUTUNU, QHeaderView.Stretch)
        self.tablo.horizontalHeader().setSectionResizeMode(KATEGORI_SUTUNU, QHeaderView.Stretch)
        self.tablo.setColumnWidth(RENK_SUTUNU, 70)
        self.tablo.setSelectionBehavior(QTableWidget.SelectRows)
        self.tablo.setSelectionMode(QTableWidget.SingleSelection)
        self.tablo.setMinimumHeight(140)
        self.tablo.cellDoubleClicked.connect(self._renk_sec)
        self.tablo.setToolTip("Seri adı: sabit metin ya da =Sayfa1!$B$1 gibi bir hücre.\n"
                              "Değerler / Kategori: Sayfa1!$B$2:$B$5 (sayfa adı yazılmazsa bu sayfa).\n"
                              "Renk: hücreye çift tıklayın (boş = otomatik).")
        self.seri_kutusu = QGroupBox("Seriler")
        sk = QVBoxLayout(self.seri_kutusu)
        sk.addWidget(self.tablo)
        dugmeler = QHBoxLayout()
        for metin, islev in (("Ekle", self._seri_ekle), ("Sil", self._seri_sil),
                             ("Yukarı", lambda: self._tasi(-1)), ("Aşağı", lambda: self._tasi(1))):
            d = QPushButton(metin)
            d.clicked.connect(islev)
            dugmeler.addWidget(d)
        dugmeler.addStretch(1)
        sk.addLayout(dugmeler)
        for s in grafik.seriler:
            self._satir_ekle(s)

        self.ileti = QLabel("")
        self.ileti.setStyleSheet("color: #C00000;")
        self.ileti.setWordWrap(True)
        tamam = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        tamam.button(QDialogButtonBox.Ok).setText("Tamam")
        tamam.button(QDialogButtonBox.Cancel).setText("İptal")
        tamam.accepted.connect(self.accept)
        tamam.rejected.connect(self.reject)
        d = QVBoxLayout(self)
        d.addLayout(genel)
        d.addWidget(self.seri_kutusu)
        d.addWidget(self.ileti)
        d.addWidget(tamam)
        if odak == "veri":
            self.tablo.setFocus()
        elif odak == "tur":
            self.tur.setFocus()

    # ------------------------------------------------------------------ alanlar
    def _alt_turleri_doldur(self, secili: Optional[str]) -> None:
        tur = self.tur.currentData()
        self.alt_tur.blockSignals(True)
        self.alt_tur.clear()
        for alt, ad in GALERI[tur]:
            self.alt_tur.addItem(ad, alt)
        self.alt_tur.setCurrentIndex(max(0, self.alt_tur.findData(secili)))
        self.alt_tur.setEnabled(self.alt_tur.count() > 1)
        self.alt_tur.blockSignals(False)

    def _satir_ekle(self, s: Optional[Seri] = None, konum: Optional[int] = None) -> None:
        s = s or Seri()
        i = self.tablo.rowCount() if konum is None else konum
        self.tablo.insertRow(i)
        ad = ("=" + referans_yaz(self.kitap, s.ad_ref)) if s.ad_ref is not None else (s.ad or "")
        for j, metin in ((AD_SUTUNU, ad), (DEGER_SUTUNU, referans_yaz(self.kitap, s.deger)),
                         (KATEGORI_SUTUNU, referans_yaz(self.kitap, s.kategori))):
            self.tablo.setItem(i, j, QTableWidgetItem(metin))
        renk = QTableWidgetItem("")
        renk.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        self._renk_yaz(renk, s.renk)
        self.tablo.setItem(i, RENK_SUTUNU, renk)

    @staticmethod
    def _renk_yaz(oge: QTableWidgetItem, renk: Optional[str]) -> None:
        oge.setData(Qt.UserRole, renk)
        oge.setBackground(QBrush(QColor(renk)) if renk else QBrush())
        oge.setText("" if renk else "otomatik")

    def _renk_sec(self, satir: int, sutun: int) -> None:
        if sutun != RENK_SUTUNU:
            return
        oge = self.tablo.item(satir, sutun)
        mevcut = oge.data(Qt.UserRole) or palet_rengi(satir)
        c = QColorDialog.getColor(QColor(mevcut), self, "Seri rengi")
        if c.isValid():
            self._renk_yaz(oge, c.name().upper())

    def _seri_ekle(self) -> None:
        self._satir_ekle()
        self.tablo.selectRow(self.tablo.rowCount() - 1)
        self.tablo.setCurrentCell(self.tablo.rowCount() - 1, DEGER_SUTUNU)

    def _seri_sil(self) -> None:
        i = self.tablo.currentRow()
        if i >= 0:
            self.tablo.removeRow(i)

    def _tasi(self, yon: int) -> None:
        i = self.tablo.currentRow()
        j = i + yon
        if i < 0 or not 0 <= j < self.tablo.rowCount():
            return
        a, b = self._satir_oku(i), self._satir_oku(j)           # iki satırın içeriği değiş tokuş edilir
        self._satira_yaz(i, b)
        self._satira_yaz(j, a)
        self.tablo.setCurrentCell(j, DEGER_SUTUNU)

    def _satir_oku(self, i: int):
        return tuple((self.tablo.item(i, j).text() if j != RENK_SUTUNU else self.tablo.item(i, j).data(Qt.UserRole))
                     for j in range(len(SUTUNLAR)))

    def _satira_yaz(self, i: int, deger) -> None:
        for j, v in enumerate(deger):
            if j == RENK_SUTUNU:
                self._renk_yaz(self.tablo.item(i, j), v)
            else:
                self.tablo.item(i, j).setText(v)

    # ------------------------------------------------------------------ onay
    def _seriler_oku(self) -> List[Seri]:
        seriler: List[Seri] = []
        for i in range(self.tablo.rowCount()):
            ad, deger, kategori, renk = self._satir_oku(i)
            n = i + 1
            if not deger.strip():
                raise ValueError(f"{n}. serinin değer aralığı boş")
            try:
                d = referans_coz(self.kitap, deger, self.sayfa)
                k = referans_coz(self.kitap, kategori, self.sayfa)
                ad_ref = referans_coz(self.kitap, ad, self.sayfa) if ad.strip().startswith("=") else None
            except ValueError as e:
                raise ValueError(f"{n}. seri: {e}") from None
            seriler.append(Seri(ad=None if ad_ref is not None or not ad.strip() else ad.strip(), ad_ref=ad_ref,
                                deger=d, kategori=k, renk=renk))
        return seriler

    def accept(self) -> None:
        try:
            seriler = self._seriler_oku()
            if self.tur.currentData() in TEK_SERILI and len(seriler) > 1:
                raise ValueError("Pasta ve halka grafiğinde yalnız bir seri olabilir")
            y_min, y_max = sayi_coz(self.y_min.text(), "En küçük"), sayi_coz(self.y_max.text(), "En büyük")
            if y_min is not None and y_max is not None and y_min >= y_max:
                raise ValueError("Eksenin en küçük değeri en büyüğünden küçük olmalı")
        except ValueError as e:
            self.ileti.setText(str(e))
            return
        tur = self.tur.currentData()
        self.sonuc = self.grafik.degistir(
            tur=tur, alt_tur=alt_tur_gecerli(tur, self.alt_tur.currentData() or "kumelenmis"), seriler=tuple(seriler),
            baslik=self.baslik.text().strip() or None, gosterge=self.gosterge.currentData(),
            x_baslik=self.x_baslik.text().strip() or None, y_baslik=self.y_baslik.text().strip() or None,
            deger_etiketi=self.deger_etiketi.isChecked(), y_min=y_min, y_max=y_max)
        super().accept()
