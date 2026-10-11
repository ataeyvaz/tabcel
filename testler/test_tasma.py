"""Faz 8e: dinamik dizi taşması (spill) — motor + model (TasmaHucre). Excel 365 davranışı; `=A1:A3` düz aralık taşmaz (bilinçli fark)."""
import pytest

from tabcel.formul.motor import Hesaplayici
from tabcel.model.adres import Aralik
from tabcel.model.deger import TASMA, Hata
from tabcel.model.komutlar import GeriAlYigini, HucrelerDegis
from tabcel.model.sayfa import CalismaKitabi, Hucre, TasmaHucre


def kur(veri=None):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for (r, c), v in (veri or {(1, 1): "c", (1, 2): 3.0, (2, 1): "a", (2, 2): 1.0, (3, 1): "b", (3, 2): 2.0,
                      (4, 1): "a", (4, 2): 5.0}).items():
        s.ata(r, c, Hucre(v))
    m = Hesaplayici(k)
    return k, s, m


def blok(s, r1, c1, r2, c2):
    return [[s.deger(r, c) for c in range(c1, c2 + 1)] for r in range(r1, r2 + 1)]


def test_dizi_sonucu_komsu_hucrelere_tasar():
    _, s, _ = kur()
    s.ata(1, 4, Hucre(formul="=SORT(A1:B4)"))
    assert blok(s, 1, 4, 4, 5) == [["a", 1.0], ["a", 5.0], ["b", 2.0], ["c", 3.0]]
    assert s.tasma[(1, 4)] == Aralik(1, 4, 4, 5)
    assert type(s.hucre(1, 4)) is Hucre and s.hucre(1, 4).formul == "=SORT(A1:B4)"           # sahibi gerçek formül
    assert type(s.hucre(2, 5)) is TasmaHucre and s.hucre(2, 5).sahip == (1, 4)
    assert s.kullanilan_aralik() == (1, 1, 4, 5)


def test_tasan_hucreleri_okuyan_formuller_guncellenir():
    _, s, _ = kur()
    s.ata(1, 4, Hucre(formul="=SORT(A1:B4,2,-1)"))
    s.ata(1, 7, Hucre(formul="=SUM(E1:E4)"))
    s.ata(2, 7, Hucre(formul="=E2*10"))
    s.ata(3, 7, Hucre(formul="=SUM(E1:E8)"))                               # taşmanın büyümesine açık aralık
    assert (s.deger(1, 7), s.deger(2, 7), s.deger(3, 7)) == (11.0, 30.0, 11.0)
    s.ata(2, 2, Hucre(10.0))                                                # kaynak değişti: sıralama ve bağımlılar yenilenir
    assert blok(s, 1, 5, 4, 5) == [[10.0], [5.0], [3.0], [2.0]] and (s.deger(1, 7), s.deger(2, 7)) == (20.0, 50.0)


def test_boyut_degisince_buyur_ve_kuculur():
    _, s, _ = kur()
    s.ata(1, 4, Hucre(formul="=SEQUENCE(B5)"))
    s.ata(1, 7, Hucre(formul="=SUM(D1:D10)"))
    s.ata(5, 2, Hucre(3.0))
    assert blok(s, 1, 4, 4, 4) == [[1.0], [2.0], [3.0], [None]] and s.deger(1, 7) == 6.0
    s.ata(5, 2, Hucre(5.0))                                                 # büyüdü: yeni hücreler dolar, toplam güncellenir
    assert blok(s, 1, 4, 5, 4) == [[1.0], [2.0], [3.0], [4.0], [5.0]] and s.deger(1, 7) == 15.0
    s.ata(5, 2, Hucre(2.0))                                                 # küçüldü: fazlalık silinir
    assert s.deger(3, 4) is None and s.hucre(3, 4) is None and s.deger(1, 7) == 3.0
    assert s.tasma[(1, 4)] == Aralik(1, 4, 2, 4)


