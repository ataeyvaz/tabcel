"""Filtre açılır paneli ve Özel Filtre / İlk 10 pencereleri (Faz 5 / 5f; faz5_tasarim.md §6.5)."""
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMenu, QPushButton, QRadioButton, QSpinBox, QVBoxLayout,
)

from ..model.adres import sutun_harfe
from ..model.bul import gorunen_metin
from ..model.filtre import (
    DegerKosulu, Filtre, IlkKosul, OrtalamaKosulu, OzelKosul, RenkKosulu, liste_degerleri, sutun_renkleri,
    veri_satirlari,
)
from ..model.harmanla import tr_kucuk

ISLEC_ADLARI = (("esit", "eşittir"), ("esit_degil", "eşit değildir"), ("buyuk", "büyüktür"),
                ("buyuk_esit", "büyük veya eşittir"), ("kucuk", "küçüktür"), ("kucuk_esit", "küçük veya eşittir"),
                ("baslar", "ile başlar"), ("baslamaz", "ile başlamaz"), ("biter", "ile biter"),
                ("bitmez", "ile bitmez"), ("icerir", "içerir"), ("icermez", "içermez"))
METIN_ISLECLERI = ("esit", "esit_degil", "baslar", "baslamaz", "biter", "bitmez", "icerir", "icermez")
SAYI_ISLECLERI = ("esit", "esit_degil", "buyuk", "buyuk_esit", "kucuk", "kucuk_esit")
BOS_ETIKET = "(Boş)"
TUMU_ETIKET = "(Tümünü Seç)"


def deger_coz(metin: str):
    """Özel Filtre değeri: Türkçe sayı yazımı (`2,5`) sayıya, aksi metne çözülür."""
    t = metin.strip()
    try:
        return float(t.replace(".", "").replace(",", ".")) if "," in t else float(t)
    except ValueError:
        return t


class OzelFiltrePenceresi(QDialog):
    """İki satır (işleç + değer), Ve/Veya. `on_ayar`: `(işleç1, değer1, işleç2, değer2)` ya da tek koşul."""

    def __init__(self, sutun_adi: str, parent=None, islecler=None, on_ayar=None, ve=True):
        super().__init__(parent)
        self.setWindowTitle("Özel Otomatik Filtre")
        islecler = islecler or tuple(k for k, _ in ISLEC_ADLARI)
        etiket = dict(ISLEC_ADLARI)
        v = QVBoxLayout(self)
        v.addWidget(QLabel(f"Satırları göster: {sutun_adi}"))
        izgara = QGridLayout()
        self._islec, self._deger = [], []
        for i in range(2):
            cb = QComboBox()
            for k in islecler:
                cb.addItem(etiket[k], k)
            if i == 1:
                cb.insertItem(0, "", None)
                cb.setCurrentIndex(0)
            de = QComboBox()
            de.setEditable(True)
            de.setCurrentText("")
            self._islec.append(cb)
            self._deger.append(de)
            izgara.addWidget(cb, i * 2 if i == 0 else 3, 0)
            izgara.addWidget(de, i * 2 if i == 0 else 3, 1)
        self.ve_dugmesi, self.veya_dugmesi = QRadioButton("Ve"), QRadioButton("Veya")
        (self.ve_dugmesi if ve else self.veya_dugmesi).setChecked(True)
        ara = QHBoxLayout()
        ara.addWidget(self.ve_dugmesi)
        ara.addWidget(self.veya_dugmesi)
        izgara.addLayout(ara, 2, 0, 1, 2)
        v.addLayout(izgara)
        v.addWidget(QLabel("? tek karakteri, * herhangi bir karakter dizisini temsil eder"))
        dugmeler = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dugmeler.button(QDialogButtonBox.Ok).setText("Tamam")
        dugmeler.button(QDialogButtonBox.Cancel).setText("İptal")
        dugmeler.accepted.connect(self.accept)
        dugmeler.rejected.connect(self.reject)
        v.addWidget(dugmeler)
        if on_ayar:
            self.ayarla(*on_ayar)

    def ayarla(self, islec1, deger1, islec2=None, deger2=None):
        for i, (k, d) in enumerate(((islec1, deger1), (islec2, deger2))):
            if k is None:
                continue
            idx = self._islec[i].findData(k)
            if idx >= 0:
                self._islec[i].setCurrentIndex(idx)
            self._deger[i].setCurrentText("" if d is None else (f"{d:g}".replace(".", ",") if isinstance(d, float) else str(d)))

    def kosul(self) -> Optional[OzelKosul]:
        ks = []
        for cb, de in zip(self._islec, self._deger):
            k, metin = cb.currentData(), de.currentText()
            if k is not None and metin != "":
                ks.append((k, deger_coz(metin)))
        if not ks:
            return None
        return OzelKosul(ks[0], ks[1] if len(ks) > 1 else None, self.ve_dugmesi.isChecked())


