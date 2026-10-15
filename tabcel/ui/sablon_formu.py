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
    QApplication, QCalendarWidget, QCheckBox, QComboBox, QCompleter, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMenu,
    QMessageBox, QPushButton, QScrollArea, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget,
    QWidgetAction,
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
        self._donus = None                         # barkod: “yeni kayıt olarak ekle” sonrası geri dönülecek form durumu
        self._yeni_dugmeleri: Dict[str, QPushButton] = {}
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
        self.matris_dugme = QPushButton("Matris giriş…")
        self.matris_dugme.setToolTip("Beden × renk gibi çeşitleri tek tabloda girin; her dolu hücre ayrı kayıt olur")
        self.matris_dugme.clicked.connect(lambda: self.matris_ac())
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
        alt.addWidget(self.matris_dugme)
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
                           ("Ctrl+F", lambda: (self.ara_kutusu.setFocus(), self.ara_kutusu.selectAll())),
                           ("Ctrl+B", lambda: self.barkod_alanina_git())):
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
        self._donus = None
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
        self._yeni_dugmeleri = {}
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
            if s.tur == "baglanti" and s.baglanti and self._hedef_barkodlu(s):
                dugme = QPushButton(f"Yeni {self.b.moduller[s.baglanti[0]].tekil_ad or 'kayıt'} olarak ekle")
                dugme.setAutoDefault(False)
                dugme.setVisible(False)
                dugme.clicked.connect(lambda _=False, k=s.kimlik: self.yeni_olarak_ekle(k))
                v.addWidget(dugme)
                self._yeni_dugmeleri[s.kimlik] = dugme
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
        self.matris_dugme.setVisible(self.g is not None and kayitlar.matris_tanimi(self.g) is not None)

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
    # ------------------------------------------------------------------ barkod (Faz 10g)
    def _hedef_barkodlu(self, s) -> bool:
        h = self.b.gorunum(s.baglanti[0]) if self.b is not None else None
        return h is not None and bool(kayitlar.barkod_sutunlari(h))

    def barkod_alanlari(self) -> List[str]:
        """Barkod okutulabilen alanlar: kendi barkod alanları + barkodlu modüle bağlanan alanlar (form sırasıyla)."""
        kendi = {s.kimlik for s in kayitlar.barkod_sutunlari(self.g)}
        bagli = {s.kimlik for s in kayitlar.barkodlu_baglantilar(self.b, self.g)}
        return [k for k in self.alanlar if k in kendi or k in bagli]

    def barkod_alanina_git(self) -> bool:
        """`Ctrl+B`: odağı barkod okutulacak alana taşır (okuyucu klavye gibi yazıp Enter gönderir)."""
        alanlar = self.barkod_alanlari()
        if not alanlar:
            return False
        a = self.alanlar[alanlar[0]]
        a.kutu.setFocus()
        kutu = a.kutu.lineEdit() if isinstance(a.kutu, QComboBox) and a.kutu.isEditable() else a.kutu
        if hasattr(kutu, "selectAll"):
            kutu.selectAll()
        return True

    def barkod_isle(self, kimlik: str) -> Optional[bool]:
        """Alana Enter basılınca barkod kuralı. None = bu alan barkod alanı değil/işlem yok (normal Enter);
        True = barkod çözüldü (sonraki alana geçilebilir); False = çözülemedi (alan başında kalınır)."""
        a = self.alanlar[kimlik]
        kod = a.metin().strip()
        if not kod:
            return None
        s = a.sutun
        if s.barkod:                                              # kendi barkod alanı: kayıtlı barkodsa o kayda git
            r = kayitlar.barkod_ara(self.g, kod, haric=self.satir)
            if r is None:
                return None
            a.yaz("")
            self._ilk = self._mevcut_metinler()
            self.kayda_git(r)
            self.durum.setText(f"Barkod {kod} kayıtlı: kayda gidildi.")
            return False
        if s.tur == "baglanti" and s.baglanti and self._hedef_barkodlu(s):
            if kosul_uyumlu(a.kutu, kod):
                self._yeni_dugmeleri[kimlik].setVisible(False)
                return True
            v = kayitlar.baglanti_degeri(self.b, s, kod)
            if v is not None:
                a.yaz(v)
                a.hata_yaz("")
                self._yeni_dugmeleri[kimlik].setVisible(False)
                self.durum.setText(f"Barkod okundu: {v}")
                return True
            ad = self.b.moduller[s.baglanti[0]].tekil_ad or "kayıt"
            a.hata_yaz(f"“{kod}” barkoduyla kayıtlı {ad.lower()} bulunamadı.")
            self._yeni_dugmeleri[kimlik].setVisible(True)
            return False
        return None

    def yeni_olarak_ekle(self, kimlik: str) -> bool:
        """Okunan barkod bulunamadı: hedef modülün yeni kayıt formu barkod önceden dolu açılır; kaydedince bu forma dönülür."""
        a = self.alanlar[kimlik]
        s = a.sutun
        kod = a.metin().strip()
        hedef = s.baglanti[0]
        bark = kayitlar.barkod_sutunlari(self.b.gorunum(hedef))
        if not kod or not bark:
            return False
        self._donus = {"modul": self.g.modul.kimlik, "satir": self.satir, "metinler": self._mevcut_metinler(),
                       "alan": kimlik, "hedef_alan": s.baglanti[1], "hedef_modul": hedef}
        self._ilk = self._mevcut_metinler()                       # taslak saklandı: modül değişimi soru çıkarmasın
        self._yukleniyor = True
        self.modul_kutusu.setCurrentIndex(max(0, self.modul_kutusu.findData(hedef)))
        self._yukleniyor = False
        self._modul_kur(hedef, None)
        self.yeni_kayit(onay=False)
        self.alanlar[bark[0].kimlik].yaz(kod)
        self.durum.setText(f"Yeni kayıt: barkod {kod} dolu. Kaydedince önceki forma dönülür.")
        return True

    def _geri_don(self, kayit_satiri: int) -> None:
        d, self._donus = self._donus, None
        if d is None:
            return
        gv = self.b.gorunum(d["hedef_modul"])
        deger = kayitlar.duzenleme_metni(gv, kayit_satiri, d["hedef_alan"])
        self._yukleniyor = True
        self.modul_kutusu.setCurrentIndex(max(0, self.modul_kutusu.findData(d["modul"])))
        self._yukleniyor = False
        self._modul_kur(d["modul"], d["satir"])
        if d["satir"] is None:
            self.yeni_kayit(onay=False)
        for k, m in d["metinler"].items():
            if k in self.alanlar:
                self.alanlar[k].yaz(m)
        self.alanlar[d["alan"]].yaz(deger)
        self.alanlar[d["alan"]].hata_yaz("")
        self._durum_yaz()
        self.durum.setText(f"Yeni kayıt eklendi: {deger}")
        self.focusNextChild()

    def _enter(self, kimlik: str) -> None:
        if self.alanlar[kimlik].sutun.tur != "hesaplanan":
            sonuc = self.barkod_isle(kimlik)
            if sonuc is False:
                return
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
        if self._donus is not None and self._donus["hedef_modul"] == self.g.modul.kimlik:
            self._geri_don(row)
            return True
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

    # ------------------------------------------------------------------ varyant matrisi (Faz 10h)
    def matris_ac(self, ortak_metinler=None, satirlar=None, sutunlar=None, degerler=None, sessiz: bool = False):
        """Matris giriş penceresi (modül `matris` tanımlıysa). `sessiz` + parametreler testler içindir (pencere gösterilmeden
        doldurulup kaydedilir); döner: pencere. Yarım düzenleme varsa önce sorulur."""
        if self.g is None or kayitlar.matris_tanimi(self.g) is None:
            return None
        if not self._kayit_birak():
            return None
        pen = MatrisPenceresi(self, ortak_metinler)
        if satirlar is not None:
            pen.satir_kutusu.setText(", ".join(satirlar))
            pen.sutun_kutusu.setText(", ".join(sutunlar or []))
            pen.tablo_kur()
            for (e, c), v in (degerler or {}).items():
                pen.hucre_yaz(e, c, v)
        if sessiz:
            return pen
        pen.exec()
        return pen

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


