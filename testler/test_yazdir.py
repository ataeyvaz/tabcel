"""Faz 4 / 4d: çizim (piksel), PDF dışa aktarma, Sayfa Yapısı penceresi, menü akışı."""
import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox

from tabcel.model.adres import Aralik
from tabcel.model.komutlar import bicim_komutu
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.sayfa_yapisi import SayfaYapisi
from tabcel.model.stil import StilYama
from tabcel.ui import yazdir as yz
from tabcel.ui.dosya_islemleri import DosyaIslemleri
from tabcel.ui.sayfa_yapisi_penceresi import SayfaYapisiPenceresi, baslik_satirlari_coz, baslik_satirlari_yaz
from tabcel.ui.window import Pencere


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _sessiz(app, monkeypatch):
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: QMessageBox.Ok)
    yield
    for p in list(DosyaIslemleri._tutulan):
        p.degisti_mi = lambda: False
        p.close()
    DosyaIslemleri._tutulan.clear()


def pencere():
    p = Pencere(CalismaKitabi())
    p.show()
    return p


def _yaz(s, ar, **yama):
    bicim_komutu(s, [ar], StilYama(**yama)).yap()


def _resim(g, dilim_no=0, boyut=(900, 600)):
    """Dilimi 96 dpi'de QImage'e çizer (yazıcıdan bağımsız piksel denetimi)."""
    c = yz.SayfaCizici(g.sayfa, g.yazdirma_yuksekligi, g.font())
    d = c.dilimler()[dilim_no]
    img = QImage(boyut[0], boyut[1], QImage.Format_RGB32)
    img.fill(QColor("white"))
    p = QPainter(img)
    c.ciz(p, d, QRectF(0, 0, boyut[0], boyut[1]), 96.0)
    p.end()
    return img, c, d


# ---------------------------------------------------------------- çizim
def test_dolgu_ve_kenarlik_cizilir():
    p = pencere()
    g = p.izgara()
    g.hucre_gir(1, 1, "x")
    _yaz(g.sayfa, Aralik(1, 1, 1, 1), dolgu="#FF0000")
    _yaz(g.sayfa, Aralik(2, 2, 2, 2), kenar={"alt": ("kalin", "#0000FF")})
    g.hucre_gir(2, 2, "y")
    img, c, d = _resim(g)
    w1, h1 = c.genislik(1), g.yazdirma_yuksekligi(1)
    assert img.pixelColor(int(w1) - 3, int(h1) - 3) == QColor("#FF0000")        # A1 dolgusu (metinden uzak köşe)
    assert img.pixelColor(int(w1) + 5, int(h1) + 5) == QColor("white")          # B2 dolgusuz
    alt_y = int(h1 + g.yazdirma_yuksekligi(2))
    mavi = [img.pixelColor(int(w1) + 20, y) for y in range(alt_y - 3, alt_y + 2)]
    assert QColor("#0000FF") in mavi                                              # kalın alt kenarlık


def test_kilavuz_yalniz_istenince():
    p = pencere()
    g = p.izgara()
    g.hucre_gir(1, 1, "x")
    g.hucre_gir(3, 3, "x")
    img, c, _ = _resim(g)
    x, y = int(c.genislik(1)), 8
    assert img.pixelColor(x, y) == QColor("white")                                # varsayılan: çizgi yok
    g.sayfa.sayfa_yapisi = SayfaYapisi(kilavuz=True)
    img, c, _ = _resim(g)
    assert any(img.pixelColor(x + k, y) != QColor("white") for k in (-1, 0, 1))


def test_metin_cizilir_ve_tasar():
    p = pencere()
    g = p.izgara()
    g.hucre_gir(1, 1, "Çok uzun bir başlık metni burada")
    g.hucre_gir(2, 1, "Çok uzun bir başlık metni burada")
    g.hucre_gir(2, 2, "engel")                                                    # 2. satırda komşu dolu: taşmaz
    img, c, _ = _resim(g)
    w1 = int(c.genislik(1))
    h = int(g.yazdirma_yuksekligi(1))

    def koyu(x0, x1, y0, y1):
        return sum(1 for x in range(int(x0), int(x1)) for y in range(int(y0), int(y1))
                   if img.pixelColor(x, y).lightness() < 128)
    assert koyu(0, w1, 0, h) > 20                                                  # metin çizildi
    assert koyu(w1 + 2, w1 + c.genislik(2) - 2, 0, h) > 20                          # 1. satırda B1'e taştı
    # B2'de 'engel' var; A2 metninin B2'ye taşan kısmı olmamalı: piksel sayısı 'engel' kadar
    assert koyu(w1, w1 + 3, h, 2 * h) == 0


