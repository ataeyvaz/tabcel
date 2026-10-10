"""Faz 6 / 6b: grafik verisi çözümleme + seri tahmini (Qt'siz; kural 11: normal / boş / hata / metin-sayı)."""
import time

import pytest

from tabcel.formul.motor import Hesaplayici
from tabcel.model.adres import Aralik
from tabcel.model.grafik import Grafik, Referans, Seri
from tabcel.model.grafik_verisi import EtiketDizisi, grafik_verisi, hucre_listesi, seriler_tahmin
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.stil import Stil


@pytest.fixture
def kitap():
    k = CalismaKitabi()
    Hesaplayici(k)
    return k


@pytest.fixture
def sayfa(kitap):
    return kitap.sayfalar[0]


def doldur(sayfa, satirlar, r0=1, c0=1):
    for i, satir in enumerate(satirlar):
        for j, v in enumerate(satir):
            if v is None:
                continue
            sayfa.ata(r0 + i, c0 + j, Hucre(None, v) if isinstance(v, str) and v.startswith("=") else Hucre(v))


def biçim(sayfa, anahtar, kod):
    sayfa.bicim_yaz(hucreler={anahtar: sayfa.havuz.kimlik(Stil(sayi_bicimi=kod))})


def ref(sayfa, r1, c1, r2, c2):
    return Referans(sayfa.kimlik, Aralik(r1, c1, r2, c2))


def g(sayfa, *seriler, **kw):
    return Grafik(seriler=tuple(seriler), **kw)


# ------------------------------------------------------------------ hücre listesi
def test_hucre_listesi_yonu_ve_kirpma(sayfa):
    doldur(sayfa, [[1.0, 2.0], [3.0, 4.0]])
    assert hucre_listesi(sayfa, Aralik(1, 1, 1, 2)) == [(1, 1), (1, 2)]            # tek satır: soldan sağa
    assert hucre_listesi(sayfa, Aralik(1, 2, 2, 2)) == [(1, 2), (2, 2)]            # tek sütun: yukarıdan aşağı
    assert hucre_listesi(sayfa, Aralik(1, 1, 2, 2)) == [(1, 1), (1, 2), (2, 1), (2, 2)]
    assert hucre_listesi(sayfa, Aralik(1, 1, 1048576, 1)) == [(1, 1), (2, 1)]      # tam sütun kullanılan alana kırpılır
    assert hucre_listesi(sayfa, Aralik(10, 10, 20, 20)) == []


def test_hucre_listesi_gizli_satir_ve_sutun(sayfa):
    doldur(sayfa, [[1.0, 2.0, 3.0]] * 4)
    sayfa.gizli_satir.add(2)
    sayfa.gizli_sutun.add(2)
    assert hucre_listesi(sayfa, Aralik(1, 1, 4, 3)) == [(1, 1), (1, 3), (3, 1), (3, 3), (4, 1), (4, 3)]
    assert len(hucre_listesi(sayfa, Aralik(1, 1, 4, 3), gizliyi_atla=False)) == 12


def test_bos_sayfa_hucre_listesi(sayfa):
    assert hucre_listesi(sayfa, Aralik(1, 1, 5, 5)) == []


# ------------------------------------------------------------------ grafik_verisi: değerler
def test_normal_deger_ve_kategori(kitap, sayfa):
    doldur(sayfa, [["Ay", "Adet"], ["Ocak", 10.0], ["Şubat", 20.0], ["Mart", 30.0]])
    v = grafik_verisi(kitap, g(sayfa, Seri(ad_ref=ref(sayfa, 1, 2, 1, 2), deger=ref(sayfa, 2, 2, 4, 2),
                                           kategori=ref(sayfa, 2, 1, 4, 1))))
    s = v.seriler[0]
    assert s.ad == "Adet" and s.degerler == (10.0, 20.0, 30.0)
    assert list(s.kategoriler) == ["Ocak", "Şubat", "Mart"] and s.x is None and not v.bos


def test_bos_hucre_none_metin_mantiksal_sifir_hata_none(kitap, sayfa):
    doldur(sayfa, [[1.0], [None], ["abc"], [True], ["=1/0"], [5.0]])
    v = grafik_verisi(kitap, g(sayfa, Seri(deger=ref(sayfa, 1, 1, 6, 1))))
    assert v.seriler[0].degerler == (1.0, None, 0.0, 0.0, None, 5.0)     # boş/hata → boşluk; metin/mantıksal → 0


