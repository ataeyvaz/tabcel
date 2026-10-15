"""Pencerenin dosya işlemleri (Faz 4 / 4b): Yeni, Aç, Kaydet, Farklı Kaydet, kapatırken sorma, veri kaybı
uyarısı, son dosyalar. `Pencere` bu karışımı miras alır; her dosya bir pencerede açılır (Excel gibi),
boş ve değişmemiş pencere yerine yenisi açılırsa o pencere kapanır."""
import time
import os
import weakref
from typing import List, Optional

from PySide6.QtCore import Qt, QThread, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMenu, QMessageBox, QToolButton,
)

from .. import APP_NAME
from .arka_plan import arka_planda
from ..io import csv_io, kurtarma, ods_io, sifreleme, son_dosyalar, xls_io, xlsx_io
from ..io.xlsx_io import Rapor, XlsxHatasi
from ..model.anlik import kitap_anligi
from ..model.komutlar import SayfaYapisiDegis
from ..model.sayfa import CalismaKitabi

XLSX_FILTRESI = "Excel Çalışma Kitabı (*.xlsx)"
CSV_FILTRESI = "CSV (Noktalı virgülle ayrılmış) (*.csv)"
ODS_FILTRESI = "OpenDocument Hesap Tablosu (*.ods)"
KAYDET_FILTRESI = XLSX_FILTRESI + ";;" + ODS_FILTRESI + ";;" + CSV_FILTRESI
PDF_FILTRESI = "PDF (*.pdf)"
XLS_FILTRESI = "Eski Excel Çalışma Kitabı (*.xls)"
ACMA_FILTRESI = ("Excel, ODS ve CSV (*.xlsx *.xls *.ods *.csv);;" + XLSX_FILTRESI + ";;" + XLS_FILTRESI + ";;" + ODS_FILTRESI
                 + ";;CSV (*.csv);;Tüm Dosyalar (*.*)")


def _damga(yol: str):
    """Dosyanın (değişiklik zamanı ns, boyut); yoksa None."""
    try:
        s = os.stat(yol)
        return (s.st_mtime_ns, s.st_size)
    except OSError:
        return None


def _ayni_yol(a: Optional[str], b: Optional[str]) -> bool:
    return bool(a and b) and os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


class _OtokayitIsi(QThread):
    """T4b: kurtarma kopyasını anlık görüntüden arka planda yazar (Qt nesnesine dokunmaz)."""

    def __init__(self, islev, damga):
        super().__init__()
        self._islev = islev
        self.damga = damga
        self.basarili = False
        self.sure_ms = 0.0

    def run(self) -> None:
        t0 = time.perf_counter()
        try:
            self._islev()
            self.basarili = True
        except Exception:                                    # otomatik işlem kullanıcıyı bölmez
            self.basarili = False
        self.sure_ms = (time.perf_counter() - t0) * 1000


