"""Pencerenin bulut işlemleri (Faz 7a): Google Drive / OneDrive'dan aç, oraya kaydet, dosya başka yerde
(web, başka bilgisayar) değişirse fark et. API yok; masaüstü eşitleme klasörü üzerinden (`io/bulut.py`).
`DosyaIslemleri`yle birlikte `Pencere`ye karışır (alanları: `yol`, `_mesgul`, `degisti_mi`, `_kaydet_yola`…)."""
import os
from typing import Optional

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMenu, QMessageBox

from .. import APP_NAME
from ..io import bulut, son_dosyalar, xlsx_io
from ..io.xlsx_io import XlsxHatasi

YOKLAMA_MS = 4000                                             # klasör izleme bulut sürücülerinde güvenilmez: yoklanır


class BulutIslemleri:
    def _bulut_kur(self) -> None:
        self._izleyici = bulut.ChangeTracker()
        self._yoklama = QTimer(self)
        self._yoklama.timeout.connect(self._dis_degisiklik_denetle)
        self._yoklama.start(YOKLAMA_MS)

    def _izle(self) -> None:
        """Açık dosyayı izlemeye al (açılış/kayıt sonrası): bilinen imza o an güncellenir."""
        self._izleyici.track(self.yol)

    # ------------------------------------------------------------------ menü
    def _bulut_menusu_doldur(self, menu: QMenu) -> None:
        self._bulut_eylem_listesi = []                        # (sağlayıcı, 'ac'|'kaydet', eylem)
        for saglayici in (bulut.GOOGLE, bulut.ONEDRIVE):
            for tur, metin in (("ac", f"{saglayici}'dan Aç…"), ("kaydet", f"{saglayici}'a Kaydet…")):
                eylem = menu.addAction(metin, lambda s=saglayici, t=tur: self._bulutta(s, t))
                self.eylemler[f"dosya.bulut_{tur}_{'google' if saglayici == bulut.GOOGLE else 'onedrive'}"] = eylem
                self._bulut_eylem_listesi.append((saglayici, tur, eylem))
        menu.aboutToShow.connect(lambda: self._bulut_eylemlerini_guncelle(True))
        self._bulut_eylemlerini_guncelle()

    def _bulut_eylemlerini_guncelle(self, yenile: bool = False) -> None:
        var = {k.provider for k in bulut.cloud_folders(refresh=yenile)}
        for saglayici, _, eylem in self._bulut_eylem_listesi:
            eylem.setVisible(saglayici in var)

    def _bulut_klasoru(self, saglayici: str) -> Optional[bulut.CloudFolder]:
        return next((k for k in bulut.cloud_folders() if k.provider == saglayici), None)

    def _bulutta(self, saglayici: str, tur: str):
        klasor = self._bulut_klasoru(saglayici)
        if klasor is None:
            QMessageBox.information(self, APP_NAME, f"Bu bilgisayarda {saglayici} klasörü bulunamadı. "
                                    f"{saglayici} masaüstü uygulamasının kurulu ve oturumunun açık olması gerekir.")
            return None
        mevcut = bulut.provider_for(self.yol) == saglayici if self.yol else False
        baslangic = os.path.dirname(self.yol) if mevcut else str(klasor.path)
        if tur == "ac":
            from .dosya_islemleri import ACMA_FILTRESI
            yol, _ = QFileDialog.getOpenFileName(self, f"{saglayici}'dan Aç", baslangic, ACMA_FILTRESI)
            return self.dosya_ac(yol) if yol else None
        from .dosya_islemleri import KAYDET_FILTRESI
        ad = os.path.basename(self.yol) if self.yol else "Kitap1.xlsx"
        yol, filtre = QFileDialog.getSaveFileName(self, f"{saglayici}'a Kaydet",
                                                  os.path.join(baslangic, ad), KAYDET_FILTRESI)
        if not yol:
            return None
        if not os.path.splitext(yol)[1]:
            yol += ".csv" if "csv" in (filtre or "").lower() else ".xlsx"
        return self._kaydet_yola(yol)

    def google_bicimi_ac(self, yol: str) -> bool:
        """`.gsheet` gibi Google biçimli dosyanın içeriği bilgisayarda yoktur: açılamaz, tarayıcıda aranır."""
        if not bulut.is_google_format(yol):
            return False
        tur = bulut.GOOGLE_FORMATS[os.path.splitext(yol)[1].lower()]
        k = QMessageBox(QMessageBox.Information, APP_NAME,
                        f"Bu bir {tur} belgesi; içeriği bu bilgisayarda değil, yalnızca Google'da duruyor. "
                        f"{APP_NAME} onu doğrudan açamaz.\n\nExcel olarak indirmek için tarayıcıda açın: "
                        "Dosya → İndir → Microsoft Excel (.xlsx); sonra indirilen dosyayı burada açın.", parent=self)
        ac = k.addButton("Tarayıcıda Ara", QMessageBox.AcceptRole)
        k.addButton("Kapat", QMessageBox.RejectRole)
        k.exec()
        if k.clickedButton() is ac:
            QDesktopServices.openUrl(QUrl(bulut.google_search_url(yol)))
        return True

    # ------------------------------------------------------------------ dışarıdan değişiklik
    def _dis_degisiklik_denetle(self) -> None:
        if self.yol is None or self._mesgul or self._izleyici.conflict or not self.isVisible():
            return
        if self._izleyici.changed():
            self._dis_degisiklik()

    def _dis_degisiklik_sorusu(self) -> str:
        """'yukle' | 'koru' | 'ayri' (yerelde kaydedilmemiş değişiklik varken). Testlerde yamalanır."""
        saglayici = bulut.provider_for(self.yol)
        nerede = f"{saglayici} üzerinden " if saglayici else ""
        k = QMessageBox(QMessageBox.Warning, APP_NAME,
                        f"“{os.path.basename(self.yol)}” başka bir yerde değiştirildi ({nerede}başka bir bilgisayar ya da "
                        "program). Sizin kaydedilmemiş değişiklikleriniz de var.", parent=self)
        yukle = k.addButton("Onların Sürümünü Yükle", QMessageBox.DestructiveRole)
        koru = k.addButton("Benimkini Koru", QMessageBox.AcceptRole)
        ayri = k.addButton("Benimkini Ayrı Kaydet…", QMessageBox.ActionRole)
        k.setDefaultButton(koru)
        k.exec()
        b = k.clickedButton()
        return "yukle" if b is yukle else "ayri" if b is ayri else "koru"

    def _dis_degisiklik(self) -> None:
        saglayici = bulut.provider_for(self.yol)
        if not self.degisti_mi():                              # yerelde kayıp yok: yeni sürüm sessizce yüklenir
            self._yeniden_yukle(f"Belgenin {saglayici + ' üzerinden ' if saglayici else ''}gelen yeni sürümü yüklendi.")
            return
        secim = self._dis_degisiklik_sorusu()
        if secim == "yukle":
            self._yeniden_yukle("Başka yerde değiştirilen sürüm yüklendi.")
        elif secim == "ayri":
            if not self.farkli_kaydet():                       # vazgeçti: bir sonraki yoklamada yine sorulur
                self._izleyici.conflict = False
                self._izleyici.known = (-1, -1)
        else:                                                  # koru: sonraki kayıtta üzerine yazma sorusu zaten çıkar
            self._izleyici.remember()

    def _yeniden_yukle(self, ileti: str) -> bool:
        """Diskteki sürümü YENİ pencerede açar, bu pencereyi (kaydedilmemiş değişiklikler atılarak) kapatır."""
        from .window import Pencere
        from .dosya_islemleri import DosyaIslemleri, _damga
        try:
            kitap, rapor = self._kitap_oku(self.yol)
        except XlsxHatasi:                                     # eşitleme yarım olabilir: sonraki yoklamada yeniden dene
            self._izleyici.conflict = False
            self._izleyici.known = (-1, -1)
            return False
        yol = self.yol
        p = Pencere(kitap)
        p.yol = os.path.abspath(yol)
        p._disk_damgasi = _damga(p.yol)
        p.rapor = rapor
        p.setGeometry(self.geometry())
        if self.isMaximized():
            p.setWindowState(p.windowState() | self.windowState())
        p._belge_adi_guncelle()
        p._bilgi_goster()
        p._izle()
        DosyaIslemleri._tutulan.append(p)
        self._temiz_damga = self.yigin.damga()                 # atılan değişiklikler için kapatırken sorma
        self._kurtarilan = False
        self._gorunum_kirli = False
        p._dosya_gorunur_yap()                                 # önce yenisi görünür: son pencere kapanınca uygulama bitmesin
        self.close()
        p.statusBar().showMessage(ileti, 6000)
        son_dosyalar.ekle(yol)
        return True
