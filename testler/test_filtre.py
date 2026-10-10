"""Faz 5 / 5f: otomatik filtre (model, komut) ve ALTTOPLAM — Qt'siz."""
import math

import pytest

from tabcel.formul import ceviri
from tabcel.formul.motor import Hesaplayici
from tabcel.model import deger as D
from tabcel.model.adres import Aralik
from tabcel.model.filtre import (
    DegerKosulu, Filtre, IlkKosul, OrtalamaKosulu, OzelKosul, RenkKosulu, aralik_genislet, gizlenecekler,
    liste_degerleri, sutun_renkleri,
)
from tabcel.model.komutlar import FiltreDegis, GeriAlYigini, SatirEkleSil, ana_sayfa
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.stil import StilYama


@pytest.fixture
def kitap():
    return CalismaKitabi()


@pytest.fixture
def sayfa(kitap):
    s = kitap.sayfalar[0]
    veri = [("Ad", "Puan", "Not"),
            ("Ali", 10.0, "a"), ("Çağla", 20.0, "b"), ("ali", 30.0, None), ("Zeynep", 40.0, "d"),
            (None, 50.0, "e"), ("İpek", "x", "f")]
    for r, satir in enumerate(veri, start=1):
        for c, v in enumerate(satir, start=1):
            if v is not None:
                s.ata(r, c, Hucre(v))
    return s


A = Aralik(1, 1, 7, 3)


def gizli(sayfa, **kosullar):
    return gizlenecekler(sayfa, Filtre(A, {int(k[1:]): v for k, v in kosullar.items()}))


class TestDegerKosulu:
    def test_normal_buyuk_kucuk_duyarsiz(self, sayfa):
        assert gizli(sayfa, c1=DegerKosulu(frozenset({"ALİ"}))) == {3, 5, 6, 7}      # Ali + ali görünür

    def test_turkce_i(self, sayfa):
        assert gizli(sayfa, c1=DegerKosulu(frozenset({"ipek"}))) == {2, 3, 4, 5, 6}   # İpek ≠ ipek? (i/İ eşit)

    def test_bos(self, sayfa):
        assert gizli(sayfa, c1=DegerKosulu(frozenset(), bos=True)) == {2, 3, 4, 5, 7}
        assert gizli(sayfa, c1=DegerKosulu(frozenset({"Ali"}), bos=False)) == {3, 5, 6, 7}

    def test_hata_degeri_gorunen_metin(self, sayfa):
        sayfa.ata(2, 2, Hucre(D.DEGER_HATASI))
        assert 2 not in gizli(sayfa, c2=DegerKosulu(frozenset({"#DEĞER!"})))

    def test_sayi_ve_metin_karisimi(self, sayfa):
        g = gizli(sayfa, c2=DegerKosulu(frozenset({"10", "x"})))
        assert g == {3, 4, 5, 6}


class TestOzelKosul:
    def test_sayi_buyuk(self, sayfa):
        assert gizli(sayfa, c2=OzelKosul(("buyuk", 25.0))) == {2, 3, 7}            # metin "x" geçmez

    def test_arasinda_ve_veya(self, sayfa):
        assert gizli(sayfa, c2=OzelKosul(("buyuk_esit", 20.0), ("kucuk_esit", 40.0))) == {2, 6, 7}
        assert gizli(sayfa, c2=OzelKosul(("kucuk", 20.0), ("buyuk", 40.0), ve=False)) == {3, 4, 5, 7}

    def test_esit_degil_metin_ve_bos_gecer(self, sayfa):
        assert gizli(sayfa, c2=OzelKosul(("esit_degil", 10.0))) == {2}

    def test_metin_islecleri_ve_joker(self, sayfa):
        assert gizli(sayfa, c1=OzelKosul(("baslar", "a"))) == {3, 5, 6, 7}        # Ali, ali
        assert gizli(sayfa, c1=OzelKosul(("biter", "li"))) == {3, 5, 6, 7}
        assert gizli(sayfa, c1=OzelKosul(("icerir", "ğl"))) == {2, 4, 5, 6, 7}
        assert gizli(sayfa, c1=OzelKosul(("esit", "?li"))) == {3, 5, 6, 7}
        assert 6 not in gizli(sayfa, c1=OzelKosul(("icermez", "a")))                # boş hücre geçer

    def test_metin_karsilastirma_turkce_siralama(self, sayfa):
        g = gizli(sayfa, c1=OzelKosul(("kucuk", "d")))                              # Ali, ali, Çağla
        assert g == {5, 6, 7}


