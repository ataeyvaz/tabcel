"""Faz 4 / 4d: sayfa yapısı + sayfalara bölme (Qt'siz) + .xlsx gidiş-dönüşü."""
import pytest

from tabcel.io import xlsx_io
from tabcel.model.adres import Aralik
from tabcel.model.komutlar import GeriAlYigini, SayfaYapisiDegis
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.sayfa_yapisi import PX_CM, SayfaYapisi
from tabcel.model.sayfalama import sayfala, yazdirma_alani


def _s():
    return CalismaKitabi().sayfalar[0]


def _olcu(s):
    return (lambda c: s.genislik(c)), (lambda r: s.yukseklik(r))


def test_varsayilan_excel_gibi():
    y = SayfaYapisi()
    g, h = y.kagit_px()
    assert (y.yon, y.kagit, y.olcek) == ("dikey", "A4", 100)
    assert abs(g - 21.0 * PX_CM) < 1e-6 and abs(h - 29.7 * PX_CM) < 1e-6
    yg, yh = y.yazdirilabilir_px()
    assert abs(yg - (21.0 - 3.56) * PX_CM) < 1e-6
    yat = y.degistir(yon="yatay")
    assert yat.kagit_px()[0] > yat.kagit_px()[1]


@pytest.mark.parametrize("kw", [{"yon": "x"}, {"kagit": "B9"}, {"olcek": 5}, {"olcek": 500}, {"ust": -1},
                                {"baslik_satirlari": (3, 1)}])
def test_gecersiz_ayar(kw):
    with pytest.raises(ValueError):
        SayfaYapisi(**kw)


def test_bos_sayfa_yazdirilmaz():
    s = _s()
    assert yazdirma_alani(s, SayfaYapisi()) is None
    assert sayfala(s, SayfaYapisi(), *_olcu(s)) == []


def test_kucuk_icerik_tek_sayfa():
    s = _s()
    s.ata(1, 1, Hucre("a"))
    s.ata(3, 2, Hucre("b"))
    p = sayfala(s, SayfaYapisi(), *_olcu(s))
    assert len(p) == 1 and p[0].satirlar == (1, 2, 3) and p[0].sutunlar == (1, 2) and p[0].toplam == 1


def test_gizli_satir_sutun_yazdirilmaz():
    s = _s()
    s.ata(1, 1, Hucre("a"))
    s.ata(4, 4, Hucre("b"))
    s.gizli_satir.add(2)
    s.gizli_sutun.add(3)
    p = sayfala(s, SayfaYapisi(), *_olcu(s))[0]
    assert p.satirlar == (1, 3, 4) and p.sutunlar == (1, 2, 4)


def test_sayfa_numarasi_once_asagi_sonra_saga():
    s = _s()
    for r in (1, 200):
        for c in (1, 40):
            s.ata(r, c, Hucre("x"))
    y = SayfaYapisi()
    p = sayfala(s, y, *_olcu(s))
    satir_say = len({d.satirlar for d in p})
    sutun_say = len({d.sutunlar for d in p})
    assert len(p) == satir_say * sutun_say and satir_say >= 2 and sutun_say >= 2
    assert [d.no for d in p] == list(range(1, len(p) + 1)) and p[0].toplam == len(p)
    # ilk sütun diliminin tüm satır dilimleri önce gelir
    assert p[0].sutunlar == p[1].sutunlar and p[0].satirlar != p[1].satirlar


def test_dilimler_tum_satirlari_tam_bir_kez_kapsar():
    s = _s()
    s.ata(1, 1, Hucre("x"))
    s.ata(500, 1, Hucre("y"))
    p = sayfala(s, SayfaYapisi(), *_olcu(s))
    gorulen = [r for d in p for r in d.satirlar]
    assert gorulen == list(range(1, 501))
    py = SayfaYapisi().yazdirilabilir_px()[1]
    assert all(sum(s.yukseklik(r) for r in d.satirlar) <= py + 1e-6 for d in p)


def test_baslik_satirlari_her_sayfada():
    s = _s()
    s.ata(1, 1, Hucre("Başlık"))
    s.ata(300, 1, Hucre("son"))
    y = SayfaYapisi(baslik_satirlari=(1, 2))
    p = sayfala(s, y, *_olcu(s))
    assert len(p) >= 2 and p[0].satirlar[:2] == (1, 2)
    for d in p[1:]:
        assert d.satirlar[:2] == (1, 2) and d.satirlar[2] > 2
    py = y.yazdirilabilir_px()[1]
    assert all(sum(s.yukseklik(r) for r in d.satirlar) <= py + 1e-6 for d in p)
    # her satır (başlık hariç) yalnız bir kez
    govde = [r for d in p for r in d.satirlar if r > 2]
    assert govde == list(range(3, 301))


