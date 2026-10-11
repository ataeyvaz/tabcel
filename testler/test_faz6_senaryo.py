"""Faz 6 / 6j: gerçek iş senaryosu — aylık gelir-gider çizelgesi.
Grafik ekle → veri değişince güncellenir → satır ekle (başvuru kayar) → geri al → kaydet/aç → PDF."""
import io
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PIL import Image
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from tabcel.formul.motor import Hesaplayici
from tabcel.io import xlsx_io
from tabcel.model.adres import Aralik
from tabcel.model.grafik import Grafik, Konum, Referans, Resim, Seri
from tabcel.model.grafik_verisi import grafik_verisi
from tabcel.model.komutlar import GeriAlYigini, SatirEkleSil
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui import yazdir as yz
from tabcel.ui.window import Pencere

AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
GELIR = [42000, 42000, 45000, 45000, 46000, 46000, 47000, 47000, 48000, 48000, 50000, 52000]
GIDER = [31000, 29500, 33000, 30250, 31800, 32000, 35000, 36100, 30900, 31200, 33500, 41000]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for c, b in enumerate(["Ay", "Gelir", "Gider", "Net"], start=1):
        s.ata(1, c, Hucre(b))
    for i, ay in enumerate(AYLAR):
        r = i + 2
        s.ata(r, 1, Hucre(ay))
        s.ata(r, 2, Hucre(float(GELIR[i])))
        s.ata(r, 3, Hucre(float(GIDER[i])))
        s.ata(r, 4, Hucre(formul=f"=B{r}-C{r}"))
    p = Pencere(k)
    p.resize(1100, 800)
    p.show()
    QApplication.processEvents()
    yield p
    p.degisti_mi = lambda: False                                    # kapanışta "kaydedilsin mi?" sormasın
    p.close()


def _grafikler(s):
    kim = s.kimlik
    sutun = Grafik(tur="sutun", baslik="Gelir ve gider",
                   seriler=(Seri(ad_ref=Referans(kim, Aralik(1, 2, 1, 2)), deger=Referans(kim, Aralik(2, 2, 13, 2)),
                                 kategori=Referans(kim, Aralik(2, 1, 13, 1))),
                            Seri(ad_ref=Referans(kim, Aralik(1, 3, 1, 3)), deger=Referans(kim, Aralik(2, 3, 13, 3)),
                                 kategori=Referans(kim, Aralik(2, 1, 13, 1)))),
                   konum=Konum(16, 1), boyut=(480, 280))
    cizgi = Grafik(tur="cizgi", baslik="Net",
                   seriler=(Seri(ad_ref=Referans(kim, Aralik(1, 4, 1, 4)), deger=Referans(kim, Aralik(2, 4, 13, 4)),
                                 kategori=Referans(kim, Aralik(2, 1, 13, 1))),),
                   konum=Konum(2, 6), boyut=(420, 260))
    return sutun, cizgi


def _net(g, grafik):
    return list(grafik_verisi(g.sayfa.kitap, grafik).seriler[0].degerler)


def test_gelir_gider_senaryosu(pencere, tmp_path):
    g = pencere.izgara()
    s = g.sayfa
    b = io.BytesIO()
    Image.new("RGB", (120, 60), (33, 115, 70)).save(b, "PNG")
    n1 = s.nesne_ekle(_grafikler(s)[0])
    n2 = s.nesne_ekle(_grafikler(s)[1])
    s.nesne_ekle(Resim(veri=b.getvalue(), ad="logo", konum=Konum(2, 12), boyut=(120, 60)))
    QApplication.processEvents()

    # 1) ilk veri doğru
    v = grafik_verisi(s.kitap, n1)
    assert [x.ad for x in v.seriler] == ["Gelir", "Gider"]
    assert list(v.seriler[0].degerler) == [float(x) for x in GELIR]
    assert _net(g, n2) == [float(a - b_) for a, b_ in zip(GELIR, GIDER)]

    # 2) hücre değişince grafik verisi (ve çizim) güncellenir
    g.nesne_dikdortgeni(n2.kimlik)
    g.hucre_gir(2, 2, "50000")
    QTest.qWait(80)
    assert _net(g, n2)[0] == 50000.0 - 31000.0
    assert not g._nesne_kirli                                       # erteleme bitti, önbellek yenilendi

    # 3) satır ekle: seri başvuruları kayar, grafikler çökmeden aynı veriyi gösterir
    once = _net(g, n2)
    y = GeriAlYigini()
    y.calistir(SatirEkleSil(s, 5, 1, True))                         # 5. satırın üstüne boş satır
    QTest.qWait(80)
    yeni = s.nesne(n2.kimlik)
    assert yeni.seriler[0].deger.aralik == Aralik(2, 4, 14, 4)
    assert s.nesne(n1.kimlik).seriler[1].deger.aralik == Aralik(2, 3, 14, 3)
    assert s.nesne(n1.kimlik).konum.satir == 17                     # çapa da aşağı kaydı (A16 → A17)
    sonra = _net(g, yeni)
    assert len(sonra) == 13 and sonra[:3] == once[:3] and sonra[4:] == once[3:]
    assert sonra[3] is None or sonra[3] != sonra[3] or sonra[3] == 0.0       # eklenen boş satır

    # 4) geri al her şeyi eski haline getirir
    y.geri_al()
    QTest.qWait(80)
    assert s.nesne(n2.kimlik).seriler[0].deger.aralik == Aralik(2, 4, 13, 4)
    assert s.nesne(n1.kimlik).konum.satir == 16
    assert _net(g, s.nesne(n2.kimlik)) == once

    # 5) kaydet → aç: kararlı, uyarısız, değerler aynı
    yol = str(tmp_path / "gelir_gider.xlsx")
    xlsx_io.kaydet(s.kitap, yol)
    k2, rapor = xlsx_io.ac(yol)
    Hesaplayici(k2).tumunu_hesapla()                                # pencerede motoru Pencere kurar
    s2 = k2.sayfalar[0]
    assert len(s2.nesneler) == 3 and not rapor.veri_kaybi
    gr = [n for n in s2.nesneler if isinstance(n, Grafik)]
    assert [x.tur for x in gr] == ["sutun", "cizgi"] and gr[1].baslik == "Net"
    assert list(grafik_verisi(k2, gr[1]).seriler[0].degerler) == once
    assert any(isinstance(n, Resim) and n.veri for n in s2.nesneler)

    # 6) PDF: grafikler ve resim dahil, dilimler sayfa yapısıyla uyumlu
    pdf = str(tmp_path / "gelir_gider.pdf")
    assert yz.pdf_yaz([g], pdf) is True
    assert open(pdf, "rb").read(4) == b"%PDF" and os.path.getsize(pdf) > 3000
    c = yz.SayfaCizici(s, g.yazdirma_yuksekligi, g.font())
    kapsam = {r for d in c.dilimler() for r in d.satirlar}
    assert 16 + 10 <= max(kapsam)                                   # 16. satırdaki 280 px'lik grafik alanın içinde
