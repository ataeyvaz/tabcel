"""Faz 5 / 5g: veri doğrulama — model, komut, denetim, ekle-sil (Qt'siz)."""
import pytest

from tabcel.formul.kosul import dogrula, liste_ogeleri
from tabcel.model import deger as D
from tabcel.model.adres import Aralik
from tabcel.model.ad import TanimliAd
from tabcel.model.dogrulama import Dogrulama, liste_sabiti_yaz, yeni_liste
from tabcel.model.komutlar import DogrulamaDegis, GeriAlYigini, SatirEkleSil, SutunEkleSil, ana_sayfa
from tabcel.model.sayfa import CalismaKitabi, Hucre

B2 = (Aralik(2, 2, 2, 2),)


@pytest.fixture
def kitap():
    return CalismaKitabi()


@pytest.fixture
def sayfa(kitap):
    return kitap.sayfalar[0]


def kur(sayfa, **kw):
    dv = Dogrulama(kw.pop("araliklar", B2), **kw)
    sayfa.dogrulamalari_yaz([dv])
    return dv


def gecer(sayfa, deger, r=2, c=2):
    return dogrula(sayfa, r, c, deger)


class TestKuralModeli:
    def test_gecersiz_alanlar(self):
        with pytest.raises(ValueError):
            Dogrulama(B2, tur="x")
        with pytest.raises(ValueError):
            Dogrulama(B2, islec="y")
        with pytest.raises(ValueError):
            Dogrulama(B2, hata=(True, "kotu", "", ""))

    def test_yeni_kural_eskinin_ustune_gelir(self):
        eski = Dogrulama((Aralik(1, 1, 5, 1),), tur="tam_sayi", formul1="=1")
        yeni = Dogrulama((Aralik(2, 1, 3, 1),), tur="ondalik", formul1="=1")
        liste = yeni_liste([eski], list(yeni.araliklar), yeni)
        assert [k.tur for k in liste] == ["tam_sayi", "ondalik"]
        # eski kuralın (2..3) satırları düşmüş olmalı: 1 ve 4..5 kalır
        kalan = [a for k in liste if k.tur == "tam_sayi" for a in k.araliklar]
        assert set(kalan) == {Aralik(1, 1, 1, 1), Aralik(4, 1, 5, 1)}

    def test_kaldirma_ve_tamamen_ortulen_kural_duser(self):
        eski = Dogrulama(B2, tur="tam_sayi", formul1="=1")
        assert yeni_liste([eski], [Aralik(1, 1, 3, 3)], None) == []

    def test_sayfa_dogrulama_arama_ve_olay(self, kitap, sayfa):
        o = []
        kitap.dinle(o.append)
        dv = kur(sayfa, tur="tam_sayi", formul1="=1")
        assert sayfa.dogrulama(2, 2) is dv and sayfa.dogrulama(2, 3) is None
        assert [(x.tur, x.ayrinti["alan"]) for x in o] == [("ek", "dogrulama")]

    def test_liste_sabiti(self):
        assert liste_sabiti_yaz(["Evet", "Hayır"]) == '"Evet,Hayır"'


class TestKomut:
    def test_yap_geri_al_yinele_ve_bos(self, sayfa):
        y = GeriAlYigini()
        dv = Dogrulama(B2, tur="tam_sayi", formul1="=1")
        k = DogrulamaDegis(sayfa, list(B2), dv)
        assert not k.bos_mu() and ana_sayfa(k, True) is sayfa
        y.calistir(k)
        assert sayfa.dogrulamalar == [dv]
        y.geri_al()
        assert sayfa.dogrulamalar == []
        y.yinele()
        assert sayfa.dogrulamalar == [dv]
        assert DogrulamaDegis(sayfa, [Aralik(9, 9, 9, 9)], None).bos_mu()


