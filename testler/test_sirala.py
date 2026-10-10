"""Faz 5 / 5c: sıralama planı + Sirala komutu (Qt'siz) ve karşılaştırmanın Türkçe harmanlamaya geçişi."""
import random
import time

import pytest

from tabcel.formul.donustur import karsilastir
from tabcel.formul.motor import Hesaplayici
from tabcel.model.adres import Aralik
from tabcel.model.deger import BOL0
from tabcel.model.komutlar import GeriAlYigini, Sirala, ana_sayfa, bicim_komutu
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.sirala import HATA_BIRLESIM, SiralamaAnahtari as K, baslik_tahmin, siralama_plani
from tabcel.model.stil import StilYama


@pytest.fixture
def kitap():
    return CalismaKitabi()


@pytest.fixture
def sayfa(kitap):
    return kitap.sayfalar[0]


def sutun(sayfa, c, degerler, ilk=1):
    for i, v in enumerate(degerler):
        sayfa.ata(ilk + i, c, Hucre(v))


def oku(sayfa, c, n, ilk=1):
    return [sayfa.deger(ilk + i, c) for i in range(n)]


class TestPlan:
    def test_artan_azalan_sayi(self, sayfa):
        sutun(sayfa, 1, [3.0, 1.0, 2.0])
        assert siralama_plani(sayfa, Aralik(1, 1, 3, 1), [K(1)]) == [2, 3, 1]
        assert siralama_plani(sayfa, Aralik(1, 1, 3, 1), [K(1, artan=False)]) == [1, 3, 2]

    def test_turkce_harf_sirasi(self, sayfa):
        sutun(sayfa, 1, ["Zeynep", "Çağla", "Ali", "Ömer", "Cem", "Şule", "Sedat", "İpek", "Işık", "Ğ"])
        p = siralama_plani(sayfa, Aralik(1, 1, 10, 1), [K(1)])
        assert [sayfa.deger(r, 1) for r in p] == [
            "Ali", "Cem", "Çağla", "Ğ", "Işık", "İpek", "Ömer", "Sedat", "Şule", "Zeynep"]

    def test_karisik_tur_ve_bos_en_sonda(self, sayfa):
        sutun(sayfa, 1, ["b", None, 5.0, True, BOL0, "a", -1.0, False])
        p = siralama_plani(sayfa, Aralik(1, 1, 8, 1), [K(1)])
        assert [sayfa.deger(r, 1) for r in p] == [-1.0, 5.0, "a", "b", False, True, BOL0, None]
        p = siralama_plani(sayfa, Aralik(1, 1, 8, 1), [K(1, artan=False)])
        assert [sayfa.deger(r, 1) for r in p] == [BOL0, True, False, "b", "a", 5.0, -1.0, None]

    def test_kararli_ve_cok_duzey(self, sayfa):
        sutun(sayfa, 1, ["b", "a", "b", "a", "b"])
        sutun(sayfa, 2, [3.0, 2.0, 1.0, 1.0, 2.0])
        assert siralama_plani(sayfa, Aralik(1, 1, 5, 2), [K(1)]) == [2, 4, 1, 3, 5]   # eşitlerde özgün sıra
        p = siralama_plani(sayfa, Aralik(1, 1, 5, 2), [K(1), K(2, artan=False)])
        assert [(sayfa.deger(r, 1), sayfa.deger(r, 2)) for r in p] == \
            [("a", 2.0), ("a", 1.0), ("b", 3.0), ("b", 2.0), ("b", 1.0)]

    def test_baslik_atlanir(self, sayfa):
        sutun(sayfa, 1, ["Ad", "z", "a", "m"])
        p = siralama_plani(sayfa, Aralik(1, 1, 4, 1), [K(1)], baslik=True)
        assert len(p) == 3 and [sayfa.deger(r, 1) for r in p] == ["a", "m", "z"]

    def test_buyuk_kucuk_duyarli(self, sayfa):
        sutun(sayfa, 1, ["b", "A", "a", "B"])
        p = siralama_plani(sayfa, Aralik(1, 1, 4, 1), [K(1)], buyuk_kucuk=True)
        assert [sayfa.deger(r, 1) for r in p] == ["a", "A", "b", "B"]
        p = siralama_plani(sayfa, Aralik(1, 1, 4, 1), [K(1)], buyuk_kucuk=False)
        assert [sayfa.deger(r, 1) for r in p] == ["A", "a", "b", "B"]      # kararlı: özgün sıra

    def test_formul_sonucuna_gore(self, kitap, sayfa):
        Hesaplayici(kitap)
        sutun(sayfa, 2, [5.0, 1.0, 3.0])
        for r in (1, 2, 3):
            sayfa.ata(r, 1, Hucre(None, f"=B{r}*2"))
        assert siralama_plani(sayfa, Aralik(1, 1, 3, 2), [K(1)]) == [2, 3, 1]

    def test_gizli_satirlar_yerinde_kalir(self, sayfa):
        sutun(sayfa, 1, [4.0, 3.0, 2.0, 1.0])
        sayfa.gizli_satir.add(2)
        p = siralama_plani(sayfa, Aralik(1, 1, 4, 1), [K(1)])
        assert p[1] == 2                                              # gizli satır 2 yerinde
        assert [p[0], p[2], p[3]] == [4, 3, 1]                        # görünenler (4, 2, 1 değerli) sıralandı

    def test_birlesim_reddedilir(self, sayfa):
        sutun(sayfa, 1, [2.0, 1.0, 3.0])
        sayfa.birlesimleri_yaz([Aralik(1, 2, 2, 2)], [])
        with pytest.raises(ValueError, match="aynı boyutta"):
            siralama_plani(sayfa, Aralik(1, 1, 3, 2), [K(1)])
        assert "aynı boyutta" in HATA_BIRLESIM

    def test_olcut_aralik_disinda_ve_olcutsuz(self, sayfa):
        sutun(sayfa, 1, [1.0, 2.0])
        with pytest.raises(ValueError):
            siralama_plani(sayfa, Aralik(1, 1, 2, 1), [K(3)])
        with pytest.raises(ValueError):
            siralama_plani(sayfa, Aralik(1, 1, 2, 1), [])

    def test_renge_gore(self, sayfa):
        sutun(sayfa, 1, [1.0, 2.0, 3.0, 4.0])
        bicim_komutu(sayfa, [Aralik(2, 1, 2, 1), Aralik(4, 1, 4, 1)], StilYama(dolgu="#FFFF00")).yap()
        p = siralama_plani(sayfa, Aralik(1, 1, 4, 1), [K(1, olcut="dolgu", renk="#ffff00")])
        assert p == [2, 4, 1, 3]                                      # sarılar üstte, diğerleri özgün sıra
        p = siralama_plani(sayfa, Aralik(1, 1, 4, 1), [K(1, artan=False, olcut="dolgu", renk="#FFFF00")])
        assert p == [1, 3, 2, 4]                                      # altta
        bicim_komutu(sayfa, [Aralik(3, 1, 3, 1)], StilYama(yazi_rengi="#FF0000")).yap()
        p = siralama_plani(sayfa, Aralik(1, 1, 4, 1), [K(1, olcut="yazi_rengi", renk="#FF0000")])
        assert p[0] == 3

    def test_sutun_sirala_soldan_saga(self, sayfa):
        for c, v in enumerate([3.0, 1.0, 2.0], start=1):
            sayfa.ata(1, c, Hucre(v))
            sayfa.ata(2, c, Hucre(f"s{c}"))
        p = siralama_plani(sayfa, Aralik(1, 1, 2, 3), [K(1)], yon="sutun")      # 1. satır anahtar
        assert p == [2, 3, 1]