class IlkOnPenceresi(QDialog):
    """İlk 10 Otomatik Filtre: Üst/Alt + sayı + Öğe/Yüzde."""

    def __init__(self, parent=None, kosul: Optional[IlkKosul] = None):
        super().__init__(parent)
        self.setWindowTitle("İlk 10 Otomatik Filtre")
        self.yon = QComboBox()
        self.yon.addItem("Üst", False)
        self.yon.addItem("Alt", True)
        self.sayi = QSpinBox()
        self.sayi.setRange(1, 500)
        self.sayi.setValue(10)
        self.birim = QComboBox()
        self.birim.addItem("Öğe", False)
        self.birim.addItem("Yüzde", True)
        if kosul is not None:
            self.yon.setCurrentIndex(1 if kosul.alt else 0)
            self.sayi.setValue(kosul.n)
            self.birim.setCurrentIndex(1 if kosul.yuzde else 0)
        h = QHBoxLayout()
        for w in (self.yon, self.sayi, self.birim):
            h.addWidget(w)
        v = QVBoxLayout(self)
        v.addLayout(h)
        dugmeler = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dugmeler.button(QDialogButtonBox.Ok).setText("Tamam")
        dugmeler.button(QDialogButtonBox.Cancel).setText("İptal")
        dugmeler.accepted.connect(self.accept)
        dugmeler.rejected.connect(self.reject)
        v.addWidget(dugmeler)

    def kosul(self) -> IlkKosul:
        return IlkKosul(self.sayi.value(), bool(self.yon.currentData()), bool(self.birim.currentData()))