def test_tamamen_bos_ve_hatali_veri_bos(kitap, sayfa):
    doldur(sayfa, [[None], ["=1/0"]])
    v = grafik_verisi(kitap, g(sayfa, Seri(deger=ref(sayfa, 1, 1, 2, 1))))
    assert v.bos
    assert grafik_verisi(kitap, g(sayfa)).bos                              # serisiz grafik


def test_formul_sonucu_okunur_ve_canli(kitap, sayfa):
    doldur(sayfa, [[1.0], [2.0], ["=A1+A2"]])
    gr = g(sayfa, Seri(deger=ref(sayfa, 1, 1, 3, 1)))
    assert grafik_verisi(kitap, gr).seriler[0].degerler == (1.0, 2.0, 3.0)
    sayfa.ata(1, 1, Hucre(10.0))
    assert grafik_verisi(kitap, gr).seriler[0].degerler == (10.0, 2.0, 12.0)


def test_gizli_satir_cizilmez_filtre_dahil(kitap, sayfa):
    doldur(sayfa, [["a", 1.0], ["b", 2.0], ["c", 3.0]])
    sayfa.gizli_satir.add(2)                                             # elle ya da filtreyle gizlenen
    v = grafik_verisi(kitap, g(sayfa, Seri(deger=ref(sayfa, 1, 2, 3, 2), kategori=ref(sayfa, 1, 1, 3, 1))))
    assert v.seriler[0].degerler == (1.0, 3.0) and list(v.seriler[0].kategoriler) == ["a", "c"]


def test_satirdaki_seri_gizli_sutun(kitap, sayfa):
    doldur(sayfa, [[1.0, 2.0, 3.0]])
    sayfa.gizli_sutun.add(2)
    assert grafik_verisi(kitap, g(sayfa, Seri(deger=ref(sayfa, 1, 1, 1, 3)))).seriler[0].degerler == (1.0, 3.0)


def test_seri_adi_kurallari(kitap, sayfa):
    doldur(sayfa, [["Başlık", 1.0]])
    assert grafik_verisi(kitap, g(sayfa, Seri(ad_ref=ref(sayfa, 1, 1, 1, 1), deger=ref(sayfa, 1, 2, 1, 2)))
                         ).seriler[0].ad == "Başlık"
    assert grafik_verisi(kitap, g(sayfa, Seri(ad="Sabit", deger=ref(sayfa, 1, 2, 1, 2)))).seriler[0].ad == "Sabit"
    # ad hücresi boşsa sabit ad, o da yoksa Seri{n}
    assert grafik_verisi(kitap, g(sayfa, Seri(ad="S", ad_ref=ref(sayfa, 5, 5, 5, 5), deger=ref(sayfa, 1, 2, 1, 2))
                                  )).seriler[0].ad == "S"
    v = grafik_verisi(kitap, g(sayfa, Seri(deger=ref(sayfa, 1, 2, 1, 2)), Seri(deger=ref(sayfa, 1, 2, 1, 2))))
    assert [s.ad for s in v.seriler] == ["Seri1", "Seri2"]


def test_silinmis_sayfa_veya_degersiz_seri_atlanir(kitap, sayfa):
    doldur(sayfa, [[1.0]])
    v = grafik_verisi(kitap, g(sayfa, Seri(ad="x"), Seri(deger=Referans(999, Aralik(1, 1, 1, 1))),
                               Seri(deger=ref(sayfa, 1, 1, 1, 1))))
    assert len(v.seriler) == 1 and v.seriler[0].ad == "Seri3"            # numara serinin grafikteki sırası


def test_baska_sayfadan_veri(kitap, sayfa):
    s2 = kitap.sayfa_ekle()
    doldur(s2, [[7.0], [8.0]])
    assert grafik_verisi(kitap, g(sayfa, Seri(deger=ref(s2, 1, 1, 2, 1)))).seriler[0].degerler == (7.0, 8.0)