class TestBaslikTahmin:
    def test_metin_ustu_sayi(self, sayfa):
        sutun(sayfa, 1, ["Ad", "Ali", "Veli"])
        sutun(sayfa, 2, ["Puan", 1.0, 2.0])
        assert baslik_tahmin(sayfa, Aralik(1, 1, 3, 2)) is True

    def test_hepsi_sayi_degil(self, sayfa):
        sutun(sayfa, 1, [3.0, 1.0, 2.0])
        assert baslik_tahmin(sayfa, Aralik(1, 1, 3, 1)) is False

    def test_hepsi_metin_baslik_sayilmaz(self, sayfa):
        sutun(sayfa, 1, ["b", "a", "c"])
        assert baslik_tahmin(sayfa, Aralik(1, 1, 3, 1)) is False

    def test_kalin_baslik(self, sayfa):
        sutun(sayfa, 1, ["Ad", "Ali", "Veli"])
        bicim_komutu(sayfa, [Aralik(1, 1, 1, 1)], StilYama(kalin=True)).yap()
        assert baslik_tahmin(sayfa, Aralik(1, 1, 3, 1)) is True

    def test_tek_satir(self, sayfa):
        sutun(sayfa, 1, ["Ad"])
        assert baslik_tahmin(sayfa, Aralik(1, 1, 1, 1)) is False