class TestSayisalTurler:
    def test_tam_sayi_arasinda(self, sayfa):
        kur(sayfa, tur="tam_sayi", islec="arasinda", formul1="=1", formul2="=10")
        assert gecer(sayfa, 5.0) and gecer(sayfa, 1.0) and gecer(sayfa, 10.0)
        assert not gecer(sayfa, 5.5) and not gecer(sayfa, 11.0) and not gecer(sayfa, 0.0)

    def test_metin_bool_hata_gecersiz(self, sayfa):
        kur(sayfa, tur="tam_sayi", islec="buyuk", formul1="=0")
        assert not gecer(sayfa, "5") and not gecer(sayfa, True) and not gecer(sayfa, D.DEGER_HATASI)

    def test_bos_girdi_bos_yoksay(self, sayfa):
        kur(sayfa, tur="tam_sayi", islec="buyuk", formul1="=0")
        assert gecer(sayfa, None)
        kur(sayfa, tur="tam_sayi", islec="buyuk", formul1="=0", bos_yoksay=False)
        assert not gecer(sayfa, None)

    @pytest.mark.parametrize("islec,a,b,gecen,gecmeyen", [
        ("arasinda_degil", 1.0, 3.0, [0.5, 3.5], [1.0, 2.0, 3.0]),
        ("esit", 2.0, None, [2.0], [1.0]),
        ("esit_degil", 2.0, None, [1.0], [2.0]),
        ("buyuk", 2.0, None, [2.5], [2.0]),
        ("kucuk", 2.0, None, [1.5], [2.0]),
        ("buyuk_esit", 2.0, None, [2.0], [1.9]),
        ("kucuk_esit", 2.0, None, [2.0], [2.1]),
    ])
    def test_islecler(self, sayfa, islec, a, b, gecen, gecmeyen):
        kur(sayfa, tur="ondalik", islec=islec, formul1=f"={a}", formul2=None if b is None else f"={b}")
        assert all(gecer(sayfa, x) for x in gecen)
        assert not any(gecer(sayfa, x) for x in gecmeyen)

    def test_tarih_ve_saat_seri_sayi(self, sayfa):
        kur(sayfa, tur="tarih", islec="buyuk_esit", formul1="=46000")
        assert gecer(sayfa, 46000.0) and not gecer(sayfa, 45999.0) and not gecer(sayfa, "x")
        kur(sayfa, tur="saat", islec="arasinda", formul1="=0.25", formul2="=0.5")
        assert gecer(sayfa, 0.3) and not gecer(sayfa, 0.6)

    def test_metin_uzunlugu(self, sayfa):
        kur(sayfa, tur="metin_uzunlugu", islec="kucuk_esit", formul1="=5")
        assert gecer(sayfa, "Çağla") and not gecer(sayfa, "Çağlar") and gecer(sayfa, 12345.0)
        assert not gecer(sayfa, 123456.0)

    def test_baska_hucreye_bakan_formul(self, sayfa):
        sayfa.ata(1, 1, Hucre(100.0))
        kur(sayfa, tur="tam_sayi", islec="kucuk_esit", formul1="=$A$1")
        assert gecer(sayfa, 100.0) and not gecer(sayfa, 101.0)
        sayfa.ata(1, 1, Hucre(5.0))
        assert not gecer(sayfa, 100.0)

    def test_goreli_basvuru_hucreye_gore_kayar(self, sayfa):
        sayfa.ata(2, 1, Hucre(10.0))
        sayfa.ata(3, 1, Hucre(50.0))
        kur(sayfa, araliklar=(Aralik(2, 2, 3, 2),), tur="tam_sayi", islec="kucuk_esit", formul1="=A2")
        assert gecer(sayfa, 10.0, 2, 2) and not gecer(sayfa, 11.0, 2, 2)
        assert gecer(sayfa, 50.0, 3, 2) and not gecer(sayfa, 51.0, 3, 2)

    def test_bozuk_formul_gecersiz(self, sayfa):
        kur(sayfa, tur="tam_sayi", islec="esit", formul1="=1/0")
        assert not gecer(sayfa, 1.0)
        kur(sayfa, tur="tam_sayi", islec="esit", formul1=None)
        assert not gecer(sayfa, 1.0)