# ------------------------------------------------------------------ etiketler, sayı biçimi
def test_kategori_etiketi_sayi_bicimiyle(kitap, sayfa):
    doldur(sayfa, [[0.5, 1.0], [0.25, 2.0]])
    biçim(sayfa, (1, 1), "0%")
    v = grafik_verisi(kitap, g(sayfa, Seri(deger=ref(sayfa, 1, 2, 2, 2), kategori=ref(sayfa, 1, 1, 2, 1))))
    assert list(v.seriler[0].kategoriler) == ["50%", "0,25"]            # biçimli / Genel (yerel gösterim)


def test_kategori_kisa_ise_sira_numarasi(kitap, sayfa):
    doldur(sayfa, [["a", 1.0], [None, 2.0], [None, 3.0]])
    v = grafik_verisi(kitap, g(sayfa, Seri(deger=ref(sayfa, 1, 2, 3, 2), kategori=ref(sayfa, 1, 1, 1, 1))))
    assert list(v.seriler[0].kategoriler) == ["a", "2", "3"]


def test_kategorisiz_seri_sira_numarasi(kitap, sayfa):
    doldur(sayfa, [[1.0], [2.0]])
    assert list(grafik_verisi(kitap, g(sayfa, Seri(deger=ref(sayfa, 1, 1, 2, 1)))).seriler[0].kategoriler) == ["1", "2"]


def test_etiketler_tembel(kitap, sayfa):
    doldur(sayfa, [["a", 1.0]])
    cagri = []
    d = EtiketDizisi(lambda i: cagri.append(i) or f"e{i}", 5)
    assert len(d) == 5 and cagri == []
    assert d[2] == "e2" and d[2] == "e2" and cagri == [2]               # önbellek
    assert d[-1] == "e4" and d[1:3] == ["e1", "e2"]
    with pytest.raises(IndexError):
        d[9]
    assert d == ["e0", "e1", "e2", "e3", "e4"]


def test_sayi_bicimi_ilk_bicimli_hucreden(kitap, sayfa):
    doldur(sayfa, [[1.0], [2.0]])
    assert grafik_verisi(kitap, g(sayfa, Seri(deger=ref(sayfa, 1, 1, 2, 1)))).sayi_bicimi == "General"
    biçim(sayfa, (2, 1), "0.00")
    assert grafik_verisi(kitap, g(sayfa, Seri(deger=ref(sayfa, 1, 1, 2, 1)))).sayi_bicimi == "0.00"


# ------------------------------------------------------------------ dağılım X değerleri
def test_dagilim_x_sayilari(kitap, sayfa):
    doldur(sayfa, [[1.5, 10.0], [2.5, 20.0], ["x", 30.0]])
    v = grafik_verisi(kitap, g(sayfa, Seri(deger=ref(sayfa, 1, 2, 3, 2), kategori=ref(sayfa, 1, 1, 3, 1)),
                               tur="dagilim"))
    assert v.seriler[0].x == (1.5, 2.5, None)                            # sayısal olmayan X → nokta çizilmez


def test_dagilim_x_yoksa_ya_da_hic_sayi_degilse_siralama(kitap, sayfa):
    doldur(sayfa, [["a", 10.0], ["b", 20.0]])
    v = grafik_verisi(kitap, g(sayfa, Seri(deger=ref(sayfa, 1, 2, 2, 2), kategori=ref(sayfa, 1, 1, 2, 1)),
                               tur="dagilim"))
    assert v.seriler[0].x == (1.0, 2.0)
    v = grafik_verisi(kitap, g(sayfa, Seri(deger=ref(sayfa, 1, 2, 2, 2)), tur="dagilim"))
    assert v.seriler[0].x == (1.0, 2.0)


# ------------------------------------------------------------------ performans
def test_100000_nokta_hizli(kitap, sayfa):
    sayfa.toplu_yaz({(r, 1): Hucre(float(r)) for r in range(1, 100001)})
    gr = g(sayfa, Seri(deger=ref(sayfa, 1, 1, 100000, 1), kategori=ref(sayfa, 1, 1, 100000, 1)))
    t = time.perf_counter()
    v = grafik_verisi(kitap, gr)
    gecen = time.perf_counter() - t
    assert len(v.seriler[0].degerler) == 100000 and v.seriler[0].kategoriler[99999] == "100000"
    assert gecen < 1.0, f"{gecen:.2f} sn"                               # hedef ≪ 1 sn; makine yükü için gevşek


