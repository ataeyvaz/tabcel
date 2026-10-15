"""Şablon Sihirbazı (Faz 10d): ne yapmak istediğinizi yazın → şablon seçin → birkaç evet/hayır soru → önizleme → Oluştur.
Mantık `sablon/` paketindedir (eşleştirme, üretim); burada yalnız arayüz vardır. Tasarım: `sablon_tasarim.md` §3.7, §7.
Yapay zekâ ve bulut yok: eşleştirme anahtar kelimelerle yerelde yapılır (kural 6)."""
import os
from typing import Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPlainTextEdit, QPushButton, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from .. import APP_NAME
from ..sablon import eslestirici, yukleyici
from ..sablon.uretici import UretimHatasi, UretimSonucu, bayraklari_coz, uret
from . import theme

ONIZLEME_SATIRI = 6
SAYFA_SECIM, SAYFA_SORULAR, SAYFA_ONIZLEME = 0, 1, 2


def _soluk(metin: str) -> QLabel:
    e = QLabel(metin)
    e.setWordWrap(True)
    e.setStyleSheet(f"color: {theme.TEXT_MUTED};")
    return e


class SablonlarPenceresi(QDialog):
    """Yüklenen şablonlar ve yükleme raporu (hatalı kullanıcı dosyaları burada nedeniyle listelenir)."""

    def __init__(self, depo, yenile, ust=None):
        super().__init__(ust)
        self.setWindowTitle("Şablonlar")
        self.setMinimumSize(620, 460)
        self.depo, self._yenile = depo, yenile
        d = QVBoxLayout(self)
        self.liste = QListWidget()
        d.addWidget(self.liste, 2)
        d.addWidget(QLabel("Yükleme raporu:"))
        self.rapor = QPlainTextEdit()
        self.rapor.setReadOnly(True)
        d.addWidget(self.rapor, 2)
        d.addWidget(_soluk(f"Kendi şablonlarınızı {self.klasor()} klasörüne koyabilirsiniz (akislar\\ ve moduller\\ "
                           "alt klasörlerinde .json). Hatalı dosyalar atlanır; nedeni yukarıda yazılır."))
        duz = QHBoxLayout()
        self.yeni_dugme = QPushButton("Yeni şablon…")
        self.duzenle_dugme = QPushButton("Düzenle…")
        self.kopya_dugme = QPushButton("Kopyasını düzenle…")
        self.sil_dugme = QPushButton("Sil…")
        for b in (self.yeni_dugme, self.duzenle_dugme, self.kopya_dugme, self.sil_dugme):
            b.setAutoDefault(False)
            duz.addWidget(b)
        duz.addStretch(1)
        d.addLayout(duz)
        alt = QHBoxLayout()
        self.klasor_ac = QPushButton("Klasörü Aç")
        self.yenile = QPushButton("Yenile")
        kapat = QPushButton("Kapat")
        alt.addWidget(self.klasor_ac)
        alt.addWidget(self.yenile)
        alt.addStretch(1)
        alt.addWidget(kapat)
        d.addLayout(alt)
        self.yeni_dugme.clicked.connect(lambda: self.yeni_sablon())
        self.duzenle_dugme.clicked.connect(lambda: self.duzenle())
        self.kopya_dugme.clicked.connect(lambda: self.kopyasini_duzenle())
        self.sil_dugme.clicked.connect(lambda: self.sil())
        self.liste.currentRowChanged.connect(lambda _i: self._dugmeleri_guncelle())
        self.klasor_ac.clicked.connect(self._klasoru_ac)
        self.yenile.clicked.connect(self._yenilendi)
        kapat.clicked.connect(self.accept)
        self._doldur()
        if self.liste.count():
            self.liste.setCurrentRow(0)

    @staticmethod
    def klasor() -> str:
        return str(yukleyici.kullanici_klasoru())

    def _doldur(self) -> None:
        self.liste.clear()
        for s in self.depo.sablonlar:
            kaynak = "yerleşik" if s.kaynak == yukleyici.YERLESIK else "sizin"
            self.liste.addItem(f"{s.etiket}  ·  {s.akis.kategori}  ·  {kaynak}")
        self.rapor.setPlainText(self.depo.rapor.metin() or f"{self.depo.rapor.yuklenen} şablon yüklendi; sorun yok.")
        self._dugmeleri_guncelle()

    def _yenilendi(self) -> None:
        self.depo = self._yenile()
        self._doldur()

    # --- Şablon Düzenleyici (Faz 11)
    def secili(self):
        i = self.liste.currentRow()
        return self.depo.sablonlar[i] if 0 <= i < len(self.depo.sablonlar) else None

    def _dugmeleri_guncelle(self) -> None:
        s = self.secili()
        self.duzenle_dugme.setEnabled(s is not None and s.kaynak == yukleyici.KULLANICI)
        self.sil_dugme.setEnabled(s is not None and s.kaynak == yukleyici.KULLANICI)
        self.kopya_dugme.setEnabled(s is not None)

    def _kullanilan_kimlikler(self):
        return {s.akis.kimlik for s in self.depo.sablonlar}

    def _duzenleyici_ac(self, taslak, uzerine_yaz: bool = False) -> bool:
        from ..sablon.duzenleme import Taslak  # noqa: F401
        from .sablon_duzenleyici import DuzenleyiciPenceresi
        pen = DuzenleyiciPenceresi(taslak, None, self, uzerine_yaz)
        self.duzenleyici = pen
        pen.exec()
        if pen.yazilan:
            self._yenilendi()
        return bool(pen.yazilan)

    def yeni_sablon(self, ad: Optional[str] = None) -> bool:
        from PySide6.QtWidgets import QInputDialog
        from ..sablon import duzenleme
        if ad is None:
            ad, ok = QInputDialog.getText(self, "Yeni şablon", "Şablonun adı:", text="Benim şablonum")
            if not ok or not ad.strip():
                return False
        return self._duzenleyici_ac(duzenleme.bos_taslak(ad.strip(), "Diğer", self._kullanilan_kimlikler()))

    def duzenle(self) -> bool:
        from ..sablon import duzenleme
        s = self.secili()
        if s is None or s.kaynak != yukleyici.KULLANICI:
            return False
        yol = yukleyici.kullanici_klasoru() / "akislar" / f"{s.akis.kimlik}.json"
        try:
            t = duzenleme.taslak_yukle(yol)
        except duzenleme.KayitHatasi as e:
            QMessageBox.warning(self, APP_NAME, str(e))
            return False
        return self._duzenleyici_ac(t, uzerine_yaz=True)

    def kopyasini_duzenle(self, ad: Optional[str] = None) -> bool:
        from PySide6.QtWidgets import QInputDialog
        from ..sablon import duzenleme
        s = self.secili()
        if s is None:
            return False
        if ad is None:
            ad, ok = QInputDialog.getText(self, "Kopyasını düzenle", "Kopyanın adı:", text=s.akis.ad + " (benim)")
            if not ok or not ad.strip():
                return False
        return self._duzenleyici_ac(duzenleme.kopya(s, ad.strip(), self._kullanilan_kimlikler()))

    def sil(self, onay: bool = False) -> bool:
        from ..sablon import duzenleme
        s = self.secili()
        if s is None or s.kaynak != yukleyici.KULLANICI:
            return False
        if not onay and QMessageBox.question(self, APP_NAME, f"“{s.akis.ad}” şablonu ve yalnız ona ait modül dosyaları silinsin mi?\n"
                                             "(Bu şablondan daha önce oluşturulmuş kitaplar etkilenmez.)",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return False
        duzenleme.kullanici_sablonu_sil(s.akis.kimlik)
        self._yenilendi()
        return True

    def _klasoru_ac(self) -> None:
        k = self.klasor()
        os.makedirs(os.path.join(k, "akislar"), exist_ok=True)
        os.makedirs(os.path.join(k, "moduller"), exist_ok=True)
        try:
            os.startfile(k)                                    # noqa: S606 — Windows Gezgini
        except (OSError, AttributeError):
            QMessageBox.information(self, APP_NAME, f"Klasör: {k}")


class SihirbazPenceresi(QDialog):
    def __init__(self, depo=None, ust=None):
        super().__init__(ust)
        self.setWindowTitle("Şablondan Yeni")
        self.setMinimumSize(700, 520)
        self.depo = depo if depo is not None else yukleyici.depo_yukle()
        self.secili = None                                      # yukleyici.Sablon
        self.sonuc: Optional[UretimSonucu] = None
        self.soru_kutulari: Dict[str, QCheckBox] = {}
        self.emin_kutulari: Dict[str, QCheckBox] = {}
        self.soru_satirlari: Dict[str, QWidget] = {}
        self._kur()
        self._listeyi_doldur(self.depo.sablonlar, None)
        self._dugmeleri_guncelle()

    # ------------------------------------------------------------------ kurulum
    def _kur(self) -> None:
        d = QVBoxLayout(self)
        self.yigin = QStackedWidget()
        d.addWidget(self.yigin, 1)
        self.yigin.addWidget(self._secim_sayfasi())
        self.yigin.addWidget(self._soru_sayfasi())
        self.yigin.addWidget(self._onizleme_sayfasi())
        alt = QHBoxLayout()
        self.sablonlar_dugmesi = QPushButton("Şablonlar…")
        self.geri = QPushButton("‹ Geri")
        self.ileri = QPushButton("İleri ›")
        self.olustur = QPushButton("Oluştur")
        self.olustur.setDefault(True)
        iptal = QPushButton("İptal")
        alt.addWidget(self.sablonlar_dugmesi)
        alt.addStretch(1)
        for b in (self.geri, self.ileri, self.olustur, iptal):
            alt.addWidget(b)
        d.addLayout(alt)
        self.sablonlar_dugmesi.clicked.connect(self._sablonlar_ac)
        self.geri.clicked.connect(self.geri_git)
        self.ileri.clicked.connect(self.ileri_git)
        self.olustur.clicked.connect(self._olustur)
        iptal.clicked.connect(self.reject)

    def _secim_sayfasi(self) -> QWidget:
        s = QWidget()
        d = QVBoxLayout(s)
        d.addWidget(QLabel("<b>Ne yapmak istiyorsunuz?</b>"))
        self.girdi = QLineEdit()
        self.girdi.setPlaceholderText("ör. stok takibi yapmak istiyorum")
        self.girdi.setClearButtonEnabled(True)
        d.addWidget(self.girdi)
        self.kategori_satiri = QHBoxLayout()
        self.kategori_dugmeleri: Dict[Optional[str], QPushButton] = {}
        d.addLayout(self.kategori_satiri)
        self._kategori_dugmeleri_kur()
        self.liste_basligi = _soluk("")
        d.addWidget(self.liste_basligi)
        self.liste = QListWidget()
        d.addWidget(self.liste, 1)
        self.secim_ayrinti = _soluk("")
        self.secim_ayrinti.setMinimumHeight(48)
        d.addWidget(self.secim_ayrinti)
        self.girdi.textChanged.connect(self._metin_degisti)
        self.liste.currentRowChanged.connect(self._liste_secimi)
        self.liste.itemDoubleClicked.connect(lambda _i: self.ileri_git())
        return s

    def _soru_sayfasi(self) -> QWidget:
        s = QWidget()
        self.soru_duzeni = QVBoxLayout(s)
        self.soru_basligi = QLabel("")
        self.soru_duzeni.addWidget(self.soru_basligi)
        self.soru_alani = QVBoxLayout()
        self.soru_duzeni.addLayout(self.soru_alani)
        self.soru_duzeni.addStretch(1)
        return s

    def _onizleme_sayfasi(self) -> QWidget:
        s = QWidget()
        d = QVBoxLayout(s)
        self.onizleme_basligi = QLabel("")
        self.onizleme_basligi.setWordWrap(True)
        d.addWidget(self.onizleme_basligi)
        self.sayfa_secici = QComboBox()
        d.addWidget(self.sayfa_secici)
        self.onizleme_tablosu = QTableWidget()
        self.onizleme_tablosu.setEditTriggers(QTableWidget.NoEditTriggers)
        self.onizleme_tablosu.setSelectionMode(QTableWidget.NoSelection)
        d.addWidget(self.onizleme_tablosu, 1)
        self.ornek_kutusu = QCheckBox("Örnek verilerle başlat (sonra silebilirsiniz)")
        d.addWidget(self.ornek_kutusu)
        self.onizleme_notu = _soluk("")
        d.addWidget(self.onizleme_notu)
        self.sayfa_secici.currentIndexChanged.connect(self._onizleme_tablosunu_doldur)
        return s

    def _kategori_dugmeleri_kur(self) -> None:
        while self.kategori_satiri.count():
            oge = self.kategori_satiri.takeAt(0).widget()
            if oge is not None:
                oge.deleteLater()
        self.kategori_dugmeleri = {}
        kategoriler = sorted({s.akis.kategori for s in self.depo.sablonlar}, key=eslestirici.katla)
        for k in [None] + kategoriler:
            b = QPushButton("Tümü" if k is None else k)
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, kat=k: self.kategori_sec(kat))
            self.kategori_satiri.addWidget(b)
            self.kategori_dugmeleri[k] = b
        self.kategori_satiri.addStretch(1)

    # ------------------------------------------------------------------ 1. sayfa: seçim
    def _listeyi_doldur(self, sablonlar, baslik: Optional[str]) -> None:
        self.liste.blockSignals(True)
        self.liste.clear()
        for s in sablonlar:
            o = QListWidgetItem(f"{s.etiket}  —  {s.akis.aciklama}")
            o.setData(Qt.UserRole, s.ic_kimlik)
            self.liste.addItem(o)
        self.liste.blockSignals(False)
        self.liste_basligi.setText(baslik or "")
        self.liste_basligi.setVisible(bool(baslik))
        if self.liste.count():
            self.liste.setCurrentRow(0)
        else:
            self.secili = None
            self.secim_ayrinti.setText("")
            self._dugmeleri_guncelle()

    def _metin_degisti(self, metin: str) -> None:
        for b in self.kategori_dugmeleri.values():
            b.setChecked(False)
        if not metin.strip():
            self._listeyi_doldur(self.depo.sablonlar, None)
            return
        akis_haritasi = {id(s.akis): s for s in self.depo.sablonlar}
        oneriler = eslestirici.oneri(metin, [s.akis for s in self.depo.sablonlar])
        if oneriler:
            self._listeyi_doldur([akis_haritasi[id(e.akis)] for e in oneriler], "Size uygun görünen şablonlar:")
        else:
            self._listeyi_doldur(self.depo.sablonlar, "Eşleşen şablon bulunamadı. Aşağıdan bir kategori ya da şablon seçebilirsiniz:")

    def kategori_sec(self, kategori: Optional[str]) -> None:
        for k, b in self.kategori_dugmeleri.items():
            b.setChecked(k == kategori)
        self.girdi.blockSignals(True)
        self.girdi.clear()
        self.girdi.blockSignals(False)
        liste = [s for s in self.depo.sablonlar if kategori is None or s.akis.kategori == kategori]
        self._listeyi_doldur(liste, None if kategori is None else f"{kategori} şablonları:")

    def _liste_secimi(self, i: int) -> None:
        o = self.liste.item(i) if i >= 0 else None
        self.secili = self.depo.bul(o.data(Qt.UserRole)) if o is not None else None
        if self.secili is None:
            self.secim_ayrinti.setText("")
        else:
            sayfalar = ", ".join(self.secili.moduller[m].sayfa_adi for m, _ in self.secili.akis.moduller)
            self.secim_ayrinti.setText(f"{self.secili.akis.aciklama}\nSayfalar (cevaplarınıza göre değişir): {sayfalar}")
        self._dugmeleri_guncelle()

    def sec_sablon(self, ic_kimlik: str) -> bool:
        """Listede (görünüyorsa) şablonu seçer; görünmüyorsa tüm şablonları gösterip seçer."""
        for _ in range(2):
            for i in range(self.liste.count()):
                if self.liste.item(i).data(Qt.UserRole) == ic_kimlik:
                    self.liste.setCurrentRow(i)
                    return True
            self.kategori_sec(None)
        return False

    # ------------------------------------------------------------------ 2. sayfa: sorular
    def _sorulari_kur(self) -> None:
        while self.soru_alani.count():
            oge = self.soru_alani.takeAt(0).widget()
            if oge is not None:
                oge.deleteLater()
        self.soru_kutulari, self.emin_kutulari, self.soru_satirlari = {}, {}, {}
        akis = self.secili.akis
        self.soru_basligi.setText(f"<b>{self.secili.etiket}</b> için birkaç soru" if akis.sorular
                                  else f"<b>{self.secili.etiket}</b> için soru yok; İleri'ye basın.")
        for s in akis.sorular:
            satir = QWidget()
            d = QVBoxLayout(satir)
            d.setContentsMargins(0, 6, 0, 6)
            k = QCheckBox(s.metin)
            k.setChecked(s.varsayilan)
            d.addWidget(k)
            if s.aciklama:
                d.addWidget(_soluk(s.aciklama))
            if s.emin_degilim:
                e = QCheckBox("Emin değilim, siz seçin")
                e.toggled.connect(lambda acik, kutu=k, soru=s: self._emin_degisti(kutu, soru, acik))
                d.addWidget(e)
                self.emin_kutulari[s.kimlik] = e
            k.toggled.connect(lambda _a: self._soru_gorunurlugu())
            self.soru_kutulari[s.kimlik] = k
            self.soru_satirlari[s.kimlik] = satir
            self.soru_alani.addWidget(satir)
        self._soru_gorunurlugu()

    def _emin_degisti(self, kutu: QCheckBox, soru, acik: bool) -> None:
        if acik:
            kutu.setChecked(soru.varsayilan)                    # önerilen (varsayılan) cevap
        kutu.setEnabled(not acik)

    def _soru_gorunurlugu(self) -> None:
        """`eger`i yanlış sorular gizlenir (cevapları False sayılır)."""
        deger: Dict[str, bool] = {}
        for s in self.secili.akis.sorular:
            gorunur = True
            if s.eger:
                gorunur = deger.get(s.eger.lstrip("!"), False) != s.eger.startswith("!")
            self.soru_satirlari[s.kimlik].setVisible(gorunur)
            deger[s.kimlik] = bool(self.soru_kutulari[s.kimlik].isChecked()) and gorunur
        for bayrak, soru in self.secili.akis.bayraklar.items():
            deger[bayrak] = deger.get(soru, False)

    def cevaplar(self) -> Dict[str, bool]:
        return {k: c.isChecked() for k, c in self.soru_kutulari.items()}

    # ------------------------------------------------------------------ 3. sayfa: önizleme
    def _onizleme_kur(self) -> bool:
        try:
            sonuc = uret(self.secili, self.cevaplar(), ornek_veri=True)
        except UretimHatasi as e:
            QMessageBox.warning(self, APP_NAME, str(e))
            return False
        self._onizleme_sonucu = sonuc
        sayfalar = [s for s in sonuc.kitap.sayfalar]
        self.onizleme_basligi.setText(
            f"<b>{self.secili.etiket}</b>: {len(sayfalar)} sayfa oluşturulacak. Aşağıda her sayfanın ilk satırları görünür.")
        self.sayfa_secici.blockSignals(True)
        self.sayfa_secici.clear()
        self.sayfa_secici.addItems([s.ad for s in sayfalar])
        self.sayfa_secici.blockSignals(False)
        self.ornek_kutusu.setChecked(self.secili.akis.ornek_veri)
        self.ornek_kutusu.setEnabled(any(m.ornek_veri for m in self.secili.moduller.values()))
        self.onizleme_notu.setText("Hesaplanan sütunlar (ƒ) ve açılır listeler tabloda kendiliğinden çalışır. "
                                   "Oluşturduktan sonra her şey düzenlenebilir.")
        self._onizleme_tablosunu_doldur()
        return True

    def _onizleme_tablosunu_doldur(self, _i: int = 0) -> None:
        sonuc = getattr(self, "_onizleme_sonucu", None)
        i = self.sayfa_secici.currentIndex()
        if sonuc is None or i < 0:
            return
        sayfa = sonuc.kitap.sayfalar[i]
        kul = sayfa.kullanilan_aralik()
        t = self.onizleme_tablosu
        t.clear()
        if kul is None:
            t.setRowCount(0)
            t.setColumnCount(0)
            return
        son_sutun = kul[3]
        satirlar = min(kul[2], ONIZLEME_SATIRI + 1)
        t.setColumnCount(son_sutun)
        t.setRowCount(max(0, satirlar - 1))
        t.setHorizontalHeaderLabels([self._gorunen(sayfa.hucre(1, c)) for c in range(1, son_sutun + 1)])
        for r in range(2, satirlar + 1):
            for c in range(1, son_sutun + 1):
                h = sayfa.hucre(r, c)
                if h is None:
                    continue
                o = QTableWidgetItem("ƒ" if h.formul is not None else self._gorunen(h))
                t.setItem(r - 2, c - 1, o)
        t.resizeColumnsToContents()

    @staticmethod
    def _gorunen(h) -> str:
        if h is None or h.deger is None:
            return ""
        v = h.deger
        return str(int(v)) if isinstance(v, float) and v == int(v) else str(v)

    # ------------------------------------------------------------------ gezinme
    def ileri_git(self) -> None:
        i = self.yigin.currentIndex()
        if i == SAYFA_SECIM and self.secili is not None:
            self._sorulari_kur()
            self.yigin.setCurrentIndex(SAYFA_SORULAR)
        elif i == SAYFA_SORULAR:
            if self._onizleme_kur():
                self.yigin.setCurrentIndex(SAYFA_ONIZLEME)
        self._dugmeleri_guncelle()

    def geri_git(self) -> None:
        i = self.yigin.currentIndex()
        if i > 0:
            self.yigin.setCurrentIndex(i - 1)
        self._dugmeleri_guncelle()

    def _dugmeleri_guncelle(self) -> None:
        i = self.yigin.currentIndex()
        self.geri.setVisible(i > 0)
        self.ileri.setVisible(i < SAYFA_ONIZLEME)
        self.ileri.setEnabled(self.secili is not None)
        self.olustur.setVisible(i == SAYFA_ONIZLEME)
        self.olustur.setDefault(i == SAYFA_ONIZLEME)
        self.ileri.setDefault(i < SAYFA_ONIZLEME)

    def _olustur(self) -> None:
        try:
            self.sonuc = uret(self.secili, self.cevaplar(), ornek_veri=self.ornek_kutusu.isChecked())
        except UretimHatasi as e:
            QMessageBox.warning(self, APP_NAME, str(e))
            return
        self.accept()

    # ------------------------------------------------------------------ şablonlar penceresi
    def depoyu_yenile(self):
        self.depo = yukleyici.depo_yukle()
        self._kategori_dugmeleri_kur()
        self.kategori_sec(None)
        return self.depo

    def _sablonlar_ac(self) -> None:
        SablonlarPenceresi(self.depo, self.depoyu_yenile, self).exec()
