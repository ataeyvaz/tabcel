"""Faz 3 / 3h: doldurma planı (Qt'siz) — seri türleri × 4 vaka, yön, biçim, Ctrl+D/R, çift tık."""
import pytest

from tabcel.model.adres import Aralik
from tabcel.model.doldur import (
    asagi_yukari_dolu_plani, bitisik_son_satir, kopya_plani, seri_plani,
)
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.stil import Stil
from tabcel.model.tarihseri import ymd_seri


def A(r1, c1, r2, c2):
    return Aralik(r1, c1, r2, c2)


@pytest.fixture
def sayfa():
    return CalismaKitabi().sayfalar[0]


def koy(s, sutun, degerler, ilk=1):
    for i, v in enumerate(degerler):
        if v is None:
            continue
        if isinstance(v, str) and v.startswith("="):
            s.ata(ilk + i, sutun, Hucre(None, v))
        else:
            s.ata(ilk + i, sutun, Hucre(float(v) if isinstance(v, int) and not isinstance(v, bool) else v))


def dikey(s, kaynak, n, sutun=1, seri=True):
    """Kaynak A(r1,sutun,r2,sutun)'in altına n hücre doldur; değerleri liste olarak verir."""
    hedef = A(kaynak.son_satir + 1, kaynak.ilk_sutun, kaynak.son_satir + n, kaynak.son_sutun)
    h, _ = (seri_plani if seri else kopya_plani)(s, kaynak, hedef)
    return [(h[(r, sutun)].deger if h[(r, sutun)] is not None and h[(r, sutun)].formul is None
             else (h[(r, sutun)].formul if h[(r, sutun)] is not None else None))
            for r in range(hedef.ilk_satir, hedef.son_satir + 1)]


def yukari(s, kaynak, n, sutun=1):
    hedef = A(kaynak.ilk_satir - n, kaynak.ilk_sutun, kaynak.ilk_satir - 1, kaynak.son_sutun)
    h, _ = seri_plani(s, kaynak, hedef)
    return [h[(r, sutun)].deger for r in range(hedef.ilk_satir, hedef.son_satir + 1)]


# ------------------------------------------------------------------ sayı
def test_tek_sayi_kopyalanir(sayfa):
    koy(sayfa, 1, [5])
    assert dikey(sayfa, A(1, 1, 1, 1), 3) == [5.0, 5.0, 5.0]


def test_iki_sayi_sabit_adim(sayfa):
    koy(sayfa, 1, [1, 3])
    assert dikey(sayfa, A(1, 1, 2, 1), 3) == [5.0, 7.0, 9.0]
    koy(sayfa, 2, [10, 7])
    assert dikey(sayfa, A(1, 2, 2, 2), 2, sutun=2) == [4.0, 1.0]


def test_uc_sayi_dogrusal_egilim(sayfa):
    koy(sayfa, 1, [1, 2, 3])
    assert dikey(sayfa, A(1, 1, 3, 1), 2) == [4.0, 5.0]
    koy(sayfa, 2, [2, 4, 7])                                # düzgün olmayan: en küçük kareler
    sonuc = dikey(sayfa, A(1, 2, 3, 2), 1, sutun=2)
    assert sonuc[0] == pytest.approx(9.3333333333, rel=1e-9)


def test_sayi_serisi_geri(sayfa):
    koy(sayfa, 1, [1, 2, 3], ilk=5)
    assert yukari(sayfa, A(5, 1, 7, 1), 3) == [-2.0, -1.0, 0.0]      # yukarı doğru azalır
    koy(sayfa, 2, [5], ilk=5)
    assert yukari(sayfa, A(5, 2, 5, 2), 2, sutun=2) == [5.0, 5.0]     # tek değer: kopya


def test_ondalik_adim_artik_birakmaz(sayfa):
    koy(sayfa, 1, [0.1, 0.2])
    assert dikey(sayfa, A(1, 1, 2, 1), 3) == [0.3, 0.4, 0.5]