# ------------------------------------------------------------------ seri tahmini
def tahmin(sayfa, aralik, tur="sutun", satirda=None):
    return seriler_tahmin(sayfa, aralik, tur, satirda)


def araliklar(seriler):
    return [(s.deger.aralik, s.kategori.aralik if s.kategori else None, s.ad_ref.aralik if s.ad_ref else None)
            for s in seriler]


def test_tahmin_baslikli_kategorili(sayfa):
    doldur(sayfa, [["Ay", "Satış", "Gider"], ["Ocak", 10.0, 4.0], ["Şubat", 20.0, 5.0], ["Mart", 30.0, 6.0]])
    seriler, satirda = tahmin(sayfa, Aralik(1, 1, 4, 3))
    assert not satirda
    assert araliklar(seriler) == [
        (Aralik(2, 2, 4, 2), Aralik(2, 1, 4, 1), Aralik(1, 2, 1, 2)),
        (Aralik(2, 3, 4, 3), Aralik(2, 1, 4, 1), Aralik(1, 3, 1, 3))]


def test_tahmin_basliksiz_kategorili(sayfa):
    doldur(sayfa, [["Ocak", 10.0], ["Şubat", 20.0]])
    seriler, _ = tahmin(sayfa, Aralik(1, 1, 2, 2))
    assert araliklar(seriler) == [(Aralik(1, 2, 2, 2), Aralik(1, 1, 2, 1), None)]


def test_tahmin_sol_ust_bos(sayfa):
    doldur(sayfa, [[None, "A", "B"], ["x", 1.0, 2.0], ["y", 3.0, 4.0]])
    seriler, _ = tahmin(sayfa, Aralik(1, 1, 3, 3))
    assert araliklar(seriler)[0] == (Aralik(2, 2, 3, 2), Aralik(2, 1, 3, 1), Aralik(1, 2, 1, 2))
    assert len(seriler) == 2


def test_tahmin_tek_sutun_sayi_seri_tek(sayfa):
    doldur(sayfa, [[1.0], [2.0], [3.0]])
    seriler, satirda = tahmin(sayfa, Aralik(1, 1, 3, 1))
    assert araliklar(seriler) == [(Aralik(1, 1, 3, 1), None, None)] and not satirda


def test_tahmin_tek_sutun_baslikli(sayfa):
    doldur(sayfa, [["Adet"], [1.0], [2.0]])
    seriler, _ = tahmin(sayfa, Aralik(1, 1, 3, 1))
    assert araliklar(seriler) == [(Aralik(2, 1, 3, 1), None, Aralik(1, 1, 1, 1))]


def test_tahmin_yillar_seri_olur_excel_gibi(sayfa):
    doldur(sayfa, [["Yıl", "Gelir"], [2020.0, 5.0], [2021.0, 6.0]])
    seriler, _ = tahmin(sayfa, Aralik(1, 1, 3, 2))
    assert len(seriler) == 2                                             # Excel de yılları seri sayar


def test_tahmin_satirda_seri_az_satir_cok_sutun(sayfa):
    doldur(sayfa, [["", "Oca", "Şub", "Mar", "Nis"], ["Satış", 1.0, 2.0, 3.0, 4.0], ["Gider", 2.0, 2.0, 2.0, 2.0]])
    seriler, satirda = tahmin(sayfa, Aralik(1, 1, 3, 5))
    assert satirda
    assert araliklar(seriler) == [
        (Aralik(2, 2, 2, 5), Aralik(1, 2, 1, 5), Aralik(2, 1, 2, 1)),
        (Aralik(3, 2, 3, 5), Aralik(1, 2, 1, 5), Aralik(3, 1, 3, 1))]


def test_tahmin_yon_zorlama_satir_sutun_degistir(sayfa):
    doldur(sayfa, [["Ay", "A", "B"], ["x", 1.0, 2.0], ["y", 3.0, 4.0], ["z", 5.0, 6.0]])
    a, s1 = tahmin(sayfa, Aralik(1, 1, 4, 3))
    b, s2 = tahmin(sayfa, Aralik(1, 1, 4, 3), satirda=True)
    assert not s1 and s2 and len(a) == 2
    assert all(s.deger.aralik.ilk_satir == s.deger.aralik.son_satir for s in b)     # satırda seri


