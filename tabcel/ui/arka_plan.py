"""Uzun dosya işlemlerini arka plan iş parçacığında çalıştırır (Faz 4 / 4f).

Ana iş parçacığı yerel bir olay döngüsünde bekler (pencere çizilir, donmuş görünmez); işlem
`gecikme_ms`ten uzun sürerse pencere devre dışı bırakılıp "bekleyin" ilerleme penceresi gösterilir. İşlev
Qt nesnesine dokunmamalıdır (yalnız saf Python: `xlsx_io`, `csv_io`). Kullanıcı bu sürede modeli
değiştiremediği için (pencere devre dışı) kaydetme güvenlidir. İşlevin istisnası ana iş parçacığında yeniden atılır.
"""
from typing import Callable, Optional

from PySide6.QtCore import QEventLoop, Qt, QThread, QTimer
from PySide6.QtWidgets import QApplication, QProgressDialog

from .. import APP_NAME


class _Is(QThread):
    def __init__(self, islev: Callable):
        super().__init__()
        self._islev = islev
        self.sonuc = None
        self.hata: Optional[BaseException] = None

    def run(self) -> None:
        try:
            self.sonuc = self._islev()
        except BaseException as e:          # noqa: BLE001 — ana iş parçacığına aktarılır
            self.hata = e


def arka_planda(parent, metin: str, islev: Callable, gecikme_ms: int = 400):
    is_ = _Is(islev)
    pencere_acik = parent is not None and parent.isEnabled()
    if parent is not None:
        parent._mesgul = True                              # bu sürede kapatma isteği ertelenir (iç içe kayıt olmasın)
    dlg = None
    if parent is not None:
        dlg = QProgressDialog(metin, "", 0, 0, parent)
        dlg.setWindowTitle(APP_NAME)
        dlg.setCancelButton(None)
        dlg.setWindowModality(Qt.WindowModal)
        dlg.setMinimumDuration(10 ** 9)                  # kendi zamanlayıcımızla göstereceğiz
        dlg.setAutoClose(False)
        dlg.setAutoReset(False)
    gosterici = QTimer()
    gosterici.setSingleShot(True)
    if dlg is not None:
        gosterici.timeout.connect(lambda: (parent.setEnabled(False), dlg.show()) if not is_.isFinished() else None)
        gosterici.start(gecikme_ms)
    is_.start()
    try:
        while not is_.isFinished():
            QApplication.processEvents(QEventLoop.ExcludeUserInputEvents, 30)
            is_.wait(15)
    finally:
        gosterici.stop()
        is_.wait()
        if dlg is not None:
            dlg.close()
            dlg.deleteLater()
        if parent is not None:
            parent._mesgul = False
        if pencere_acik:
            parent.setEnabled(True)
    if is_.hata is not None:
        raise is_.hata
    return is_.sonuc
