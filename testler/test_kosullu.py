"""Faz 5 / 5h: koşullu biçim — model, değerlendirme, öncelik, ekle-sil, komut (Qt'siz)."""
import pytest

from tabcel.formul.kosul import KosulluHesap, yuzdebirlik
from tabcel.model import deger as D
from tabcel.model.adres import Aralik
from tabcel.model.komutlar import GeriAlYigini, KosulluDegis, SatirEkleSil, ana_sayfa
from tabcel.model.kosullu import KosulluKural, RENK_OLCEKLERI, aralik_temizle, kural_ekle
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.stil import StilYama

KIRMIZI = StilYama(dolgu="#FFC7CE", yazi_rengi="#9C0006")
SARI = StilYama(dolgu="#FFEB9C")
A = (Aralik(1, 1, 8, 1),)


@pytest.fixture
def sayfa():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    return s


def doldur(sayfa, degerler, sutun=1):
    for r, v in enumerate(degerler, start=1):
        if v is not None:
            sayfa.ata(r, sutun, Hucre(v))


def kur(sayfa, *kurallar):
    sayfa.kosullulari_yaz(list(kurallar))
    return KosulluHesap(sayfa)


def uygulanan(h, r, c=1):
    yama, cubuk = h.hucre(r, c)
    return yama


def kosul(**kw):
    kw.setdefault("bicim", KIRMIZI)
    return KosulluKural(kw.pop("araliklar", A), **kw)


class TestHucreDegeri:
    def test_buyuk_normal_bos_hata_karisim(self, sayfa):
        doldur(sayfa, [1.0, 6.0, None, "metin", D.DEGER_HATASI, 5.0, True])
        h = kur(sayfa, kosul(tur="hucre_degeri", islec="buyuk", formul1="=5"))
        assert [uygulanan(h, r) is not None for r in range(1, 8)] == [False, True, False, True, False, False, True]
        # metin ve mantıksal sayıdan büyük (Excel sırası); hata uygulanmaz; boş 0 gibi

    def test_bos_hucre_sifir_gibi(self, sayfa):
        doldur(sayfa, [None, 1.0])
        h = kur(sayfa, kosul(tur="hucre_degeri", islec="kucuk", formul1="=5"))
        assert uygulanan(h, 1) is not None and uygulanan(h, 2) is not None

    @pytest.mark.parametrize("islec,a,b,gecen,gecmeyen", [
        ("arasinda", 2.0, 4.0, [2.0, 3.0, 4.0], [1.0, 5.0]),
        ("arasinda_degil", 2.0, 4.0, [1.0, 5.0], [2.0, 3.0, 4.0]),
        ("esit", 3.0, None, [3.0], [2.0]),
        ("esit_degil", 3.0, None, [2.0], [3.0]),
        ("buyuk_esit", 3.0, None, [3.0, 4.0], [2.0]),
        ("kucuk_esit", 3.0, None, [3.0, 2.0], [4.0]),
    ])
    def test_islecler(self, sayfa, islec, a, b, gecen, gecmeyen):
        doldur(sayfa, gecen + gecmeyen)
        h = kur(sayfa, kosul(tur="hucre_degeri", islec=islec, formul1=f"={a}",
                              formul2=None if b is None else f"={b}"))
        n = len(gecen)
        assert all(uygulanan(h, r) for r in range(1, n + 1))
        assert not any(uygulanan(h, r) for r in range(n + 1, n + len(gecmeyen) + 1))

    def test_metin_karsilastirma_turkce_ve_buyuk_kucuk_duyarsiz(self, sayfa):
        doldur(sayfa, ["çay", "Zeynep", "ali", "ALİ"])
        h = kur(sayfa, kosul(tur="hucre_degeri", islec="esit", formul1='="Ali"'))
        assert [bool(uygulanan(h, r)) for r in range(1, 5)] == [False, False, True, True]
        h = kur(sayfa, kosul(tur="hucre_degeri", islec="kucuk", formul1='="d"'))
        assert [bool(uygulanan(h, r)) for r in range(1, 5)] == [True, False, True, True]     # ç < d

    def test_hucre_basvurulu_goreli_formul(self, sayfa):
        doldur(sayfa, [10.0, 1.0, 20.0, 99.0])
        doldur(sayfa, [5.0, 5.0, 5.0, 5.0], sutun=2)
        h = kur(sayfa, kosul(araliklar=(Aralik(1, 1, 4, 1),), tur="hucre_degeri", islec="buyuk", formul1="=B1"))
        assert [bool(uygulanan(h, r)) for r in range(1, 5)] == [True, False, True, True]
        sayfa.ata(2, 2, Hucre(0.5))
        h.gecersiz()
        assert uygulanan(h, 2)