class TestIlkOrtalamaRenk:
    def test_ilk_ve_son(self, sayfa):
        assert gizli(sayfa, c2=IlkKosul(2)) == {2, 3, 4, 7}                         # 50, 40
        assert gizli(sayfa, c2=IlkKosul(2, alt=True)) == {4, 5, 6, 7}               # 10, 20

    def test_yuzde(self, sayfa):
        assert gizli(sayfa, c2=IlkKosul(40, yuzde=True)) == {2, 3, 4, 7}            # 5 sayı × %40 = 2

    def test_ortalama(self, sayfa):
        assert gizli(sayfa, c2=OrtalamaKosulu(True)) == {2, 3, 4, 7}                # ort 30 → 40, 50
        assert gizli(sayfa, c2=OrtalamaKosulu(False)) == {4, 5, 6, 7}

    def test_ilk_diger_sutun_filtresinden_bagimsiz(self, sayfa):
        g = gizli(sayfa, c1=DegerKosulu(frozenset({"Ali"})), c2=IlkKosul(1))
        assert g == {2, 3, 4, 5, 6, 7}                                              # en büyük 50 başka satırda → hepsi gizli

    def test_renk(self, sayfa):
        sayfa.bicim_yaz(hucreler={(3, 1): sayfa.havuz.kimlik(sayfa.havuz.stil(0).__class__(dolgu="#ff0000"))})
        assert gizli(sayfa, c1=RenkKosulu("dolgu", "#FF0000")) == {2, 4, 5, 6, 7}
        assert gizli(sayfa, c1=RenkKosulu("dolgu", None)) == {3}


class TestListe:
    def test_degerler_sirali_benzersiz_bos(self, sayfa):
        d, bos, atlanan = liste_degerleri(sayfa, Filtre(A), 1)
        assert d == ["Ali", "Çağla", "İpek", "Zeynep"] and bos and atlanan == 0

    def test_diger_sutun_filtresi_listeyi_daraltir(self, sayfa):
        f = Filtre(A, {2: OzelKosul(("buyuk", 25.0))})
        d, bos, _ = liste_degerleri(sayfa, f, 1)
        assert d == ["ali", "Zeynep"] and bos

    def test_kendi_sutun_filtresi_listeyi_daraltmaz(self, sayfa):
        f = Filtre(A, {1: DegerKosulu(frozenset({"Ali"}))})
        assert len(liste_degerleri(sayfa, f, 1)[0]) == 4

    def test_renkler(self, sayfa):
        assert sutun_renkleri(sayfa, Filtre(A), 1, "dolgu") == [None]


def test_aralik_genislet(sayfa):
    assert aralik_genislet(sayfa, Aralik(1, 1, 3, 3)) == A
    assert aralik_genislet(sayfa, A) == A
    sayfa.ata(9, 1, Hucre("uzak"))                                                  # boş satır 8 durdurur
    assert aralik_genislet(sayfa, A) == A


class TestKomut:
    def test_uygula_geri_al_yinele(self, kitap, sayfa):
        y = GeriAlYigini()
        f = Filtre(A, {2: OzelKosul(("buyuk", 25.0))})
        y.calistir(FiltreDegis(sayfa, f))
        assert sayfa.filtre == f and sayfa.gizli_satir == {2, 3, 7}
        y.geri_al()
        assert sayfa.filtre is None and sayfa.gizli_satir == set()
        y.yinele()
        assert sayfa.gizli_satir == {2, 3, 7}

    def test_kaldirinca_satirlar_gorunur(self, sayfa):
        y = GeriAlYigini()
        y.calistir(FiltreDegis(sayfa, Filtre(A, {2: IlkKosul(1)})))
        y.calistir(FiltreDegis(sayfa, None))
        assert sayfa.filtre is None and sayfa.gizli_satir == set()
        y.geri_al()
        assert sayfa.gizli_satir == {2, 3, 4, 5, 7}

    def test_filtre_disindaki_gizli_satir_korunur(self, sayfa):
        sayfa.gizli_satir.add(20)
        y = GeriAlYigini()
        y.calistir(FiltreDegis(sayfa, Filtre(A, {2: IlkKosul(1)})))
        assert 20 in sayfa.gizli_satir
        y.calistir(FiltreDegis(sayfa, Filtre(A, {})))                               # filtreyi temizle
        assert sayfa.gizli_satir == {20}

    def test_elle_gizlenen_filtre_araliginda_yeniden_hesaplanir(self, sayfa):
        sayfa.gizli_satir.add(3)
        FiltreDegis(sayfa, Filtre(A, {})).yap()
        assert sayfa.gizli_satir == set()                                           # Excel gibi tek bit

    def test_olaylar_ek_ve_boyut(self, kitap, sayfa):
        o = []
        kitap.dinle(o.append)
        FiltreDegis(sayfa, Filtre(A, {2: IlkKosul(1)})).yap()
        turler = [(x.tur, x.ayrinti.get("alan")) for x in o]
        assert ("ek", "filtre") in turler and ("boyut", None) in turler
        assert turler.index(("ek", "filtre")) < turler.index(("boyut", None))

    def test_ana_sayfa_ve_ekle_sil_filtreyi_kaydirir(self, sayfa):
        k = FiltreDegis(sayfa, Filtre(A, {2: IlkKosul(1)}))
        assert ana_sayfa(k, True) is sayfa
        y = GeriAlYigini()
        y.calistir(k)
        y.calistir(SatirEkleSil(sayfa, 1, 2, True))
        assert sayfa.filtre.aralik == Aralik(3, 1, 9, 3)
        y.geri_al()
        assert sayfa.filtre.aralik == A


