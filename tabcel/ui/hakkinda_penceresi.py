"""Hakkında penceresi (Faz 7b): sürüm, künye, gizlilik notu ve kullanılan açık kaynak bileşenler (CLAUDE.md kural 5)."""
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from .. import APP_NAME, DEVELOPERS, __version__
from . import theme

# (ad, ne için, lisans) — yeni bağımlılık eklenince buraya ve README'ye yazılır
BILESENLER = [
    ("PySide6 (Qt)", "arayüz", "LGPL v3"),
    ("openpyxl + et_xmlfile", ".xlsx okuma/yazma", "MIT"),
    ("Pillow", "resim işleme", "HPND (MIT benzeri)"),
    ("comtypes", "Windows yazım denetimi", "MIT"),
]


def hakkinda_metni() -> str:
    """Pencerenin düz metin özeti (testte ve panoya kopyalamada kullanılır)."""
    satirlar = [APP_NAME, f"Sürüm {__version__}  ·  Türkçe hesap tablosu", DEVELOPERS,
                "Çalışma kitaplarınız bu bilgisayarda kalır; hiçbir sunucuya gönderilmez.",
                "Kullanılan açık kaynak bileşenler:"]
    satirlar += [f"•  {ad} — {ne} ({lisans})" for ad, ne, lisans in BILESENLER]
    return "\n".join(satirlar)


class HakkindaPenceresi(QDialog):
    def __init__(self, ust=None):
        super().__init__(ust)
        self.setWindowTitle(f"{APP_NAME} Hakkında")
        self.setFixedWidth(460)
        d = QVBoxLayout(self)
        d.setContentsMargins(20, 18, 20, 14)
        d.setSpacing(10)

        baslik = QLabel(APP_NAME)
        f = baslik.font()
        f.setPointSizeF(f.pointSizeF() + 8)
        f.setBold(True)
        baslik.setFont(f)
        baslik.setStyleSheet(f"color: {theme.ACCENT};")
        d.addWidget(baslik)

        alt = QLabel(f"Sürüm {__version__}  ·  Türkçe hesap tablosu")
        alt.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        d.addWidget(alt)

        imza = QLabel(DEVELOPERS)
        f2 = imza.font()
        f2.setBold(True)
        imza.setFont(f2)
        d.addWidget(imza)

        gizlilik = QLabel("Çalışma kitaplarınız bu bilgisayarda kalır; hiçbir sunucuya gönderilmez. "
                          "Bulut yapay zekâ, telemetri ve hesap bağlantısı yoktur.")
        gizlilik.setWordWrap(True)
        d.addWidget(gizlilik)

        bilesenler = QLabel("Kullanılan açık kaynak bileşenler:\n" + "\n".join(
            f"•  {ad} — {ne} ({lisans})" for ad, ne, lisans in BILESENLER))
        bilesenler.setWordWrap(True)
        bilesenler.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        d.addWidget(bilesenler)

        dugmeler = QDialogButtonBox()
        kapat = dugmeler.addButton("Kapat", QDialogButtonBox.AcceptRole)
        kapat.setDefault(True)
        dugmeler.accepted.connect(self.accept)
        d.addWidget(dugmeler)