class TestMetinBosHata:
    def test_icerir_icermez_baslar_biter(self, sayfa):
        doldur(sayfa, ["Çağla", "ağaç", None, 12.0])
        for islec, beklenen in (("icerir", [True, True, False, False]), ("icermez", [False, False, True, True]),
                                ("baslar", [True, False, False, False]), ("biter", [False, True, False, False])):
            h = kur(sayfa, kosul(tur="metin", islec=islec, metin="ağ" if islec == "icerir" else "ç"
                                 if islec == "biter" else "çağ" if islec == "baslar" else "ağ"))
            assert [bool(uygulanan(h, r)) for r in range(1, 5)] == beklenen, islec

    def test_sayi_gorunen_metinde_aranir(self, sayfa):
        doldur(sayfa, [123.0, 45.0])
        h = kur(sayfa, kosul(tur="metin", islec="icerir", metin="2"))
        assert [bool(uygulanan(h, r)) for r in (1, 2)] == [True, False]

    def test_bos_ve_bos_degil(self, sayfa):
        doldur(sayfa, ["x", None, "  ", 0.0])
        h = kur(sayfa, kosul(tur="bos"))
        assert [bool(uygulanan(h, r)) for r in range(1, 5)] == [False, True, True, False]
        h = kur(sayfa, kosul(tur="bos_degil"))
        assert [bool(uygulanan(h, r)) for r in range(1, 5)] == [True, False, False, True]

    def test_hata_ve_hata_degil(self, sayfa):
        doldur(sayfa, [D.DEGER_HATASI, 1.0, None, "x"])
        h = kur(sayfa, kosul(tur="hata"))
        assert [bool(uygulanan(h, r)) for r in range(1, 5)] == [True, False, False, False]
        h = kur(sayfa, kosul(tur="hata_degil"))
        assert [bool(uygulanan(h, r)) for r in range(1, 5)] == [False, True, True, True]


class TestYinelenen:
    def test_yinelenen_ve_benzersiz(self, sayfa):
        doldur(sayfa, [1.0, 2.0, 1.0, "Ali", "ali", None, None, "Veli"])
        h = kur(sayfa, kosul(tur="yinelenen"))
        assert [bool(uygulanan(h, r)) for r in range(1, 9)] == [True, False, True, True, True, False, False, False]
        h = kur(sayfa, kosul(tur="yinelenen", benzersiz=True))
        assert [bool(uygulanan(h, r)) for r in range(1, 9)] == [False, True, False, False, False, False, False, True]

    def test_sayi_ile_metin_ayri_hata_degerleri(self, sayfa):
        doldur(sayfa, [1.0, "1", D.DEGER_HATASI, D.DEGER_HATASI])
        h = kur(sayfa, kosul(tur="yinelenen"))
        assert [bool(uygulanan(h, r)) for r in range(1, 5)] == [False, False, True, True]

    def test_degisince_gecersiz_ile_yenilenir(self, sayfa):
        doldur(sayfa, [1.0, 2.0])
        h = kur(sayfa, kosul(tur="yinelenen"))
        assert not uygulanan(h, 1)
        sayfa.ata(2, 1, Hucre(1.0))
        assert not uygulanan(h, 1)                            # önbellek: gecersiz() çağrılana dek
        h.gecersiz()
        assert uygulanan(h, 1)