# ------------------------------------------------------------------ tarih
def stil_koy(s, adres_listesi, kod):
    k = s.havuz.kimlik(Stil(sayi_bicimi=kod))
    s.bicim_yaz({a: k for a in adres_listesi})


def test_tek_tarih_gun_artar(sayfa):
    d = float(ymd_seri(2026, 10, 12))
    koy(sayfa, 1, [d])
    stil_koy(sayfa, [(1, 1)], "d.mm.yyyy")
    assert dikey(sayfa, A(1, 1, 1, 1), 2) == [d + 1, d + 2]


def test_iki_tarih_gun_adimi(sayfa):
    d = float(ymd_seri(2026, 1, 1))
    koy(sayfa, 1, [d, d + 7])
    stil_koy(sayfa, [(1, 1), (2, 1)], "d.mm.yyyy")
    assert dikey(sayfa, A(1, 1, 2, 1), 2) == [d + 14, d + 21]


def test_aylik_tarih_serisi_ayni_gun(sayfa):
    koy(sayfa, 1, [float(ymd_seri(2026, 1, 31)), float(ymd_seri(2026, 2, 28))])
    stil_koy(sayfa, [(1, 1), (2, 1)], "d.mm.yyyy")
    # gün aynı değil (31/28): gün adımı olarak devam eder (28 gün)
    assert dikey(sayfa, A(1, 1, 2, 1), 1) == [float(ymd_seri(2026, 2, 28)) + 28]
    koy(sayfa, 2, [float(ymd_seri(2026, 1, 15)), float(ymd_seri(2026, 2, 15))])
    stil_koy(sayfa, [(1, 2), (2, 2)], "d.mm.yyyy")
    assert dikey(sayfa, A(1, 2, 2, 2), 2, sutun=2) == [float(ymd_seri(2026, 3, 15)), float(ymd_seri(2026, 4, 15))]


def test_yillik_ve_ay_sonu_kisaltma(sayfa):
    koy(sayfa, 1, [float(ymd_seri(2025, 1, 31)), float(ymd_seri(2025, 3, 31))])
    stil_koy(sayfa, [(1, 1), (2, 1)], "d.mm.yyyy")
    assert dikey(sayfa, A(1, 1, 2, 1), 2) == [float(ymd_seri(2025, 5, 31)), float(ymd_seri(2025, 7, 31))]
    koy(sayfa, 2, [float(ymd_seri(2025, 1, 31)), float(ymd_seri(2025, 2, 28))])
    koy(sayfa, 3, [float(ymd_seri(2026, 3, 10)), float(ymd_seri(2027, 3, 10))])
    stil_koy(sayfa, [(1, 3), (2, 3)], "d.mm.yyyy")
    assert dikey(sayfa, A(1, 3, 2, 3), 1, sutun=3) == [float(ymd_seri(2028, 3, 10))]


def test_tarih_biçimsiz_sayi_gun_degil_sayi(sayfa):
    koy(sayfa, 1, [46307.0])                                # biçim Genel: tek sayı kopya
    assert dikey(sayfa, A(1, 1, 1, 1), 2) == [46307.0, 46307.0]


def test_tarih_geri(sayfa):
    d = float(ymd_seri(2026, 10, 12))
    koy(sayfa, 1, [d], ilk=5)
    stil_koy(sayfa, [(5, 1)], "d.mm.yyyy")
    assert yukari(sayfa, A(5, 1, 5, 1), 2) == [d - 2, d - 1]


