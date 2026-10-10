"""Özel Sıralama penceresi (Faz 5 / 5c; faz5_tasarim.md §3.3)."""
from typing import List, Optional

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QVBoxLayout,
)

from ..model.adres import Aralik, sutun_harfe
from ..model.bul import gorunen_metin
from ..model.sirala import SiralamaAnahtari, baslik_tahmin

EN_COK_DUZEY = 64                      # Excel
OLCUTLER = (("deger", "Hücre Değerleri"), ("dolgu", "Hücre Rengi"), ("yazi_rengi", "Yazı Tipi Rengi"))


class SiralaPenceresi(QDialog):
    def __init__(self, sayfa, aralik: Aralik, aktif_sutun: int, parent=None, baslik: Optional[bool] = None):
        super().__init__(parent)
        self.setWindowTitle("Sırala")
        self.sayfa, self.aralik = sayfa, aralik
        self._aktif_sutun = aktif_sutun
        self.baslik_kutusu = QCheckBox("Verilerim üst bilgi içeriyor")
        self.baslik_kutusu.setChecked(baslik_tahmin(sayfa, aralik) if baslik is None else baslik)
        self.baslik_kutusu.toggled.connect(self._etiketleri_yenile)
        self.buyuk_kucuk_kutusu = QCheckBox("Büyük/küçük harf duyarlı")
        self.yon_kutusu = QComboBox()
        self.yon_kutusu.addItems(["Yukarıdan aşağıya sırala", "Soldan sağa sırala"])
        self.yon_kutusu.currentIndexChanged.connect(self._yon_degisti)

        self.tablo = QTableWidget(0, 4)
        self.tablo.setHorizontalHeaderLabels(["Sırala", "Sıralama ölçütü", "Renk", "Düzen"])
        self.tablo.horizontalHeader().setStretchLastSection(True)
        self.tablo.setColumnWidth(0, 160)
        self.tablo.setColumnWidth(1, 140)
        self.tablo.setColumnWidth(2, 90)
        self.tablo.setSelectionBehavior(QTableWidget.SelectRows)
        self.tablo.setSelectionMode(QTableWidget.SingleSelection)

        ekle = QPushButton("Düzey Ekle")
        sil = QPushButton("Düzeyi Sil")
        kopyala = QPushButton("Düzeyi Kopyala")
        yukari = QPushButton("▲")
        asagi = QPushButton("▼")
        ekle.clicked.connect(lambda: self.duzey_ekle())
        sil.clicked.connect(self.duzey_sil)
        kopyala.clicked.connect(self.duzey_kopyala)
        yukari.clicked.connect(lambda: self.tasi(-1))
        asagi.clicked.connect(lambda: self.tasi(1))
        yukari.setToolTip("Yukarı taşı")
        asagi.setToolTip("Aşağı taşı")
        dugmeler = QHBoxLayout()
        for d in (ekle, sil, kopyala, yukari, asagi):
            dugmeler.addWidget(d)
        dugmeler.addStretch(1)

        secenek = QHBoxLayout()
        secenek.addWidget(self.baslik_kutusu)
        secenek.addWidget(self.buyuk_kucuk_kutusu)
        secenek.addWidget(self.yon_kutusu)
        tamam = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        tamam.accepted.connect(self.accept)
        tamam.rejected.connect(self.reject)
        ana = QVBoxLayout(self)
        ana.addLayout(dugmeler)
        ana.addWidget(self.tablo)
        ana.addLayout(secenek)
        ana.addWidget(tamam)
        self.resize(560, 340)
        self.duzey_ekle(aktif_sutun)

    # ------------------------------------------------------------------ etiketler
    def _satir_yonu(self) -> bool:
        return self.yon_kutusu.currentIndex() == 0

    def _cizgiler(self) -> List[int]:
        a = self.aralik
        return (list(range(a.ilk_sutun, a.son_sutun + 1)) if self._satir_yonu()
                else list(range(a.ilk_satir, a.son_satir + 1)))

    def _etiket(self, k: int) -> str:
        """Düzey listesindeki ad: üst bilgi varsa başlık metni, yoksa "Sütun A" / "Satır 3"."""
        if self.baslik_kutusu.isChecked():
            r, c = (self.aralik.ilk_satir, k) if self._satir_yonu() else (k, self.aralik.ilk_sutun)
            m = gorunen_metin(self.sayfa, r, c)
            if m:
                return m
        return f"Sütun {sutun_harfe(k)}" if self._satir_yonu() else f"Satır {k}"

    def _etiketleri_yenile(self) -> None:
        for i in range(self.tablo.rowCount()):
            kutu = self.tablo.cellWidget(i, 0)
            secili = kutu.currentData()
            kutu.blockSignals(True)
            kutu.clear()
            for k in self._cizgiler():
                kutu.addItem(self._etiket(k), k)
            kutu.setCurrentIndex(max(0, kutu.findData(secili)))
            kutu.blockSignals(False)

    def _yon_degisti(self) -> None:
        self.tablo.setRowCount(0)
        self.duzey_ekle(self._aktif_sutun if self._satir_yonu() else self.aralik.ilk_satir)

    def _duzen_etiketleri(self, kutu: QComboBox, olcut: str, k: int) -> None:
        kutu.clear()
        if olcut != "deger":
            kutu.addItem("Üstte", True)
            kutu.addItem("Altta", False)
            return
        sayisal = self._sayisal_mi(k)
        kutu.addItem("Küçükten Büyüğe" if sayisal else "A'dan Z'ye", True)
        kutu.addItem("Büyükten Küçüğe" if sayisal else "Z'den A'ya", False)

    def _sayisal_mi(self, k: int) -> bool:
        a = self.aralik
        satir = self._satir_yonu()
        ilk = (a.ilk_satir + (1 if self.baslik_kutusu.isChecked() else 0)) if satir else a.ilk_sutun
        son = a.son_satir if satir else a.son_sutun
        var = False
        for i in range(ilk, min(son, ilk + 200) + 1):
            v = self.sayfa.deger(i, k) if satir else self.sayfa.deger(k, i)
            if v is None:
                continue
            if isinstance(v, (str, bool)) or not isinstance(v, (int, float)):
                return False
            var = True
        return var

    def _renkler(self, k: int, olcut: str) -> List[str]:
        a = self.aralik
        satir = self._satir_yonu()
        ilk, son = (a.ilk_satir, a.son_satir) if satir else (a.ilk_sutun, a.son_sutun)
        renkler = []
        for i in range(ilk, son + 1):
            st = self.sayfa.stil(i, k) if satir else self.sayfa.stil(k, i)
            r = st.dolgu if olcut == "dolgu" else st.yazi_rengi
            if r and r not in renkler:
                renkler.append(r)
        return renkler

    # ------------------------------------------------------------------ düzeyler
    def duzey_ekle(self, k: Optional[int] = None, olcut: str = "deger", artan: bool = True,
                   renk: Optional[str] = None) -> bool:
        if self.tablo.rowCount() >= EN_COK_DUZEY:
            return False
        if k is None:                                     # sıradaki henüz kullanılmayan çizgi
            kullanilan = {a.sutun for a in self.anahtarlar()}
            k = next((x for x in self._cizgiler() if x not in kullanilan), self._cizgiler()[0])
        i = self.tablo.rowCount()
        self.tablo.insertRow(i)
        kutu = QComboBox()
        for x in self._cizgiler():
            kutu.addItem(self._etiket(x), x)
        kutu.setCurrentIndex(max(0, kutu.findData(k)))
        olcut_kutusu = QComboBox()
        for kod, ad in OLCUTLER:
            olcut_kutusu.addItem(ad, kod)
        olcut_kutusu.setCurrentIndex(max(0, olcut_kutusu.findData(olcut)))
        renk_kutusu = QComboBox()
        duzen = QComboBox()
        self.tablo.setCellWidget(i, 0, kutu)
        self.tablo.setCellWidget(i, 1, olcut_kutusu)
        self.tablo.setCellWidget(i, 2, renk_kutusu)
        self.tablo.setCellWidget(i, 3, duzen)

        def yenile(*_):
            o, x = olcut_kutusu.currentData(), kutu.currentData()
            renk_kutusu.clear()
            renk_kutusu.setEnabled(o != "deger")
            if o != "deger":
                for r in self._renkler(x, o):
                    renk_kutusu.addItem(r, r)
            secili = duzen.currentData()
            duzen.blockSignals(True)
            self._duzen_etiketleri(duzen, o, x)
            duzen.setCurrentIndex(0 if secili in (None, True) else 1)
            duzen.blockSignals(False)

        kutu.currentIndexChanged.connect(yenile)
        olcut_kutusu.currentIndexChanged.connect(yenile)
        yenile()
        if renk is not None:
            renk_kutusu.setCurrentIndex(max(0, renk_kutusu.findData(renk)))
        duzen.setCurrentIndex(0 if artan else 1)
        self.tablo.selectRow(i)
        return True

    def duzey_sil(self) -> None:
        i = self.tablo.currentRow()
        if i >= 0 and self.tablo.rowCount() > 1:
            self.tablo.removeRow(i)

    def duzey_kopyala(self) -> None:
        i = self.tablo.currentRow()
        if i < 0:
            return
        a = self.anahtarlar()[i]
        self.duzey_ekle(a.sutun, a.olcut, a.artan, a.renk)

    def tasi(self, yon: int) -> None:
        i = self.tablo.currentRow()
        j = i + yon
        if i < 0 or not 0 <= j < self.tablo.rowCount():
            return
        liste = self.anahtarlar()
        liste[i], liste[j] = liste[j], liste[i]
        self.tablo.setRowCount(0)
        for a in liste:
            self.duzey_ekle(a.sutun, a.olcut, a.artan, a.renk)
        self.tablo.selectRow(j)

    # ------------------------------------------------------------------ sonuç
    def anahtarlar(self) -> List[SiralamaAnahtari]:
        sonuc = []
        for i in range(self.tablo.rowCount()):
            k = self.tablo.cellWidget(i, 0).currentData()
            o = self.tablo.cellWidget(i, 1).currentData()
            renk = self.tablo.cellWidget(i, 2).currentData() if o != "deger" else None
            artan = self.tablo.cellWidget(i, 3).currentData()
            sonuc.append(SiralamaAnahtari(k, bool(artan), o, renk))
        return sonuc

    def baslik(self) -> bool:
        return self.baslik_kutusu.isChecked()

    def buyuk_kucuk(self) -> bool:
        return self.buyuk_kucuk_kutusu.isChecked()

    def yon(self) -> str:
        return "satir" if self._satir_yonu() else "sutun"