def test_tahmin_tek_hucre_bitisik_bolge(sayfa):
    doldur(sayfa, [["Ay", "Adet"], ["Ocak", 10.0], ["Şubat", 20.0]])
    seriler, _ = tahmin(sayfa, Aralik(2, 2, 2, 2))
    assert araliklar(seriler) == [(Aralik(2, 2, 3, 2), Aralik(2, 1, 3, 1), Aralik(1, 2, 1, 2))]


def test_tahmin_tam_sutun_secimi_kullanilan_alana_kirpilir(sayfa):
    doldur(sayfa, [["Ay", "Adet"], ["Ocak", 10.0], ["Şubat", 20.0]])
    seriler, _ = tahmin(sayfa, Aralik(1, 1, 1048576, 2))
    assert seriler[0].deger.aralik == Aralik(2, 2, 3, 2)


def test_tahmin_metin_sutunu_seri_degil(sayfa):
    doldur(sayfa, [["Ad", "Not", "Adet"], ["a", "x", 1.0], ["b", "y", 2.0]])
    seriler, _ = tahmin(sayfa, Aralik(1, 1, 3, 3))
    assert [s.deger.aralik for s in seriler] == [Aralik(2, 3, 3, 3)]    # "Not" sütunu sayısal değil: atlanır


def test_tahmin_tarih_sutunu_kategori(sayfa):
    doldur(sayfa, [["Tarih", "Satış"], [46000.0, 5.0], [46001.0, 6.0]])
    biçim(sayfa, (2, 1), "dd.mm.yyyy")
    biçim(sayfa, (3, 1), "dd.mm.yyyy")
    seriler, _ = tahmin(sayfa, Aralik(1, 1, 3, 2))
    assert len(seriler) == 1 and seriler[0].kategori.aralik == Aralik(2, 1, 3, 1)


def test_tahmin_dagilim_ilk_sutun_x(sayfa):
    doldur(sayfa, [["X", "Y"], [1.0, 10.0], [2.0, 20.0]])
    seriler, _ = tahmin(sayfa, Aralik(1, 1, 3, 2), tur="dagilim")
    assert araliklar(seriler) == [(Aralik(2, 2, 3, 2), Aralik(2, 1, 3, 1), Aralik(1, 2, 1, 2))]
    seriler, _ = tahmin(sayfa, Aralik(1, 1, 3, 2), tur="sutun")          # sütun grafiğinde X sütunu da seri
    assert len(seriler) == 2


def test_tahmin_pasta_yalniz_ilk_seri(sayfa):
    doldur(sayfa, [["Ay", "A", "B"], ["x", 1.0, 2.0], ["y", 3.0, 4.0]])
    assert len(tahmin(sayfa, Aralik(1, 1, 3, 3), tur="pasta")[0]) == 1
    assert len(tahmin(sayfa, Aralik(1, 1, 3, 3), tur="halka")[0]) == 1


def test_tahmin_sayisal_veri_yoksa_hata(sayfa):
    doldur(sayfa, [["a", "b"], ["c", "d"]])
    with pytest.raises(ValueError, match="sayısal veri yok"):
        tahmin(sayfa, Aralik(1, 1, 2, 2))
    with pytest.raises(ValueError):
        tahmin(sayfa, Aralik(5, 5, 6, 6))                                # boş alan


def test_tahmin_bos_sayfa_hata(sayfa):
    with pytest.raises(ValueError):
        tahmin(sayfa, Aralik(1, 1, 3, 3))


def test_tahmin_sonucu_grafik_verisine_cevrilir(kitap, sayfa):
    doldur(sayfa, [["Ay", "Satış"], ["Ocak", 10.0], ["Şubat", 20.0]])
    seriler, _ = tahmin(sayfa, Aralik(1, 1, 3, 2))
    v = grafik_verisi(kitap, Grafik(seriler=tuple(seriler)))
    assert v.seriler[0].ad == "Satış" and v.seriler[0].degerler == (10.0, 20.0)
    assert list(v.seriler[0].kategoriler) == ["Ocak", "Şubat"]