class TestListe:
    def test_sabit_liste_buyuk_kucuk_duyarsiz_turkce(self, sayfa):
        kur(sayfa, tur="liste", formul1='"Evet,Hayır,İyi"')
        assert gecer(sayfa, "evet") and gecer(sayfa, "HAYIR") and gecer(sayfa, "iyi") and gecer(sayfa, "İYİ")
        assert not gecer(sayfa, "ıyı") and not gecer(sayfa, "Belki")

    def test_sayi_ve_metin_ayni_gorunumde_eslesir(self, sayfa):
        kur(sayfa, tur="liste", formul1='"1,2,3"')
        assert gecer(sayfa, 2.0) and gecer(sayfa, "2") and not gecer(sayfa, 4.0)

    def test_aralik_listesi_ve_degisince(self, sayfa):
        for i, v in enumerate(("Ali", "Veli", None, 7.0), start=1):
            if v is not None:
                sayfa.ata(i, 5, Hucre(v))
        kur(sayfa, tur="liste", formul1="=$E$1:$E$4")
        assert gecer(sayfa, "veli") and gecer(sayfa, 7.0) and not gecer(sayfa, "Can")
        sayfa.ata(2, 5, Hucre("Can"))
        assert gecer(sayfa, "Can") and not gecer(sayfa, "Veli")

    def test_ogeler_bos_hucre_acilir_listede_bos_satir(self, sayfa):
        sayfa.ata(1, 5, Hucre("a"))
        sayfa.ata(3, 5, Hucre("c"))
        dv = kur(sayfa, tur="liste", formul1="=$E$1:$E$3")
        assert liste_ogeleri(dv, sayfa, 2, 2) == ["a", "c"]
        assert liste_ogeleri(dv, sayfa, 2, 2, bos_dahil=True) == ["a", "", "c"]

    def test_tanimli_ad_ve_baska_sayfa(self, kitap, sayfa):
        s2 = kitap.sayfa_ekle("Liste")
        s2.ata(1, 1, Hucre("x"))
        s2.ata(2, 1, Hucre("y"))
        kur(sayfa, tur="liste", formul1=f"=[{s2.kimlik}]!$A$1:$A$2")
        assert gecer(sayfa, "Y") and not gecer(sayfa, "z")
        kitap.ad_yaz(TanimliAd("Secenekler", f"=[{s2.kimlik}]!$A$1:$A$2"))
        kur(sayfa, tur="liste", formul1="=Secenekler")
        assert gecer(sayfa, "x") and not gecer(sayfa, "q")

    def test_hatali_kaynak_gecersiz_ve_bos(self, sayfa):
        sayfa.ata(1, 5, Hucre(D.DEGER_HATASI))
        dv = kur(sayfa, tur="liste", formul1="=$E$1:$E$2")
        assert liste_ogeleri(dv, sayfa, 2, 2) is None and not gecer(sayfa, "a")
        assert gecer(sayfa, None)                                           # bos_yoksay


class TestOzel:
    def test_formul_yeni_degerle_degerlenir(self, sayfa):
        kur(sayfa, tur="ozel", formul1="=B2>10")
        assert gecer(sayfa, 11.0) and not gecer(sayfa, 10.0)
        assert gecer(sayfa, "a")                                            # Excel: metin > sayı DOĞRU

    def test_hucre_degeri_geri_konur(self, sayfa):
        sayfa.ata(2, 2, Hucre("eski"))
        kur(sayfa, tur="ozel", formul1="=LEN(B2)=3")
        assert gecer(sayfa, "abc") and sayfa.deger(2, 2) == "eski"
        sayfa._hucreler.pop((2, 2))
        assert gecer(sayfa, "xyz") and sayfa.hucre(2, 2) is None

    def test_baska_hucre_ve_sifir_degil_sayi(self, sayfa):
        sayfa.ata(1, 1, Hucre("x"))
        kur(sayfa, tur="ozel", formul1="=COUNTIF($A$1:$A$3,B2)=0")
        assert gecer(sayfa, "y") and not gecer(sayfa, "x") and not gecer(sayfa, "X")
        kur(sayfa, tur="ozel", formul1="=B2*0+1")
        assert gecer(sayfa, 3.0)
        kur(sayfa, tur="ozel", formul1="=B2*0")
        assert not gecer(sayfa, 3.0)


