"""Uygulama içi yardım: "Yardım ve Nasıl Kullanılır" penceresi (Sözcük'teki `help.py` düzeni).

İçerik `tabcel/yardim.md` dosyasındadır (konulara bölünmüş Markdown); yeni özellik eklendikçe oraya yazılır.
Pencere konu listesi, arama (Türkçe büyük/küçük harf duyarsız, eşleşmeler vurgulanır) ve konular arası
bağlantılar (`[Başlık](konu:kimlik)`) sunar. Tamamen çevrimdışıdır. Kullanıcıya görünen ad `APP_NAME`'den gelir:
yardım metninde ad `{APP_NAME}` yer tutucusuyla yazılır (CLAUDE.md kural 1).
"""
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor, QTextFrameFormat, QTextLength, QTextTable
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QSplitter, QTextBrowser, QTextEdit,
    QVBoxLayout, QWidget,
)

from .. import APP_NAME, resource_dir
from ..model.harmanla import tr_kucuk
from . import theme

YARDIM_DOSYASI = resource_dir() / "tabcel" / "yardim.md"
KONU_RE = re.compile(r"^<!--\s*konu:\s*([\w-]+)\s*\|\s*(.+?)\s*-->\s*$", re.MULTILINE)
BAGLANTI_ONEKI = "konu"
ILK_KONU = "baslarken"


@dataclass
class Konu:
    anahtar: str
    baslik: str
    govde: str

    def duz(self) -> str:
        """Arama için işaretlerden arındırılmış metin."""
        metin = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", self.govde)
        return re.sub(r"[`*#|>]", " ", metin)


def konulari_yukle(yol: Path = YARDIM_DOSYASI) -> List[Konu]:
    metin = yol.read_text(encoding="utf-8").replace("{APP_NAME}", APP_NAME)
    eslesmeler = list(KONU_RE.finditer(metin))
    konular = []
    for i, m in enumerate(eslesmeler):
        son = eslesmeler[i + 1].start() if i + 1 < len(eslesmeler) else len(metin)
        konular.append(Konu(m.group(1), m.group(2), metin[m.end():son].strip()))
    return konular


def ara(konular: List[Konu], sorgu: str) -> List[Konu]:
    """Tüm sorgu sözcüklerini içeren konular, ilgiye göre sıralı: başlıkta geçen, sonra ifadenin ve sözcüklerin
    konuda kaç kez geçtiği ("Yenilikler" her şeyden söz ettiği için yalnız bahsetmek öne almaz)."""
    sozcukler = tr_kucuk(sorgu).split()
    if not sozcukler:
        return list(konular)
    ifade = " ".join(sozcukler)
    puanli = []
    for i, k in enumerate(konular):
        baslik, metin = tr_kucuk(k.baslik), tr_kucuk(k.duz())
        if not all(s in baslik or s in metin for s in sozcukler):
            continue
        puan = 100 * sum(s in baslik for s in sozcukler) + 5 * metin.count(ifade) + sum(metin.count(s) for s in sozcukler)
        puanli.append((-puan, i, k))
    return [k for _, _, k in sorted(puanli, key=lambda t: (t[0], t[1]))]


def kisayollar(konular: List[Konu]) -> set:
    """Yardımda `Ctrl+B` biçiminde geçen kısayollar (test: uygulamada tanımlı olduklarını denetlemek için)."""
    bulunan = set()
    for k in konular:
        for kod in re.findall(r"`([^`]+)`", k.govde):
            if re.fullmatch(r"((Ctrl|Shift|Alt)\+)+(F\d{1,2}|[A-Z0-9=\-]|Boşluk|Enter|Home|End|PgUp|PgDown)|F\d{1,2}|Delete|Esc", kod):
                bulunan.add(kod)
    return bulunan