class DosyaIslemleri:
    """`Pencere` karışımı. Gerektirdiği alanlar: `kitap`, `yigin`, `belge_adi`, `_baslik_guncelle()`."""

    _acik_pencereler = weakref.WeakSet()                  # aynı dosyayı iki kez açmamak için (zayıf)
    _tutulan: List["DosyaIslemleri"] = []                 # yeni()/dosya_ac() ile açılanlar: kapanana dek canlı

    # ------------------------------------------------------------------ kurulum
    OTOKAYIT_MS = 120_000                                     # kurtarma kopyası aralığı (2 dakika)

    def _dosya_kur(self) -> None:
        self.kurtarma_kimligi = kurtarma.yeni_kimlik()
        self._kurtarilan = False                              # kurtarma kopyasından açıldı, henüz kaydedilmedi
        self._gorunum_surum = 0                               # dondurma/kılavuz/sekme rengi (komut olmayan) değişiklik sayısı
        self._gorunum_kirli = False
        self._mesgul = False                                  # arka planda dosya işlemi sürüyor (kapatma ertelenir)
        self._disk_damgasi = None                             # açılış/kayıtta dosyanın (mtime, boyut): başka yerde değişti mi
        self.kitap.dinle(self._gorunum_olayi)
        self._son_otokayit = None
        self._otokayit_isi: Optional[_OtokayitIsi] = None   # arka planda süren kurtarma kopyası yazımı
        self._otokayit_zamanlayici = QTimer(self)
        self._otokayit_zamanlayici.timeout.connect(lambda: self.otokayit_yap(arka_plan=True))
        self._otokayit_zamanlayici.start(self.OTOKAYIT_MS)
        self.parola: Optional[str] = None                     # parolayla şifreli kaydet (yalnız bellekte; Faz 8b)
        self.yol: Optional[str] = None
        self.kaynak_yol: Optional[str] = None               # .csv'den açıldıysa o dosya (kayıt yolu değil)
        self.rapor: Rapor = Rapor()
        self._temiz_damga = self.yigin.damga()
        DosyaIslemleri._acik_pencereler.add(self)
        self._bulut_kur()
        for tus, islem in (("Ctrl+N", self.yeni), ("Ctrl+O", self.ac_penceresi), ("Ctrl+S", self.kaydet),
                           ("Ctrl+Shift+S", self.farkli_kaydet), ("F12", self.farkli_kaydet),
                           ("Ctrl+P", self.yazdir_baslat)):
            QShortcut(QKeySequence(tus), self, activated=lambda f=islem: f(), context=Qt.WindowShortcut)

    def _gorunum_olayi(self, olay) -> None:
        if olay.tur == "bicim" and olay.ayrinti.get("gorunum"):
            self.gorunum_degisti_isaretle()

    def gorunum_degisti_isaretle(self) -> None:
        """Geri al yığınına girmeyen ama dosyaya yazılan görünüm değişikliği (dondurma, kılavuz, sekme rengi):
        belge "değişti" sayılır; kapatırken sorulur."""
        self._gorunum_surum += 1
        self._gorunum_kirli = True
        self._baslik_guncelle()

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
        def ekle(anahtar, metin, islev):
            self.eylemler["dosya." + anahtar] = menu.addAction(metin, islev)     # eylem kataloğu (5j-3)
        ekle("yeni", "Yeni\tCtrl+N", self.yeni)
        ekle("sablondan_yeni", "Şablondan Yeni…", self.sablondan_yeni)
        ekle("kitaptan_sablon", "Kitaptan Şablon Oluştur…", self.kitaptan_sablon_olustur)
        ekle("ac", "Aç…\tCtrl+O", self.ac_penceresi)
        menu.addSeparator()
        ekle("kaydet", "Kaydet\tCtrl+S", self.kaydet)
        ekle("farkli_kaydet", "Farklı Kaydet…\tCtrl+Shift+S", self.farkli_kaydet)
        ekle("parola", "Parola Belirle…", self.parola_belirle)
        self._bulut_menusu_doldur(menu)                       # yalnız bilgisayarda o bulut klasörü varsa görünür (7a)
        menu.addSeparator()
        ekle("sayfa_yapisi", "Sayfa Yapısı…", self.sayfa_yapisi_ac)
        ekle("onizleme", "Yazdırma Önizleme…", self.onizleme_ac)
        ekle("yazdir", "Yazdır…\tCtrl+P", self.yazdir_baslat)
        ekle("pdf_etkin", "PDF Olarak Dışa Aktar (Etkin Sayfa)…", lambda: self.pdf_aktar(False))
        ekle("pdf_tum", "PDF Olarak Dışa Aktar (Tüm Sayfalar)…", lambda: self.pdf_aktar(True))
        menu.addSeparator()
        self.son_menusu = menu.addMenu("Son Kullanılanlar")
        self.son_menusu.aboutToShow.connect(self._son_menusu_hazirla)
        menu.addSeparator()
        ekle("cikis", "Çıkış", self.close)

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
        if getattr(self, "_kurtarilan", False) or getattr(self, "_gorunum_kirli", False):
            return True
        temiz = getattr(self, "_temiz_damga", None)          # kurulum sırasında henüz yok
        return temiz is not None and not self.yigin.damga_esit(self.yigin.damga(), temiz)

    def _bos_ve_temiz(self) -> bool:
        return (self.yol is None and not self.degisti_mi() and len(self.kitap.sayfalar) == 1
                and self.kitap.sayfalar[0].kullanilan_aralik() is None)

    def _belge_adi_guncelle(self) -> None:
        kaynak = self.yol or self.kaynak_yol
        self.belge_adi = os.path.basename(kaynak) if kaynak else (getattr(self, "taslak_adi", None) or "Adsız")
        self._baslik_guncelle()

    def _isaretle_temiz(self) -> None:
        self._temiz_damga = self.yigin.damga()
        self._kurtarilan = False
        self._gorunum_kirli = False
        self._son_otokayit = None
        self.otokayit_bekle()                                 # süren yazım silmeden SONRA dosya bırakmasın
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

    def sablondan_yeni(self):
        """Şablon Sihirbazı (Faz 10d): ne yapmak istediğini yaz → şablon → sorular → önizleme → yeni pencerede kitap."""
        from .window import Pencere
        d = self._sihirbaz_olustur()
        if d.exec() != QDialog.Accepted or d.sonuc is None:
            return None
        p = Pencere(d.sonuc.kitap)
        p.taslak_adi = d.secili.etiket
        p._belge_adi_guncelle()
        p._gorunum_kirli = True                               # henüz kaydedilmedi: kapatırken sorulur
        p._baslik_guncelle()
        DosyaIslemleri._tutulan.append(p)
        p._dosya_gorunur_yap()
        if self._bos_ve_temiz() and p is not self:
            self.close()
        return p

    def kitaptan_sablon_olustur(self, ad=None, sayfalar=None):
        """Açık kitaptaki sayfalardan kullanıcı şablonu taslağı üretir ve Şablon Düzenleyici'de açar (Faz 11). Testler `ad`/`sayfalar`
        verip pencereyi atlayabilir; döner: düzenleyici penceresi (ya da None)."""
        from ..sablon import duzenleme, yukleyici
        from .sablon_duzenleyici import DuzenleyiciPenceresi, KitaptanSablonPenceresi
        mevcut = {s.akis.kimlik for s in yukleyici.depo_yukle().sablonlar}
        if ad is None:
            pen = KitaptanSablonPenceresi(self.kitap, self, mevcut)
            if pen.exec() != QDialog.Accepted or pen.sonuc is None:
                return None
            sonuc = pen.sonuc
        else:
            sonuc = duzenleme.kitaptan_taslak(self.kitap, sayfalar or list(self.kitap.sayfalar), ad, kullanilan_akis_kimlikleri=mevcut)
        if sonuc.uyarilar:
            QMessageBox.information(self, "Kitaptan Şablon", "\n".join(sonuc.uyarilar[:10]))
        ed = DuzenleyiciPenceresi(sonuc.taslak, None, self)
        self._duzenleyici = ed
        ed.exec() if ad is None else ed.show()
        return ed

    def _sihirbaz_olustur(self):
        """Testlerde yamalanır."""
        from .sablon_sihirbazi import SihirbazPenceresi
        return SihirbazPenceresi(None, self)

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
            if _ayni_yol(p.yol, yol) or (p.yol is None and not p._kurtarilan and _ayni_yol(p.kaynak_yol, yol)):
                son_dosyalar.ekle(yol)
                p._dosya_gorunur_yap()
                return p
        if self.google_bicimi_ac(yol):                       # .gsheet vb.: içerik bilgisayarda yok (7a)
            return None
        uzanti = os.path.splitext(yol)[1].lower()
        csv_mi = uzanti == ".csv"
        kaynak_mi = csv_mi or uzanti == ".xls"               # .csv/.xls'den açılan: kayıt yolu değil, Farklı Kaydet (.xlsx)
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
        if kaynak_mi:
            p.kaynak_yol = os.path.abspath(yol)              # kayıt yolu değil: Kaydet → Farklı Kaydet (.xlsx önerilir)
        else:
            p.yol = os.path.abspath(yol)
            p._disk_damgasi = _damga(p.yol)
            p._izle()
        p.rapor = rapor
        if not kaynak_mi:
            p.parola = getattr(self, "_okunan_parola", None)     # parolalı dosya: kaydederken yeniden şifrelenir
        p._belge_adi_guncelle()
        p._bilgi_goster()
        son_dosyalar.ekle(yol)
        DosyaIslemleri._tutulan.append(p)
        p._dosya_gorunur_yap()
        if self._bos_ve_temiz() and p is not self:
            self.close()                                     # boş, değişmemiş pencere yerine açıldı
        return p

    def _csv_ayarlari(self, yol: str):
        """(satırlar, metin_olarak[, koru, sütun_türleri, ondalık]) | None (iptal). Testlerde yamalanır."""
        from .csv_penceresi import csv_ayarlari_sor
        return csv_ayarlari_sor(yol, self)

    def _csv_oku(self, yol: str):
        a = self._csv_ayarlari(yol)
        if a is None:
            return None
        satirlar, metin_olarak, *ek = a                       # ek: (koru, sütun türleri, ondalık); eski 2'liler de geçer
        koru, turler, ondalik = ek if len(ek) == 3 else (True, None, "otomatik")
        kitap, uyarilar = arka_planda(self, "CSV içe aktarılıyor…", lambda: csv_io.kitap_olustur(
            satirlar, csv_io.sayfa_adi_uret(yol), metin_olarak, koru, turler, ondalik))
        r = Rapor()
        for u in uyarilar:
            r.ekle(u)
        return kitap, r

    def _parola_sor(self, yol: str, yanlis: bool = False) -> Optional[str]:
        """Parolalı dosya için parola ister (iptal → None). Testlerde yamalanır."""
        metin = (f"“{os.path.basename(yol)}” parolayla korunuyor.\nParola:" if not yanlis
                 else "Parola yanlış. Yeniden deneyin:")
        parola, tamam = QInputDialog.getText(self, "Parola", metin, QLineEdit.Password)
        return parola if tamam else None

    def _kitap_oku(self, yol: str, parola: Optional[str] = None):
        """(kitap, rapor) | None (parola sorusunda İptal). Parolalı .xlsx'te kullanılan parola `self._okunan_parola`ya
        konur (pencere onu kaydederken yeniden kullanır; hiçbir yere yazılmaz)."""
        if not os.path.exists(yol):
            raise XlsxHatasi(f"Dosya bulunamadı: {yol}")
        self._okunan_parola = None
        uzanti = os.path.splitext(yol)[1].lower()
        if uzanti == ".xls":
            return arka_planda(self, "Dosya açılıyor…", lambda: xls_io.ac(yol))
        if uzanti == ".ods":
            return arka_planda(self, "Dosya açılıyor…", lambda: ods_io.ac(yol))
        sifreli = sifreleme.sifreli_mi(yol)
        yanlis = False
        while True:
            if sifreli and not parola:
                parola = self._parola_sor(yol, yanlis)
                if parola is None:
                    return None
            try:
                sonuc = arka_planda(self, "Dosya açılıyor…", lambda: xlsx_io.ac(yol, parola if sifreli else None))
            except sifreleme.YanlisParola:
                parola, yanlis = None, True
                continue
            self._okunan_parola = parola if sifreli else None
            return sonuc

    # ------------------------------------------------------------------ kaydet
    def _disk_degisti_sorusu(self) -> bool:
        """Dosya açıldıktan sonra başka bir yerde (başka program/başka Tabcel penceresi) değişti: üzerine yazılsın mı?"""
        c = QMessageBox.warning(
            self, APP_NAME, f"“{os.path.basename(self.yol)}” açıldıktan sonra başka bir yerde değiştirilmiş. "
            "Üzerine yazarsanız o değişiklikler kaybolur. Devam edilsin mi?",
            QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        return c == QMessageBox.Yes

    def kaydet(self) -> bool:
        if self.yol is None:
            return self.farkli_kaydet()
        if self._disk_damgasi is not None and _damga(self.yol) not in (None, self._disk_damgasi):
            if not self._disk_degisti_sorusu():
                return False
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
        elif self.kaynak_yol and self._kurtarilan:           # kurtarılan: özgün dosyanın üzerine yazmayı önermez
            onerilen = os.path.splitext(self.kaynak_yol)[0] + " (Kurtarılan).xlsx"
        elif self.kaynak_yol:                                # .csv'den açıldı: aynı adla .xlsx öner
            onerilen = os.path.splitext(self.kaynak_yol)[0] + ".xlsx"
        else:
            onerilen = os.path.join(self._baslangic_klasoru(), "Kitap1.xlsx")
        yol, filtre = QFileDialog.getSaveFileName(self, "Farklı Kaydet", onerilen, KAYDET_FILTRESI)
        if not yol:
            return False
        if not os.path.splitext(yol)[1]:
            yol += ".csv" if "csv" in (filtre or "").lower() else ".ods" if "ods" in (filtre or "").lower() else ".xlsx"
        hedef_eski = self.yol or self.kaynak_yol
        if self.rapor.veri_kaybi and _ayni_yol(yol, hedef_eski) and os.path.exists(yol):
            if self._veri_kaybi_sorusu() != "kaydet":        # özgün (grafikli vb.) dosyanın üzerine yazılıyor
                return False
        return self._kaydet_yola(yol)

    def _parola_belirle_sorusu(self):
        """(parola | '' (kaldır) | None (iptal)). Testlerde yamalanır. Yeni parola iki kez sorulur (yazım hatası
        belgeyi kilitlemesin); boş bırakılırsa parola kaldırılır."""
        varsa = " Boş bırakırsanız parola kaldırılır." if self.parola else ""
        p1, tamam = QInputDialog.getText(self, "Parola Belirle", "Yeni parola:" + varsa, QLineEdit.Password)
        if not tamam:
            return None
        if p1 == "":
            return ""
        p2, tamam = QInputDialog.getText(self, "Parola Belirle", "Parolayı yeniden yazın:", QLineEdit.Password)
        if not tamam:
            return None
        if p1 != p2:
            QMessageBox.warning(self, APP_NAME, "Parolalar eşleşmiyor; parola değiştirilmedi.")
            return None
        return p1

    def parola_belirle(self) -> bool:
        """Çalışma kitabını parolayla şifreler (Excel: Dosya → Parolayla Şifrele). Parola bir sonraki kayıtta uygulanır;
        belge "değişti" sayılır. Parola unutulursa dosya AÇILAMAZ (kurtarma yolu yok). Kaydedilince bu pencerenin otomatik
        kurtarma kopyası yazılmaz (düz kopya diskte kalmasın)."""
        yeni = self._parola_belirle_sorusu()
        if yeni is None:
            return False
        yeni = yeni or None
        if yeni == self.parola:
            return False
        self.parola = yeni
        self.gorunum_degisti_isaretle()
        self.statusBar().showMessage("Parola belirlendi; kaydedince uygulanır." if yeni
                                     else "Parola kaldırıldı; kaydedince uygulanır.", 6000)
        return True

    def _parolasiz_kayit_sorusu(self) -> bool:
        """Parolalı belge .csv/.ods olarak kaydedilirken: bu biçimler parola desteklemez. Evet → parola kalkar."""
        c = QMessageBox.warning(
            self, APP_NAME, "Bu biçim parola ile korumayı desteklemez; dosya parolasız kaydedilir ve parola kalkar. "
            "Devam edilsin mi?", QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if c != QMessageBox.Yes:
            return False
        self.parola = None
        return True

    def _csv_cok_sayfa_sorusu(self) -> bool:
        """Birden çok sayfalı kitap CSV'ye yazılırken yalnız etkin sayfa kaydedilir: devam edilsin mi?"""
        c = QMessageBox.question(
            self, APP_NAME, "CSV biçimi yalnızca etkin sayfayı kaydeder; diğer sayfalar ve biçimlendirme "
            "kaydedilmez. Devam edilsin mi?", QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Yes)
        return c == QMessageBox.Yes

    def _kaydet_yola(self, yol: str) -> bool:
        csv_mi = os.path.splitext(yol)[1].lower() == ".csv"
        kayit_raporu = None
        if self.parola and os.path.splitext(yol)[1].lower() in (".csv", ".ods") and not self._parolasiz_kayit_sorusu():
            return False
        try:
            if csv_mi:
                if len(self.kitap.sayfalar) > 1 and not self._csv_cok_sayfa_sorusu():
                    return False
                sayfa = self.izgara().sayfa
                arka_planda(self, "Kaydediliyor…", lambda: csv_io.dosya_yaz(sayfa, yol))
            elif os.path.splitext(yol)[1].lower() == ".ods":
                self.otokayit_bekle()
                kayit_raporu = arka_planda(self, "Kaydediliyor…", lambda: ods_io.kaydet(self.kitap, yol))
            else:
                self.otokayit_bekle()                         # iki yazım aynı anda belleği ikiye katlamasın
                parola = self.parola
                kayit_raporu = arka_planda(self, "Kaydediliyor…", lambda: xlsx_io.kaydet(
                    self.kitap, yol, **({"parola": parola} if parola else {})))
        except (XlsxHatasi, csv_io.CsvHatasi) as e:
            QMessageBox.critical(self, APP_NAME, str(e))
            return False
        except Exception as e:                               # beklenmeyen hata: pencere kapanmasın, veri kaybolmasın
            QMessageBox.critical(self, APP_NAME, f"Dosya kaydedilemedi: {e}")
            return False
        self.yol = os.path.abspath(yol)
        self.kaynak_yol = None
        self._disk_damgasi = _damga(self.yol)
        self._izle()
        # artık dosya bu kitabın kendisi: açılıştaki kayıp uyarısı biter; kayıt sırasındaki düzeltmeler bildirilir
        self.rapor = kayit_raporu if isinstance(kayit_raporu, Rapor) else Rapor()
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
        if self._mesgul:                                     # kayıt/açma sürerken (görev çubuğundan kapat vb.)
            return False
        if not self.degisti_mi():
            return True
        c = self._kapatma_sorusu()
        if c == "kaydet":
            return self.kaydet()
        return c == "kaydetme"

    # ------------------------------------------------------------------ otomatik kurtarma (4e)
    def otokayit_yap(self, arka_plan: bool = False) -> bool:
        """Değişmiş belgenin kurtarma kopyasını yazar (değişiklik yoksa ya da son kopyadan beri aynıysa
        yazmaz). Kitabın anlık görüntüsü ana iş parçacığında alınır (ucuz); `arka_plan` ise yazım iş
        parçacığında sürer ve True "başlatıldı" demektir (zamanlayıcı yolu, T4b), değilse burada biter.
        Önceki yazım sürüyorsa yazmaz. Hata sessizce yutulur: otomatik işlem kullanıcıyı bölmez."""
        if self._otokayit_isi is not None or not self.degisti_mi():
            return False
        if self.parola:                                       # parolalı belge: düz kurtarma kopyası APPDATA'ya yazılmaz
            return False
        damga =(self.yigin.damga(), self._gorunum_surum)
        if self._son_otokayit is not None and self.yigin.damga_esit(damga[0], self._son_otokayit[0]) \
                and damga[1] == self._son_otokayit[1]:
            return False
        try:
            anlik = kitap_anligi(self.kitap)
            rapor = Rapor(list(self.rapor.uyarilar), self.rapor.veri_kaybi)
        except Exception:
            return False
        kimlik, ad, yol = self.kurtarma_kimligi, self.belge_adi, self.yol or self.kaynak_yol
        is_ = _OtokayitIsi(lambda: kurtarma.kopya_yaz(anlik, kimlik, ad, yol, rapor), damga)
        if not arka_plan:
            is_.run()                                         # aynı iş, bu iş parçacığında
            return self._otokayit_sonucu(is_)
        self._otokayit_isi = is_
        is_.finished.connect(lambda: self._otokayit_bitti(is_))
        is_.start(QThread.LowPriority)
        return True

    def _otokayit_sonucu(self, is_: _OtokayitIsi) -> bool:
        if not is_.basarili:
            return False
        # yazım arka planda olsa da Python kilidini (GIL) ana iş parçacığıyla paylaşır: payı ≤ ~%10 kalsın
        self._otokayit_zamanlayici.setInterval(max(self.OTOKAYIT_MS, int(is_.sure_ms * 10)))
        self._son_otokayit = is_.damga
        return True

    def _otokayit_bitti(self, is_: _OtokayitIsi) -> None:
        if self._otokayit_isi is not is_:                    # otokayit_bekle zaten işledi
            return
        self._otokayit_isi = None
        self._otokayit_sonucu(is_)
        is_.deleteLater()

    def otokayit_bekle(self) -> None:
        """Süren arka plan yazımı bitene dek bekler (silme, elle kayıt, kapanış öncesi)."""
        is_ = getattr(self, "_otokayit_isi", None)
        if is_ is not None:
            is_.wait()
            self._otokayit_bitti(is_)

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
        p.rapor = Rapor(list(k.uyarilar), k.veri_kaybi)       # özgün dosyadaki kayıp uyarıları unutulmaz
        for u in rapor.uyarilar:
            p.rapor.ekle(u, rapor.veri_kaybi)
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
        self.otokayit_bekle()
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

    def sayfa_yapisi_degistir(self, **alanlar) -> bool:
        """Şerit düğmeleri (Sayfa Düzeni): etkin sayfanın `SayfaYapisi` alanlarını değiştirir; `sayfa_yapisi_ac`
        ile aynı geri alınabilir komut. Geçersiz değerde uyarır. Değişen yoksa False."""
        sayfa = self.izgara().sayfa
        try:
            yeni = sayfa.sayfa_yapisi.degistir(**alanlar)
        except ValueError as e:
            QMessageBox.warning(self, APP_NAME, str(e))
            return False
        kmt = SayfaYapisiDegis(sayfa, yeni)
        if kmt.bos_mu():
            return False
        self.yigin.calistir(kmt)
        self._baslik_guncelle()
        self._eylem_durumlari()
        return True

    # --- el ile sayfa sonları (T9): etkin hücrenin ÜSTÜNE ve SOLUNA, Excel gibi ---
    def sayfa_sonu_ekle(self) -> bool:
        g = self.izgara()
        r, c = g._aktif
        y = g.sayfa.sayfa_yapisi
        kw = {}
        if r >= 2 and r not in y.satir_kesmeleri:
            kw["satir_kesmeleri"] = y.satir_kesmeleri + (r,)
        if c >= 2 and c not in y.sutun_kesmeleri:
            kw["sutun_kesmeleri"] = y.sutun_kesmeleri + (c,)
        if not kw:
            return False
        g.sayfa.gorunum_yaz(sayfa_sonlari=True)               # ekleyince çizgiler görünsün
        ok = self.sayfa_yapisi_degistir(**kw)
        if ok and (y.sigdir_genislik or y.sigdir_yukseklik):
            self.statusBar().showMessage("Sığdır seçeneği açıkken sayfa sonları yok sayılır (Excel gibi); "
                                         "yazdırmada ve sayfa sınırı çizgilerinde görünmez.", 8000)
        return ok

    def sayfa_sonu_kaldir(self) -> bool:
        g = self.izgara()
        r, c = g._aktif
        y = g.sayfa.sayfa_yapisi
        kw = {}
        if r in y.satir_kesmeleri:
            kw["satir_kesmeleri"] = tuple(k for k in y.satir_kesmeleri if k != r)
        if c in y.sutun_kesmeleri:
            kw["sutun_kesmeleri"] = tuple(k for k in y.sutun_kesmeleri if k != c)
        return bool(kw) and self.sayfa_yapisi_degistir(**kw)

    def sayfa_sonlarini_sifirla(self) -> bool:
        return self.sayfa_yapisi_degistir(satir_kesmeleri=(), sutun_kesmeleri=())

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