def kosul_uyumlu(kutu, metin: str) -> bool:
    """Açılır liste kutusunda `metin` (Türkçe harf duyarsız) tam bir seçenekse True."""
    if not isinstance(kutu, QComboBox):
        return False
    h = kucuk(metin.strip())
    return any(kucuk(kutu.itemText(i)) == h and kutu.itemText(i) for i in range(kutu.count()))


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


class _MatrisTablosu(QTableWidget):
    """Matris ızgarası: Excel'den kopyalanan sekmeli metni (Ctrl+V) etkin hücreden başlayarak yapıştırır; Delete boşaltır."""

    def keyPressEvent(self, olay):
        if olay.matches(QKeySequence.Paste):
            self.yapistir(QApplication.clipboard().text())
            return
        if olay.key() == Qt.Key_Delete:
            for oge in self.selectedItems():
                oge.setText("")
            return
        super().keyPressEvent(olay)

    def yapistir(self, metin: str) -> None:
        r0, c0 = max(self.currentRow(), 0), max(self.currentColumn(), 0)
        for i, satir in enumerate(metin.replace("\r", "").split("\n")):
            if satir == "" and i == len(metin.replace("\r", "").split("\n")) - 1:
                continue
            for j, deger in enumerate(satir.split("\t")):
                if r0 + i < self.rowCount() and c0 + j < self.columnCount():
                    self.item(r0 + i, c0 + j).setText(deger.strip())