class YardimPenceresi(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle(f"{APP_NAME} — Yardım ve Nasıl Kullanılır")
        self.resize(1000, 700)
        self.konular = konulari_yukle()
        self.anahtara_gore = {k.anahtar: k for k in self.konular}
        self.acik: Optional[str] = None

        self.arama = QLineEdit(placeholderText="Yardımda ara (ör. grafik, filtre, kısayol, F4)")
        self.arama.setClearButtonEnabled(True)
        self.arama.textChanged.connect(self._suz)
        self.arama.returnPressed.connect(self._ilk_sonucu_ac)
        self.sonuc_etiketi = QLabel()
        self.sonuc_etiketi.setStyleSheet(f"color: {theme.TEXT_MUTED};")

        self.liste = QListWidget()
        self.liste.setMinimumWidth(220)
        self.liste.currentItemChanged.connect(lambda oge, _: oge and self.konu_goster(oge.data(Qt.UserRole)))

        self.tarayici = QTextBrowser()
        self.tarayici.setOpenLinks(False)
        self.tarayici.anchorClicked.connect(self._baglanti)
        self.tarayici.document().setDocumentMargin(24)

        sol = QWidget()
        sol_d = QVBoxLayout(sol)
        sol_d.setContentsMargins(0, 0, 0, 0)
        sol_d.addWidget(self.liste, 1)
        sol_d.addWidget(self.sonuc_etiketi)
        bolen = QSplitter()
        bolen.addWidget(sol)
        bolen.addWidget(self.tarayici)
        bolen.setStretchFactor(1, 1)
        bolen.setSizes([240, 760])
        d = QVBoxLayout(self)
        d.setContentsMargins(12, 12, 12, 12)
        d.addWidget(self.arama)
        d.addWidget(bolen, 1)

        self._suz("")
        self.konu_ac(ILK_KONU if ILK_KONU in self.anahtara_gore else self.konular[0].anahtar)

    # ------------------------------------------------------------------ konular
    def konu_ac(self, anahtar: str) -> None:
        if anahtar not in self.anahtara_gore:
            return
        if self.arama.text() and anahtar not in [self.liste.item(i).data(Qt.UserRole) for i in range(self.liste.count())]:
            self.arama.clear()
        for i in range(self.liste.count()):
            if self.liste.item(i).data(Qt.UserRole) == anahtar:
                self.liste.setCurrentRow(i)
        self.konu_goster(anahtar)

    def konu_goster(self, anahtar: str) -> None:
        konu = self.anahtara_gore[anahtar]
        if self.acik != anahtar:
            self.acik = anahtar
            self.tarayici.setMarkdown(konu.govde)
            self._belgeyi_bicimle()
            self.tarayici.verticalScrollBar().setValue(0)
        self._vurgula()

    def _belgeyi_bicimle(self) -> None:
        belge = self.tarayici.document()
        yazi = QFont("Segoe UI")
        yazi.setPointSizeF(10.5)
        belge.setDefaultFont(yazi)
        for cerceve in belge.rootFrame().childFrames():          # Markdown tabloları kenarlıksız gelir
            if not isinstance(cerceve, QTextTable):
                continue
            bicim = cerceve.format()
            bicim.setBorder(1)
            bicim.setBorderStyle(QTextFrameFormat.BorderStyle_Solid)
            bicim.setBorderBrush(QColor("#d6d6d6"))
            bicim.setBorderCollapse(True)
            bicim.setCellPadding(6)
            bicim.setWidth(QTextLength(QTextLength.PercentageLength, 100))
            cerceve.setFormat(bicim)
            for sutun in range(cerceve.columns()):
                hucre = cerceve.cellAt(0, sutun)
                hb = hucre.format()
                hb.setBackground(QColor("#e8f3ec"))
                hucre.setFormat(hb)
        blok = belge.begin()
        while blok.isValid():                                    # başlık renkleri ve kısayol kodları
            seviye = blok.blockFormat().headingLevel()
            if seviye:
                im = QTextCursor(blok)
                im.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                b = QTextCharFormat()
                b.setForeground(QColor(theme.ACCENT if seviye == 1 else "#1f1f1f"))
                im.mergeCharFormat(b)
            it = blok.begin()
            while not it.atEnd():
                parca = it.fragment()
                if parca.isValid() and parca.charFormat().fontFixedPitch():
                    im = QTextCursor(belge)
                    im.setPosition(parca.position())
                    im.setPosition(parca.position() + parca.length(), QTextCursor.KeepAnchor)
                    b = QTextCharFormat()
                    b.setBackground(QColor("#f0f0f0"))
                    b.setForeground(QColor("#1f1f1f"))
                    b.setFontFamilies(["Segoe UI"])
                    b.setFontWeight(QFont.DemiBold)
                    im.mergeCharFormat(b)
                it += 1
            blok = blok.next()
        belge.setModified(False)

    def _baglanti(self, url) -> None:
        if url.scheme() == BAGLANTI_ONEKI:
            self.konu_ac(url.path())

    # ------------------------------------------------------------------ arama
    def _suz(self, metin: str) -> None:
        bulunan = ara(self.konular, metin)
        self.liste.blockSignals(True)
        self.liste.clear()
        for k in bulunan:
            oge = QListWidgetItem(k.baslik)
            oge.setData(Qt.UserRole, k.anahtar)
            self.liste.addItem(oge)
            if k.anahtar == self.acik:
                self.liste.setCurrentItem(oge)
        self.liste.blockSignals(False)
        if metin.strip():
            self.sonuc_etiketi.setText(f"{len(bulunan)} konu bulundu" if bulunan else "Sonuç bulunamadı")
            if bulunan and self.acik not in [k.anahtar for k in bulunan]:
                self.liste.setCurrentRow(0)
        else:
            self.sonuc_etiketi.setText("")
        self._vurgula()

    def _ilk_sonucu_ac(self) -> None:
        if self.liste.count():
            self.liste.setCurrentRow(0)
            self.konu_goster(self.liste.item(0).data(Qt.UserRole))

    def _vurgula(self) -> None:
        """Arama sözcüklerini açık konuda sarıyla vurgular ve ilk eşleşmeye kaydırır."""
        sozcukler = tr_kucuk(self.arama.text()).split()
        belge = self.tarayici.document()
        secimler = []
        bicim = QTextCharFormat()
        bicim.setBackground(QColor("#fff3a3"))
        if sozcukler:
            metin = tr_kucuk(belge.toPlainText())
            for s in sozcukler:
                i = metin.find(s)
                while i >= 0:
                    im = QTextCursor(belge)
                    im.setPosition(i)
                    im.setPosition(i + len(s), QTextCursor.KeepAnchor)
                    sec = QTextEdit.ExtraSelection()
                    sec.cursor, sec.format = im, bicim
                    secimler.append(sec)
                    i = metin.find(s, i + len(s))
        self.tarayici.setExtraSelections(secimler)
        if secimler:
            ilk = min(secimler, key=lambda x: x.cursor.position())
            im = QTextCursor(belge)
            im.setPosition(ilk.cursor.selectionStart())
            self.tarayici.setTextCursor(im)
            self.tarayici.ensureCursorVisible()


def yardim_goster(ust, konu: Optional[str] = None) -> YardimPenceresi:
    """Yardım penceresini (tek örnek) açar ve öne getirir."""
    pencere = getattr(ust, "_yardim_penceresi", None)
    if pencere is None:
        pencere = YardimPenceresi(ust)
        ust._yardim_penceresi = pencere
    if konu:
        pencere.konu_ac(konu)
    pencere.show()
    pencere.raise_()
    pencere.activateWindow()
    return pencere