# ------------------------------------------------------------------ ay / gün adları
def test_ay_adlari(sayfa):
    koy(sayfa, 1, ["Ocak"])
    assert dikey(sayfa, A(1, 1, 1, 1), 3) == ["Şubat", "Mart", "Nisan"]
    koy(sayfa, 2, ["Kasım"])
    assert dikey(sayfa, A(1, 2, 1, 2), 3, sutun=2) == ["Aralık", "Ocak", "Şubat"]        # döngüsel
    koy(sayfa, 3, ["Oca", "Mar"])
    assert dikey(sayfa, A(1, 3, 2, 3), 2, sutun=3) == ["May", "Tem"]                      # adım 2
    koy(sayfa, 4, ["Pazartesi"])
    assert dikey(sayfa, A(1, 4, 1, 4), 2, sutun=4) == ["Salı", "Çarşamba"]


def test_ad_buyuk_kucuk_harf_korunur(sayfa):
    koy(sayfa, 1, ["OCAK"])
    assert dikey(sayfa, A(1, 1, 1, 1), 2) == ["ŞUBAT", "MART"]
    koy(sayfa, 2, ["ocak"])
    assert dikey(sayfa, A(1, 2, 1, 2), 1, sutun=2) == ["şubat"]
    koy(sayfa, 3, ["Pzt"])
    assert dikey(sayfa, A(1, 3, 1, 3), 2, sutun=3) == ["Sal", "Çar"]
    koy(sayfa, 4, ["pazar"])
    assert dikey(sayfa, A(1, 4, 1, 4), 1, sutun=4) == ["pazartesi"]


def test_ad_geri_ve_duzensiz(sayfa):
    koy(sayfa, 1, ["Mart"], ilk=3)
    assert yukari(sayfa, A(3, 1, 3, 1), 2) == ["Ocak", "Şubat"]
    koy(sayfa, 2, ["Ocak", "Mart", "Nisan"])                 # düzensiz adım: desen yinelenir
    assert dikey(sayfa, A(1, 2, 3, 2), 4, sutun=2) == ["Ocak", "Mart", "Nisan", "Ocak"]
    koy(sayfa, 3, ["Ocak", "Foo"])
    assert dikey(sayfa, A(1, 3, 2, 3), 2, sutun=3) == ["Ocak", "Foo"]


# ------------------------------------------------------------------ metin + sayı
def test_metin_sayi(sayfa):
    koy(sayfa, 1, ["Ürün 1"])
    assert dikey(sayfa, A(1, 1, 1, 1), 3) == ["Ürün 2", "Ürün 3", "Ürün 4"]          # tek değer bile artar
    koy(sayfa, 2, ["1. Çeyrek"])
    assert dikey(sayfa, A(1, 2, 1, 2), 2, sutun=2) == ["2. Çeyrek", "3. Çeyrek"]
    koy(sayfa, 3, ["A01"])
    assert dikey(sayfa, A(1, 3, 1, 3), 2, sutun=3) == ["A02", "A03"]                  # basamak korunur
    koy(sayfa, 4, ["x9"])
    assert dikey(sayfa, A(1, 4, 1, 4), 2, sutun=4) == ["x10", "x11"]


def test_metin_sayi_adim_ve_geri(sayfa):
    koy(sayfa, 1, ["No 10", "No 20"])
    assert dikey(sayfa, A(1, 1, 2, 1), 2) == ["No 30", "No 40"]
    koy(sayfa, 2, ["Ürün 5"], ilk=4)
    assert yukari(sayfa, A(4, 2, 4, 2), 2, sutun=2) == ["Ürün 3", "Ürün 4"]
    koy(sayfa, 3, ["Ürün 1", "Ürün 2", "Foo 3"])             # farklı önek: desen yinelenir
    assert dikey(sayfa, A(1, 3, 3, 3), 3, sutun=3) == ["Ürün 1", "Ürün 2", "Foo 3"]
    koy(sayfa, 4, ["a1"], ilk=1)
    assert dikey(sayfa, A(1, 4, 1, 4), 1, sutun=4) == ["a2"]