class TestIlkOrtalama:
    def test_ilk_son_eslerle(self, sayfa):
        doldur(sayfa, [10.0, 50.0, 30.0, 50.0, 20.0, "x", None])
        h = kur(sayfa, kosul(tur="ilk_son", n=2))
        assert [bool(uygulanan(h, r)) for r in range(1, 8)] == [False, True, False, True, False, False, False]
        h = kur(sayfa, kosul(tur="ilk_son", n=1, alt=True))
        assert [bool(uygulanan(h, r)) for r in range(1, 8)] == [True, False, False, False, False, False, False]

    def test_yuzde_ve_bos_aralik(self, sayfa):
        doldur(sayfa, [1.0, 2.0, 3.0, 4.0, 5.0])
        h = kur(sayfa, kosul(tur="ilk_son", n=40, yuzde=True))
        assert [bool(uygulanan(h, r)) for r in range(1, 6)] == [False, False, False, True, True]
        h = kur(sayfa, kosul(araliklar=(Aralik(1, 3, 3, 3),), tur="ilk_son", n=1))
        assert not uygulanan(h, 1, 3)

    def test_ortalama_ustu_alti_esit_std(self, sayfa):
        doldur(sayfa, [10.0, 20.0, 30.0, 40.0, 50.0])          # ort 30, örnek sapma ≈ 15,81
        h = kur(sayfa, kosul(tur="ortalama", ustu=True))
        assert [bool(uygulanan(h, r)) for r in range(1, 6)] == [False, False, False, True, True]
        h = kur(sayfa, kosul(tur="ortalama", ustu=True, esit=True))
        assert uygulanan(h, 3)
        h = kur(sayfa, kosul(tur="ortalama", ustu=False))
        assert [bool(uygulanan(h, r)) for r in range(1, 6)] == [True, True, False, False, False]
        h = kur(sayfa, kosul(tur="ortalama", ustu=True, std=1))
        assert [bool(uygulanan(h, r)) for r in range(1, 6)] == [False, False, False, False, True]


class TestFormul:
    def test_goreli_formul_satirin_baska_hucresine_bakar(self, sayfa):
        doldur(sayfa, [1.0, 2.0, 3.0], sutun=1)
        doldur(sayfa, [3.0, 2.0, 1.0], sutun=2)
        h = kur(sayfa, kosul(araliklar=(Aralik(1, 1, 3, 1),), tur="formul", formul1="=$B1>A1"))
        assert [bool(uygulanan(h, r)) for r in (1, 2, 3)] == [True, False, False]

    def test_mantiksal_sifir_olmayan_ve_hata(self, sayfa):
        doldur(sayfa, [4.0])
        for f, beklenen in (("=A1>3", True), ("=A1*0", False), ("=A1*2", True), ("=1/0", False), ("=\"x\"", False)):
            h = kur(sayfa, kosul(araliklar=(Aralik(1, 1, 1, 1),), tur="formul", formul1=f))
            assert bool(uygulanan(h, 1)) is beklenen, f

    def test_tum_satir_boyama_formulu(self, sayfa):
        doldur(sayfa, ["a", "b", "a"], sutun=1)
        h = kur(sayfa, kosul(araliklar=(Aralik(1, 1, 3, 3),), tur="formul", formul1='=$A1="a"'))
        assert uygulanan(h, 1, 3) and not uygulanan(h, 2, 3) and uygulanan(h, 3, 2)


class TestOncelikVeDur:
    def test_yamalar_birlesir_ust_oncelik_kazanir(self, sayfa):
        doldur(sayfa, [10.0])
        ust = kosul(tur="hucre_degeri", islec="buyuk", formul1="=5", bicim=StilYama(dolgu="#FF0000"))
        alt = kosul(tur="hucre_degeri", islec="buyuk", formul1="=1",
                    bicim=StilYama(dolgu="#00FF00", kalin=True))
        h = kur(sayfa, ust, alt)
        assert h.hucre(1, 1)[0] == StilYama(dolgu="#FF0000", kalin=True)

    def test_dur_sonrakileri_atlar(self, sayfa):
        doldur(sayfa, [10.0])
        ust = kosul(tur="hucre_degeri", islec="buyuk", formul1="=5", bicim=StilYama(dolgu="#FF0000"), dur=True)
        alt = kosul(tur="hucre_degeri", islec="buyuk", formul1="=1", bicim=StilYama(kalin=True))
        assert kur(sayfa, ust, alt).hucre(1, 1)[0] == StilYama(dolgu="#FF0000")
        # dur yalnız ESLESEN kuralda geçerli: eşleşmeyen dur kural sonrakini engellemez
        yok = kosul(tur="hucre_degeri", islec="kucuk", formul1="=1", bicim=SARI, dur=True)
        assert kur(sayfa, yok, alt).hucre(1, 1)[0] == StilYama(kalin=True)

    def test_aralik_disi_ve_kural_yok(self, sayfa):
        doldur(sayfa, [10.0, 10.0])
        h = kur(sayfa, kosul(araliklar=(Aralik(1, 1, 1, 1),), tur="hucre_degeri", islec="buyuk", formul1="=5"))
        assert h.hucre(2, 1) == (None, None) and h.hucre(1, 1)[0] is not None
        assert KosulluHesap(sayfa).var_mi() and not KosulluHesap(CalismaKitabi().sayfalar[0]).var_mi()

    def test_bozuk_formul_kural_uygulanmaz_digerleri_calisir(self, sayfa):
        doldur(sayfa, [10.0])
        bozuk = kosul(tur="hucre_degeri", islec="buyuk", formul1=None)
        iyi = kosul(tur="hucre_degeri", islec="buyuk", formul1="=5", bicim=SARI)
        assert kur(sayfa, bozuk, iyi).hucre(1, 1)[0] == SARI


