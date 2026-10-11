"""KVKK Paylaşım Temizleyici penceresi (Faz 9d). Yardımcı araçtır; mevzuata uygunluk iddiası yoktur (kural 20). Mantık
`model/temizle.py` ve `io/temiz_dosya.py`'dedir.

Akış: tarama (donmadan, ilerleme + iptal) → tür başına Maskele / Sil / Bırak (+ tek tek işaretleme, maske ayarı) → “Temiz kopya
oluştur” → etkilenen formüller listesi (isteğe bağlı “değere çevir”) → yeni dosya adı → yazma + doğrulama. **Özgün dosya ve açık
kitap değişmez** (kural 17)."""
import os
import time
from collections import Counter
from typing import List, Optional

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QProgressBar, QPushButton, QSpinBox, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QApplication,
)

from .. import APP_NAME
from ..formul import ceviri
from ..io import temiz_dosya, xlsx_io
from ..model import kimlik, temizle
from . import theme

DILIM_MS = 12
ROL_KAYIT = Qt.UserRole
BASLIK_NOTU = ("Yardımcı araçtır; bulduklarını siz onaylarsınız ve yasal uygunluğu garanti etmez. "
               "Verileriniz bilgisayarınızdan çıkmaz. Özgün dosyanız değişmez: temizlenmiş sonuç yeni bir dosyaya yazılır.")


class MaskeAyariPenceresi(QDialog):
    def __init__(self, tur: str, ayar: kimlik.MaskeAyari, ust=None):
        super().__init__(ust)
        self.setWindowTitle(f"Maske — {kimlik.TUR_ADLARI[tur]}")
        f = QFormLayout(self)
        self.bas = QSpinBox()
        self.bas.setRange(0, 12)
        self.bas.setValue(ayar.bas)
        self.son = QSpinBox()
        self.son.setRange(0, 12)
        self.son.setValue(ayar.son)
        self.karakter = QLineEdit(ayar.karakter)
        self.karakter.setMaxLength(1)
        f.addRow("Baştan açık kalan karakter:", self.bas)
        f.addRow("Sondan açık kalan karakter:", self.son)
        f.addRow("Maske karakteri:", self.karakter)
        self.onizleme = QLabel("")
        f.addRow("Örnek:", self.onizleme)
        d = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        d.button(QDialogButtonBox.Ok).setText("Tamam")
        d.button(QDialogButtonBox.Cancel).setText("İptal")
        d.accepted.connect(self.accept)
        d.rejected.connect(self.reject)
        f.addRow(d)
        self._tur = tur
        for w in (self.bas, self.son):
            w.valueChanged.connect(self._ornek)
        self.karakter.textChanged.connect(self._ornek)
        self._ornek()

    def ayar(self) -> kimlik.MaskeAyari:
        return kimlik.MaskeAyari(self.bas.value(), self.son.value(), self.karakter.text() or "*")

    def _ornek(self) -> None:
        orn = {kimlik.TC: "12345678950", kimlik.VKN: "1234567890", kimlik.IBAN: "TR330006100519786457841326",
               kimlik.KART: "4111111111111111", kimlik.TELEFON: "05321234567", kimlik.EPOSTA: "ornek@ornek.com",
               kimlik.AD: "Ayşe Örnek"}[self._tur]
        self.onizleme.setText(kimlik.maskele(self._tur, orn, self.ayar()))