# ------------------------------------------------------------------ formül ve diğerleri
def test_formul_kayar(sayfa):
    koy(sayfa, 1, [1, 2])
    koy(sayfa, 2, ["=A1*2"])
    assert dikey(sayfa, A(1, 2, 1, 2), 2, sutun=2) == ["=A2*2", "=A3*2"]
    koy(sayfa, 3, ["=$A$1+A1"], ilk=1)
    assert dikey(sayfa, A(1, 3, 1, 3), 1, sutun=3) == ["=$A$1+A2"]


def test_formul_geri_ve_yatay(sayfa):
    sayfa.ata(5, 2, Hucre(None, "=A5+1"))
    hedef = A(3, 2, 4, 2)
    h, _ = seri_plani(sayfa, A(5, 2, 5, 2), hedef)
    assert h[(4, 2)].formul == "=A4+1" and h[(3, 2)].formul == "=A3+1"
    sayfa.ata(1, 1, Hucre(1.0))
    sayfa.ata(1, 2, Hucre(2.0))
    sayfa.ata(2, 1, Hucre(None, "=A1+B1"))
    h, _ = seri_plani(sayfa, A(2, 1, 2, 1), A(2, 2, 2, 3))
    assert h[(2, 2)].formul == "=B1+C1" and h[(2, 3)].formul == "=C1+D1"


def test_metin_mantiksal_desen_yinelenir(sayfa):
    koy(sayfa, 1, ["abc", True])
    assert dikey(sayfa, A(1, 1, 2, 1), 3) == ["abc", True, "abc"]
    koy(sayfa, 2, [1, "x", 3])                               # karışık: desen
    assert dikey(sayfa, A(1, 2, 3, 2), 4, sutun=2) == [1.0, "x", 3.0, 1.0]


def test_bos_hucre_hedefi_bosaltir(sayfa):
    koy(sayfa, 1, [None, 5], ilk=1)
    sayfa.ata(3, 1, Hucre("eski"))
    sayfa.ata(4, 1, Hucre("eski2"))
    h, _ = seri_plani(sayfa, A(1, 1, 1, 1), A(2, 1, 4, 1))   # kaynak boş hücre
    assert h[(2, 1)] is None and h[(4, 1)] is None


def test_bicim_desen_olarak_kopyalanir(sayfa):
    koy(sayfa, 1, [1, 2])
    k = sayfa.havuz.kimlik(Stil(kalin=True))
    sayfa.bicim_yaz({(1, 1): k})
    _, st = seri_plani(sayfa, A(1, 1, 2, 1), A(3, 1, 6, 1))
    assert [st[(r, 1)] for r in range(3, 7)] == [k, 0, k, 0]


def test_coklu_serit_ayri_seri(sayfa):
    koy(sayfa, 1, [1, 2])
    koy(sayfa, 2, [10, 20])
    koy(sayfa, 3, ["Ocak", "Şubat"])
    h, _ = seri_plani(sayfa, A(1, 1, 2, 3), A(3, 1, 4, 3))
    assert [h[(3, c)].deger for c in (1, 2, 3)] == [3.0, 30.0, "Mart"]
    assert [h[(4, c)].deger for c in (1, 2, 3)] == [4.0, 40.0, "Nisan"]


def test_yatay_doldurma(sayfa):
    sayfa.ata(1, 1, Hucre(1.0))
    sayfa.ata(1, 2, Hucre(2.0))
    sayfa.ata(2, 1, Hucre("Ürün 1"))
    sayfa.ata(2, 2, Hucre("Ürün 2"))
    h, _ = seri_plani(sayfa, A(1, 1, 2, 2), A(1, 3, 2, 5))
    assert [h[(1, c)].deger for c in (3, 4, 5)] == [3.0, 4.0, 5.0]
    assert [h[(2, c)].deger for c in (3, 4, 5)] == ["Ürün 3", "Ürün 4", "Ürün 5"]
    h, _ = seri_plani(sayfa, A(1, 2, 1, 2), A(1, 1, 1, 1))
    assert h[(1, 1)].deger == 2.0                            # tek sayı geriye kopya