# ----------------------------------------------------------------------------------- ALTTOPLAM
def sonuc(kitap, sayfa, formul, r=20, c=1):
    sayfa.ata(r, c, ceviri.hucre_girdisi(formul, kitap))
    return sayfa.deger(r, c)


@pytest.fixture
def liste(kitap):
    """B1:B6 = 1..6; satır 2 ve 4 FİLTREYLE, satır 6 ELLE gizli (filtre aralığı dışı)."""
    s = kitap.sayfalar[0]
    for r in range(1, 7):
        s.ata(r, 2, Hucre(float(r)))
    s.ata(1, 1, Hucre("Başlık"))
    for r in range(2, 7):
        s.ata(r, 1, Hucre("x"))
    Hesaplayici(kitap)
    return s


class TestAlttoplam:
    def test_ad_cevirisi(self):
        assert ceviri.hucre_girdisi("=ALTTOPLAM(9;B1:B6)", None).formul == "=SUBTOTAL(9,B1:B6)"

    def test_filtre_yokken_tum_satirlar(self, kitap, liste):
        assert sonuc(kitap, liste, "=ALTTOPLAM(9;B1:B6)") == 21.0
        assert sonuc(kitap, liste, "=ALTTOPLAM(109;B1:B6)", 21) == 21.0

    def test_filtreyle_gizli_iki_grupta_da_dislanir(self, kitap, liste):
        liste.ata(20, 1, ceviri.hucre_girdisi("=ALTTOPLAM(9;B1:B6)", kitap))
        liste.ata(21, 1, ceviri.hucre_girdisi("=ALTTOPLAM(109;B1:B6)", kitap))
        FiltreDegis(liste, Filtre(Aralik(1, 1, 6, 2), {2: OzelKosul(("esit_degil", 2.0), ("esit_degil", 4.0))})).yap()
        assert liste.gizli_satir == {2, 4}
        assert liste.deger(20, 1) == 15.0 and liste.deger(21, 1) == 15.0             # motor `boyut`ta yeniden hesapladı

    def test_elle_gizli_yalniz_101_den_sonra_dislanir(self, kitap, liste):
        liste.gizli_satir.add(6)                                                      # filtre yok → elle gizli
        liste.boyut_degisti()
        assert sonuc(kitap, liste, "=ALTTOPLAM(9;B1:B6)") == 21.0
        assert sonuc(kitap, liste, "=ALTTOPLAM(109;B1:B6)", 21) == 15.0

    def test_elle_gizli_filtre_araligi_disinda_9da_sayilir(self, kitap, liste):
        FiltreDegis(liste, Filtre(Aralik(1, 1, 4, 2), {2: IlkKosul(1)})).yap()        # satır 2,3 gizli; 5,6 aralık dışı
        liste.gizli_satir.add(6)
        assert sonuc(kitap, liste, "=ALTTOPLAM(9;B1:B6)") == 1 + 4 + 5 + 6 == 16.0

    def test_alttoplam_hucreleri_sayilmaz(self, kitap, liste):
        liste.ata(7, 2, ceviri.hucre_girdisi("=ALTTOPLAM(9;B1:B6)", kitap))
        assert sonuc(kitap, liste, "=ALTTOPLAM(9;B1:B7)") == 21.0

    @pytest.mark.parametrize("no,beklenen", [(1, 3.5), (2, 6.0), (3, 6.0), (4, 6.0), (5, 1.0), (6, 720.0),
                                             (7, math.sqrt(3.5)), (8, math.sqrt(35 / 12)), (9, 21.0),
                                             (10, 3.5), (11, 35 / 12)])
    def test_islev_numaralari(self, kitap, liste, no, beklenen):
        assert sonuc(kitap, liste, f"=ALTTOPLAM({no};B1:B6)") == pytest.approx(beklenen)
        assert sonuc(kitap, liste, f"=ALTTOPLAM({100 + no};B1:B6)", 21) == pytest.approx(beklenen)

    def test_bos_metin_karisim_ve_hata(self, kitap, liste):
        liste.ata(8, 2, Hucre("metin"))
        liste.ata(9, 2, Hucre(D.DEGER_HATASI))
        assert sonuc(kitap, liste, "=ALTTOPLAM(9;B1:B8)") == 21.0                    # metin atlanır
        assert sonuc(kitap, liste, "=ALTTOPLAM(3;B1:B8)", 21) == 7.0                 # dolu sayısı
        assert sonuc(kitap, liste, "=ALTTOPLAM(9;B1:B9)", 22) == D.DEGER_HATASI      # hata yayılır
        assert sonuc(kitap, liste, "=ALTTOPLAM(99;B1:B6)", 23) == D.DEGER_HATASI     # geçersiz işlev no

    def test_birden_cok_aralik(self, kitap, liste):
        assert sonuc(kitap, liste, "=ALTTOPLAM(9;B1:B2;B5:B6)") == 14.0

    def test_filtre_kalkinca_geri_hesaplanir(self, kitap, liste):
        liste.ata(20, 1, ceviri.hucre_girdisi("=ALTTOPLAM(109;B1:B6)", kitap))
        y = GeriAlYigini()
        y.calistir(FiltreDegis(liste, Filtre(Aralik(1, 1, 6, 2), {2: IlkKosul(1)})))
        assert liste.deger(20, 1) == 1.0 + 6.0
        y.geri_al()
        assert liste.deger(20, 1) == 21.0