def test_baslik_sayfadan_buyukse_yinelenmez():
    s = _s()
    s.ata(1, 1, Hucre("x"))
    s.ata(120, 1, Hucre("y"))
    p = sayfala(s, SayfaYapisi(baslik_satirlari=(1, 100)), *_olcu(s))
    assert all(d.satirlar.count(1) <= 1 for d in p) and len(p) >= 2
    assert p[1].satirlar[0] != 1 or len(p) == 1


def test_sigdir_genislik_ve_olcek():
    s = _s()
    for c in range(1, 31):
        s.ata(1, c, Hucre("x"))
    y = SayfaYapisi()
    assert len({d.sutunlar for d in sayfala(s, y, *_olcu(s))}) > 1
    p = sayfala(s, y.degistir(sigdir_genislik=True), *_olcu(s))
    assert len(p) == 1 and 0.1 <= p[0].olcek < 1.0 and len(p[0].sutunlar) == 30
    p50 = sayfala(s, y.degistir(olcek=50), *_olcu(s))
    assert p50[0].olcek == 0.5 and len(p50[0].sutunlar) > len(sayfala(s, y, *_olcu(s))[0].sutunlar)


def test_yazdirma_alani_ayarli_ve_birlesim():
    s = _s()
    s.ata(1, 1, Hucre("x"))
    s.birlesimleri_yaz([Aralik(1, 1, 3, 4)], [])
    a = yazdirma_alani(s, SayfaYapisi())
    assert (a.son_satir, a.son_sutun) == (3, 4)
    y = SayfaYapisi(alan=Aralik(2, 2, 2, 3))
    p = sayfala(s, y, *_olcu(s))
    assert p[0].satirlar == (2,) and p[0].sutunlar == (2, 3)


def test_dev_hucre_tek_basina_sayfa():
    s = _s()
    s.ata(1, 1, Hucre("x"))
    s.ata(2, 1, Hucre("y"))
    s.satir_yukseklik[1] = 545
    s.satir_yukseklik[2] = 545
    s.sutun_genislik[1] = 1790                                   # sayfa genişliğinden (~650 px) büyük
    p = sayfala(s, SayfaYapisi(), *_olcu(s))
    assert [d.satirlar for d in p] == [(1,), (2,)] and p[0].sutunlar == (1,)   # sığmayan öğe kendi sayfasında


def test_komut_geri_al_ve_xlsx_gidis_donus(tmp_path):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre("a"))
    yigin = GeriAlYigini()
    yeni = SayfaYapisi(yon="yatay", kagit="Letter", ust=2.0, alt=1.5, sol=1.0, sag=1.2, olcek=80,
                       alan=Aralik(1, 1, 20, 5), baslik_satirlari=(1, 2), kilavuz=True, yatay_ortala=True)
    yigin.calistir(SayfaYapisiDegis(s, yeni))
    assert s.sayfa_yapisi == yeni
    yigin.geri_al()
    assert s.sayfa_yapisi == SayfaYapisi()
    yigin.yinele()
    yol = str(tmp_path / "p.xlsx")
    xlsx_io.kaydet(k, yol)
    k2, _ = xlsx_io.ac(yol)
    assert k2.sayfalar[0].sayfa_yapisi == yeni


def test_xlsx_sigdir_genislik_gidis_donus(tmp_path):
    k = CalismaKitabi()
    k.sayfalar[0].ata(1, 1, Hucre("a"))
    k.sayfalar[0].sayfa_yapisi = SayfaYapisi(sigdir_genislik=True)
    yol = str(tmp_path / "q.xlsx")
    xlsx_io.kaydet(k, yol)
    k2, _ = xlsx_io.ac(yol)
    assert k2.sayfalar[0].sayfa_yapisi.sigdir_genislik is True
    # varsayılan yapı da aynen döner
    k.sayfalar[0].sayfa_yapisi = SayfaYapisi()
    xlsx_io.kaydet(k, yol)
    assert xlsx_io.ac(yol)[0].sayfalar[0].sayfa_yapisi == SayfaYapisi()
