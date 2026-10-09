"""Pencerenin dosya işlemleri (Faz 4 / 4b): Yeni, Aç, Kaydet, Farklı Kaydet, kapatırken sorma, veri kaybı
uyarısı, son dosyalar. `Pencere` bu karışımı miras alır; her dosya bir pencerede açılır (Excel gibi),
boş ve değişmemiş pencere yerine yenisi açılırsa o pencere kapanır."""
import os
import weakref
from typing import List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QMenu, QMessageBox, QToolButton,
)

from .. import APP_NAME
from ..io import csv_io, kurtarma, son_dosyalar, xlsx_io
from ..io.xlsx_io import Rapor, XlsxHatasi
from ..model.komutlar import SayfaYapisiDegis
from ..model.sayfa import CalismaKitabi

XLSX_FILTRESI = "Excel Çalışma Kitabı (*.xlsx)"
CSV_FILTRESI = "CSV (Noktalı virgülle ayrılmış) (*.csv)"
KAYDET_FILTRESI = XLSX_FILTRESI + ";;" + CSV_FILTRESI
PDF_FILTRESI = "PDF (*.pdf)"
ACMA_FILTRESI = ("Excel ve CSV (*.xlsx *.csv);;" + XLSX_FILTRESI + ";;CSV (*.csv);;Tüm Dosyalar (*.*)")


def _ayni_yol(a: Optional[str], b: Optional[str]) -> bool:
    return bool(a and b) and os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