class EtkilenenFormuller(QDialog):
    """Maskeleme sonrası sonucu değişen/hataya dönen formüller; güvenli olanlar için “değere çevir” seçeneği."""

    def __init__(self, etkiler: List[temizle.FormulEtkisi], kitap, ust=None):
        super().__init__(ust)
        self.setWindowTitle("Etkilenen formüller")
        self.setMinimumSize(620, 380)
        d = QVBoxLayout(self)
        d.addWidget(QLabel("Maskeleme nedeniyle şu formüllerin sonucu değişiyor ya da hataya dönüyor. Formüller temiz kopyada "
                           "korunur ve maskeli değerle yeniden hesaplanır. İsterseniz özgün sonuçlarıyla değere çevirebilirsiniz; "
                           "ama sonuç kişisel veriden türetilmişse (örn. kimlik no + 1) yine bilgi taşır — yalnız toplam, "
                           "uzunluk gibi sonuçlar için işaretleyin."))
        d.itemAt(0).widget().setWordWrap(True)
        self.agac = QTreeWidget()
        self.agac.setHeaderLabels(["Hücre", "Formül", "Özgün sonuç", "Maskeli sonuç"])
        self.agac.setRootIsDecorated(False)
        self.etkiler = etkiler
        for e in etkiler:
            o = QTreeWidgetItem([f"{e.sayfa_ad}!{e.adres}", _tr_formul(e.formul, kitap), _goster(e.eski),
                                 _goster(e.yeni) + ("  (hata)" if e.hataya_dondu else "")])
            if e.degere_cevrilebilir:
                o.setFlags(o.flags() | Qt.ItemIsUserCheckable)
                o.setCheckState(0, Qt.Unchecked)
                o.setToolTip(0, "İşaretlerseniz formül, özgün sonucuyla değere çevrilir.")
            else:
                o.setToolTip(0, "Sonuç maskelenen bir değeri içerdiği için değere çevrilemez.")
            self.agac.addTopLevelItem(o)
        for i, g in enumerate((90, 200, 130, 130)):
            self.agac.setColumnWidth(i, g)
        d.addWidget(self.agac)
        d.addWidget(QLabel("Kutusu olmayan satırlar değere çevrilemez (sonuçları maskelenen bir değeri içerir)."))
        b = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        b.button(QDialogButtonBox.Ok).setText("Devam")
        b.button(QDialogButtonBox.Cancel).setText("Vazgeç")
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)
        d.addWidget(b)

    def secilenler(self) -> List[temizle.FormulEtkisi]:
        return [e for i, e in enumerate(self.etkiler)
                if self.agac.topLevelItem(i).flags() & Qt.ItemIsUserCheckable
                and self.agac.topLevelItem(i).checkState(0) == Qt.Checked]


def _tr_formul(formul: str, kitap) -> str:
    try:
        return ceviri.disa(formul, kitap)
    except Exception:
        return formul