def test_birlesim_tek_dikdortgen_ve_yatay_ortala():
    p = pencere()
    g = p.izgara()
    g.hucre_gir(1, 1, "b")
    _yaz(g.sayfa, Aralik(1, 1, 1, 3), dolgu="#00FF00")
    g.sayfa.birlesimleri_yaz([Aralik(1, 1, 1, 3)], [])
    img, c, _ = _resim(g)
    tum = int(c.genislik(1) + c.genislik(2) + c.genislik(3))
    assert img.pixelColor(tum - 3, 4) == QColor("#00FF00")                         # sol üst stilinin dolgusu tümünü kaplar
    g.sayfa.sayfa_yapisi = SayfaYapisi(yatay_ortala=True)
    img2, _, _ = _resim(g)
    assert img2.pixelColor(2, 4) == QColor("white") and img2.pixelColor(450, 4) == QColor("#00FF00")


def test_olcek_cizimi_kucultur():
    p = pencere()
    g = p.izgara()
    g.hucre_gir(1, 1, "x")
    _yaz(g.sayfa, Aralik(1, 1, 1, 1), dolgu="#FF0000")
    g.sayfa.sayfa_yapisi = SayfaYapisi(olcek=50)
    img, c, _ = _resim(g)
    assert img.pixelColor(int(c.genislik(1) * 0.5) - 3, 5) == QColor("#FF0000")
    assert img.pixelColor(int(c.genislik(1) * 0.5) + 6, 5) == QColor("white")


# ---------------------------------------------------------------- PDF
def _pdf_sayfalari(yol):
    veri = open(yol, "rb").read()
    assert veri.startswith(b"%PDF")
    return len(re.findall(rb"/Type\s*/Page(?![s\w])", veri)), veri


def _kutular(veri):
    return [tuple(round(float(x)) for x in m) for m in re.findall(
        rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]", veri)]


def test_pdf_yaz_sayfa_sayisi_ve_yon(tmp_path):
    p = pencere()
    g = p.izgara()
    for r in range(1, 160):
        g.hucre_gir(r, 1, f"Satır {r}")
    yol = str(tmp_path / "a.pdf")
    assert yz.pdf_yaz([g], yol)
    n, veri = _pdf_sayfalari(yol)
    assert n == len(yz.SayfaCizici(g.sayfa, g.yazdirma_yuksekligi, g.font()).dilimler()) and n >= 3
    assert _kutular(veri)[0] == (0, 0, 595, 842)                                    # A4 dikey
    g.sayfa.sayfa_yapisi = SayfaYapisi(yon="yatay", kagit="Letter")
    yol2 = str(tmp_path / "b.pdf")
    assert yz.pdf_yaz([g], yol2)
    assert _kutular(open(yol2, "rb").read())[0] == (0, 0, 792, 612)                 # Letter yatay
    assert [x.name for x in tmp_path.iterdir() if x.suffix == ".tmp"] == []


def test_pdf_bos_sayfa_dosya_yazmaz(tmp_path):
    g = pencere().izgara()
    yol = str(tmp_path / "bos.pdf")
    assert not yz.pdf_yaz([g], yol) and not os.path.exists(yol) and list(tmp_path.iterdir()) == []


def test_pdf_tum_sayfalar_farkli_yon(tmp_path):
    p = pencere()
    g1 = p.izgara()
    g1.hucre_gir(1, 1, "a")
    p.sayfa_ekle()
    g2 = p.izgara()
    g2.hucre_gir(1, 1, "b")
    g2.sayfa.sayfa_yapisi = SayfaYapisi(yon="yatay")
    yol = str(tmp_path / "t.pdf")
    assert yz.pdf_yaz([g1, g2], yol)
    n, veri = _pdf_sayfalari(yol)
    assert n == 2
    kutular = _kutular(veri)
    assert (0, 0, 595, 842) in kutular and (0, 0, 842, 595) in kutular


def test_pdf_yazma_hatasi(tmp_path):
    g = pencere().izgara()
    g.hucre_gir(1, 1, "a")
    with pytest.raises(OSError):
        yz.pdf_yaz([g], str(tmp_path / "yok_klasor" / "a.pdf"))


def test_pdf_eski_dosya_bozulmaz(tmp_path):
    g = pencere().izgara()
    g.hucre_gir(1, 1, "a")
    yol = tmp_path / "e.pdf"
    yol.write_bytes(b"ESKI")
    try:
        yz.pdf_yaz([g], str(tmp_path / "yok_klasor" / "e.pdf"))
    except OSError:
        pass
    assert yol.read_bytes() == b"ESKI"


# ---------------------------------------------------------------- menü / pencere
def test_menuden_pdf(tmp_path, monkeypatch):
    p = pencere()
    p.izgara().hucre_gir(1, 1, "merhaba")
    hedef = str(tmp_path / "cikti")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (hedef, ""))
    assert p.pdf_aktar() and os.path.exists(hedef + ".pdf")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: ("", ""))
    assert not p.pdf_aktar()