def test_gecersiz_hedef(sayfa):
    with pytest.raises(ValueError):
        seri_plani(sayfa, A(1, 1, 2, 2), A(5, 1, 6, 2))      # bitişik değil
    with pytest.raises(ValueError):
        seri_plani(sayfa, A(1, 1, 2, 2), A(3, 1, 4, 3))      # genişlik farklı
    with pytest.raises(ValueError):
        seri_plani(sayfa, A(1, 1, 2, 2), A(2, 1, 3, 2))      # çakışık


# ------------------------------------------------------------------ Ctrl+D / Ctrl+R
def test_ctrl_d_ilk_satir_kopyalanir(sayfa):
    koy(sayfa, 1, [1, 2, 3])
    koy(sayfa, 2, ["=A1*2"])
    h, st = asagi_yukari_dolu_plani(sayfa, A(1, 1, 3, 2), True)
    assert h[(2, 1)].deger == 1.0 and h[(3, 1)].deger == 1.0           # seri değil kopya
    assert h[(2, 2)].formul == "=A2*2" and h[(3, 2)].formul == "=A3*2"
    assert (1, 1) not in h


def test_ctrl_d_tek_hucre_ustten(sayfa):
    koy(sayfa, 1, [7])
    h, _ = asagi_yukari_dolu_plani(sayfa, A(2, 1, 2, 1), True)
    assert h[(2, 1)].deger == 7.0
    assert asagi_yukari_dolu_plani(sayfa, A(1, 1, 1, 1), True) is None   # üstte satır yok


def test_ctrl_r(sayfa):
    sayfa.ata(1, 1, Hucre(4.0))
    sayfa.ata(1, 2, Hucre(9.0))
    sayfa.ata(2, 1, Hucre(None, "=A1*2"))
    h, _ = asagi_yukari_dolu_plani(sayfa, A(1, 1, 2, 3), False)
    assert h[(1, 2)].deger == 4.0 and h[(1, 3)].deger == 4.0
    assert h[(2, 2)].formul == "=B1*2" and h[(2, 3)].formul == "=C1*2"
    h, _ = asagi_yukari_dolu_plani(sayfa, A(1, 2, 2, 2), False)           # tek sütun: soldan
    assert h[(1, 2)].deger == 4.0 and h[(2, 2)].formul == "=B1*2"
    assert asagi_yukari_dolu_plani(sayfa, A(1, 1, 2, 1), False) is None


def test_ctrl_d_bicim_gelir(sayfa):
    k = sayfa.havuz.kimlik(Stil(italik=True))
    sayfa.bicim_yaz({(1, 1): k})
    _, st = asagi_yukari_dolu_plani(sayfa, A(1, 1, 3, 1), True)
    assert st[(2, 1)] == k and st[(3, 1)] == k


# ------------------------------------------------------------------ çift tık
def test_bitisik_son_satir(sayfa):
    koy(sayfa, 1, [1])
    koy(sayfa, 2, ["a", "b", "c", "d"], ilk=1)
    koy(sayfa, 2, ["z"], ilk=6)                              # boşluktan sonrası sayılmaz
    assert bitisik_son_satir(sayfa, A(1, 1, 1, 1)) == 4
    assert bitisik_son_satir(sayfa, A(1, 2, 1, 2)) is None   # solda ve sağda veri yok
    koy(sayfa, 7, ["x", "y"], ilk=1)
    assert bitisik_son_satir(sayfa, A(1, 6, 1, 6)) == 2      # sol (5) boş, sağ (7) dolu
    assert bitisik_son_satir(sayfa, A(1, 3, 1, 3)) == 4      # sol (2) dolu: solu tercih eder
    assert bitisik_son_satir(sayfa, A(4, 1, 4, 1)) is None   # son satır zaten sonda
