"""Faz 3 Opus gözden geçirmesi (test.md §12) bulguları için gerileme testleri."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from tabcel.model.adres import MAX_COL, MAX_ROW, Aralik
from tabcel.model.doldur import seri_plani
from tabcel.model.girdi import akilli_coz, duzenleme_metni, sayi_coz
from tabcel.model.komutlar import bicim_komutu
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.sayi_bicimi import bicimle, sigdir
from tabcel.model.stil import StilYama


def _sayfa():
    return CalismaKitabi().sayfalar[0]


# 1: kesme işaretli metin düzenleyince değişmez
@pytest.mark.parametrize("m", ["12.10.2026", "15%", "1.5", "₺100", "14:30", "1 1/2", "12 Ekim 2026"])
def test_metin_duzenleme_gidis_donus(m):
    h = Hucre(m)
    duz = duzenleme_metni(h)
    assert duz == "'" + m
    sonuc, _ = akilli_coz(duz)
    assert sonuc.deger == m


# 2: yüzde biçimli sayı düzenleyince aynı değere döner
@pytest.mark.parametrize("v", [1e-7, 0.123456789012345, 0.15, 0.0001, 12.5, -0.07, 1e-10])
def test_yuzde_duzenleme_gidis_donus(v):
    metin = duzenleme_metni(Hucre(v), "0.00%")
    assert "E" not in metin and metin.endswith("%")
    sonuc, _ = akilli_coz(metin)
    assert sonuc.deger == v


# 3: doldurma 13+ basamakta
def test_doldur_uzun_sayi_serisi():
    s = _sayfa()
    s.ata(1, 1, Hucre(8690000000001.0))
    s.ata(2, 1, Hucre(8690000000002.0))
    hucreler, _ = seri_plani(s, Aralik(1, 1, 2, 1), Aralik(3, 1, 5, 1))
    assert [hucreler[(r, 1)].deger for r in (3, 4, 5)] == [8690000000003.0, 8690000000004.0, 8690000000005.0]
    s.ata(1, 2, Hucre(1e15))
    s.ata(2, 2, Hucre(1e15 + 1))
    hucreler, _ = seri_plani(s, Aralik(1, 2, 2, 2), Aralik(3, 2, 3, 2))
    assert hucreler[(3, 2)].deger == 1e15 + 2


# 4: çok büyük sayılar çökmez
@pytest.mark.parametrize("v", [1e26, 1e28, 1e100, 1e300, -1.5e308])
@pytest.mark.parametrize("kod", ["0", "0.00", "#,##0.00", "General", '"₺"#,##0.00', "0.00E+00"])
def test_cok_buyuk_sayi_bicimlenir(v, kod):
    assert bicimle(v, kod).metin
    sigdir(v, kod, lambda m: True)


# 5: sonsuz sayı saklanmaz
def test_sonsuz_sayi_metin_kalir():
    assert sayi_coz("1E400") is None
    assert akilli_coz("1E400")[0].deger == "1E400"


# 13: çift işaretli para metin kalır
def test_cift_isaret_para():
    assert akilli_coz("-₺-5")[0].deger == "-₺-5"
    assert akilli_coz("-₺5")[0].deger == -5.0


# 7: tam satır biçimi sütun biçimiyle kesişimi ezmez
def test_tam_satir_sutun_kesisimi():
    s = _sayfa()
    bicim_komutu(s, [Aralik(1, 2, MAX_ROW, 2)], StilYama(dolgu="#FF0000")).yap()
    bicim_komutu(s, [Aralik(3, 1, 3, MAX_COL)], StilYama(kalin=True)).yap()
    st = s.stil(3, 2)
    assert st.dolgu == "#FF0000" and st.kalin
    assert s.stil(4, 2).dolgu == "#FF0000" and not s.stil(4, 2).kalin
    assert s.stil(3, 5).kalin and s.stil(3, 5).dolgu != "#FF0000"


# 8: tüm sayfa seçimi çok sayıda biçimli satırı atlamaz
def test_tum_sayfa_cok_bicimli_satir():
    s = _sayfa()
    for r in range(1, 40):
        bicim_komutu(s, [Aralik(r, 1, r, MAX_COL)], StilYama(kalin=True)).yap()
    bicim_komutu(s, [Aralik(1, 1, MAX_ROW, MAX_COL)], StilYama(dolgu="#00FF00")).yap()
    for r in (1, 5, 39, 40, 1000):
        assert s.stil(r, 3).dolgu == "#00FF00"
    assert s.stil(5, 3).kalin
    bicim_komutu(s, [Aralik(1, 1, MAX_ROW, 20)], StilYama(italik=True)).yap()   # sınır altı: kesişimler yazılır
    assert s.stil(5, 3).italik and s.stil(5, 3).kalin and s.stil(1000, 3).italik
    assert not s.stil(5, 30).italik


# 6: kaydırılmış metin için yerleşim önbelleği sınırlı; otomatik yükseklik layout biriktirmez
def test_kaydirilmis_metin_onbellegi_sinirli():
    from PySide6.QtWidgets import QApplication
    from tabcel.ui.window import Pencere
    QApplication.instance() or QApplication([])
    p = Pencere()
    p.show()
    g = p.izgara()
    g.sec((1, 1), (400, 1))
    g.bicim_uygula(StilYama(kaydir=True))
    for r in range(1, 401):
        g.sayfa.ata(r, 1, Hucre(f"satır {r} " + "uzun metin " * 12))
    for genislik in range(60, 260, 5):                   # sütun genişliği adım adım değişir
        g.sayfa.sutun_genislik[1] = genislik
        g._oto_gecersiz()
        g._oto_hesapla()
    toplam_layout = sum(len(fe.sar) for fe in g._font_onb.values())
    assert toplam_layout <= g._SAR_SINIRI                # 400 × 40 genişlik = 16.000 layout birikmedi
    assert any(v > g.sayfa.yukseklik(1) for v in g._oto.values())
    # çizim yolu hâlâ sarar (görünür hücreler)
    g.viewport().grab()
    assert sum(len(fe.sar) for fe in g._font_onb.values()) <= g._SAR_SINIRI


# 12: Genel + tarih harfi KeyError değil BicimHatasi verir
@pytest.mark.parametrize("kod", ["Genel m", "General m", "Genel a", "General dd"])
def test_genel_ile_tarih_harfi_gecersiz(kod):
    from tabcel.model.sayi_bicimi import BicimHatasi, kanonige
    with pytest.raises(BicimHatasi):
        kanonige(kod)
