"""Bul ve Değiştir penceresi (Faz 5 / 5b; faz5_tasarim.md §2.2). Kipsiz (modeless) pencere.

Model mantığı `model/bul.py`'dedir; burada yalnız arayüz, hücreye gitme ve komutu çalıştırma var.
"""
import os
from typing import List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTabBar, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from .. import APP_NAME
from ..formul.ceviri import hucre_girdisi_akilli, hucre_metni
from ..model.bul import (
    BulSecenek, degistir_komutu, degistirme_plani, eslesmeler, gorunen_metin, not_metni,
)
from ..model.sayfa import Sayfa

BULUNAMADI = "Aradığınız bulunamadı."


def metin_al(sayfa: Sayfa, satir: int, sutun: int, bakilan: str) -> Optional[str]:
    """Aranacak metin: formül = düzenleme metni (Türkçe formül), değer = görünen metin, not = not metni."""
    if bakilan == "not":
        return not_metni(sayfa, satir, sutun)
    if bakilan == "deger":
        return gorunen_metin(sayfa, satir, sutun)
    return hucre_metni(sayfa.hucre(satir, sutun), sayfa.kitap, sayfa.stil(satir, sutun).sayi_bicimi)


def coz(sayfa: Sayfa, satir: int, sutun: int, metin: str):
    """Değiştirilen metni elle yazılmış gibi çözer (`Izgara.hucre_gir` ile aynı kurallar): metin biçimli
    hücre her şeyi metin tutar; önerilen sayı biçimi yalnız Genel hücreye. Geçersiz formül → ValueError."""
    from ..model.sayfa import Hucre
    stil = sayfa.stil(satir, sutun)
    if stil.sayi_bicimi == "@":
        return (Hucre(metin) if metin else None), None
    h, kod = hucre_girdisi_akilli(metin, sayfa.kitap)
    if kod is not None and stil.sayi_bicimi != "General":
        kod = None
    return h, kod


