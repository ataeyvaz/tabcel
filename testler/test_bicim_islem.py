"""Faz 3 / 3d: biçim araç çubuğu mantığı (Qt'siz) — hangi düğme hangi yamayı üretir."""
import pytest

from tabcel.model import bicim_islem as bi
from tabcel.model.adres import Aralik
from tabcel.model.komutlar import BicimPlani, bicim_komutu
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.stil import Stil, StilYama


def test_boyut_adimlari():
    assert bi.sonraki_boyut(11, +1) == 12.0
    assert bi.sonraki_boyut(11, -1) == 10.0
    assert bi.sonraki_boyut(12, +1) == 14.0           # 13 listede yok
    assert bi.sonraki_boyut(13, -1) == 12.0
    assert bi.sonraki_boyut(72, +1) == 72.0           # uçta yerinde
    assert bi.sonraki_boyut(8, -1) == 8.0
    assert bi.sonraki_boyut(1, +1) == 8.0 and bi.sonraki_boyut(500, -1) == 72.0


def test_boyut_coz():
    assert bi.boyut_coz("12") == 12.0
    assert bi.boyut_coz(" 10,5 ") == 10.5 and bi.boyut_coz("10.5") == 10.5
    assert bi.boyut_coz("") is None and bi.boyut_coz("abc") is None
    assert bi.boyut_coz("0") is None and bi.boyut_coz("410") is None
    assert bi.boyut_coz("409") == 409.0 and bi.boyut_coz("1") == 1.0
    assert bi.etkin_boyut(Stil()) == 11.0 and bi.etkin_boyut(Stil(boyut=14)) == 14.0


@pytest.mark.parametrize("uretici,alan,acik,kapali", [
    (bi.kalin_yamasi, "kalin", True, False),
    (bi.italik_yamasi, "italik", True, False),
    (bi.ustu_cizili_yamasi, "ustu_cizili", True, False),
    (bi.kaydir_yamasi, "kaydir", True, False),
])
def test_acma_kapama_dugmeleri(uretici, alan, acik, kapali):
    assert uretici(Stil()).uygula(Stil()) == Stil().degistir(**{alan: acik})
    acik_stil = Stil().degistir(**{alan: acik})
    assert uretici(acik_stil).uygula(acik_stil) == Stil().degistir(**{alan: kapali})


def test_alti_cizili():
    assert bi.alti_cizili_yamasi(Stil()).uygula(Stil()).alti_cizili == "tek"
    assert bi.alti_cizili_yamasi(Stil(alti_cizili="tek")).uygula(Stil(alti_cizili="tek")).alti_cizili == "yok"
    cift = Stil(alti_cizili="cift")                    # çift çizgi varken düğme kapatır
    assert bi.alti_cizili_yamasi(cift).uygula(cift).alti_cizili == "yok"


def test_yatay_ve_dikey_hiza_tekrar_basinca_geri_doner():
    assert bi.yatay_yamasi(Stil(), "sol").uygula(Stil()).yatay == "sol"
    s = Stil(yatay="sag")
    assert bi.yatay_yamasi(s, "sag").uygula(s).yatay == "genel"
    assert bi.yatay_yamasi(s, "orta").uygula(s).yatay == "orta"
    assert bi.dikey_yamasi(Stil(), "ust").uygula(Stil()).dikey == "ust"
    u = Stil(dikey="ust")
    assert bi.dikey_yamasi(u, "ust").uygula(u).dikey == "alt"
    assert bi.dikey_yamasi(Stil(), "alt").uygula(Stil()).dikey == "alt"      # alt zaten varsayılan


def test_girinti():
    s = Stil()
    y = bi.girinti_yamasi(s, +1)
    assert y.uygula(s).girinti == 1 and y.uygula(s).yatay == "sol"           # genel hiza sola döner
    s2 = Stil(yatay="sag", girinti=2)
    assert bi.girinti_yamasi(s2, +1).uygula(s2) == s2.degistir(girinti=3)    # sağ hiza korunur
    assert bi.girinti_yamasi(Stil(), -1) is None                              # 0'dan azaltma
    assert bi.girinti_yamasi(Stil(girinti=15), +1) is None                    # 15'ten artırma
    s3 = Stil(yatay="sol", girinti=1)
    assert bi.girinti_yamasi(s3, -1).uygula(s3).girinti == 0


def test_sayi_dugmeleri_kodlari():
    assert bi.YUZDE == "0%"
    assert bi.PARA == '"₺"#,##0.00'
    assert bi.BINLIK == "#,##0.00"
    assert bi.sayi_bicimi_yamasi("0%").uygula(Stil()).sayi_bicimi == "0%"


def test_ondalik_artir_azalt():
    s = Stil(sayi_bicimi="0.00")
    assert bi.ondalik_yamasi(s, +1).uygula(s).sayi_bicimi == "0.000"
    assert bi.ondalik_yamasi(s, -1).uygula(s).sayi_bicimi == "0.0"
    s0 = Stil(sayi_bicimi="0")
    assert bi.ondalik_yamasi(s0, -1) is None                                  # zaten 0 basamak
    assert bi.ondalik_yamasi(s0, +1).uygula(s0).sayi_bicimi == "0.0"
    # Genel biçimde görünen ondalıktan başlar
    g = Stil()
    assert bi.ondalik_yamasi(g, +1, 3.25).uygula(g).sayi_bicimi == "0.000"
    assert bi.ondalik_yamasi(g, +1, 3.0).uygula(g).sayi_bicimi == "0.0"


def test_ondalik_bozuk_kod_none():
    assert bi.ondalik_yamasi(Stil(sayi_bicimi="[>x]0"), +1) is None