class TestRenkOlcegi:
    def test_uc_renkli_ara_renk(self, sayfa):
        doldur(sayfa, [0.0, 50.0, 100.0, None, "x", None])
        h = kur(sayfa, KosulluKural(A, tur="renk_olcegi", noktalar=RENK_OLCEKLERI["yesil_sari_kirmizi"]))
        dolgu = lambda r: (uygulanan(h, r)._alanlar["dolgu"] if uygulanan(h, r) else None)
        assert dolgu(1) == "#F8696B" and dolgu(2) == "#FFEB84" and dolgu(3) == "#63BE7B"
        assert dolgu(5) is None and dolgu(6) is None                          # metin/boş boyanmaz

    def test_ara_renk_dogrusal(self, sayfa):
        doldur(sayfa, [0.0, 10.0, 5.0])
        h = kur(sayfa, KosulluKural(A, tur="renk_olcegi", noktalar=(("min", None, "#000000"), ("max", None, "#FEFEFE"))))
        assert uygulanan(h, 3)._alanlar["dolgu"] == "#7F7F7F"

    def test_sayi_yuzde_yuzdebirlik_noktalari(self, sayfa):
        doldur(sayfa, [0.0, 100.0, 40.0, 60.0])
        h = kur(sayfa, KosulluKural(A, tur="renk_olcegi",
                                    noktalar=(("sayi", "=40", "#000000"), ("yuzde", "=60", "#FFFFFF"))))
        dolgu = lambda r: uygulanan(h, r)._alanlar["dolgu"]
        assert dolgu(1) == "#000000" and dolgu(3) == "#000000" and dolgu(2) == "#FFFFFF"   # 60. yüzde = 60
        assert dolgu(4) == "#FFFFFF"
        h = kur(sayfa, KosulluKural(A, tur="renk_olcegi",
                                    noktalar=(("min", None, "#000000"), ("yuzdebirlik", "=50", "#808080"),
                                              ("max", None, "#FFFFFF"))))
        assert uygulanan(h, 4)._alanlar["dolgu"] != uygulanan(h, 3)._alanlar["dolgu"]

    def test_yuzdebirlik_islevi(self):
        assert yuzdebirlik([1.0, 2.0, 3.0, 4.0], 50) == 2.5 and yuzdebirlik([7.0], 90) == 7.0
        assert yuzdebirlik([1.0, 2.0, 3.0], 0) == 1.0 and yuzdebirlik([1.0, 2.0, 3.0], 100) == 3.0

    def test_gecersiz_nokta_sayisi(self):
        with pytest.raises(ValueError):
            KosulluKural(A, tur="renk_olcegi", noktalar=(("min", None, "#000000"),))


class TestVeriCubugu:
    def test_oran_ve_alt_ust_sinir(self, sayfa):
        doldur(sayfa, [0.0, 50.0, 100.0, "x", None])
        h = kur(sayfa, KosulluKural(A, tur="veri_cubugu", bicim=None, renk="#638EC6"))
        oran = lambda r: h.hucre(r, 1)[1][0]
        assert oran(1) == pytest.approx(0.1) and oran(2) == pytest.approx(0.5) and oran(3) == pytest.approx(0.9)
        assert h.hucre(4, 1)[1] is None and h.hucre(5, 1)[1] is None
        assert h.hucre(3, 1)[1][1:] == ("#638EC6", False, True)

    def test_sabit_uclar_ve_esit_degerler(self, sayfa):
        doldur(sayfa, [5.0, 5.0])
        h = kur(sayfa, KosulluKural(A, tur="veri_cubugu", bicim=None))
        assert h.hucre(1, 1)[1][0] == pytest.approx(0.9)                     # min = max: tam çubuk
        h = kur(sayfa, KosulluKural(A, tur="veri_cubugu", bicim=None, min_nokta=("sayi", "=0"),
                                    max_nokta=("sayi", "=10"), yalniz_cubuk=True, gradyan=False))
        assert h.hucre(1, 1)[1] == (pytest.approx(0.5), "#638EC6", True, False)

    def test_cubuk_ve_renk_kurallari_birlikte(self, sayfa):
        doldur(sayfa, [1.0, 9.0])
        h = kur(sayfa, kosul(tur="hucre_degeri", islec="buyuk", formul1="=5"),
                KosulluKural(A, tur="veri_cubugu", bicim=None))
        yama, cubuk = h.hucre(2, 1)
        assert yama == KIRMIZI and cubuk is not None