def test_dolu_hucre_tasmayi_engeller_bosalinca_tasar():
    _, s, _ = kur()
    s.ata(3, 5, Hucre("engel"))
    s.ata(1, 4, Hucre(formul="=SORT(A1:B4)"))
    assert s.deger(1, 4) == TASMA and s.tasma == {} and s.deger(2, 4) is None and s.deger(3, 5) == "engel"
    s.ata(3, 5, None)                                                       # engel kalktı: taşar
    assert blok(s, 1, 4, 4, 5)[3] == ["c", 3.0] and (1, 4) in s.tasma


def test_taşma_alanina_yazilinca_hata_ve_geri_alinca_duzelir():
    k, s, _ = kur()
    y = GeriAlYigini()
    s.ata(1, 4, Hucre(formul="=SORT(A1:B4)"))
    y.calistir(HucrelerDegis(s, {(2, 5): Hucre("kullanıcı")}))              # kullanıcı taşan hücreye yazdı
    assert s.deger(1, 4) == TASMA and s.deger(2, 5) == "kullanıcı" and s.deger(4, 5) is None
    y.geri_al()                                                             # geri al: eski taşan hücre geri gelir, formül yeniden taşar
    assert s.deger(1, 4) == "a" and blok(s, 1, 4, 4, 5)[1] == ["a", 5.0] and (1, 4) in s.tasma
    y.yinele()
    assert s.deger(1, 4) == TASMA


def test_formul_silinince_ve_sabitle_degisince_tasma_kalkar():
    k, s, _ = kur()
    y = GeriAlYigini()
    s.ata(1, 4, Hucre(formul="=SEQUENCE(3)"))
    s.ata(1, 7, Hucre(formul="=SUM(D1:D3)"))
    assert s.deger(1, 7) == 6.0
    y.calistir(HucrelerDegis(s, {(1, 4): None}))
    assert blok(s, 1, 4, 3, 4) == [[None], [None], [None]] and s.tasma == {} and s.deger(1, 7) == 0.0
    y.geri_al()
    assert blok(s, 1, 4, 3, 4) == [[1.0], [2.0], [3.0]] and s.deger(1, 7) == 6.0
    y.calistir(HucrelerDegis(s, {(1, 4): Hucre(9.0)}))                       # formül sabit değerle değişti
    assert blok(s, 1, 4, 3, 4) == [[9.0], [None], [None]] and s.deger(1, 7) == 9.0


def test_iki_taşma_cakisirsa_ikincisi_hata():
    _, s, _ = kur()
    s.ata(1, 4, Hucre(formul="=SEQUENCE(3)"))
    s.ata(2, 4, Hucre(formul="=SEQUENCE(2)"))                                # D2, D1'in taşma alanında: o dolu hücre → D1 engellenir
    assert s.deger(1, 4) == TASMA and blok(s, 2, 4, 3, 4) == [[1.0], [2.0]]
    s.ata(2, 4, None)
    assert blok(s, 1, 4, 3, 4) == [[1.0], [2.0], [3.0]]


def test_sayfa_siniri_ve_birlesik_hucre_engeller():
    _, s, _ = kur()
    s.ata(1_048_575, 1, Hucre(formul="=SEQUENCE(5)"))
    assert s.deger(1_048_575, 1) == TASMA
    s.birlesim_yukle([Aralik(3, 8, 3, 9)])
    s.ata(1, 8, Hucre(formul="=SEQUENCE(4)"))
    assert s.deger(1, 8) == TASMA                                            # birleşik hücre taşmayı engeller