def test_menuden_bos_sayfa_pdf_uyarir(tmp_path, monkeypatch):
    p = pencere()
    iletiler = []
    monkeypatch.setattr(QMessageBox, "information", lambda w, b, m, *a: iletiler.append(m))
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(tmp_path / "x.pdf"), ""))
    assert not p.pdf_aktar() and iletiler and not (tmp_path / "x.pdf").exists()


def test_sayfa_yapisi_penceresi_ve_geri_al(monkeypatch):
    p = pencere()
    p.izgara().hucre_gir(1, 1, "x")
    p._temiz_damga = p.yigin.damga()                              # kayıt noktası
    d_kayit = {}

    def sahte_exec(self):
        self.yatay.setChecked(True)
        self.kagit.setCurrentText("A3")
        self.sigdir.setChecked(True)
        self.kenarlar["ust"].setValue(3.0)
        self.alan.setText("A1:C10")
        self.baslik.setText("1:2")
        self.kilavuz.setChecked(True)
        self._tamam()
        d_kayit["ok"] = self.sonuc()
        return QDialog.Accepted
    monkeypatch.setattr(SayfaYapisiPenceresi, "exec", sahte_exec)
    assert p.sayfa_yapisi_ac()
    y = p.izgara().sayfa.sayfa_yapisi
    assert (y.yon, y.kagit, y.sigdir_genislik, y.ust) == ("yatay", "A3", True, 3.0)
    assert y.alan == Aralik(1, 1, 10, 3) and y.baslik_satirlari == (1, 2) and y.kilavuz
    assert p.degisti_mi()                                          # kayıt gerektirir (.xlsx'e yazılır)
    p.izgara().geri_al()
    assert p.izgara().sayfa.sayfa_yapisi == SayfaYapisi()


def test_sayfa_yapisi_gecersiz_giris_pencereyi_kapatmaz(monkeypatch):
    uyarilar = []
    monkeypatch.setattr(QMessageBox, "warning", lambda w, b, m, *a: uyarilar.append(m))
    d = SayfaYapisiPenceresi(SayfaYapisi())
    d.baslik.setText("abc")
    d._tamam()
    assert d.sonuc() is None and uyarilar and d.result() == 0
    d.baslik.setText("")
    d.alan.setText("??")
    d._tamam()
    assert d.sonuc() is None and len(uyarilar) == 2


def test_baslik_satirlari_yazim():
    assert baslik_satirlari_coz("1:2") == (1, 2) and baslik_satirlari_coz("$3") == (3, 3)
    assert baslik_satirlari_coz("  ") is None
    assert baslik_satirlari_yaz((1, 2)) == "$1:$2" and baslik_satirlari_yaz(None) == ""
    for k in ("5:2", "0:1", "a:b"):
        with pytest.raises(ValueError):
            baslik_satirlari_coz(k)


def test_otomatik_satir_yuksekligi_yazdirmaya_yansir():
    p = pencere()
    g = p.izgara()
    g.hucre_gir(1, 1, "Uzun bir metin " * 8)
    g.sec((1, 1))
    g.bicim_uygula(StilYama(kaydir=True))
    assert g.yazdirma_yuksekligi(1) > g.sayfa.yukseklik(1)
    g.yakinlastir(2.0)
    assert abs(g.yazdirma_yuksekligi(1) - g.sayfa.yukseklik(1)) > 5 and g.yazdirma_yuksekligi(1) < 600


def test_sigmayan_sayi_diyez_basar():
    p = pencere()
    g = p.izgara()
    g.hucre_gir(1, 1, "123456789012")
    g.sayfa.sutun_genislik[1] = 30
    img1, c, _ = _resim(g)
    koyu = sum(1 for x in range(0, 30) for y in range(0, 20) if img1.pixelColor(x, y).lightness() < 128)
    assert koyu > 10
    # '#' karakterleri dar sütuna sığar: sağdaki komşu sütuna taşan koyu piksel yok
    assert sum(1 for x in range(31, 120) for y in range(0, 20) if img1.pixelColor(x, y).lightness() < 128) == 0