class MatrisPenceresi(QDialog):
    """Beden × renk gibi iki boyutlu giriş: ortak alanlar (ör. ürün) + satır/sütun etiketleri + ızgara. Her dolu hücre ayrı kayıt olur;
    mevcut kayıt varsa değeri güncellenir; boş hücre yazılmaz. Kaydet = tek geri al adımı; tek ihlal bile varsa hiçbir şey yazılmaz."""

    def __init__(self, form: "SablonFormu", ortak_metinler=None):
        super().__init__(form)
        self.form = form
        self.g = form.g
        self.sa, self.su, self.de = kayitlar.matris_tanimi(self.g)
        self.setWindowTitle(f"{self.g.modul.ad} — Matris giriş")
        self.setMinimumSize(560, 440)
        self.ortak = {s.kimlik: s for s in kayitlar.matris_ortak_alanlari(self.g)}
        self.ortak_kutulari: Dict[str, QWidget] = {}
        self.etiketler_satir: List[str] = []
        self.etiketler_sutun: List[str] = []
        d = QVBoxLayout(self)
        ust = QFormLayout()
        for k, s in self.ortak.items():
            kutu = form._kutu_olustur(s)
            self.ortak_kutulari[k] = kutu
            ust.addRow(s.ad + (" *" if s.zorunlu else ""), kutu)
            if ortak_metinler and k in ortak_metinler:
                self._kutu_yaz(kutu, ortak_metinler[k])
        self.satir_kutusu = QLineEdit()
        self.satir_kutusu.setPlaceholderText(f"virgülle: ör. S, M, L, XL")
        self.sutun_kutusu = QLineEdit()
        self.sutun_kutusu.setPlaceholderText("virgülle: ör. Kırmızı, Mavi")
        ust.addRow(f"{self.sa.ad} (satırlar)", self.satir_kutusu)
        ust.addRow(f"{self.su.ad} (sütunlar)", self.sutun_kutusu)
        d.addLayout(ust)
        sat = QHBoxLayout()
        self.kur_dugme = QPushButton("Tabloyu kur / mevcut kayıtları getir")
        self.kur_dugme.clicked.connect(self.tablo_kur)
        sat.addWidget(self.kur_dugme)
        sat.addStretch(1)
        d.addLayout(sat)
        self.tablo = _MatrisTablosu(0, 0)
        d.addWidget(self.tablo, 1)
        self.ileti = QLabel("")
        self.ileti.setWordWrap(True)
        self.ileti.setStyleSheet(f"color: {HATA_RENGI};")
        d.addWidget(self.ileti)
        alt = QHBoxLayout()
        alt.addStretch(1)
        self.kaydet_dugme = QPushButton("Kaydet")
        kapat = QPushButton("Kapat")
        self.kaydet_dugme.clicked.connect(lambda: self.kaydet())
        kapat.clicked.connect(self.reject)
        alt.addWidget(self.kaydet_dugme)
        alt.addWidget(kapat)
        d.addLayout(alt)
        for dugme in self.findChildren(QPushButton):
            dugme.setAutoDefault(False)

    @staticmethod
    def _kutu_yaz(kutu, metin: str) -> None:
        if isinstance(kutu, QComboBox):
            i = kutu.findText(metin, Qt.MatchFixedString)
            kutu.setCurrentIndex(i) if i >= 0 else kutu.setCurrentText(metin)
        elif isinstance(kutu, QCheckBox):
            kutu.setChecked(kucuk(metin) in ("evet", "e", "1"))
        else:
            kutu.setText(metin)

    @staticmethod
    def _kutu_oku(kutu) -> str:
        if isinstance(kutu, QComboBox):
            return kutu.currentText()
        if isinstance(kutu, QCheckBox):
            return "Evet" if kutu.isChecked() else "Hayır"
        return kutu.text()

    def _ortak_hucreler(self) -> Dict[str, object]:
        satir = kayitlar.yeni_satir(self.g) or self.g.ilk_satir
        return {k: kayitlar.metinden_hucre(self.g, satir, k, self._kutu_oku(kutu)) for k, kutu in self.ortak_kutulari.items()}

    @staticmethod
    def _etiketler(metin: str) -> List[str]:
        gorulen, cikti = set(), []
        for p in metin.replace(";", ",").split(","):
            p = p.strip()
            if p and kucuk(p) not in gorulen:
                gorulen.add(kucuk(p))
                cikti.append(p)
        return cikti

    def tablo_kur(self) -> None:
        """Yazılan etiketler + seçili ortak alanlara (ürün) ait mevcut kayıtların etiketleriyle ızgarayı kurar; mevcut değerleri doldurur.
        Izgaradaki girilmiş ama kaydedilmemiş değerler korunur."""
        eski = self.degerler()
        mevcut = kayitlar.matris_mevcut(self.g, self._ortak_hucreler())
        satirlar, sutunlar = self._etiketler(self.satir_kutusu.text()), self._etiketler(self.sutun_kutusu.text())
        for (e, c) in mevcut:
            if kucuk(e) not in {kucuk(x) for x in satirlar}:
                satirlar.append(e)
            if kucuk(c) not in {kucuk(x) for x in sutunlar}:
                sutunlar.append(c)
        self.etiketler_satir, self.etiketler_sutun = satirlar, sutunlar
        self.satir_kutusu.setText(", ".join(satirlar))
        self.sutun_kutusu.setText(", ".join(sutunlar))
        self.tablo.clear()
        self.tablo.setRowCount(len(satirlar))
        self.tablo.setColumnCount(len(sutunlar))
        self.tablo.setVerticalHeaderLabels(satirlar)
        self.tablo.setHorizontalHeaderLabels(sutunlar)
        for i in range(len(satirlar)):
            for j in range(len(sutunlar)):
                self.tablo.setItem(i, j, QTableWidgetItem(""))
        kucuk_mevcut = {(kucuk(e), kucuk(c)): h for (e, c), (_r, h) in mevcut.items()}
        for i, e in enumerate(satirlar):
            for j, c in enumerate(sutunlar):
                v = eski.get((kucuk(e), kucuk(c)))
                if v:
                    self.tablo.item(i, j).setText(v)
                else:
                    h = kucuk_mevcut.get((kucuk(e), kucuk(c)))
                    if h is not None and h.deger is not None:
                        self.tablo.item(i, j).setText(kayitlar._metin(h))
        self.ileti.setText("")

    def hucre_yaz(self, satir_etiketi: str, sutun_etiketi: str, metin: str) -> None:
        i = [kucuk(x) for x in self.etiketler_satir].index(kucuk(satir_etiketi))
        j = [kucuk(x) for x in self.etiketler_sutun].index(kucuk(sutun_etiketi))
        self.tablo.item(i, j).setText(str(metin))

    def degerler(self) -> Dict[tuple, str]:
        """{(satır etiketi, sütun etiketi) küçük harf: ızgaradaki metin} (boşlar dâhil değil)."""
        cikti = {}
        for i, e in enumerate(self.etiketler_satir):
            for j, c in enumerate(self.etiketler_sutun):
                oge = self.tablo.item(i, j)
                if oge is not None and oge.text().strip():
                    cikti[(kucuk(e), kucuk(c))] = oge.text().strip()
        return cikti

    def plan(self):
        satir = kayitlar.yeni_satir(self.g) or self.g.ilk_satir
        hucreler = {}
        for i, e in enumerate(self.etiketler_satir):
            for j, c in enumerate(self.etiketler_sutun):
                oge = self.tablo.item(i, j)
                metin = oge.text().strip() if oge is not None else ""
                hucreler[(e, c)] = kayitlar.metinden_hucre(self.g, satir, self.de.kimlik, metin) if metin else None
        return kayitlar.matris_plani(self.form.b, self.g, self._ortak_hucreler(), hucreler)

    def kaydet(self) -> bool:
        if not self.etiketler_satir or not self.etiketler_sutun:
            self.ileti.setText("Önce satır ve sütun etiketlerini yazıp tabloyu kurun.")
            return False
        plan = self.plan()
        self.ileti.setStyleSheet(f"color: {HATA_RENGI};")
        if not plan.tamam:
            self.ileti.setText("\n".join(f"{e}: {i.ileti}" for e, i in plan.ihlaller[:8]) +
                               ("\n…" if len(plan.ihlaller) > 8 else ""))
            return False
        if not plan.yazimlar:
            self.ileti.setText("Yazılacak değişiklik yok.")
            return False
        izgara = self.form.pencere.izgara()
        if izgara.sayfa is not self.g.sayfa:
            self.form.pencere.sekmeler.setCurrentIndex(self.form.pencere.kitap.sayfalar.index(self.g.sayfa))
            izgara = self.form.pencere.izgara()
        self.form._kaydediyor = True
        try:
            izgara.yigin.calistir(HucrelerDegis(self.g.sayfa, plan.yazimlar))        # tek geri al adımı
            izgara._guncelle()
        finally:
            self.form._kaydediyor = False
        self.form.kayit_satirlari = kayitlar.kayit_satirlari(self.g)
        self.form.kaydedildi.emit()
        self.form._yukle(self.form.satir if self.form.satir in self.form.kayit_satirlari else None)
        self.tablo_kur()                                    # ızgara kayıtlı değerlerle yenilenir
        self.ileti.setStyleSheet(f"color: {theme.ACCENT};")
        self.ileti.setText(f"Kaydedildi: {plan.yeni} yeni kayıt, {plan.guncellenen} güncelleme"
                           + (f", {plan.degismeyen} değişmeyen." if plan.degismeyen else "."))
        return True


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