def test_tek_hucreli_dizi_ve_duz_aralik_tasmaz():
    _, s, _ = kur()
    s.ata(1, 4, Hucre(formul="=SEQUENCE(1)"))
    assert s.deger(1, 4) == 1.0 and s.tasma == {}
    s.ata(1, 5, Hucre(formul="=B1:B4"))                                      # örtük kesişim: 1. satır → B1
    assert s.deger(1, 5) == 3.0 and s.tasma == {}
    s.ata(2, 5, Hucre(formul="=B1:B4*2"))                                    # hesaplanmış dizi taşar
    assert blok(s, 2, 5, 5, 5) == [[6.0], [2.0], [4.0], [10.0]]


def test_hata_sonucu_ve_bos_oge():
    _, s, _ = kur({(1, 1): 1.0, (3, 1): 3.0})
    s.ata(1, 4, Hucre(formul="=A1:A3*1"))
    assert blok(s, 1, 4, 3, 4) == [[1.0], [0.0], [3.0]]                      # boş öğe 0
    s.ata(1, 6, Hucre(formul="=FILTER(A1:A3,A1:A3>9)"))
    assert s.deger(1, 6) == Hata("#CALC!") and (1, 6) not in s.tasma
    s.ata(1, 7, Hucre(formul="=SORT(1/0)"))
    assert s.deger(1, 7) == Hata("#DIV/0!")


def test_satir_ekle_sil_taşmayi_yeniden_kurar():
    from tabcel.model.komutlar import SatirEkleSil
    k, s, _ = kur()
    y = GeriAlYigini()
    s.ata(1, 4, Hucre(formul="=SEQUENCE(3)"))
    y.calistir(SatirEkleSil(s, 2, 1, True))                                   # taşmanın içine satır ekle
    assert blok(s, 1, 4, 4, 4) == [[1.0], [2.0], [3.0], [None]] and s.tasma[(1, 4)] == Aralik(1, 4, 3, 4)
    y.geri_al()
    assert blok(s, 1, 4, 3, 4) == [[1.0], [2.0], [3.0]]


def test_baska_sayfadan_okuma_ve_zincir():
    k, s, _ = kur()
    s2 = k.sayfa_ekle("Ikinci")
    s2.ata(1, 1, Hucre(formul="=SUM(Sayfa1!D1:D10)"))
    s.ata(1, 4, Hucre(formul="=SEQUENCE(3)"))
    assert s2.deger(1, 1) == 6.0
    s.ata(1, 4, Hucre(formul="=SEQUENCE(4)"))
    assert s2.deger(1, 1) == 10.0
    s.ata(1, 7, Hucre(formul="=SORT(D1:D4,1,-1)"))                            # taşmanın taşmayı okuması
    assert blok(s, 1, 7, 4, 7) == [[4.0], [3.0], [2.0], [1.0]]
    s.ata(1, 4, Hucre(formul="=SEQUENCE(2)"))
    assert blok(s, 1, 7, 4, 7) == [[2.0], [1.0], [0.0], [0.0]]                  # boş öğeler sonda, taşarken 0


def test_degisken_islev_her_hesapta_yeniler():
    _, s, _ = kur()
    s.ata(1, 4, Hucre(formul="=RANDARRAY(3,1,1,1000000,TRUE)"))
    ilk = blok(s, 1, 4, 3, 4)
    s.ata(5, 5, Hucre(1.0))                                                  # herhangi bir değişiklik değişken hücreleri yeniler
    assert blok(s, 1, 4, 3, 4) != ilk and (1, 4) in s.tasma


def test_kopya_sabit_olarak_okunur_ama_girdi_degil():
    """Taşan hücreler kopyalanırken/okunurken sabit değer gibi görünür; `Hucre` ile eşit değildir."""
    _, s, _ = kur()
    s.ata(1, 4, Hucre(formul="=SEQUENCE(3)"))
    t = s.hucre(2, 4)
    assert t.deger == 2.0 and t.formul is None and t != Hucre(2.0) and Hucre(2.0) != t
    s.ata(2, 4, Hucre(2.0))                                                  # kullanıcı AYNI değeri yazsa da engel olur
    assert s.deger(1, 4) == TASMA