class TestEkleSil:
    def test_satir_ekle_aralik_ve_formul_kayar_geri_al(self, kitap, sayfa):
        sayfa.ata(1, 1, Hucre(5.0))
        dv = kur(sayfa, tur="tam_sayi", islec="kucuk_esit", formul1="=$A$1")
        y = GeriAlYigini()
        y.calistir(SatirEkleSil(sayfa, 1, 2, True))
        k = sayfa.dogrulamalar[0]
        assert k.araliklar == (Aralik(4, 2, 4, 2),) and k.formul1 == "=$A$3"
        assert gecer(sayfa, 5.0, 4, 2) and not gecer(sayfa, 6.0, 4, 2)         # =$A$3 (5) kaydı izler
        y.geri_al()
        assert sayfa.dogrulamalar == [dv]

    def test_liste_sabiti_ekle_silde_degismez(self, sayfa):
        kur(sayfa, tur="liste", formul1='"Evet,Hayır"')
        SutunEkleSil(sayfa, 1, 1, True).yap()
        assert sayfa.dogrulamalar[0].formul1 == '"Evet,Hayır"'
        assert sayfa.dogrulamalar[0].araliklar == (Aralik(2, 3, 2, 3),)

    def test_aralik_silinince_kural_duser(self, sayfa):
        kur(sayfa, tur="tam_sayi", formul1="=1")
        y = GeriAlYigini()
        y.calistir(SatirEkleSil(sayfa, 2, 1, False))
        assert sayfa.dogrulamalar == []
        y.geri_al()
        assert len(sayfa.dogrulamalar) == 1


# ----------------------------------------------------------------------------------- .xlsx
class TestXlsx:
    def _kitap(self, *kurallar):
        k = CalismaKitabi()
        k.sayfa_ekle("Liste Sayfası")
        k.sayfalar[0].dogrulamalari_yaz(list(kurallar))
        return k

    def _tur(self, tmp_path, *kurallar):
        from tabcel.io import xlsx_io
        k = self._kitap(*kurallar)
        yol = str(tmp_path / "d.xlsx")
        xlsx_io.kaydet(k, yol)
        k2, rapor = xlsx_io.ac(yol)
        return k2.sayfalar[0].dogrulamalar, rapor

    @pytest.mark.parametrize("dv", [
        Dogrulama((Aralik(1, 1, 3, 1), Aralik(5, 1, 5, 1)), tur="tam_sayi", islec="arasinda", formul1="=1",
                  formul2="=$B$1", giris=(True, "T", "İ"), hata=(True, "uyari", "H", "E")),
        Dogrulama((Aralik(1, 3, 3, 3),), tur="liste", formul1='"Evet,Hayır"', acilir_liste=False, bos_yoksay=False),
        Dogrulama((Aralik(1, 4, 3, 4),), tur="liste", formul1="=[2]!$A$1:$A$5"),
        Dogrulama((Aralik(1, 5, 1, 5),), tur="ozel", formul1="=COUNTIF($E:$E,E1)=1"),
        Dogrulama((Aralik(1, 6, 1, 6),), tur="tarih", islec="buyuk", formul1="=46000", hata=(False, "bilgi", "", "")),
        Dogrulama((Aralik(1, 7, 1, 7),), tur="ondalik", islec="arasinda_degil", formul1="=0.5", formul2="=2.5"),
        Dogrulama((Aralik(1, 8, 1, 8),), tur="metin_uzunlugu", islec="kucuk_esit", formul1="=10"),
        Dogrulama((Aralik(1, 9, 1, 9),), tur="saat", islec="esit_degil", formul1="=0.5"),
        Dogrulama((Aralik(1, 10, 1, 10),), tur="her_deger", giris=(True, "", "Not")),
    ])
    def test_gidis_donus(self, tmp_path, dv):
        okunan, rapor = self._tur(tmp_path, dv)
        assert okunan == [dv] and not rapor.uyarilar

    def test_liste_sayfa_adi_cevrilir(self, tmp_path):
        import zipfile
        from tabcel.io import xlsx_io
        k = self._kitap(Dogrulama((Aralik(1, 1, 1, 1),), tur="liste", formul1="=[2]!$A$1:$A$3"))
        yol = str(tmp_path / "s.xlsx")
        xlsx_io.kaydet(k, yol)
        with zipfile.ZipFile(yol) as z:
            xml = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        assert "'Liste Sayfası'!$A$1:$A$3" in xml and 'type="list"' in xml

    def test_tara_uyari_vermez(self, tmp_path):
        from tabcel.io import xlsx_io
        k = self._kitap(Dogrulama((Aralik(1, 1, 1, 1),), tur="tam_sayi", formul1="=1", islec="buyuk"))
        yol = str(tmp_path / "t.xlsx")
        xlsx_io.kaydet(k, yol)
        assert xlsx_io.tara(yol).uyarilar == []

    def test_dogrulamasiz_dosya(self, tmp_path):
        okunan, rapor = self._tur(tmp_path)
        assert okunan == [] and not rapor.uyarilar