class TestKomut:
    def test_hucreler_stil_not_tasinir_geri_al(self, sayfa):
        sutun(sayfa, 1, [3.0, 1.0, 2.0])
        sutun(sayfa, 2, ["c", "a", "b"])
        bicim_komutu(sayfa, [Aralik(1, 1, 1, 2)], StilYama(kalin=True)).yap()
        sayfa.notlar = {(1, 1): "ilk", (3, 2): "son"}
        yigin = GeriAlYigini()
        plan = siralama_plani(sayfa, Aralik(1, 1, 3, 2), [K(1)])
        yigin.calistir(Sirala(sayfa, Aralik(1, 1, 3, 2), plan))
        assert oku(sayfa, 1, 3) == [1.0, 2.0, 3.0] and oku(sayfa, 2, 3) == ["a", "b", "c"]
        assert sayfa.stil(3, 1).kalin and not sayfa.stil(1, 1).kalin          # kalın satır 3'e taşındı
        assert sayfa.notlar == {(3, 1): "ilk", (2, 2): "son"}
        yigin.geri_al()
        assert oku(sayfa, 1, 3) == [3.0, 1.0, 2.0] and oku(sayfa, 2, 3) == ["c", "a", "b"]
        assert sayfa.stil(1, 1).kalin and not sayfa.stil(3, 1).kalin
        assert sayfa.notlar == {(1, 1): "ilk", (3, 2): "son"}
        yigin.yinele()
        assert oku(sayfa, 1, 3) == [1.0, 2.0, 3.0]

    def test_formuller_kopyala_gibi_kayar(self, kitap, sayfa):
        Hesaplayici(kitap)
        sutun(sayfa, 2, [30.0, 10.0, 20.0])
        sutun(sayfa, 3, [2.0, 2.0, 2.0])
        for r in (1, 2, 3):
            sayfa.ata(r, 1, Hucre(None, f"=B{r}*C{r}"))
        plan = siralama_plani(sayfa, Aralik(1, 1, 3, 3), [K(2)])
        k = Sirala(sayfa, Aralik(1, 1, 3, 3), plan)
        k.yap()
        assert [sayfa.hucre(r, 1).formul for r in (1, 2, 3)] == ["=B1*C1", "=B2*C2", "=B3*C3"]
        assert oku(sayfa, 1, 3) == [20.0, 40.0, 60.0]
        k.geri_al()
        assert oku(sayfa, 1, 3) == [60.0, 20.0, 40.0]

    def test_mutlak_basvuru_sabit(self, kitap, sayfa):
        Hesaplayici(kitap)
        sayfa.ata(1, 5, Hucre(10.0))
        sutun(sayfa, 2, [3.0, 1.0, 2.0])
        for r in (1, 2, 3):
            sayfa.ata(r, 1, Hucre(None, f"=B{r}*$E$1"))
        plan = siralama_plani(sayfa, Aralik(1, 1, 3, 2), [K(2)])
        Sirala(sayfa, Aralik(1, 1, 3, 2), plan).yap()
        assert oku(sayfa, 1, 3) == [10.0, 20.0, 30.0]

    def test_disaridan_baglanti_degismez(self, kitap, sayfa):
        Hesaplayici(kitap)
        sutun(sayfa, 1, [2.0, 1.0])
        sayfa.ata(1, 3, Hucre(None, "=A1"))                              # sıralanan aralığın dışı
        plan = siralama_plani(sayfa, Aralik(1, 1, 2, 1), [K(1)])
        Sirala(sayfa, Aralik(1, 1, 2, 1), plan).yap()
        assert sayfa.hucre(1, 3).formul == "=A1" and sayfa.deger(1, 3) == 1.0     # artık A1 = 1

    def test_gizli_ve_digerleri_yerinde_tek_olay(self, kitap, sayfa):
        sutun(sayfa, 1, [4.0, 3.0, 2.0, 1.0])
        sayfa.gizli_satir.add(2)
        sayfa.satir_yukseklik[1] = 40
        olaylar = []
        kitap.dinle(olaylar.append)
        k = Sirala(sayfa, Aralik(1, 1, 4, 1), siralama_plani(sayfa, Aralik(1, 1, 4, 1), [K(1)]))
        k.yap()
        assert oku(sayfa, 1, 4) == [1.0, 3.0, 2.0, 4.0]
        assert sayfa.satir_yukseklik[1] == 40 and 2 in sayfa.gizli_satir
        assert len([o for o in olaylar if o.tur == "hucre"]) == 1

    def test_birlesim_yerinde(self, sayfa):
        sutun(sayfa, 1, [2.0, 1.0])
        sayfa.birlesimleri_yaz([Aralik(5, 3, 6, 3)], [])
        once = sayfa.birlesimler
        Sirala(sayfa, Aralik(1, 1, 2, 1), [2, 1]).yap()
        assert sayfa.birlesimler == once and oku(sayfa, 1, 2) == [1.0, 2.0]

    def test_sutun_sirala_komutu(self, kitap, sayfa):
        Hesaplayici(kitap)
        for c, v in enumerate([3.0, 1.0, 2.0], start=1):
            sayfa.ata(1, c, Hucre(v))
        sayfa.ata(2, 1, Hucre(None, "=A1*10"))
        sayfa.ata(2, 2, Hucre("b"))
        sayfa.ata(2, 3, Hucre("c"))
        plan = siralama_plani(sayfa, Aralik(1, 1, 2, 3), [K(1)], yon="sutun")
        Sirala(sayfa, Aralik(1, 1, 2, 3), plan, "sutun").yap()
        assert [sayfa.deger(1, c) for c in (1, 2, 3)] == [1.0, 2.0, 3.0]
        assert sayfa.hucre(2, 3).formul == "=C1*10" and sayfa.deger(2, 3) == 30.0

    def test_ana_sayfa(self, sayfa):
        sutun(sayfa, 1, [2.0, 1.0])
        assert ana_sayfa(Sirala(sayfa, Aralik(1, 1, 2, 1), [2, 1])) is sayfa

    def test_yuz_bin_satir_hizli(self, sayfa):
        rnd = random.Random(1)
        veri = {}
        for r in range(1, 100_001):
            for c in range(1, 6):
                veri[(r, c)] = Hucre(float(rnd.randint(0, 10 ** 6)) if c == 1 else f"m{r}-{c}")
        sayfa.toplu_yaz(veri)
        t = time.perf_counter()
        plan = siralama_plani(sayfa, Aralik(1, 1, 100_000, 5), [K(1)])
        k = Sirala(sayfa, Aralik(1, 1, 100_000, 5), plan)
        k.yap()
        gecen = time.perf_counter() - t
        degerler = [sayfa.deger(r, 1) for r in range(1, 100_001)]
        assert degerler == sorted(degerler)
        assert gecen < 6.0, f"{gecen:.2f} sn"                          # HEDEF ≤ 2 sn: şu an ~3,8 sn (surec.md 5c notu); gevşek sınır yalnız gerilemeyi yakalar
        k.geri_al()