# ----------------------------------------------------------------------------------- .xlsx
class TestXlsx:
    def _kitap(self, f):
        k = CalismaKitabi()
        s = k.sayfalar[0]
        for r, (a, b) in enumerate([("Ad", "P"), ("Ali", 1.0), ("Ayşe", 2.0), ("Can", 3.0), ("Zeki", 4.0)], 1):
            s.ata(r, 1, Hucre(a))
            s.ata(r, 2, Hucre(b))
        FiltreDegis(s, f).yap()
        return k

    @pytest.mark.parametrize("kosul", [
        DegerKosulu(frozenset({"Ali", "Can"}), False),
        DegerKosulu(frozenset({"Ali"}), True),
        OzelKosul(("baslar", "a")),
        OzelKosul(("icermez", "an")),
        OzelKosul(("bitmez", "i")),
        OzelKosul(("buyuk_esit", 1.0), ("kucuk", 3.0)),
        OzelKosul(("esit", 1.0), ("esit", 4.0), ve=False),
        IlkKosul(2),
        IlkKosul(1, alt=True),
        IlkKosul(50, yuzde=True),
        OzelKosul(("esit_degil", "Can")),
    ])
    def test_gidis_donus(self, tmp_path, kosul):
        from tabcel.io import xlsx_io
        c = 2 if isinstance(kosul, (IlkKosul,)) or (isinstance(kosul, OzelKosul) and isinstance(kosul.k1[1], float)) else 1
        f = Filtre(Aralik(1, 1, 5, 2), {c: kosul})
        k = self._kitap(f)
        yol = str(tmp_path / "f.xlsx")
        xlsx_io.kaydet(k, yol)
        k2, rapor = xlsx_io.ac(yol)
        s2 = k2.sayfalar[0]
        assert s2.filtre == f and s2.gizli_satir == k.sayfalar[0].gizli_satir
        assert not rapor.uyarilar

    def test_ortalama_ve_filtresiz_dosya(self, tmp_path):
        from tabcel.io import xlsx_io
        from tabcel.model.filtre import OrtalamaKosulu
        f = Filtre(Aralik(1, 1, 5, 2), {2: OrtalamaKosulu(False)})
        k = self._kitap(f)
        yol = str(tmp_path / "a.xlsx")
        xlsx_io.kaydet(k, yol)
        assert xlsx_io.ac(yol)[0].sayfalar[0].filtre == f
        k0 = CalismaKitabi()
        xlsx_io.kaydet(k0, yol)
        assert xlsx_io.ac(yol)[0].sayfalar[0].filtre is None

    def test_kosulsuz_filtre_dugmesi_korunur(self, tmp_path):
        from tabcel.io import xlsx_io
        f = Filtre(Aralik(1, 1, 5, 2))
        yol = str(tmp_path / "k.xlsx")
        xlsx_io.kaydet(self._kitap(f), yol)
        assert xlsx_io.ac(yol)[0].sayfalar[0].filtre == f

    def test_renk_filtresi_uyarisi_gizlilik_kalir(self, tmp_path):
        from tabcel.io import xlsx_io
        f = Filtre(Aralik(1, 1, 5, 2), {1: RenkKosulu("dolgu", "#ff0000")})
        k = self._kitap(f)
        yol = str(tmp_path / "r.xlsx")
        rapor = xlsx_io.kaydet(k, yol)
        assert any("Renge göre" in u for u in rapor.uyarilar)
        s2 = xlsx_io.ac(yol)[0].sayfalar[0]
        assert s2.filtre.aralik == f.aralik and s2.filtre.kosullar == {}
        assert s2.gizli_satir == {2, 3, 4, 5}                               # satır gizliliği dosyada korunur