class DosyaIslemleri:
    """`Pencere` karışımı. Gerektirdiği alanlar: `kitap`, `yigin`, `belge_adi`, `_baslik_guncelle()`."""

    _acik_pencereler = weakref.WeakSet()                  # aynı dosyayı iki kez açmamak için (zayıf)
    _tutulan: List["DosyaIslemleri"] = []                 # yeni()/dosya_ac() ile açılanlar: kapanana dek canlı

    # ------------------------------------------------------------------ kurulum
    OTOKAYIT_MS = 120_000                                     # kurtarma kopyası aralığı (2 dakika)

    def _dosya_kur(self) -> None:
        self.kurtarma_kimligi = kurtarma.yeni_kimlik()
        self._kurtarilan = False                              # kurtarma kopyasından açıldı, henüz kaydedilmedi
        self._son_otokayit = None
        self._otokayit_zamanlayici = QTimer(self)
        self._otokayit_zamanlayici.timeout.connect(self.otokayit_yap)
        self._otokayit_zamanlayici.start(self.OTOKAYIT_MS)
        self.yol: Optional[str] = None
        self.kaynak_yol: Optional[str] = None               # .csv'den açıldıysa o dosya (kayıt yolu değil)
        self.rapor: Rapor = Rapor()
        self._temiz_damga = self.yigin.damga()
        DosyaIslemleri._acik_pencereler.add(self)
        for tus, islem in (("Ctrl+N", self.yeni), ("Ctrl+O", self.ac_penceresi), ("Ctrl+S", self.kaydet),
                           ("Ctrl+Shift+S", self.farkli_kaydet), ("F12", self.farkli_kaydet),
                           ("Ctrl+P", self.yazdir_baslat)):
            QShortcut(QKeySequence(tus), self, activated=lambda f=islem: f(), context=Qt.WindowShortcut)

    def _bilgi_cubugu_olustur(self) -> QFrame:
        """Açılan dosyada korunamayan öğe varsa uyarı şeridi (kapatılabilir)."""
        b = QFrame()
        b.setObjectName("infoBar")
        b.setStyleSheet("#infoBar { background: #FFF4CE; border-bottom: 1px solid #E0C97A; }"
                        " #infoBar QLabel { color: #5A4A00; }")
        h = QHBoxLayout(b)
        h.setContentsMargins(10, 4, 6, 4)
        self.bilgi_etiketi = QLabel()
        self.bilgi_etiketi.setWordWrap(True)
        kapat = QToolButton()
        kapat.setText("×")
        kapat.setToolTip("Kapat")
        kapat.clicked.connect(b.hide)
        h.addWidget(self.bilgi_etiketi, 1)
        h.addWidget(kapat)
        b.hide()
        return b

    def _bilgi_goster(self) -> None:
        if self.rapor.uyarilar:
            self.bilgi_etiketi.setText("\n".join(self.rapor.uyarilar))
            self.bilgi_cubugu.show()
        else:
            self.bilgi_cubugu.hide()

    def _dosya_menusu_doldur(self, menu: QMenu) -> None:
        menu.addAction("Yeni\tCtrl+N", self.yeni)
        menu.addAction("Aç…\tCtrl+O", self.ac_penceresi)
        menu.addSeparator()
        menu.addAction("Kaydet\tCtrl+S", self.kaydet)
        menu.addAction("Farklı Kaydet…\tCtrl+Shift+S", self.farkli_kaydet)
        menu.addSeparator()
        menu.addAction("Sayfa Yapısı…", self.sayfa_yapisi_ac)
        menu.addAction("Yazdırma Önizleme…", self.onizleme_ac)
        menu.addAction("Yazdır…\tCtrl+P", self.yazdir_baslat)
        menu.addAction("PDF Olarak Dışa Aktar (Etkin Sayfa)…", lambda: self.pdf_aktar(False))
        menu.addAction("PDF Olarak Dışa Aktar (Tüm Sayfalar)…", lambda: self.pdf_aktar(True))
        menu.addSeparator()
        self.son_menusu = menu.addMenu("Son Kullanılanlar")
        self.son_menusu.aboutToShow.connect(self._son_menusu_hazirla)
        menu.addSeparator()
        menu.addAction("Çıkış", self.close)

    def _son_menusu_hazirla(self) -> None:
        self.son_menusu.clear()
        liste = son_dosyalar.oku()
        if not liste:
            self.son_menusu.addAction("(boş)").setEnabled(False)
            return
        for y in liste:
            self.son_menusu.addAction(os.path.basename(y)).triggered.connect(
                lambda _=False, yol=y: self.dosya_ac(yol))
            self.son_menusu.actions()[-1].setToolTip(y)

    # ------------------------------------------------------------------ durum
    def degisti_mi(self) -> bool:
        """Son kayıt/açılıştan beri geri al yığını değişti mi (geri alıp kayıt noktasına dönülürse hayır)."""
        if getattr(self, "_kurtarilan", False):
            return True
        temiz = getattr(self, "_temiz_damga", None)          # kurulum sırasında henüz yok
        return temiz is not None and not self.yigin.damga_esit(self.yigin.damga(), temiz)

    def _bos_ve_temiz(self) -> bool:
        return (self.yol is None and not self.degisti_mi() and len(self.kitap.sayfalar) == 1
                and self.kitap.sayfalar[0].kullanilan_aralik() is None)

    def _belge_adi_guncelle(self) -> None:
        kaynak = self.yol or self.kaynak_yol
        self.belge_adi = os.path.basename(kaynak) if kaynak else "Adsız"
        self._baslik_guncelle()

    def _isaretle_temiz(self) -> None:
        self._temiz_damga = self.yigin.damga()
        self._kurtarilan = False
        self._son_otokayit = None
        kurtarma.sil(self.kurtarma_kimligi)                   # kaydedildi: kurtarma kopyası gereksiz
        self._baslik_guncelle()

    # ------------------------------------------------------------------ yeni / aç
    def yeni(self):
        """Boş kitapla yeni pencere."""
        from .window import Pencere
        p = Pencere(CalismaKitabi())
        DosyaIslemleri._tutulan.append(p)
        p._dosya_gorunur_yap()
        return p

    def _dosya_gorunur_yap(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def ac_penceresi(self):
        yol, _ = QFileDialog.getOpenFileName(self, "Aç", self._baslangic_klasoru(), ACMA_FILTRESI)
        if yol:
            return self.dosya_ac(yol)
        return None

    def _baslangic_klasoru(self) -> str:
        return os.path.dirname(self.yol) if self.yol else ""

    def dosya_ac(self, yol: str):
        """`yol`u yeni pencerede açar (açıksa o pencereyi öne getirir); başarısızsa None ve ileti."""
        from .window import Pencere
        for p in list(DosyaIslemleri._acik_pencereler):
            if _ayni_yol(p.yol, yol) or (p.yol is None and _ayni_yol(p.kaynak_yol, yol)):
                son_dosyalar.ekle(yol)
                p._dosya_gorunur_yap()
                return p
        csv_mi = os.path.splitext(yol)[1].lower() == ".csv"
        try:
            sonuc = self._csv_oku(yol) if csv_mi else self._kitap_oku(yol)
        except (XlsxHatasi, csv_io.CsvHatasi) as e:
            son_dosyalar.sil(yol)
            QMessageBox.critical(self, APP_NAME, str(e))
            return None
        if sonuc is None:                                    # CSV penceresinde İptal
            return None
        kitap, rapor = sonuc
        p = Pencere(kitap)
        if csv_mi:
            p.kaynak_yol = os.path.abspath(yol)              # kayıt yolu değil: Kaydet → Farklı Kaydet (.xlsx önerilir)
        else:
            p.yol = os.path.abspath(yol)
        p.rapor = rapor
        p._belge_adi_guncelle()
        p._bilgi_goster()
        son_dosyalar.ekle(yol)
        DosyaIslemleri._tutulan.append(p)
        p._dosya_gorunur_yap()
        if self._bos_ve_temiz() and p is not self:
            self.close()                                     # boş, değişmemiş pencere yerine açıldı
        return p

    def _csv_ayarlari(self, yol: str):
        """(satırlar, metin_olarak) | None (iptal). Testlerde yamalanır."""
        from .csv_penceresi import csv_ayarlari_sor
        return csv_ayarlari_sor(yol, self)

    def _csv_oku(self, yol: str):
        a = self._csv_ayarlari(yol)
        if a is None:
            return None
        satirlar, metin_olarak = a
        kitap, uyarilar = csv_io.kitap_olustur(satirlar, csv_io.sayfa_adi_uret(yol), metin_olarak)
        r = Rapor()
        for u in uyarilar:
            r.ekle(u)
        return kitap, r

    @staticmethod
    def _kitap_oku(yol: str):
        if not os.path.exists(yol):
            raise XlsxHatasi(f"Dosya bulunamadı: {yol}")
        return xlsx_io.ac(yol)

    # ------------------------------------------------------------------ kaydet
    def kaydet(self) -> bool:
        if self.yol is None:
            return self.farkli_kaydet()
        if self.rapor.veri_kaybi:
            secim = self._veri_kaybi_sorusu()
            if secim == "farkli":
                return self.farkli_kaydet()
            if secim != "kaydet":
                return False
        return self._kaydet_yola(self.yol)

    def farkli_kaydet(self) -> bool:
        if self.yol:
            onerilen = self.yol
        elif self.kaynak_yol:                                # .csv'den açıldı: aynı adla .xlsx öner
            onerilen = os.path.splitext(self.kaynak_yol)[0] + ".xlsx"
        else:
            onerilen = os.path.join(self._baslangic_klasoru(), "Kitap1.xlsx")
        yol, filtre = QFileDialog.getSaveFileName(self, "Farklı Kaydet", onerilen, KAYDET_FILTRESI)
        if not yol:
            return False
        if not os.path.splitext(yol)[1]:
            yol += ".csv" if "csv" in (filtre or "").lower() else ".xlsx"
        return self._kaydet_yola(yol)

    def _csv_cok_sayfa_sorusu(self) -> bool:
        """Birden çok sayfalı kitap CSV'ye yazılırken yalnız etkin sayfa kaydedilir: devam edilsin mi?"""
        c = QMessageBox.question(
            self, APP_NAME, "CSV biçimi yalnızca etkin sayfayı kaydeder; diğer sayfalar ve biçimlendirme "
            "kaydedilmez. Devam edilsin mi?", QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Yes)
        return c == QMessageBox.Yes

    def _kaydet_yola(self, yol: str) -> bool:
        csv_mi = os.path.splitext(yol)[1].lower() == ".csv"
        try:
            if csv_mi:
                if len(self.kitap.sayfalar) > 1 and not self._csv_cok_sayfa_sorusu():
                    return False
                csv_io.dosya_yaz(self.izgara().sayfa, yol)
            else:
                xlsx_io.kaydet(self.kitap, yol)
        except (XlsxHatasi, csv_io.CsvHatasi) as e:
            QMessageBox.critical(self, APP_NAME, str(e))
            return False
        self.yol = os.path.abspath(yol)
        self.kaynak_yol = None
        self.rapor = Rapor()                                 # artık dosya bu kitabın kendisi: kayıp uyarısı biter
        self._bilgi_goster()
        self._belge_adi_guncelle()
        self._isaretle_temiz()
        son_dosyalar.ekle(yol)
        self.statusBar().showMessage("Kaydedildi", 4000)
        return True

    def _veri_kaybi_sorusu(self) -> str:
        """'farkli' | 'kaydet' | 'iptal'."""
        k = QMessageBox(QMessageBox.Warning, APP_NAME,
                        "Bu dosyada " + APP_NAME + "'in koruyamadığı öğeler var (grafik, resim, koşullu biçim vb.). "
                        "Üzerine kaydederseniz bu öğeler dosyadan çıkar.\n\nÖzgün dosyaya dokunmamak için "
                        "“Farklı Kaydet”i seçin.", parent=self)
        farkli = k.addButton("Farklı Kaydet", QMessageBox.AcceptRole)
        yine = k.addButton("Yine de Kaydet", QMessageBox.DestructiveRole)
        k.addButton("İptal", QMessageBox.RejectRole)
        k.setDefaultButton(farkli)
        k.exec()
        b = k.clickedButton()
        return "farkli" if b is farkli else "kaydet" if b is yine else "iptal"

    # ------------------------------------------------------------------ kapatma
    def _kapatma_sorusu(self) -> str:
        """'kaydet' | 'kaydetme' | 'iptal'."""
        k = QMessageBox(QMessageBox.Question, APP_NAME,
                        f"“{self.belge_adi}” içindeki değişiklikler kaydedilsin mi?", parent=self)
        kay = k.addButton("Kaydet", QMessageBox.AcceptRole)
        kayma = k.addButton("Kaydetme", QMessageBox.DestructiveRole)
        k.addButton("İptal", QMessageBox.RejectRole)
        k.setDefaultButton(kay)
        k.exec()
        b = k.clickedButton()
        return "kaydet" if b is kay else "kaydetme" if b is kayma else "iptal"

    def _kapanabilir_mi(self) -> bool:
        if not self.degisti_mi():
            return True
        c = self._kapatma_sorusu()
        if c == "kaydet":
            return self.kaydet()
        return c == "kaydetme"

    # ------------------------------------------------------------------ otomatik kurtarma (4e)
    def otokayit_yap(self) -> bool:
        """Değişmiş belgenin kurtarma kopyasını yazar (değişiklik yoksa ya da son kopyadan beri aynıysa
        yazmaz). Hata sessizce yutulur: otomatik işlem kullanıcıyı bölmez. Yazıldıysa True."""
        if not self.degisti_mi():
            return False
        damga = self.yigin.damga()
        if self._son_otokayit is not None and self.yigin.damga_esit(damga, self._son_otokayit):
            return False
        try:
            kurtarma.kopya_yaz(self.kitap, self.kurtarma_kimligi, self.belge_adi, self.yol or self.kaynak_yol)
        except (OSError, XlsxHatasi):
            return False
        self._son_otokayit = damga
        return True

    def _kurtarma_sorusu(self, liste):
        """(eylem, seçilenler); eylem 'ac' | 'sil' | 'sonra'. Testlerde yamalanır."""
        from .kurtarma_penceresi import KurtarmaPenceresi
        d = KurtarmaPenceresi(liste, self)
        d.exec()
        return d.eylem(), d.secilenler()

    def kurtarma_denetle(self) -> int:
        """Çökmüş oturumlardan kalan kopyaları önerir; açılan belge sayısını verir."""
        liste = kurtarma.bekleyenler()
        if not liste:
            return 0
        eylem, secilen = self._kurtarma_sorusu(liste)
        if eylem == "sil":
            for k in secilen:
                kurtarma.sil(k.kimlik)
            return 0
        if eylem != "ac":
            return 0                                          # "sonra": dosyalar kalır, sonraki açılışta yine sorulur
        acilan = 0
        for k in secilen:
            if self.kurtarilani_ac(k) is not None:
                acilan += 1
        return acilan

    def kurtarilani_ac(self, k):
        from .window import Pencere
        try:
            kitap, rapor = kurtarma.ac(k)
        except XlsxHatasi as e:
            QMessageBox.critical(self, APP_NAME, f"“{k.ad}” kurtarılamadı: {e}\nKopya silinmedi: {k.dosya}")
            return None
        p = Pencere(kitap)
        p.kurtarma_kimligi = k.kimlik                         # aynı kopyayı güncellemeye devam eder
        kurtarma.sahiplen(k.kimlik)
        p.kaynak_yol = k.yol                                  # kayıt yolu DEĞİL: Farklı Kaydet'te öneri olur
        p.rapor = rapor
        p.rapor.ekle("Bu belge otomatik kurtarma kopyasından açıldı; kaydedilmemiş değişiklikleri içerir. "
                     "Kaybolmaması için kaydedin.")
        p._kurtarilan = True
        p._belge_adi_guncelle()
        p._bilgi_goster()
        DosyaIslemleri._tutulan.append(p)
        p._dosya_gorunur_yap()
        return p

    def _pencere_kapandi(self) -> None:
        self._otokayit_zamanlayici.stop()
        kurtarma.sil(self.kurtarma_kimligi)                   # bilerek kapatıldı: kopya gereksiz
        DosyaIslemleri._acik_pencereler.discard(self)
        if self in DosyaIslemleri._tutulan:
            DosyaIslemleri._tutulan.remove(self)

    # ------------------------------------------------------------------ yazdırma / PDF (4d)
    def sayfa_yapisi_ac(self) -> bool:
        from .sayfa_yapisi_penceresi import SayfaYapisiPenceresi
        sayfa = self.izgara().sayfa
        d = SayfaYapisiPenceresi(sayfa.sayfa_yapisi, self)
        if d.exec() != QDialog.Accepted or d.sonuc() is None:
            return False
        kmt = SayfaYapisiDegis(sayfa, d.sonuc())
        if not kmt.bos_mu():
            self.yigin.calistir(kmt)
            self._baslik_guncelle()
        return True

    def _yazdirilacak(self, tum: bool = False):
        return [self._izgaralar[s] for s in self.kitap.sayfalar] if tum else [self.izgara()]

    def _yazdirilacak_yok(self) -> None:
        QMessageBox.information(self, APP_NAME, "Yazdırılacak bir şey yok: sayfa boş.")

    def pdf_aktar(self, tum: bool = False) -> bool:
        from . import yazdir as yz
        temel = os.path.splitext(self.yol or self.kaynak_yol or "Kitap1")[0] + ".pdf"
        yol, _ = QFileDialog.getSaveFileName(self, "PDF Olarak Dışa Aktar", temel, PDF_FILTRESI)
        if not yol:
            return False
        if not os.path.splitext(yol)[1]:
            yol += ".pdf"
        try:
            ok = yz.pdf_yaz(self._yazdirilacak(tum), yol)
        except PermissionError:
            QMessageBox.critical(self, APP_NAME, "PDF yazılamadı: dosya başka bir uygulamada açık olabilir.")
            return False
        except OSError as e:
            QMessageBox.critical(self, APP_NAME, f"PDF yazılamadı: {e.strerror or e}")
            return False
        if not ok:
            self._yazdirilacak_yok()
            return False
        self.statusBar().showMessage("PDF olarak dışa aktarıldı", 4000)
        return True

    def yazdir_baslat(self) -> bool:
        from PySide6.QtPrintSupport import QPrintDialog, QPrinter
        from . import yazdir as yz
        printer = QPrinter(QPrinter.HighResolution)
        if QPrintDialog(printer, self).exec() != QPrintDialog.Accepted:
            return False
        try:
            ok = yz.yazdir(printer, self._yazdirilacak(), self.belge_adi)
        except OSError as e:
            QMessageBox.critical(self, APP_NAME, f"Yazdırılamadı: {e}")
            return False
        if not ok:
            self._yazdirilacak_yok()
            return False
        return True

    def onizleme_ac(self) -> None:
        from PySide6.QtPrintSupport import QPrintPreviewDialog, QPrinter
        from . import yazdir as yz
        printer = QPrinter(QPrinter.HighResolution)
        d = QPrintPreviewDialog(printer, self)
        def ciz(pr):
            try:
                yz.yazdir(pr, self._yazdirilacak(), self.belge_adi)
            except OSError:
                pass                                          # önizlemede hedef yok; sessiz
        d.paintRequested.connect(ciz)
        d.exec()