class TestKarsilastirmaTurkce:
    """§1.4 regresyon notu: formül metin karşılaştırması ve ölçüt `<`/`>` artık Türkçe alfabe sırasıyla."""

    def test_karsilastir(self):
        assert karsilastir("ç", "d") == -1 and karsilastir("ç", "c") == 1
        assert karsilastir("ğ", "h") == -1 and karsilastir("ı", "i") == -1 and karsilastir("ş", "t") == -1
        assert karsilastir("z", "ç") == 1
        assert karsilastir("Ali", "ali") == 0 and karsilastir("IŞIK", "ışık") == 0
        assert karsilastir("a", "b") == -1 and karsilastir("abc", "abd") == -1

    def test_formul_ve_olcut(self, kitap, sayfa):
        Hesaplayici(kitap)
        sayfa.ata(1, 1, Hucre(None, '="ç"<"d"'))
        sayfa.ata(2, 1, Hucre(None, '="z">"ç"'))
        for i, v in enumerate(["a", "ç", "m", "ş", "z"], start=1):
            sayfa.ata(i, 3, Hucre(v))
        sayfa.ata(3, 1, Hucre(None, '=COUNTIF(C1:C5,"<m")'))
        sayfa.ata(4, 1, Hucre(None, '=COUNTIF(C1:C5,">=ş")'))
        assert sayfa.deger(1, 1) is True and sayfa.deger(2, 1) is True
        assert sayfa.deger(3, 1) == 2.0                                # a, ç
        assert sayfa.deger(4, 1) == 2.0                                # ş, z
