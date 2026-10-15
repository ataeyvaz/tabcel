"""Şablon kayıt formu (Faz 10f): şablon tablosundaki her kayıt için otomatik form. Mantık/kural `sablon/kayitlar.py`da (Qt yok).

- Form ayrı veri tutmaz: tablonun veri bölgesini okur/yazar; kayıt = tek `HucrelerDegis` komutu → tek geri al adımı; tablodaki
  düzenleme de aynı yığına girer. Alan kuralları tablodaki hücre doğrulamasıdır, satır kuralları tanımdaki formüldür (kural 21).
- Klavye: Enter = sonraki alan (son alanda Kaydet), Ctrl+Enter = Kaydet ve yeni, Ctrl+PgUp/PgDn = önceki/sonraki kayıt,
  Ctrl+F = kayıt ara, Esc = kapat. Hata iletisi alanın altında; `durdur` ihlali kaydı engeller, `uyar` onayla geçilir.
"""
from typing import Dict, List, Optional

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCalendarWidget, QCheckBox, QComboBox, QCompleter, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMenu,
    QMessageBox, QPushButton, QScrollArea, QToolButton, QVBoxLayout, QWidget, QWidgetAction,
)

from ..formul import kosul
from ..metin_tr import kucuk
from ..model.adres import Aralik
from ..model.komutlar import HucrelerDegis
from ..model.tarihseri import seri_ymd, ymd_seri
from ..sablon import kayitlar
from . import theme

HATA_RENGI = "#c00000"


class _Alan:
    """Bir sütunun form bileşeni + hata etiketi."""

    def __init__(self, sutun, kutu: QWidget, hata: QLabel, satir_kutusu: QWidget):
        self.sutun, self.kutu, self.hata, self.satir_kutusu = sutun, kutu, hata, satir_kutusu

    def metin(self) -> str:
        k = self.kutu
        if isinstance(k, QCheckBox):
            return "Evet" if k.isChecked() else "Hayır"
        if isinstance(k, QComboBox):
            return k.currentText()
        if isinstance(k, QLabel):
            return k.text()
        return k.text()

    def yaz(self, metin: str) -> None:
        k = self.kutu
        if isinstance(k, QCheckBox):
            k.setChecked(kucuk(metin) in ("evet", "e", "1"))
        elif isinstance(k, QComboBox):
            i = k.findText(metin, Qt.MatchFixedString)
            if i >= 0:
                k.setCurrentIndex(i)
            else:
                k.setCurrentText(metin)
        else:
            k.setText(metin)

    def hata_yaz(self, ileti: str) -> None:
        self.hata.setText(ileti)
        self.hata.setVisible(bool(ileti))