def test_hazir_adi():
    assert bi.hazir_adi("General") == "Genel"
    assert bi.hazir_adi("0%") == "Özel"
    assert bi.hazir_adi(bi.PARA) == "Para Birimi"


# ------------------------------------------------------------------ kenarlık planı
def _uygula(sayfa, araliklar, secenek):
    BicimPlani(sayfa, bi.kenarlik_plani(araliklar, secenek)).yap()


def _kenar(sayfa, r, c):
    k = sayfa.stil(r, c).kenar
    return {y: (getattr(k, y)[0] if getattr(k, y) else None) for y in ("ust", "alt", "sol", "sag")}


@pytest.fixture
def sayfa():
    return CalismaKitabi().sayfalar[0]


def test_dis_kenarlik_yalniz_cerceve(sayfa):
    _uygula(sayfa, [Aralik(2, 2, 4, 4)], "dis")
    assert _kenar(sayfa, 2, 2) == {"ust": "ince", "alt": None, "sol": "ince", "sag": None}   # sol üst köşe
    assert _kenar(sayfa, 3, 3) == {"ust": None, "alt": None, "sol": None, "sag": None}       # iç hücre
    assert _kenar(sayfa, 4, 4) == {"ust": None, "alt": "ince", "sol": None, "sag": "ince"}   # sağ alt köşe
    assert _kenar(sayfa, 2, 3)["ust"] == "ince" and _kenar(sayfa, 3, 2)["sol"] == "ince"
    assert _kenar(sayfa, 1, 1) == {"ust": None, "alt": None, "sol": None, "sag": None}       # dışarısı etkilenmez


def test_tek_hucrede_dis_kenarlik_dort_kenar(sayfa):
    _uygula(sayfa, [Aralik(3, 3, 3, 3)], "dis")
    assert _kenar(sayfa, 3, 3) == {"ust": "ince", "alt": "ince", "sol": "ince", "sag": "ince"}


def test_kalin_dis(sayfa):
    _uygula(sayfa, [Aralik(1, 1, 2, 2)], "kalin_dis")
    assert _kenar(sayfa, 1, 1)["ust"] == "kalin" and _kenar(sayfa, 2, 2)["alt"] == "kalin"


def test_tum_kenarliklar_ic_cizgiler_dahil(sayfa):
    _uygula(sayfa, [Aralik(1, 1, 2, 2)], "tum")
    for r in (1, 2):
        for c in (1, 2):
            assert _kenar(sayfa, r, c) == {"ust": "ince", "alt": "ince", "sol": "ince", "sag": "ince"}


def test_tek_kenar_secenekleri(sayfa):
    a = [Aralik(2, 2, 3, 3)]
    _uygula(sayfa, a, "alt")
    assert _kenar(sayfa, 3, 2)["alt"] == "ince" and _kenar(sayfa, 3, 3)["alt"] == "ince"
    assert _kenar(sayfa, 2, 2)["alt"] is None
    _uygula(sayfa, a, "ust")
    assert _kenar(sayfa, 2, 3)["ust"] == "ince" and _kenar(sayfa, 3, 3)["ust"] is None
    _uygula(sayfa, a, "sol")
    assert _kenar(sayfa, 3, 2)["sol"] == "ince" and _kenar(sayfa, 3, 3)["sol"] is None
    _uygula(sayfa, a, "sag")
    assert _kenar(sayfa, 2, 3)["sag"] == "ince" and _kenar(sayfa, 2, 2)["sag"] is None
    _uygula(sayfa, a, "cift_alt")
    assert _kenar(sayfa, 3, 2)["alt"] == "cift"


def test_kenarlik_yok_hepsini_kaldirir_diger_stili_korur(sayfa):
    sayfa.bicim_yaz({(2, 2): sayfa.havuz.kimlik(Stil(kalin=True))})
    _uygula(sayfa, [Aralik(2, 2, 2, 2)], "tum")
    _uygula(sayfa, [Aralik(2, 2, 2, 2)], "yok")
    assert sayfa.stil(2, 2).kenar.bos_mu() and sayfa.stil(2, 2).kalin


def test_kenarlik_yok_sinir_hucrelerde_dis_kenarligi_da_siler(sayfa):
    _uygula(sayfa, [Aralik(2, 2, 4, 4)], "dis")
    _uygula(sayfa, [Aralik(2, 2, 4, 4)], "yok")
    assert all(_kenar(sayfa, r, c) == {"ust": None, "alt": None, "sol": None, "sag": None}
               for r in range(2, 5) for c in range(2, 5))


def test_coklu_secimde_her_bolge_kendi_cercevesi(sayfa):
    _uygula(sayfa, [Aralik(1, 1, 1, 1), Aralik(3, 3, 3, 4)], "dis")
    assert _kenar(sayfa, 1, 1) == {"ust": "ince", "alt": "ince", "sol": "ince", "sag": "ince"}
    assert _kenar(sayfa, 3, 3)["sol"] == "ince" and _kenar(sayfa, 3, 3)["sag"] is None
    assert _kenar(sayfa, 3, 4)["sag"] == "ince"


def test_kenarlik_grubu_tek_adimda_geri_alinir(sayfa):
    g = BicimPlani(sayfa, bi.kenarlik_plani([Aralik(2, 2, 4, 4)], "dis"))
    g.yap()
    assert not sayfa.stil(2, 2).kenar.bos_mu()
    g.geri_al()
    assert all(sayfa.stil(r, c).kenar.bos_mu() for r in range(2, 5) for c in range(2, 5))
    assert sayfa.kullanilan_aralik(bicim_dahil=True) is None


def test_gecersiz_secenek():
    with pytest.raises(ValueError):
        bi.kenarlik_plani([Aralik(1, 1, 1, 1)], "mavi")