def _goster(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v == int(v) and abs(v) < 1e15:
        return str(int(v))
    return str(v)


class TemizleyiciPenceresi(QDialog):
    hucreyeGit = Signal(object, int, int)

    def __init__(self, pencere):
        super().__init__(pencere)
        self.pencere = pencere
        self.setWindowTitle("Paylaşım Temizleyici")
        self.setMinimumSize(760, 600)
        d = QVBoxLayout(self)
        not_ = QLabel(BASLIK_NOTU)
        not_.setWordWrap(True)
        not_.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        d.addWidget(not_)
        self.ilerleme = QProgressBar()
        self.ilerleme.setRange(0, 1000)
        self.ilerleme.setTextVisible(False)
        self.ilerleme.setMaximumHeight(8)
        d.addWidget(self.ilerleme)
        self.ozet = QLabel("")
        self.ozet.setWordWrap(True)
        d.addWidget(self.ozet)
        self.turler = QTreeWidget()                                  # tür başına eylem satırı
        self.turler.setHeaderLabels(["Veri türü", "Adet", "Gizli yerde", "Eylem", ""])
        self.turler.setRootIsDecorated(False)
        self.turler.setMaximumHeight(190)
        self.turler.header().setStretchLastSection(False)
        d.addWidget(self.turler)
        self.agac = QTreeWidget()
        self.agac.setHeaderLabels(["Yer", "Bulgu (maskeli gösterim)", "Not"])
        self.agac.setColumnWidth(0, 230)
        self.agac.setColumnWidth(1, 250)
        d.addWidget(self.agac, 1)
        self.uyarilar = QLabel("")
        self.uyarilar.setWordWrap(True)
        self.uyarilar.setTextFormat(Qt.PlainText)
        d.addWidget(self.uyarilar)
        alt = QHBoxLayout()
        self.tara_dugmesi = QPushButton("Yeniden tara")
        self.iptal_dugmesi = QPushButton("İptal")
        self.iptal_dugmesi.setEnabled(False)
        self.olustur_dugmesi = QPushButton("Temiz kopya oluştur…")
        self.olustur_dugmesi.setDefault(True)
        self.olustur_dugmesi.setEnabled(False)
        kapat = QPushButton("Kapat")
        for b in (self.tara_dugmesi, self.iptal_dugmesi):
            alt.addWidget(b)
        alt.addStretch(1)
        alt.addWidget(self.olustur_dugmesi)
        alt.addWidget(kapat)
        d.addLayout(alt)
        self.tara_dugmesi.clicked.connect(self.tara)
        self.iptal_dugmesi.clicked.connect(self.iptal)
        self.olustur_dugmesi.clicked.connect(self.olustur)
        kapat.clicked.connect(self.close)
        self.agac.itemClicked.connect(lambda o, _k: self._git(o))
        self._uretec = None
        self._tarayici: Optional[temizle.Tarayici] = None
        self.kayitlar: List[temizle.Kayit] = []
        self.plan = temizle.Plan()
        self.meta = temiz_dosya.DosyaMeta()
        self._eylem_kutulari = {}
        self.sonuc_yolu: Optional[str] = None
        self._zamanlayici = QTimer(self)
        self._zamanlayici.setInterval(0)
        self._zamanlayici.timeout.connect(self._sur)

    # ------------------------------------------------------------------ tarama
    def tara(self) -> None:
        self.iptal()
        self.agac.clear()
        self.turler.clear()
        self.kayitlar = []
        self._eylem_kutulari = {}
        self.olustur_dugmesi.setEnabled(False)
        p = self.pencere
        yol = p.yol or getattr(p, "kaynak_yol", None)
        self.meta = temiz_dosya.meta_tara(yol) if yol and str(yol).lower().endswith((".xlsx", ".xlsm")) and os.path.exists(yol) \
            else temiz_dosya.DosyaMeta()
        self._tarayici = temizle.Tarayici(p.kitap)
        self._uretec = self._tarayici.calistir()
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
            self.ozet.setText("Tarama iptal edildi.")

    def _sur(self) -> None:
        if self._uretec is None:
            return
        bitis = time.perf_counter() + DILIM_MS / 1000
        try:
            while time.perf_counter() < bitis:
                olay = next(self._uretec)
                if olay[0] == "ilerleme":
                    self.ilerleme.setValue(int(olay[1] * 1000))
                    self.ozet.setText(olay[2])
                elif olay[0] == "kayit":
                    self.kayitlar.append(olay[1])
        except StopIteration:
            self._uretec = None
            self._zamanlayici.stop()
            self.tara_dugmesi.setEnabled(True)
            self.iptal_dugmesi.setEnabled(False)
            self.ilerleme.setValue(1000)
            self._sonuclari_goster()
        except Exception as e:
            self._uretec = None
            self._zamanlayici.stop()
            self.tara_dugmesi.setEnabled(True)
            self.iptal_dugmesi.setEnabled(False)
            self.ozet.setText(f"Tarama tamamlanamadı: {e}")

    # ------------------------------------------------------------------ sonuç
    def _sonuclari_goster(self) -> None:
        t = self._tarayici
        n = len(self.kayitlar)
        self.plan = temizle.Plan()
        self.turler.clear()
        self._eylem_kutulari = {}
        sayac = Counter(k.tur for k in self.kayitlar)
        gizli = Counter(k.tur for k in self.kayitlar if k.yer.gizli)
        for tur in kimlik.TURLER:
            if not sayac.get(tur):
                continue
            o = QTreeWidgetItem([kimlik.TUR_ADLARI[tur], str(sayac[tur]), str(gizli.get(tur, 0)) if gizli.get(tur) else "—"])
            self.turler.addTopLevelItem(o)
            kutu = QComboBox()
            for e in (temizle.MASKELE, temizle.SIL, temizle.BIRAK):
                kutu.addItem(temizle.EYLEM_ADLARI[e], e)
            kutu.currentIndexChanged.connect(lambda _i, tur=tur, kutu=kutu: self._eylem_degisti(tur, kutu))
            self.turler.setItemWidget(o, 3, kutu)
            ayar = QPushButton("Maske…")
            ayar.clicked.connect(lambda _c=False, tur=tur: self._maske_ayari(tur))
            self.turler.setItemWidget(o, 4, ayar)
            self._eylem_kutulari[tur] = kutu
        for i, g in enumerate((180, 60, 90, 110, 80)):
            self.turler.setColumnWidth(i, g)
        self.agac.clear()
        grup = {}
        for i, k in enumerate(self.kayitlar):
            ust = grup.get(k.tur)
            if ust is None:
                ust = grup[k.tur] = QTreeWidgetItem([kimlik.TUR_ADLARI[k.tur], "", ""])
                self.agac.addTopLevelItem(ust)
            yer = f"{k.sayfa_ad}!{k.yer.adres}" if k.yer.adres else f"{k.sayfa_ad or 'Kitap'}: {k.yer.ayrinti}"
            ayrinti = k.yer.ayrinti if k.yer.adres and k.yer.tur != temizle.HUCRE else ""
            notlar = [x for x in (k.yer.gizli, "belirsiz" if k.bulgu.guven == kimlik.BELIRSIZ else "",
                                  "sütun başlığından öneri" if k.tur == kimlik.AD else "", ayrinti) if x]
            o = QTreeWidgetItem([yer, kimlik.maskele(k.tur, k.bulgu.metin), "; ".join(notlar)])
            o.setFlags(o.flags() | Qt.ItemIsUserCheckable)
            o.setCheckState(0, Qt.Checked)
            o.setData(0, ROL_KAYIT, i)
            if k.yer.gizli:
                o.setForeground(2, Qt.red)
            ust.addChild(o)
        for ust in grup.values():
            ust.setText(0, f"{ust.text(0)} ({ust.childCount()})")
            ust.setExpanded(ust.childCount() <= 8)
        self.agac.itemChanged.connect(self._isaret_degisti)
        # uyarılar
        u = []
        gizli_toplam = sum(gizli.values())
        if gizli_toplam:
            u.append(f"⚠ {gizli_toplam} bulgu gizli satır/sütun/sayfa/ad içinde; bunlar normalde görünmez ama dosyayla paylaşılırdı.")
        if t.resim_sayisi:
            u.append(f"⚠ {t.resim_sayisi} resim var; resimlerin içeriği taranamaz (kimlik/ekran görüntüsü olabilir). Elle gözden geçirin.")
        if self.meta.alanlar:
            u.append("Özgün dosyanın meta verisi temiz kopyaya taşınmaz: " + ", ".join(f"{a}" for a, _ in self.meta.alanlar) + ".")
        if self.meta.ust_alt:
            u.append("Özgün dosyadaki üst/alt bilgi temiz kopyada bulunmaz.")
        self.uyarilar.setText("\n".join(u))
        self.ozet.setText(f"{n} bulgu, {t.taranan_hucre} hücre tarandı." if n else
                          f"Kişisel veri bulunmadı ({t.taranan_hucre} hücre tarandı). Yine de elle göz atmanız önerilir.")
        self.olustur_dugmesi.setEnabled(True)

    def _eylem_degisti(self, tur: str, kutu: QComboBox) -> None:
        self.plan.eylem[tur] = kutu.currentData()

    def _isaret_degisti(self, oge: QTreeWidgetItem, _k) -> None:
        i = oge.data(0, ROL_KAYIT)
        if i is None:
            return
        if oge.checkState(0) == Qt.Checked:
            self.plan.haric.discard(i)
        else:
            self.plan.haric.add(i)

    def _maske_ayari(self, tur: str) -> None:
        mevcut = self.plan.maske.get(tur) or kimlik.VARSAYILAN_MASKELER.get(tur, kimlik.MaskeAyari(1, 1))
        d = MaskeAyariPenceresi(tur, mevcut, self)
        if d.exec() == QDialog.Accepted:
            self.plan.maske[tur] = d.ayar()
            self._onizlemeyi_yenile(tur)

    def _onizlemeyi_yenile(self, tur: str) -> None:
        for ust_i in range(self.agac.topLevelItemCount()):
            ust = self.agac.topLevelItem(ust_i)
            for j in range(ust.childCount()):
                o = ust.child(j)
                k = self.kayitlar[o.data(0, ROL_KAYIT)]
                if k.tur == tur:
                    o.setText(1, kimlik.maskele(tur, k.bulgu.metin, self.plan.maske.get(tur)))

    def _git(self, oge: QTreeWidgetItem) -> None:
        i = oge.data(0, ROL_KAYIT)
        if i is None:
            return
        k = self.kayitlar[i]
        sayfa = self.pencere.kitap.sayfa_kimlikle(k.yer.sayfa_kimlik) if k.yer.sayfa_kimlik is not None else None
        if sayfa is not None and k.yer.tur in (temizle.HUCRE, temizle.FORMUL, temizle.NOT, temizle.NOT_YAZAR):
            r, c = k.yer.anahtar[0], k.yer.anahtar[1]
            self.pencere.hucreye_git(sayfa, r, c)

    # ------------------------------------------------------------------ temiz kopya
    def _onerilen_ad(self) -> str:
        p = self.pencere
        kaynak = p.yol or getattr(p, "kaynak_yol", None)
        if kaynak:
            return os.path.splitext(kaynak)[0] + " (temiz).xlsx"
        return os.path.join(p._baslangic_klasoru() if hasattr(p, "_baslangic_klasoru") else "", "Kitap (temiz).xlsx")

    def olustur(self) -> bool:
        """Temiz kopyayı üretir ve yeni dosyaya yazar. Döner: yazıldı mı."""
        p = self.pencere
        etkin = [k for i, k in enumerate(self.kayitlar) if i not in self.plan.haric and self.plan.eylem_of(k.tur) != temizle.BIRAK]
        if not etkin:
            if QMessageBox.question(self, APP_NAME, "Maskelenecek ya da silinecek bulgu yok. Yine de temiz bir kopya "
                                    "(meta veri ve üst/alt bilgi olmadan) yazılsın mı?") != QMessageBox.Yes:
                return False
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            tk = temizle.temiz_kopya(p.kitap, self.kayitlar, self.plan)
        finally:
            QApplication.restoreOverrideCursor()
        try:
            if tk.etkiler:
                d = EtkilenenFormuller(tk.etkiler, tk.kitap, self)
                if d.exec() != QDialog.Accepted:
                    return False
                tk.degere_cevir(d.secilenler())
            kaynak = p.yol or getattr(p, "kaynak_yol", None)
            yol, _ = QFileDialog.getSaveFileName(self, "Temiz Kopyayı Kaydet", self._onerilen_ad(), "Excel Çalışma Kitabı (*.xlsx)")
            if not yol:
                return False
            if not os.path.splitext(yol)[1]:
                yol += ".xlsx"
            try:
                rapor = temiz_dosya.temiz_yaz(tk, yol, kaynak)
            except temiz_dosya.OzgunYolaYazmaHatasi as e:
                QMessageBox.warning(self, APP_NAME, str(e))
                return False
            except temiz_dosya.DogrulamaHatasi as e:
                QMessageBox.critical(self, APP_NAME, str(e))
                return False
            except xlsx_io.XlsxHatasi as e:
                QMessageBox.warning(self, APP_NAME, str(e))
                return False
            ek = ("\n\nUyarı: " + "; ".join(rapor.uyarilar)) if rapor.uyarilar else ""
            QMessageBox.information(
                self, APP_NAME, f"Temiz kopya yazıldı:\n{yol}\n\nDoğrulandı: dosyanın hiçbir parçasında maskelenen/silinen "
                f"özgün değer bulunmuyor. Özgün dosyanız değişmedi.{ek}")
            self.sonuc_yolu = yol
            return True
        finally:
            tk.kapat()