class BulPenceresi(QDialog):
    def __init__(self, pencere):
        super().__init__(pencere)
        self.pencere = pencere
        self.setWindowTitle("Bul ve Değiştir")
        self.setModal(False)
        self.sekme = QTabBar()
        self.sekme.addTab("Bul")
        self.sekme.addTab("Değiştir")
        self.sekme.setExpanding(False)
        self.sekme.currentChanged.connect(self._sekme_degisti)

        self.bul_metni = QLineEdit()
        self.degistir_metni = QLineEdit()
        self.degistir_etiketi = QLabel("Yeni metin:")
        form = QFormLayout()
        form.addRow("Aranan:", self.bul_metni)
        form.addRow(self.degistir_etiketi, self.degistir_metni)

        self.secenek_dugmesi = QPushButton("Seçenekler >>")
        self.secenek_dugmesi.setCheckable(True)
        self.secenek_dugmesi.toggled.connect(self._secenekleri_goster)
        self.kapsam = QComboBox()
        self.kapsam.addItems(["Sayfa", "Çalışma Kitabı"])
        self.yon = QComboBox()
        self.yon.addItems(["Satırlarda", "Sütunlarda"])
        self.bakilan = QComboBox()
        self.bakilan.addItems(["Formüller", "Değerler", "Notlar"])
        self.bakilan.currentIndexChanged.connect(self._dugmeleri_guncelle)
        self.buyuk_kucuk = QCheckBox("Büyük/küçük harf eşleştir")
        self.tam_hucre = QCheckBox("Hücre içeriğinin tamamını eşleştir")
        self.secenekler = QWidget()
        sg = QGridLayout(self.secenekler)
        sg.setContentsMargins(0, 0, 0, 0)
        sg.addWidget(QLabel("İçinde:"), 0, 0)
        sg.addWidget(self.kapsam, 0, 1)
        sg.addWidget(QLabel("Ara:"), 1, 0)
        sg.addWidget(self.yon, 1, 1)
        sg.addWidget(QLabel("Bakılacak yer:"), 2, 0)
        sg.addWidget(self.bakilan, 2, 1)
        sg.addWidget(self.buyuk_kucuk, 3, 0, 1, 2)
        sg.addWidget(self.tam_hucre, 4, 0, 1, 2)
        self.secenekler.setVisible(False)

        self.tumunu_bul_dugmesi = QPushButton("Tümünü Bul")
        self.sonrakini_bul_dugmesi = QPushButton("Sonrakini Bul")
        self.degistir_dugmesi = QPushButton("Değiştir")
        self.tumunu_degistir_dugmesi = QPushButton("Tümünü Değiştir")
        self.kapat_dugmesi = QPushButton("Kapat")
        self.sonrakini_bul_dugmesi.setDefault(True)
        self.tumunu_bul_dugmesi.clicked.connect(self.tumunu_bul)
        self.sonrakini_bul_dugmesi.clicked.connect(lambda: self.sonrakini_bul())
        self.degistir_dugmesi.clicked.connect(self.degistir)
        self.tumunu_degistir_dugmesi.clicked.connect(self.tumunu_degistir)
        self.kapat_dugmesi.clicked.connect(self.close)
        dugmeler = QHBoxLayout()
        for d in (self.secenek_dugmesi,):
            dugmeler.addWidget(d)
        dugmeler.addStretch(1)
        for d in (self.tumunu_degistir_dugmesi, self.degistir_dugmesi, self.tumunu_bul_dugmesi,
                  self.sonrakini_bul_dugmesi, self.kapat_dugmesi):
            dugmeler.addWidget(d)

        self.sonuclar = QTreeWidget()
        self.sonuclar.setHeaderLabels(["Çalışma kitabı", "Sayfa", "Hücre", "Değer", "Formül"])
        self.sonuclar.setRootIsDecorated(False)
        self.sonuclar.setVisible(False)
        self.sonuclar.itemClicked.connect(self._sonuca_git)
        self.durum = QLabel("")

        ana = QVBoxLayout(self)
        ana.addWidget(self.sekme)
        ana.addLayout(form)
        ana.addWidget(self.secenekler)
        ana.addLayout(dugmeler)
        ana.addWidget(self.durum)
        ana.addWidget(self.sonuclar)
        self._eslesmeler: List[Tuple[Sayfa, int, int]] = []
        self._kisit = None            # (sayfa, [Aralik]) çok hücreli seçim içinde arama
        self._son_git = None
        self.resize(560, 190)
        self._sekme_degisti(0)

    # ------------------------------------------------------------------ görünüm
    def ac(self, degistir: bool = False) -> None:
        """Pencereyi açar (Ctrl+F → Bul, Ctrl+H → Değiştir); etkin hücre metni aranan alanına ÖNERİLMEZ
        (Excel de son aranan metni korur)."""
        self.sekme.setCurrentIndex(1 if degistir else 0)
        self.show()
        self.raise_()
        self.activateWindow()
        self.bul_metni.setFocus()
        self.bul_metni.selectAll()

    def _sekme_degisti(self, i: int) -> None:
        d = i == 1
        for w in (self.degistir_metni, self.degistir_etiketi, self.degistir_dugmesi,
                  self.tumunu_degistir_dugmesi):
            w.setVisible(d)
        self.adjustSize()
        self._dugmeleri_guncelle()

    def _secenekleri_goster(self, acik: bool) -> None:
        self.secenekler.setVisible(acik)
        self.secenek_dugmesi.setText("Seçenekler <<" if acik else "Seçenekler >>")
        self.adjustSize()

    def _dugmeleri_guncelle(self) -> None:
        formul = self.bakilan.currentIndex() == 0
        self.degistir_dugmesi.setEnabled(formul)           # Excel: değiştirme yalnız Formüller'de
        self.tumunu_degistir_dugmesi.setEnabled(formul)

    # ------------------------------------------------------------------ arama
    def secenek(self) -> BulSecenek:
        return BulSecenek(
            self.bul_metni.text(), self.buyuk_kucuk.isChecked(), self.tam_hucre.isChecked(),
            ("formul", "deger", "not")[self.bakilan.currentIndex()],
            "kitap" if self.kapsam.currentIndex() == 1 else "sayfa",
            "sutun" if self.yon.currentIndex() == 1 else "satir")

    def _secim(self):
        """Aranacak seçim: çok hücreli seçim varsa o (ve hatırlanır); arama etkin hücreyi seçim içinde
        ilerlettiğinden seçim tek hücreye iner — bu durumda önceki kısıt, etkin hücre hâlâ bizim
        gittiğimiz hücreyse sürer (Excel: seçim içinde aranırken seçim korunur)."""
        g = self.pencere.izgara()
        sec = g.secimler
        if not (len(sec) == 1 and sec[0].ilk_satir == sec[0].son_satir
                and sec[0].ilk_sutun == sec[0].son_sutun):
            self._kisit = (g.sayfa, list(sec))
            return sec
        if self._kisit is not None and self._son_git == (g.sayfa, *g.aktif) and self._kisit[0] is g.sayfa:
            return self._kisit[1]
        self._kisit = None
        return None

    def _eslesme_listesi(self, baslangic=True) -> List[Tuple[Sayfa, int, int]]:
        g = self.pencere.izgara()
        return list(eslesmeler(self.pencere.kitap, g.sayfa, self._secim(), self.secenek(), metin_al,
                               g.aktif if baslangic else None))

    def sonrakini_bul(self, ters: bool = False) -> bool:
        if not self.bul_metni.text():
            self.bul_metni.setFocus()
            return False
        g = self.pencere.izgara()
        liste = self._eslesme_listesi()
        if not liste:
            self.durum.setText(BULUNAMADI)
            self._bilgi(BULUNAMADI)
            return False
        if ters:
            hedef = liste[-1]
            if hedef[0] is g.sayfa and (hedef[1], hedef[2]) == g.aktif and len(liste) > 1:
                hedef = liste[-2]
        else:
            hedef = liste[0]
        self.durum.setText("")
        self._git(*hedef)
        return True

    def _bilgi(self, ileti: str) -> None:
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            return                                         # testlerde kipli ileti penceresi açılmaz
        QMessageBox.information(self, APP_NAME, ileti)

    def _git(self, sayfa: Sayfa, satir: int, sutun: int) -> None:
        """Hücreyi etkinleştirir (gerekirse sayfayı değiştirir)."""
        kisit = self._secim()                 # sec() seçimi bozmadan önce kısıtı yakala
        p = self.pencere
        if sayfa is not p.izgara().sayfa:
            p.sekmeler.setCurrentIndex(p.kitap.sayfalar.index(sayfa))
        p.izgara().sec((satir, sutun))
        self._son_git = (sayfa, satir, sutun)
        if kisit is None:
            self._kisit = None

    def tumunu_bul(self) -> None:
        self.sonuclar.clear()
        if not self.bul_metni.text():
            return
        liste = self._eslesme_listesi(baslangic=False)
        self._eslesmeler = liste
        for s, r, c in liste:
            from ..model.adres import hucre_yaz
            h = s.hucre(r, c)
            deger = gorunen_metin(s, r, c) or ""
            formul = hucre_metni(h, s.kitap) if (h is not None and h.formul is not None) else ""
            if self.secenek().bakilan == "not":
                deger = not_metni(s, r, c) or ""
            oge = QTreeWidgetItem([self.pencere.belge_adi, s.ad, hucre_yaz(r, c), deger, formul])
            oge.setData(0, Qt.UserRole, (s, r, c))
            self.sonuclar.addTopLevelItem(oge)
        self.sonuclar.setVisible(True)
        self.durum.setText(f"{len(liste)} hücre bulundu." if liste else BULUNAMADI)
        for i in range(5):
            self.sonuclar.resizeColumnToContents(i)
        self.resize(max(self.width(), 560), 190 + 160)

    def _sonuca_git(self, oge: QTreeWidgetItem, _kolon: int = 0) -> None:
        veri = oge.data(0, Qt.UserRole)
        if veri:
            self._git(*veri)

    # ------------------------------------------------------------------ değiştirme
    def _calistir(self, bulunanlar) -> Tuple[int, int]:
        """Eşleşenleri değiştirir (tek geri al adımı). Döner: (değişen hücre, atlanan)."""
        sec = self.secenek()
        plan, atlanan = degistirme_plani(bulunanlar, sec, self.degistir_metni.text(), metin_al, coz)
        komut = degistir_komutu(plan)
        if komut is not None:
            self.pencere.yigin.calistir(komut)
            self.pencere.izgara()._guncelle()
        return sum(len(v) for v in plan.values()), atlanan

    def tumunu_degistir(self) -> None:
        if not self.bul_metni.text() or self.bakilan.currentIndex() != 0:
            return
        n, atlanan = self._calistir(self._eslesme_listesi(baslangic=False))
        ileti = f"{n} hücre değiştirildi." if n else BULUNAMADI
        if atlanan:
            ileti += f" {atlanan} hücrede formül geçersiz olacağı için değiştirilmedi."
        self.durum.setText(ileti)
        if n or atlanan:
            self._bilgi(ileti)

    def degistir(self) -> None:
        """Etkin hücre eşleşiyorsa onu değiştirir, sonra sonrakini bulur; eşleşmiyorsa yalnız bulur."""
        if not self.bul_metni.text() or self.bakilan.currentIndex() != 0:
            return
        g = self.pencere.izgara()
        sec = self.secenek()
        aktif = (g.sayfa, *g.aktif)
        liste = list(eslesmeler(self.pencere.kitap, g.sayfa, None, sec, metin_al, None))
        if aktif in liste:
            n, atlanan = self._calistir([aktif])
            if atlanan and not n:
                self.durum.setText("Bu hücrede formül geçersiz olacağı için değiştirilmedi.")
                self._bilgi(self.durum.text())
        self.sonrakini_bul()