class FiltrePaneli(QFrame):
    """Sütun filtresi paneli (açılır pencere). `kosulSecildi(kosul | None)`: None = bu sütunun filtresini
    temizle; `sirala(artan)`. Değer listesi diğer sütunların filtrelerine göre görünen satırlardan kurulur."""
    kosulSecildi = Signal(object)
    sirala = Signal(bool)

    def __init__(self, sayfa, filtre: Filtre, sutun: int, parent=None):
        super().__init__(parent, Qt.Popup)
        self.setFrameShape(QFrame.StyledPanel)
        self.sayfa, self.filtre, self.sutun = sayfa, filtre, sutun
        ad = self._sutun_adi()
        v = QVBoxLayout(self)
        v.setContentsMargins(6, 6, 6, 6)

        def dugme(metin, islev, etkin=True):
            d = QPushButton(metin)
            d.setFlat(True)
            d.setStyleSheet("text-align:left;padding:3px 6px;")
            d.setEnabled(etkin)
            d.clicked.connect(islev)
            v.addWidget(d)
            return d
        dugme("A'dan Z'ye Sırala", lambda: self._sirala(True))
        dugme("Z'den A'ya Sırala", lambda: self._sirala(False))
        self.temizle_dugmesi = dugme(f"\"{ad}\" Filtresini Temizle", self._temizle, sutun in filtre.kosullar)
        sayi_mi = self._sayisal()
        self.renk_menusu = self._renk_dugmesi(v)
        mdugme = QPushButton(("Sayı Filtreleri" if sayi_mi else "Metin Filtreleri") + "  ▸")
        mdugme.setFlat(True)
        mdugme.setStyleSheet("text-align:left;padding:3px 6px;")
        self.ozel_menu = QMenu(mdugme)
        etiket = dict(ISLEC_ADLARI)
        for k in (SAYI_ISLECLERI if sayi_mi else METIN_ISLECLERI):
            self.ozel_menu.addAction(etiket[k][0].upper() + etiket[k][1:] + "…", lambda _=False, k=k: self._ozel_ac(k))
        if sayi_mi:
            self.ozel_menu.addAction("Arasında…", self._arasinda)
            self.ozel_menu.addAction("İlk 10…", self._ilk_on)
            self.ozel_menu.addAction("Ortalamanın Üstünde", lambda: self._bitir(OrtalamaKosulu(True)))
            self.ozel_menu.addAction("Ortalamanın Altında", lambda: self._bitir(OrtalamaKosulu(False)))
        self.ozel_menu.addSeparator()
        self.ozel_menu.addAction("Özel Filtre…", lambda: self._ozel_ac(None))
        mdugme.setMenu(self.ozel_menu)
        v.addWidget(mdugme)

        self.ara = QLineEdit()
        self.ara.setPlaceholderText("Ara")
        self.ara.textChanged.connect(self._ara_degisti)
        v.addWidget(self.ara)
        self.liste = QListWidget()
        self.liste.setMinimumSize(220, 180)
        v.addWidget(self.liste)
        self.atlanan = 0
        self._listeyi_kur()
        self.liste.itemChanged.connect(self._oge_degisti)
        alt = QHBoxLayout()
        self.tamam = QPushButton("Tamam")
        iptal = QPushButton("İptal")
        self.tamam.clicked.connect(self._tamam)
        iptal.clicked.connect(self.close)
        alt.addStretch(1)
        alt.addWidget(self.tamam)
        alt.addWidget(iptal)
        v.addLayout(alt)

    # --- yardımcılar ---
    def _sutun_adi(self) -> str:
        m = gorunen_metin(self.sayfa, self.filtre.aralik.ilk_satir, self.sutun)
        return m if m else f"Sütun {sutun_harfe(self.sutun)}"

    def _sayisal(self) -> bool:
        sayi = metin = 0
        for r in veri_satirlari(self.filtre):
            d = self.sayfa.deger(r, self.sutun)
            if isinstance(d, (int, float)) and not isinstance(d, bool):
                sayi += 1
            elif isinstance(d, str):
                metin += 1
        return sayi > metin

    def _renk_dugmesi(self, v):
        renkler = sutun_renkleri(self.sayfa, self.filtre, self.sutun, "dolgu")
        if len(renkler) < 2:
            return None
        d = QPushButton("Renge Göre Filtrele  ▸")
        d.setFlat(True)
        d.setStyleSheet("text-align:left;padding:3px 6px;")
        m = QMenu(d)
        for renk in renkler:
            m.addAction(renk.upper() if renk else "Dolgu yok", lambda _=False, r=renk: self._bitir(RenkKosulu("dolgu", r)))
        d.setMenu(m)
        v.addWidget(d)
        return m

    def _listeyi_kur(self) -> None:
        degerler, bos, self.atlanan = liste_degerleri(self.sayfa, self.filtre, self.sutun)
        mevcut = self.filtre.kosullar.get(self.sutun)
        izinli = ({tr_kucuk(m) for m in mevcut.metinler}, mevcut.bos) if isinstance(mevcut, DegerKosulu) else None
        self.liste.blockSignals(True)
        self.liste.clear()
        self._ogeler: List[QListWidgetItem] = []
        tumu = self._oge(TUMU_ETIKET, True)
        self._ogeler.append(tumu)
        for m in degerler:
            self._ogeler.append(self._oge(m, izinli is None or tr_kucuk(m) in izinli[0]))
        if bos:
            self._ogeler.append(self._oge(BOS_ETIKET, izinli is None or izinli[1]))
        self.liste.blockSignals(False)
        self._tumu_durumu()

    def _oge(self, metin: str, isaretli: bool) -> QListWidgetItem:
        o = QListWidgetItem(metin)
        o.setFlags(o.flags() | Qt.ItemIsUserCheckable)
        o.setCheckState(Qt.Checked if isaretli else Qt.Unchecked)
        self.liste.addItem(o)
        return o

    def _tumu_durumu(self) -> None:
        tumu, digerleri = self._ogeler[0], self._ogeler[1:]
        durum = [o.checkState() for o in digerleri if not o.isHidden()]
        self.liste.blockSignals(True)
        if durum and all(d == Qt.Checked for d in durum):
            tumu.setCheckState(Qt.Checked)
        elif durum and all(d == Qt.Unchecked for d in durum):
            tumu.setCheckState(Qt.Unchecked)
        else:
            tumu.setCheckState(Qt.PartiallyChecked)
        self.liste.blockSignals(False)

    def _oge_degisti(self, oge) -> None:
        if oge is self._ogeler[0]:
            durum = oge.checkState() if oge.checkState() != Qt.PartiallyChecked else Qt.Checked
            self.liste.blockSignals(True)
            for o in self._ogeler[1:]:
                if not o.isHidden():
                    o.setCheckState(durum)
            self.liste.blockSignals(False)
        self._tumu_durumu()

    def _ara_degisti(self, metin: str) -> None:
        q = tr_kucuk(metin)
        for o in self._ogeler[1:]:
            o.setHidden(bool(q) and q not in tr_kucuk(o.text()))
        self._tumu_durumu()

    # --- eylemler ---
    def liste_kosulu(self) -> Optional[DegerKosulu]:
        """Listedeki işaretlere göre koşul; her şey işaretliyse (süzme yok) None."""
        degerler = self._ogeler[1:]
        if all(o.checkState() == Qt.Checked for o in degerler):
            return None
        bos = any(o.text() == BOS_ETIKET and o.checkState() == Qt.Checked for o in degerler)
        metinler = frozenset(o.text() for o in degerler if o.text() != BOS_ETIKET and o.checkState() == Qt.Checked)
        return DegerKosulu(metinler, bos)

    def _tamam(self) -> None:
        self._bitir(self.liste_kosulu())

    def _bitir(self, kosul) -> None:
        self.close()
        self.kosulSecildi.emit(kosul)

    def _temizle(self) -> None:
        self._bitir(None)

    def _sirala(self, artan: bool) -> None:
        self.close()
        self.sirala.emit(artan)

    def _ozel_ac(self, islec: Optional[str]) -> None:
        mevcut = self.filtre.kosullar.get(self.sutun)
        on = None
        if isinstance(mevcut, OzelKosul):
            on = (mevcut.k1[0], mevcut.k1[1]) + ((mevcut.k2[0], mevcut.k2[1]) if mevcut.k2 else ())
        elif islec is not None:
            on = (islec, "")
        pen = OzelFiltrePenceresi(self._sutun_adi(), self.window(), on_ayar=on,
                                  ve=mevcut.ve if isinstance(mevcut, OzelKosul) else True)
        self.ozel_pencere = pen
        self._pencere_ac(pen, lambda: self._bitir(pen.kosul()))

    def _arasinda(self) -> None:
        pen = OzelFiltrePenceresi(self._sutun_adi(), self.window(), on_ayar=("buyuk_esit", "", "kucuk_esit", ""))
        self.ozel_pencere = pen
        self._pencere_ac(pen, lambda: self._bitir(pen.kosul()))

    def _ilk_on(self) -> None:
        mevcut = self.filtre.kosullar.get(self.sutun)
        pen = IlkOnPenceresi(self.window(), mevcut if isinstance(mevcut, IlkKosul) else None)
        self.ozel_pencere = pen
        self._pencere_ac(pen, lambda: self._bitir(pen.kosul()))

    def _pencere_ac(self, pen: QDialog, kabul) -> None:
        self.hide()
        if pen.exec() == QDialog.Accepted:
            kabul()
        else:
            self.close()