class SablonFormu(QDialog):
    """Pencere ile birlikte yaşayan, kalıcı (modalsız) form. `ac(modul=None, satir=None)` ile gösterilir."""
    kaydedildi = Signal()

    def __init__(self, pencere):
        super().__init__(pencere)
        self.pencere = pencere
        self.setWindowTitle("Kayıt Formu")
        self.setModal(False)
        self.setMinimumWidth(460)
        self.b: Optional[kayitlar.Baglam] = None
        self.g: Optional[kayitlar.ModulGorunumu] = None
        self.satir: Optional[int] = None           # None = yeni kayıt
        self.kayit_satirlari: List[int] = []
        self.alanlar: Dict[str, _Alan] = {}
        self._ilk: Dict[str, str] = {}             # yüklendiği andaki metinler (çakışma + kirli denetimi)
        self._yukleniyor = False
        self._kaydediyor = False                   # kendi yazımımızın olayı formu yeniden yüklemesin
        self._kur()

    # ------------------------------------------------------------------ kurulum
    def _kur(self) -> None:
        d = QVBoxLayout(self)
        ust = QHBoxLayout()
        self.modul_kutusu = QComboBox()
        self.modul_kutusu.currentIndexChanged.connect(self._modul_degisti)
        self.modul_etiketi = QLabel("Tablo:")
        ust.addWidget(self.modul_etiketi)
        ust.addWidget(self.modul_kutusu, 1)
        self.ara_kutusu = QLineEdit()
        self.ara_kutusu.setPlaceholderText("Kayıt ara (Ctrl+F)")
        self.ara_kutusu.setClearButtonEnabled(True)
        self.ara_kutusu.returnPressed.connect(self.ara)
        ust.addWidget(self.ara_kutusu, 1)
        d.addLayout(ust)
        gezin = QHBoxLayout()
        self.onceki = QPushButton("‹ Önceki")
        self.sonraki = QPushButton("Sonraki ›")
        self.sayac = QLabel("")
        self.sayac.setAlignment(Qt.AlignCenter)
        self.yeni_dugme = QPushButton("Yeni kayıt")
        self.onceki.clicked.connect(lambda: self.git(-1))
        self.sonraki.clicked.connect(lambda: self.git(1))
        self.yeni_dugme.clicked.connect(lambda: self.yeni_kayit())
        for w in (self.onceki, self.sayac, self.sonraki):
            gezin.addWidget(w, 1 if w is self.sayac else 0)
        gezin.addWidget(self.yeni_dugme)
        d.addLayout(gezin)
        self.kaydirma = QScrollArea()
        self.kaydirma.setWidgetResizable(True)
        self.kaydirma.setFrameShape(QScrollArea.NoFrame)
        self.icerik = QWidget()
        self.form = QFormLayout(self.icerik)
        self.form.setLabelAlignment(Qt.AlignRight)
        self.kaydirma.setWidget(self.icerik)
        d.addWidget(self.kaydirma, 1)
        self.kural_etiketi = QLabel("")
        self.kural_etiketi.setWordWrap(True)
        self.kural_etiketi.setStyleSheet(f"color: {HATA_RENGI};")
        self.kural_etiketi.setVisible(False)
        d.addWidget(self.kural_etiketi)
        self.durum = QLabel("")
        self.durum.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        d.addWidget(self.durum)
        alt = QHBoxLayout()
        self.sil_dugme = QPushButton("Sil")
        self.sil_dugme.clicked.connect(self.sil)
        self.ornek_dugme = QPushButton("Örnek verileri temizle")
        self.ornek_dugme.setToolTip("Şablonla gelen örnek kayıtları siler (kendi değiştirdiğiniz satırlara dokunmaz)")
        self.ornek_dugme.clicked.connect(self.ornekleri_temizle)
        self.kaydet_dugme = QPushButton("Kaydet")
        self.kaydet_dugme.setDefault(False)
        self.kaydet_dugme.clicked.connect(lambda: self.kaydet())
        self.kaydet_yeni_dugme = QPushButton("Kaydet ve yeni")
        self.kaydet_yeni_dugme.clicked.connect(lambda: self.kaydet(yeni=True))
        kapat = QPushButton("Kapat")
        kapat.clicked.connect(self.close)
        alt.addWidget(self.sil_dugme)
        alt.addWidget(self.ornek_dugme)
        alt.addStretch(1)
        for w in (self.kaydet_dugme, self.kaydet_yeni_dugme, kapat):
            alt.addWidget(w)
        d.addLayout(alt)
        for dugme in self.findChildren(QPushButton):
            dugme.setAutoDefault(False)                     # Enter alan gezintisi içindir; bir düğmeyi tetiklemesin
            dugme.setDefault(False)
        for tus, islev in (("Ctrl+Return", lambda: self.kaydet(yeni=True)), ("Ctrl+Enter", lambda: self.kaydet(yeni=True)),
                           ("Ctrl+PgUp", lambda: self.git(-1)), ("Ctrl+PgDown", lambda: self.git(1)),
                           ("Ctrl+F", lambda: (self.ara_kutusu.setFocus(), self.ara_kutusu.selectAll()))):
            QShortcut(QKeySequence(tus), self, activated=islev, context=Qt.WindowShortcut)

    # ------------------------------------------------------------------ açma
    def ac(self, modul: Optional[str] = None, satir: Optional[int] = None) -> bool:
        """Formu gösterir. Şablon yok / uyuşmuyorsa False (form kapalı: tablo çalışır). `satir`: o kayıtla aç."""
        self.b = kayitlar.Baglam.kur(self.pencere.kitap)
        if self.b is None:
            return False
        adaylar = [m for m in self.b.modul_kimlikleri() if self.b.gorunum(m).girdi_alanlari()]
        if not adaylar:
            return False
        if modul is None:
            g = self.b.gorunum_sayfadan(self.pencere.izgara().sayfa)
            modul = g.modul.kimlik if g is not None and g.modul.kimlik in adaylar else adaylar[0]
        self._yukleniyor = True
        self.modul_kutusu.clear()
        for m in adaylar:
            self.modul_kutusu.addItem(self.b.moduller[m].ad, m)
        self.modul_kutusu.setCurrentIndex(adaylar.index(modul))
        self.modul_etiketi.setVisible(len(adaylar) > 1)
        self.modul_kutusu.setVisible(len(adaylar) > 1)
        self._yukleniyor = False
        self._modul_kur(modul, satir)
        self.show()
        self.raise_()
        self.activateWindow()
        self._ilk_alana_odaklan()
        return True

    def _modul_degisti(self, _i: int) -> None:
        if self._yukleniyor or self.b is None:
            return
        if not self._kayit_birak():
            self._yukleniyor = True
            self.modul_kutusu.setCurrentIndex(self.modul_kutusu.findData(self.g.modul.kimlik))
            self._yukleniyor = False
            return
        self._modul_kur(self.modul_kutusu.currentData(), None)

    def _modul_kur(self, modul: str, satir: Optional[int]) -> None:
        self.g = self.b.gorunum(modul)
        self.setWindowTitle(f"{self.g.modul.tekil_ad or self.g.modul.ad} — Kayıt Formu")
        self._alanlari_kur()
        self.kayit_satirlari = kayitlar.kayit_satirlari(self.g)
        if satir is not None and satir in self.kayit_satirlari:
            self.kayda_git(satir)
        elif self.kayit_satirlari:
            self.kayda_git(self.kayit_satirlari[0])
        else:
            self.yeni_kayit(onay=False)

    def _alanlari_kur(self) -> None:
        while self.form.rowCount():
            self.form.removeRow(0)
        self.alanlar = {}
        onceki = None
        for s in self.g.alanlar():
            kutu = self._kutu_olustur(s)
            hata = QLabel("")
            hata.setWordWrap(True)
            hata.setStyleSheet(f"color: {HATA_RENGI}; font-size: 11px;")
            hata.setVisible(False)
            kolon = QWidget()
            v = QVBoxLayout(kolon)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(1)
            v.addWidget(kutu)
            v.addWidget(hata)
            etiket = s.ad + (" *" if s.zorunlu else "")
            if s.aciklama:
                kutu.setToolTip(s.aciklama)
            self.form.addRow(etiket, kolon)
            self.alanlar[s.kimlik] = _Alan(s, kutu, hata, kolon)
            if s.tur != "hesaplanan":
                if isinstance(kutu, QLineEdit) or hasattr(kutu, "metin_kutusu"):
                    kutu.returnPressed.connect(lambda k=s.kimlik: self._enter(k))
                    kutu.textChanged.connect(self._degisti)
                elif isinstance(kutu, QComboBox):
                    kutu.currentTextChanged.connect(self._degisti)
                elif isinstance(kutu, QCheckBox):
                    kutu.toggled.connect(self._degisti)
                kutu.installEventFilter(self)
                if onceki is not None:
                    self.setTabOrder(onceki, kutu)
                onceki = kutu
        self._ilk = self._mevcut_metinler()               # yeni kurulan boş form kirli sayılmaz

    def _kutu_olustur(self, s) -> QWidget:
        if s.tur == "hesaplanan":
            e = QLabel("")
            e.setTextInteractionFlags(Qt.TextSelectableByMouse)
            e.setStyleSheet(f"color: {theme.TEXT_MUTED};")
            return e
        if s.tur == "evet_hayir":
            return QCheckBox()
        if s.tur == "liste":
            c = QComboBox()
            c.addItem("")
            c.addItems(s.secenekler)
            return c
        if s.tur == "baglanti":
            c = QComboBox()
            c.setEditable(True)
            c.setInsertPolicy(QComboBox.NoInsert)
            c.addItem("")
            m, a = s.baglanti
            c.addItems(self._baglanti_secenekleri(s))
            q = QCompleter(c.model(), c)
            q.setCaseSensitivity(Qt.CaseInsensitive)
            q.setFilterMode(Qt.MatchContains)
            c.setCompleter(q)
            c.setCurrentIndex(0)
            return c
        e = QLineEdit()
        if s.tur == "tarih":
            e.setPlaceholderText("gg.aa.yyyy")
            sar = QWidget()
            h = QHBoxLayout(sar)
            h.setContentsMargins(0, 0, 0, 0)
            h.addWidget(e, 1)
            takvim = QToolButton()
            takvim.setText("📅")
            takvim.setToolTip("Takvimden seç")
            takvim.setAutoRaise(True)
            takvim.clicked.connect(lambda _=False, k=e, t=takvim: self._takvim_ac(k, t))
            h.addWidget(takvim)
            sar.metin_kutusu = e
            sar.setFocusProxy(e)
            return _TarihKutusu(e, sar)
        return e

    def _baglanti_secenekleri(self, s) -> List[str]:
        dv = self.g.sayfa.dogrulama(self.g.ilk_satir, self.g.sutunlar[s.kimlik])
        if dv is None:
            return []
        oge = kosul.liste_ogeleri(dv, self.g.sayfa, self.g.ilk_satir, self.g.sutunlar[s.kimlik], self.pencere.kitap)
        return sorted({o for o in (oge or []) if o}, key=kucuk)

    def _takvim_ac(self, kutu: QLineEdit, dugme: QToolButton) -> None:
        takvim = QCalendarWidget()
        takvim.setGridVisible(True)
        h = kayitlar.metinden_hucre(self.g, self.satir or self.g.ilk_satir, self._kimlik_of(kutu), kutu.text())
        if h is not None and isinstance(h.deger, float):
            y, a, g = seri_ymd(int(h.deger))
            from PySide6.QtCore import QDate
            takvim.setSelectedDate(QDate(y, a, g))
        menu = QMenu(self)
        wa = QWidgetAction(menu)
        wa.setDefaultWidget(takvim)
        menu.addAction(wa)

        def sec(tarih):
            kutu.setText(f"{tarih.day():02d}.{tarih.month():02d}.{tarih.year()}")
            menu.close()
        takvim.clicked.connect(sec)
        menu.exec(dugme.mapToGlobal(dugme.rect().bottomLeft()))

    def _kimlik_of(self, kutu) -> str:
        for k, a in self.alanlar.items():
            if a.kutu is kutu or getattr(a.kutu, "metin_kutusu", None) is kutu:
                return k
        return ""

    # ------------------------------------------------------------------ yükleme
    def _degisti(self, *_a) -> None:
        if not self._yukleniyor:
            self._durum_yaz()

    def _mevcut_metinler(self) -> Dict[str, str]:
        return {k: a.metin() for k, a in self.alanlar.items() if a.sutun.tur != "hesaplanan"}

    def kirli_mi(self) -> bool:
        return self._mevcut_metinler() != self._ilk

    def _durum_yaz(self) -> None:
        kirli = self.kirli_mi()
        n = len(self.kayit_satirlari)
        if self.satir is None:
            self.sayac.setText(f"Yeni kayıt  ({n} kayıt var)")
        else:
            self.sayac.setText(f"Kayıt {self.kayit_satirlari.index(self.satir) + 1} / {n}" if self.satir in self.kayit_satirlari
                               else f"Satır {self.satir}")
        self.durum.setText("Değişiklikler kaydedilmedi." if kirli else "")
        i = self.kayit_satirlari.index(self.satir) if self.satir in self.kayit_satirlari else -1
        self.onceki.setEnabled(self.satir is None and bool(n) or i > 0)
        self.sonraki.setEnabled(i >= 0 and i < n - 1)
        self.sil_dugme.setEnabled(self.satir is not None)
        self.ornek_dugme.setVisible(self.b is not None and bool(kayitlar.ornek_satirlari(self.b)))

    def _yukle(self, satir: Optional[int]) -> None:
        self._yukleniyor = True
        self.satir = satir
        for k, a in self.alanlar.items():
            if a.sutun.tur == "hesaplanan":
                a.kutu.setText(kayitlar.gorunen(self.g, satir, k) if satir is not None else "")
                a.hata_yaz("")
                continue
            if satir is not None:
                a.yaz(kayitlar.duzenleme_metni(self.g, satir, k))
            else:
                a.yaz(self._varsayilan_metin(a.sutun))
            a.hata_yaz("")
        self.kural_etiketi.setVisible(False)
        self._ilk = self._mevcut_metinler()
        self._yukleniyor = False
        self._durum_yaz()

    def _varsayilan_metin(self, s) -> str:
        v = s.varsayilan
        if v is None:
            return "Hayır" if s.tur == "evet_hayir" else ""
        if s.tur == "evet_hayir":
            return "Evet" if v else "Hayır"
        if isinstance(v, bool):
            return "Evet" if v else "Hayır"
        if isinstance(v, float) and v == int(v):
            return str(int(v))
        return str(v).replace(".", ",") if isinstance(v, float) else str(v)

    def _ilk_alana_odaklan(self) -> None:
        for a in self.alanlar.values():
            if a.sutun.tur != "hesaplanan":
                kutu = a.kutu
                kutu.setFocus()
                if hasattr(kutu, "selectAll"):
                    kutu.selectAll()
                break

    # ------------------------------------------------------------------ gezinme
    def _kayit_birak(self) -> bool:
        """Kaydedilmemiş değişiklik varsa sorar; devam edilebilirse True."""
        if not self.kirli_mi():
            return True
        s = QMessageBox(QMessageBox.Question, "Kayıt Formu", "Bu kayıttaki değişiklikler kaydedilmedi.",
                        QMessageBox.NoButton, self)
        kaydet = s.addButton("Kaydet", QMessageBox.AcceptRole)
        at = s.addButton("Değişiklikleri at", QMessageBox.DestructiveRole)
        s.addButton("İptal", QMessageBox.RejectRole)
        s.exec()
        if s.clickedButton() is kaydet:
            return self.kaydet(sessiz_gec=True)
        return s.clickedButton() is at

    def kayda_git(self, satir: int) -> bool:
        if not self._kayit_birak():
            return False
        self.kayit_satirlari = kayitlar.kayit_satirlari(self.g)
        self._yukle(satir)
        return True

    def git(self, yon: int) -> bool:
        if self.g is None:
            return False
        self.kayit_satirlari = kayitlar.kayit_satirlari(self.g)
        if self.satir is None:
            hedef = self.kayit_satirlari[-1] if (yon < 0 and self.kayit_satirlari) else None
        elif self.satir in self.kayit_satirlari:
            i = self.kayit_satirlari.index(self.satir) + yon
            hedef = self.kayit_satirlari[i] if 0 <= i < len(self.kayit_satirlari) else None
        else:
            hedef = None
        if hedef is None:
            return False
        return self.kayda_git(hedef)

    def yeni_kayit(self, onay: bool = True) -> bool:
        if onay and not self._kayit_birak():
            return False
        self.kayit_satirlari = kayitlar.kayit_satirlari(self.g)
        if kayitlar.yeni_satir(self.g) is None:
            QMessageBox.warning(self, "Kayıt Formu", "Tablonun veri bölgesi dolu; yeni kayıt eklenemez.")
            return False
        self._yukle(None)
        self._ilk_alana_odaklan()
        return True

    def ara(self) -> bool:
        """Kutudaki metni kayıtların görünen metinlerinde arar (Türkçe harf duyarsız, içerir); sonraki eşleşmeye gider."""
        aranan = kucuk(self.ara_kutusu.text().strip())
        if not aranan or self.g is None:
            return False
        kayitlar_ = kayitlar.kayit_satirlari(self.g)
        if not kayitlar_:
            return False
        bas = kayitlar_.index(self.satir) + 1 if self.satir in kayitlar_ else 0
        sira = kayitlar_[bas:] + kayitlar_[:bas]
        for r in sira:
            if any(aranan in kucuk(kayitlar.gorunen(self.g, r, k)) for k in self.g.sutunlar):
                self.durum.setText("")
                return self.kayda_git(r)
        self.durum.setText("Eşleşen kayıt bulunamadı.")
        return False

    # ------------------------------------------------------------------ kaydetme
    def _enter(self, kimlik: str) -> None:
        girdiler = [k for k, a in self.alanlar.items() if a.sutun.tur != "hesaplanan"]
        if kimlik == girdiler[-1]:
            self.kaydet()
        else:
            self.focusNextChild()

    def eventFilter(self, nesne, olay):
        if olay.type() == QEvent.KeyPress and olay.key() in (Qt.Key_Return, Qt.Key_Enter) \
                and not (olay.modifiers() & Qt.ControlModifier):
            for k, a in self.alanlar.items():
                if a.kutu is nesne and isinstance(nesne, (QComboBox, QCheckBox)) and a.sutun.tur != "hesaplanan":
                    self._enter(k)
                    return True
        return super().eventFilter(nesne, olay)

    def _taslak(self) -> Dict[str, object]:
        row = self.satir if self.satir is not None else kayitlar.yeni_satir(self.g)
        return {k: kayitlar.metinden_hucre(self.g, row, k, a.metin())
                for k, a in self.alanlar.items() if a.sutun.tur != "hesaplanan"}

    def denetle(self) -> List[kayitlar.Ihlal]:
        """Taslağı denetler, ihlalleri formda gösterir ve döndürür."""
        row = self.satir if self.satir is not None else kayitlar.yeni_satir(self.g)
        ihlaller = kayitlar.kayit_denetle(self.b, self.g, row, self._taslak())
        for a in self.alanlar.values():
            a.hata_yaz("")
        genel = []
        for i in ihlaller:
            if i.alan and i.alan in self.alanlar:
                self.alanlar[i.alan].hata_yaz(i.ileti)
            else:
                genel.append(i.ileti)
        self.kural_etiketi.setText("\n".join(genel))
        self.kural_etiketi.setVisible(bool(genel))
        return ihlaller

    def kaydet(self, yeni: bool = False, sessiz_gec: bool = False) -> bool:
        """Kaydeder; ihlal `durdur` ise kaydetmez (False). `uyar` ihlalleri için onay sorar (`sessiz_gec`: sorma)."""
        if self.g is None:
            return False
        ihlaller = self.denetle()
        durduran = [i for i in ihlaller if i.siddet == kayitlar.DURDUR]
        if durduran:
            ilk = next((self.alanlar[i.alan] for i in durduran if i.alan in self.alanlar), None)
            if ilk is not None:
                ilk.kutu.setFocus()
            self.durum.setText("Kayıt yapılamadı: kırmızı uyarıları düzeltin.")
            return False
        if ihlaller and not sessiz_gec:
            ileti = "\n".join(i.ileti for i in ihlaller)
            if QMessageBox.question(self, "Kayıt Formu", ileti + "\n\nYine de kaydedilsin mi?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return False
        row = self.satir if self.satir is not None else kayitlar.yeni_satir(self.g)
        if row is None:
            QMessageBox.warning(self, "Kayıt Formu", "Tablonun veri bölgesi dolu.")
            return False
        if self.satir is not None and self._baska_yerde_degisti(row):
            if QMessageBox.question(self, "Kayıt Formu", "Bu kayıt tabloda başka yerde değiştirilmiş. Üzerine yazılsın mı?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return False
        taslak = self._taslak()
        yeni_hucreler = kayitlar.yazim_haritasi(self.b, self.g, row, taslak)
        izgara = self.pencere.izgara()
        if izgara.sayfa is not self.g.sayfa:
            self.pencere.sekmeler.setCurrentIndex(self.pencere.kitap.sayfalar.index(self.g.sayfa))
            izgara = self.pencere.izgara()
        self._kaydediyor = True
        try:
            izgara.yigin.calistir(HucrelerDegis(self.g.sayfa, yeni_hucreler))
            izgara._guncelle()
        finally:
            self._kaydediyor = False
        self.kayit_satirlari = kayitlar.kayit_satirlari(self.g)
        self.kaydedildi.emit()
        if yeni:
            self._yukle(None)
            self._ilk_alana_odaklan()
        else:
            self._yukle(row)
        self.durum.setText("Kaydedildi.")
        return True

    def _baska_yerde_degisti(self, row: int) -> bool:
        guncel = {k: kayitlar.duzenleme_metni(self.g, row, k) for k, a in self.alanlar.items() if a.sutun.tur != "hesaplanan"}
        return guncel != {k: v for k, v in self._ilk.items()} and guncel != self._mevcut_metinler()

    def sil(self) -> bool:
        if self.satir is None or self.g is None:
            return False
        if QMessageBox.question(self, "Kayıt Formu", "Bu kayıt silinsin mi? (Geri alınabilir.)",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return False
        yeni = {(self.satir, self.g.sutunlar[s.kimlik]): None for s in self.g.girdi_alanlari()}
        izgara = self.pencere.izgara()
        izgara.yigin.calistir(HucrelerDegis(self.g.sayfa, yeni))
        izgara._guncelle()
        self.kayit_satirlari = kayitlar.kayit_satirlari(self.g)
        self.kaydedildi.emit()
        if self.kayit_satirlari:
            self._yukle(self.kayit_satirlari[min(len(self.kayit_satirlari) - 1, max(0, sum(1 for r in self.kayit_satirlari if r < self.satir)))])
        else:
            self._yukle(None)
        return True

    # ------------------------------------------------------------------ tablo ile canlı eşzaman
    def olay(self, olay) -> None:
        """Kitap olayları (tablo değişti): açık kayıt değiştiyse ve formda yarım düzenleme yoksa alanlar yenilenir; yarım düzenleme
        varsa kaybolmaz, uyarı yazılır (kaydedince çakışma sorulur). Satır/sütun ekle-sil'de form yeniden kurulur."""
        if self.g is None or self._kaydediyor or not self.isVisible() or olay.sayfa is not self.g.sayfa:
            return
        if olay.tur in ("hucre", "sonuc"):
            if self.satir is None:
                self.kayit_satirlari = kayitlar.kayit_satirlari(self.g)
                self._durum_yaz()
                return
            satirlar = {r for r, _ in olay["degisiklikler"]}
            self.kayit_satirlari = kayitlar.kayit_satirlari(self.g)
            if self.satir not in satirlar:
                self._durum_yaz()
                return
            if not self.kirli_mi():
                self._yukle(self.satir)
            else:
                self._hesaplananlari_yenile()
                self.durum.setText("Bu kayıt tabloda başka yerde değişti; kaydederseniz üzerine yazılır.")
        elif olay.tur == "yapi":
            if self.kirli_mi():
                self.durum.setText("Tablo yapısı değişti; kaydetmeden önce kaydı kontrol edin.")
                return
            self.ac(self.g.modul.kimlik)

    def _hesaplananlari_yenile(self) -> None:
        if self.satir is None:
            return
        for k, a in self.alanlar.items():
            if a.sutun.tur == "hesaplanan":
                a.kutu.setText(kayitlar.gorunen(self.g, self.satir, k))

    def ornekleri_temizle(self) -> bool:
        """Üretimdeki örnek kayıtları (hâlâ değişmemiş olanları) siler; tek geri al adımı. Sonradan eklenen kayıtlara dokunmaz."""
        from ..model.komutlar import Grup
        haritalar = kayitlar.ornek_temizleme_haritasi(self.b)
        if not haritalar:
            return False
        adet = sum(len({r for r, _ in h}) for _, h in haritalar)
        if QMessageBox.question(self, "Kayıt Formu", f"Şablonla gelen {adet} örnek kayıt silinsin mi? (Geri alınabilir.)",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return False
        izgara = self.pencere.izgara()
        izgara.yigin.calistir(Grup([HucrelerDegis(s, h) for s, h in haritalar]))
        izgara._guncelle()
        kayitlar.ornek_kaydini_sifirla(self.b)
        self.kayit_satirlari = kayitlar.kayit_satirlari(self.g)
        self.kaydedildi.emit()
        self._yukle(self.kayit_satirlari[0] if self.kayit_satirlari else None)
        return True

    def closeEvent(self, olay) -> None:
        if self.g is not None and not self._kayit_birak():
            olay.ignore()
            return
        super().closeEvent(olay)


class EslemePenceresi(QDialog):
    """Başlığı bulunamayan sütunlar için yeniden eşleme: her eksik sütuna tablodaki bir başlık seçilir (ya da eşlenmez)."""

    YOK = "— tabloda yok (eşleme yapma)"

    def __init__(self, durumlar, ust=None):
        super().__init__(ust)
        self.setWindowTitle("Sütunları Yeniden Eşle")
        self.setMinimumWidth(520)
        self.durumlar = durumlar
        self.kutular = {}
        d = QVBoxLayout(self)
        a = QLabel("Şablonun beklediği bazı sütun başlıkları tabloda bulunamadı (silinmiş ya da yeniden adlandırılmış olabilir). "
                   "Her biri için tablodaki karşılığını seçin; tablo ve formüller değiştirilmez.")
        a.setWordWrap(True)
        d.addWidget(a)
        f = QFormLayout()
        for dur in durumlar:
            for sk, baslik in dur.eksik:
                c = QComboBox()
                c.addItem(self.YOK)
                c.addItems(dur.adaylar)
                if baslik in dur.adaylar:
                    c.setCurrentText(baslik)
                f.addRow(f"{dur.sayfa_adi}: “{baslik}”", c)
                self.kutular[(dur.modul, sk)] = c
        d.addLayout(f)
        alt = QHBoxLayout()
        alt.addStretch(1)
        tamam, iptal = QPushButton("Eşle"), QPushButton("İptal")
        tamam.clicked.connect(self.accept)
        iptal.clicked.connect(self.reject)
        alt.addWidget(tamam)
        alt.addWidget(iptal)
        d.addLayout(alt)

    def harita(self):
        h = {}
        for (mk, sk), c in self.kutular.items():
            if c.currentText() != self.YOK:
                h.setdefault(mk, {})[sk] = c.currentText()
        return h


class _TarihKutusu(QWidget):
    """Tarih alanı: metin kutusu + takvim düğmesi (QLineEdit gibi davranır)."""

    def __init__(self, kutu: QLineEdit, kap: QWidget):
        super().__init__()
        self.metin_kutusu = kutu
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(kap)
        self.setFocusProxy(kutu)
        self.returnPressed = kutu.returnPressed
        self.textChanged = kutu.textChanged

    def text(self) -> str:
        return self.metin_kutusu.text()

    def setText(self, t: str) -> None:
        self.metin_kutusu.setText(t)

    def selectAll(self) -> None:
        self.metin_kutusu.selectAll()