class TestKuralModeli:
    def test_gecersiz_alanlar(self):
        with pytest.raises(ValueError):
            KosulluKural(A, tur="x")
        with pytest.raises(ValueError):
            KosulluKural(A, tur="hucre_degeri", islec="y")
        with pytest.raises(ValueError):
            KosulluKural(A, tur="metin", islec="buyuk")
        with pytest.raises(ValueError):
            KosulluKural(A, tur="veri_cubugu", min_nokta=("kotu", None))

    def test_bicimsiz_mu_ve_kural_ekle_oncelik(self):
        assert KosulluKural(A, tur="bos", bicim=None).bicimsiz_mu()
        assert not KosulluKural(A, tur="veri_cubugu", bicim=None).bicimsiz_mu()
        a, b = kosul(tur="bos"), kosul(tur="hata")
        assert kural_ekle([a], b) == [b, a] and kural_ekle([a], b, basa=False) == [a, b]

    def test_aralik_temizle(self):
        k = kosul(araliklar=(Aralik(1, 1, 5, 1),), tur="bos")
        assert aralik_temizle([k], [Aralik(1, 1, 5, 1)]) == []
        kalan = aralik_temizle([k], [Aralik(2, 1, 3, 1)])
        assert {a for x in kalan for a in x.araliklar} == {Aralik(1, 1, 1, 1), Aralik(4, 1, 5, 1)}
        assert aralik_temizle([k], [Aralik(9, 9, 9, 9)]) == [k]


class TestKomutVeEkleSil:
    def test_yap_geri_al_yinele_islev_ve_olay(self, sayfa):
        kitap = sayfa.kitap
        o = []
        kitap.dinle(o.append)
        y = GeriAlYigini()
        a, b = kosul(tur="bos"), kosul(tur="hata")
        k = KosulluDegis(sayfa, [a])
        assert ana_sayfa(k, True) is sayfa and not k.bos_mu()
        y.calistir(k)
        y.calistir(KosulluDegis(sayfa, lambda eski: kural_ekle(eski, b)))
        assert sayfa.kosullu == [b, a]
        y.geri_al()
        assert sayfa.kosullu == [a]
        y.yinele()
        assert sayfa.kosullu == [b, a]
        assert [x.ayrinti["alan"] for x in o if x.tur == "ek"] == ["kosullu"] * 4
        assert KosulluDegis(sayfa, [b, a]).bos_mu()

    def test_satir_ekle_aralik_formul_ve_nokta_kayar_geri_al(self, sayfa):
        doldur(sayfa, [1.0, 2.0, 3.0, 4.0], sutun=1)
        sayfa.ata(1, 4, Hucre(5.0))
        formul = kosul(araliklar=(Aralik(2, 1, 4, 1),), tur="formul", formul1="=A2>$D$1")
        olcek = KosulluKural((Aralik(2, 1, 4, 1),), tur="renk_olcegi", bicim=None,
                             noktalar=(("sayi", "=$D$1", "#000000"), ("max", None, "#FFFFFF")))
        cubuk = KosulluKural((Aralik(2, 1, 4, 1),), tur="veri_cubugu", bicim=None, max_nokta=("sayi", "=$D$1"))
        sayfa.kosullulari_yaz([formul, olcek, cubuk])
        y = GeriAlYigini()
        y.calistir(SatirEkleSil(sayfa, 1, 2, True))
        f, o, c = sayfa.kosullu
        assert f.araliklar == (Aralik(4, 1, 6, 1),) and f.formul1 == "=A4>$D$3"
        assert o.noktalar[0][1] == "=$D$3" and c.max_nokta == ("sayi", "=$D$3")
        y.geri_al()
        assert sayfa.kosullu == [formul, olcek, cubuk]

    def test_aralik_silinince_kural_duser(self, sayfa):
        sayfa.kosullulari_yaz([kosul(araliklar=(Aralik(2, 1, 2, 1),), tur="bos")])
        SatirEkleSil(sayfa, 2, 1, False).yap()
        assert sayfa.kosullu == []
