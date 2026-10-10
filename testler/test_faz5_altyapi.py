"""Faz 5 / 5a: ortak altyapı — aralık yardımcıları, Türkçe harmanlama, ağaç kaydırma, ek veri
depoları (+ ekle-sil + geri al), tanımlı ad deposu, `ek`/`ad` olayları (Qt'siz)."""
import random
import time
from dataclasses import dataclass, replace
from typing import Any, Dict, Tuple

import pytest

from tabcel.formul.agac import formul_ayristir, agac_kaydir, Sabit
from tabcel.formul.kaydir import ek_duzeltmeleri, kopyala
from tabcel.formul.motor import Hesaplayici
from tabcel.formul.sozcuk import FormulHatasi
from tabcel.model.ad import TanimliAd, ad_anahtari
from tabcel.model.adres import (
    MAX_COL, MAX_ROW, Aralik, aralik_cikar, aralik_kaydir, bitisik_bolge,
)
from tabcel.model.deger import BOL0, YOK, Hata
from tabcel.model.harmanla import deger_anahtari, metin_anahtari
from tabcel.model.komutlar import GeriAlYigini, SatirEkleSil, SutunEkleSil
from tabcel.model.sayfa import CalismaKitabi, Hucre


def A(r1, c1, r2, c2):
    return Aralik(r1, c1, r2, c2)


# ---------------------------------------------------------------- aralık yardımcıları
class TestAralikKaydir:
    def test_ekleme_oncesi_kaydirir_icine_buyutur_sonrasi_dokunmaz(self):
        ar = A(5, 2, 8, 4)
        assert aralik_kaydir(ar, 0, 1, 2, MAX_ROW) == A(7, 2, 10, 4)       # üstüne ekleme
        assert aralik_kaydir(ar, 0, 5, 2, MAX_ROW) == A(7, 2, 10, 4)       # ilk satıra ekleme: kayar
        assert aralik_kaydir(ar, 0, 6, 2, MAX_ROW) == A(5, 2, 10, 4)       # içine ekleme: büyür
        assert aralik_kaydir(ar, 0, 9, 2, MAX_ROW) == ar                    # altına ekleme: aynı
        assert aralik_kaydir(ar, 1, 3, 1, MAX_COL) == A(5, 2, 8, 5)         # sütun içine ekleme

    def test_silme_kucultur_kaydirir_tamamen_silineni_kaldirir(self):
        ar = A(5, 2, 8, 4)
        assert aralik_kaydir(ar, 0, 1, -2, MAX_ROW) == A(3, 2, 6, 4)        # üstten silme
        assert aralik_kaydir(ar, 0, 6, -2, MAX_ROW) == A(5, 2, 6, 4)        # içinden silme
        assert aralik_kaydir(ar, 0, 4, -2, MAX_ROW) == A(4, 2, 6, 4)        # baştan kısmen
        assert aralik_kaydir(ar, 0, 7, -5, MAX_ROW) == A(5, 2, 6, 4)        # sondan kısmen
        assert aralik_kaydir(ar, 0, 5, -4, MAX_ROW) is None                 # tamamı silindi
        assert aralik_kaydir(ar, 0, 1, -10, MAX_ROW) is None
        assert aralik_kaydir(ar, 1, 2, -3, MAX_COL) is None                 # sütunların tamamı

    def test_sayfa_sinirina_itilen(self):
        assert aralik_kaydir(A(MAX_ROW, 1, MAX_ROW, 1), 0, 1, 1, MAX_ROW) is None
        assert aralik_kaydir(A(MAX_ROW - 1, 1, MAX_ROW, 1), 0, 1, 1, MAX_ROW) == A(MAX_ROW, 1, MAX_ROW, 1)

    def test_tam_sutun_satir_korunur(self):
        tam = A(1, 3, MAX_ROW, 3)
        assert aralik_kaydir(tam, 0, 10, 4, MAX_ROW) == tam                 # tam sütun, satır ekleme: aynı
        assert aralik_kaydir(tam, 1, 1, 1, MAX_COL) == A(1, 4, MAX_ROW, 4)


class TestAralikCikar:
    def test_kesisim_yoksa_aynen(self):
        assert aralik_cikar(A(1, 1, 3, 3), A(5, 5, 6, 6)) == [A(1, 1, 3, 3)]

    def test_tamamen_ortulurse_bos(self):
        assert aralik_cikar(A(2, 2, 3, 3), A(1, 1, 5, 5)) == []

    def test_ortadan_delik_dort_parca(self):
        parcalar = aralik_cikar(A(1, 1, 5, 5), A(3, 3, 3, 3))
        assert len(parcalar) == 4
        kalan = {(r, c) for p in parcalar for r in range(p.ilk_satir, p.son_satir + 1)
                 for c in range(p.ilk_sutun, p.son_sutun + 1)}
        assert kalan == {(r, c) for r in range(1, 6) for c in range(1, 6)} - {(3, 3)}
        assert sum((p.son_satir - p.ilk_satir + 1) * (p.son_sutun - p.ilk_sutun + 1) for p in parcalar) == 24

    @pytest.mark.parametrize("a,b", [
        (A(1, 1, 5, 5), A(1, 1, 2, 2)), (A(1, 1, 5, 5), A(4, 4, 9, 9)), (A(2, 2, 6, 4), A(1, 3, 3, 9)),
        (A(1, 1, 4, 4), A(1, 2, 4, 3)), (A(1, 1, 4, 4), A(2, 1, 3, 4)),
    ])
    def test_alan_esitligi(self, a, b):
        def hucreler(x):
            return {(r, c) for r in range(x.ilk_satir, x.son_satir + 1)
                    for c in range(x.ilk_sutun, x.son_sutun + 1)}
        parcalar = aralik_cikar(a, b)
        birlesik = [h for p in parcalar for h in hucreler(p)]
        assert len(birlesik) == len(set(birlesik))                          # çakışma yok
        assert set(birlesik) == hucreler(a) - hucreler(b)


class TestBitisikBolge:
    def _sayfa(self, hucreler):
        k = CalismaKitabi()
        s = k.sayfalar[0]
        for r, c in hucreler:
            s.ata(r, c, Hucre(1.0))
        return s

    def test_tek_hucre(self):
        s = self._sayfa([(5, 5)])
        assert bitisik_bolge(s, 5, 5) == A(5, 5, 5, 5)

    def test_bos_hucre_komsusuz_kendisi(self):
        s = self._sayfa([(5, 5)])
        assert bitisik_bolge(s, 20, 20) == A(20, 20, 20, 20)

    def test_dikdortgen_tablo(self):
        s = self._sayfa([(r, c) for r in range(2, 8) for c in range(3, 6)])
        assert bitisik_bolge(s, 4, 4) == A(2, 3, 7, 5)
        assert bitisik_bolge(s, 2, 3) == A(2, 3, 7, 5)

    def test_capraz_komsu_dahil(self):
        s = self._sayfa([(1, 1), (2, 2), (3, 3)])
        assert bitisik_bolge(s, 1, 1) == A(1, 1, 3, 3)

    def test_bosluk_ayirir(self):
        s = self._sayfa([(1, 1), (1, 2), (4, 1), (4, 2)])
        assert bitisik_bolge(s, 1, 1) == A(1, 1, 1, 2)
        assert bitisik_bolge(s, 4, 2) == A(4, 1, 4, 2)

    def test_sayfa_kenarinda(self):
        s = self._sayfa([(1, 1), (1, 2), (2, 1)])
        assert bitisik_bolge(s, 1, 1) == A(1, 1, 2, 2)

    def test_bos_hucre_icinden_baslayinca(self):
        s = self._sayfa([(1, 1), (1, 3), (3, 1), (3, 3)])
        assert bitisik_bolge(s, 2, 2) == A(1, 1, 3, 3)


# ---------------------------------------------------------------- Türkçe harmanlama
def sirala(liste, **kw):
    return sorted(liste, key=lambda x: metin_anahtari(x, **kw))


class TestMetinAnahtari:
    def test_turkce_alfabe_sirasi(self):
        alfabe = list("abcçdefgğhıijklmnoöpqrsştuüvwxyz")
        assert sirala(list(reversed(alfabe))) == alfabe

    def test_ozel_harfler_komsu_harflerin_arasinda(self):
        assert sirala(["d", "ç", "z", "c"]) == ["c", "ç", "d", "z"]
        assert sirala(["i", "ı", "h", "j"]) == ["h", "ı", "i", "j"]
        assert sirala(["ü", "u", "v", "ö", "o", "p", "ş", "s", "t", "ğ", "g", "h"]) == \
            ["g", "ğ", "h", "o", "ö", "p", "s", "ş", "t", "u", "ü", "v"]

    def test_noktali_noktasiz_i_buyuk_harfler(self):
        # İ→i, I→ı: "Irmak" (ı...) "İzmir" (i...)'den ÖNCE gelir
        assert sirala(["İzmir", "Irmak", "Isparta", "Ankara"]) == ["Ankara", "Irmak", "Isparta", "İzmir"]
        assert metin_anahtari("I")[0] == metin_anahtari("ı")[0]
        assert metin_anahtari("İ")[0] == metin_anahtari("i")[0]

    def test_buyuk_kucuk_harf_birincil_olarak_esit(self):
        assert metin_anahtari("ABC") == metin_anahtari("abc")
        assert metin_anahtari("Çay")[0] == metin_anahtari("çay")[0]

    def test_buyuk_kucuk_duyarli_kucuk_once(self):
        assert sirala(["Ali", "ali", "ALİ"], buyuk_kucuk=True)[0] == "ali"
        assert sirala(["b", "A", "a", "B"], buyuk_kucuk=True) == ["a", "A", "b", "B"]

    def test_rakam_harften_once_noktalama_rakamdan_once(self):
        assert sirala(["a", "1", "_", " ", "9", "z"]) == [" ", "_", "1", "9", "a", "z"]
        assert sirala(["a1", "aa", "a#"]) == ["a#", "a1", "aa"]

    def test_rakamlar_metin_olarak_karakter_karakter(self):
        assert sirala(["10", "9", "1"]) == ["1", "10", "9"]

    def test_kisa_cizgi_ve_kesme_birincil_yok_sayilir(self):
        assert metin_anahtari("co-op")[0] == metin_anahtari("coop")[0]
        assert metin_anahtari("o'neil")[0] == metin_anahtari("oneil")[0]
        # eşitlikte çizgisiz önce
        assert sirala(["co-op", "coop"]) == ["coop", "co-op"]
        # ama çizgi sıralamayı harflerin önüne taşımaz
        assert sirala(["a-c", "ab"]) == ["ab", "a-c"]

    def test_aksanli_yabanci_harf_temel_harfle_esit_sonra(self):
        assert metin_anahtari("é")[0] == metin_anahtari("e")[0]
        assert sirala(["âb", "ab", "ac"]) == ["ab", "âb", "ac"]
        assert sirala(["î", "i", "j"]) == ["i", "î", "j"]

    def test_onek_kisa_once(self):
        assert sirala(["abc", "ab", "a", ""]) == ["", "a", "ab", "abc"]

    def test_gercek_isimler(self):
        girdi = ["Şule", "Selim", "Çağrı", "Cem", "Özlem", "Oya", "Ümit", "Uğur", "Ayşe", "Ali", "Gül", "Ğ", "Hakan"]
        assert sirala(girdi) == ["Ali", "Ayşe", "Cem", "Çağrı", "Gül", "Ğ", "Hakan", "Oya", "Özlem",
                                 "Selim", "Şule", "Uğur", "Ümit"]


class TestDegerAnahtari:
    KARISIK = [None, "metin", 5.0, True, BOL0, False, -3.0, "Abc", YOK, 0.0, "", None]

    def test_artan_duzen(self):
        s = sorted(self.KARISIK, key=lambda v: deger_anahtari(v, True))
        assert s[:3] == [-3.0, 0.0, 5.0]                                  # sayılar
        assert s[3:6] == ["", "Abc", "metin"]                             # metinler
        assert s[6:8] == [False, True]                                    # YANLIŞ < DOĞRU
        assert all(isinstance(x, Hata) for x in s[8:10])                  # hatalar
        assert s[10:] == [None, None]                                     # boş en sonda

    def test_azalan_duzen(self):
        s = sorted(self.KARISIK, key=lambda v: deger_anahtari(v, False))
        assert all(isinstance(x, Hata) for x in s[:2])
        assert s[2:4] == [True, False]
        assert s[4:7] == ["metin", "Abc", ""]
        assert s[7:10] == [5.0, 0.0, -3.0]
        assert s[10:] == [None, None]                                     # boş yine en sonda

    def test_hatalar_birbirine_esit_kararli(self):
        assert deger_anahtari(BOL0) == deger_anahtari(YOK)
        assert deger_anahtari(BOL0, False)[0] == deger_anahtari(YOK, False)[0]
        s = sorted([YOK, BOL0, YOK, BOL0], key=deger_anahtari)
        assert s == [YOK, BOL0, YOK, BOL0]                                # sıra korunur

    def test_metin_turkce_harmanla(self):
        s = sorted(["z", "ç", "d", "c"], key=deger_anahtari)
        assert s == ["c", "ç", "d", "z"]
        s = sorted(["z", "ç", "d", "c"], key=lambda v: deger_anahtari(v, False))
        assert s == ["z", "d", "ç", "c"]

    def test_sayi_onbes_basamak(self):
        assert deger_anahtari(0.1 + 0.2) == deger_anahtari(0.3)
        assert deger_anahtari(1.0) < deger_anahtari(1.0000001)

    def test_sayi_metinden_once_bool_sayidan_ayri(self):
        assert deger_anahtari(1.0) < deger_anahtari("1") < deger_anahtari(False) < deger_anahtari(True)

    def test_buyuk_kucuk_duyarli_metin(self):
        s = sorted(["B", "a", "b", "A"], key=lambda v: deger_anahtari(v, True, True))
        assert s == ["a", "A", "b", "B"]


# ---------------------------------------------------------------- agac_kaydir ⇔ kopyala
SABLONLAR = [
    "=A1", "=$A$1", "=$A1+B$2", "=SUM(A1:B5)", "=SUM($A$1:B5)", "=SUM(A1:$B$5)", "=A:A", "=$A:C",
    "=1:3", "=$1:$3", "=IF(A1>5,B2*2,C3)", "=-A1%+B1", "=A1&\"x\"&B2", "=SUM(A1:B2,C3,{1,2;3,4})",
    "=Sayfa!A1", "=[2]!B3+[2]!$C$4", "=A1:B2 B2:C3", "=MyAd+A1", "=VLOOKUP(A1,$B$1:$D$10,2,FALSE)",
    "=SUM(A1:INDEX(B:B,3))", "=#N/A+A1", "=IF(,A1,)",
]


def test_agac_kaydir_kopyala_ile_ayni_rastgele_formuller():
    rnd = random.Random(5)
    sayac = 0
    for _ in range(200):
        f = rnd.choice(SABLONLAR)
        # sayfa içinde ve dışında kalan kaymalar
        dr, dc = rnd.randint(-6, 8), rnd.randint(-4, 6)
        ag = formul_ayristir(f)
        try:
            beklenen = formul_ayristir(kopyala(f, dr, dc))
        except FormulHatasi:
            # metin yolu `#REF! B2:C3` (hata sözcüğü + kesişim) biçimini ayrıştıramaz; ağaç yolunun
            # bu durumda yine de #REF! düğümüyle kesişim kurduğunu denetle
            assert "#REF!" in kopyala(f, dr, dc)
            assert " " in f and agac_kaydir(ag, dr, dc) is not None
            continue
        assert agac_kaydir(ag, dr, dc) == beklenen, (f, dr, dc)
        sayac += 1
    assert sayac >= 170


def test_agac_kaydir_sayfa_disina_cikan_ref_hatasi():
    ag = formul_ayristir("=A1+B5")
    sonuc = agac_kaydir(ag, -1, 0)
    assert sonuc.a == Sabit(Hata("#REF!")) and sonuc.b.basvuru.r1 == 4
    sonuc = agac_kaydir(formul_ayristir("=XFD1"), 0, 1)
    assert sonuc == Sabit(Hata("#REF!"))


def test_agac_kaydir_degismeyeni_paylasir_ve_onbellekler():
    ag = formul_ayristir("=SUM($A$1:$B$2)+1")
    assert agac_kaydir(ag, 0, 0) is ag
    assert agac_kaydir(ag, 3, 4) == ag                                  # tamamı mutlak: eşit
    g1 = formul_ayristir("=A1*2+C3")
    assert agac_kaydir(g1, 1, 1) is agac_kaydir(g1, 1, 1)               # önbellek
    assert agac_kaydir(g1, 1, 1) is not agac_kaydir(g1, 2, 1)
    # paylaşım: değişmeyen alt ağaç aynı nesne
    g2 = formul_ayristir("=$A$1+B1")
    k = agac_kaydir(g2, 1, 0)
    assert k.a is g2.a and k.b is not g2.b


def test_agac_kaydir_hiz():
    ag = formul_ayristir("=A1>5")
    t = time.perf_counter()
    for i in range(1000):
        agac_kaydir(ag, i % 40, i // 40)
    gecen = time.perf_counter() - t
    assert gecen < 0.05, f"1000 kaydırma {gecen * 1000:.1f} ms"       # hedef ≤ 10 ms; makine yükü için gevşek


# ---------------------------------------------------------------- ek veri depoları
@dataclass(frozen=True)
class Kural:
    araliklar: Tuple[Aralik, ...]
    ad: str = "k"
    formul1: Any = None


@dataclass(frozen=True)
class FiltreT:
    aralik: Aralik
    kosullar: Dict[int, Any]

    def __hash__(self):
        return hash((self.aralik, tuple(sorted(self.kosullar))))


@pytest.fixture
def kitap():
    return CalismaKitabi()


@pytest.fixture
def sayfa(kitap):
    return kitap.sayfalar[0]


def olaylari_topla(kitap):
    liste = []
    kitap.dinle(liste.append)
    return liste


class TestEkVeriKaydirma:
    def test_notlar_satir_ekle_sil(self, sayfa):
        sayfa.notlar = {(3, 2): "a", (6, 2): "b", (8, 4): "c"}
        sayfa.satir_ekle(5, 2)
        assert sayfa.notlar == {(3, 2): "a", (8, 2): "b", (10, 4): "c"}
        assert sayfa.silinen_notlar == {}
        sayfa.satir_sil(7, 2)                                  # 7-8 silinir: "b" (8,2) gider
        assert sayfa.notlar == {(3, 2): "a", (8, 4): "c"}
        assert sayfa.silinen_notlar == {(8, 2): "b"}

    def test_notlar_sutun_ekle_sil(self, sayfa):
        sayfa.notlar = {(1, 2): "a", (1, 5): "b"}
        sayfa.sutun_ekle(3, 1)
        assert sayfa.notlar == {(1, 2): "a", (1, 6): "b"}
        sayfa.sutun_sil(2, 1)
        assert sayfa.notlar == {(1, 5): "b"} and sayfa.silinen_notlar == {(1, 2): "a"}

    def test_dogrulama_ve_kosullu_araliklari_kayar_buyur_kuculur_duser(self, sayfa):
        sayfa.dogrulamalar = [Kural((A(2, 1, 5, 1),), "d1"), Kural((A(10, 1, 12, 1), A(20, 3, 20, 3)), "d2")]
        sayfa.kosullu = [Kural((A(4, 1, 6, 2),), "k1")]
        sayfa.satir_ekle(3, 2)                                 # d1 içine ekleme büyür; d2 ve k1 ... k1 içine
        assert sayfa.dogrulamalar[0].araliklar == (A(2, 1, 7, 1),)
        assert sayfa.dogrulamalar[1].araliklar == (A(12, 1, 14, 1), A(22, 3, 22, 3))
        assert sayfa.kosullu[0].araliklar == (A(6, 1, 8, 2),)
        sayfa.satir_sil(10, 5)                                 # d2'nin 12-14'ü (10-14 silinir) → tamamen gider; 22→17
        assert len(sayfa.dogrulamalar[1].araliklar) == 1
        assert sayfa.dogrulamalar[1].araliklar == (A(17, 3, 17, 3),)

    def test_araligi_kalmayan_kural_duser(self, sayfa):
        sayfa.dogrulamalar = [Kural((A(3, 1, 4, 1),)), Kural((A(9, 1, 9, 1),))]
        sayfa.satir_sil(3, 2)
        assert [k.araliklar for k in sayfa.dogrulamalar] == [(A(7, 1, 7, 1),)]

    def test_filtre_araligi_kayar_baslik_silinirse_kalkar(self, sayfa):
        sayfa.filtre = FiltreT(A(3, 1, 10, 4), {2: "x", 4: "y"})
        sayfa.satir_ekle(1, 1)
        assert sayfa.filtre.aralik == A(4, 1, 11, 4)
        sayfa.satir_ekle(8, 3)                                 # içine ekleme: büyür
        assert sayfa.filtre.aralik == A(4, 1, 14, 4)
        sayfa.sutun_sil(1, 1)                                  # sütun: aralık küçülür, koşul anahtarları kayar
        assert sayfa.filtre.aralik == A(4, 1, 14, 3) and sorted(sayfa.filtre.kosullar) == [1, 3]
        sayfa.sutun_sil(1, 1)                                  # koşul sütunu 1 silinir
        assert sorted(sayfa.filtre.kosullar) == [2]
        sayfa.satir_sil(5, 3)                                  # veri satırları silinir: filtre durur
        assert sayfa.filtre.aralik.ilk_satir == 4 and sayfa.filtre is not None
        sayfa.satir_sil(4, 1)                                  # başlık satırı silinir
        assert sayfa.filtre is None

    def test_filtre_tamamen_silinirse_kalkar(self, sayfa):
        sayfa.filtre = FiltreT(A(3, 2, 6, 3), {})
        sayfa.sutun_sil(2, 2)
        assert sayfa.filtre is None

    def test_ek_veri_yoksa_maliyetsiz_ve_hatasiz(self, sayfa):
        sayfa.satir_ekle(1, 1)
        sayfa.sutun_sil(1, 1)
        assert sayfa.notlar == {} and sayfa.dogrulamalar == [] and sayfa.kosullu == [] and sayfa.filtre is None


class TestEkDurumu:
    def test_gidis_donus(self, sayfa):
        sayfa.notlar = {(1, 1): "n"}
        sayfa.dogrulamalar = [Kural((A(1, 1, 2, 2),))]
        sayfa.kosullu = [Kural((A(3, 3, 4, 4),))]
        sayfa.filtre = FiltreT(A(1, 1, 5, 5), {})
        durum = sayfa.ek_durumu()
        sayfa.satir_ekle(1, 3)
        sayfa.notlar[(9, 9)] = "z"
        assert sayfa.ek_durumu() != durum
        sayfa.ek_durumu_yukle(durum)
        assert sayfa.notlar == {(1, 1): "n"}
        assert sayfa.dogrulamalar[0].araliklar == (A(1, 1, 2, 2),)
        assert sayfa.kosullu[0].araliklar == (A(3, 3, 4, 4),)
        assert sayfa.filtre.aralik == A(1, 1, 5, 5)

    def test_durum_kopyadir(self, sayfa):
        sayfa.notlar = {(1, 1): "n"}
        durum = sayfa.ek_durumu()
        sayfa.notlar[(2, 2)] = "m"
        sayfa.dogrulamalar.append(Kural((A(1, 1, 1, 1),)))
        assert durum[0] == {(1, 1): "n"} and durum[1] == []

    def test_yukle_tek_ek_olayi_degismediyse_olay_yok(self, kitap, sayfa):
        sayfa.notlar = {(1, 1): "n"}
        durum = sayfa.ek_durumu()
        olaylar = olaylari_topla(kitap)
        sayfa.ek_durumu_yukle(durum)
        assert olaylar == []                                   # aynı durum: olay yok
        sayfa.notlar = {}
        sayfa.dogrulamalar = [Kural((A(1, 1, 1, 1),))]
        sayfa.ek_durumu_yukle(durum)
        ek = [o for o in olaylar if o.tur == "ek"]
        assert len(ek) == 1 and ek[0]["alan"] == "hepsi" and ek[0].sayfa is sayfa
        assert (1, 1) in ek[0]["anahtarlar"]


class TestAdDeposu:
    def test_kapsam_onceligi_ve_buyuk_kucuk_duyarsiz(self, kitap):
        s2 = kitap.sayfa_ekle("Ikinci")
        kitap.ad_yaz(TanimliAd("Oran", "=0.18"))
        kitap.ad_yaz(TanimliAd("ORAN", "=0.08", kapsam=s2.kimlik))
        assert kitap.ad_bul("oran", s2.kimlik).formul == "=0.08"              # sayfa kapsamı önce
        assert kitap.ad_bul("oran", kitap.sayfalar[0].kimlik).formul == "=0.18"
        assert kitap.ad_bul("ORAN").formul == "=0.18"
        assert kitap.ad_bul("yok") is None

    def test_turkce_buyuk_kucuk(self, kitap):
        kitap.ad_yaz(TanimliAd("Işık", "=1"))
        assert kitap.ad_bul("ışık") is not None
        assert kitap.ad_bul("IŞIK") is not None
        assert kitap.ad_bul("işik") is None                    # i ≠ ı
        assert ad_anahtari(None, "İZ") == (None, "iz")

    def test_silinen_sayfanin_kapsamli_adi_gorunmez_geri_gelince_doner(self, kitap):
        s2 = kitap.sayfa_ekle("Ikinci")
        kimlik = s2.kimlik
        kitap.ad_yaz(TanimliAd("Yerel", "=5", kapsam=kimlik))
        assert kitap.ad_bul("yerel", kimlik) is not None
        indeks = kitap.sayfa_sil(s2)
        assert kitap.sayfa_kimlikle(kimlik) is None
        assert kitap.ad_bul("yerel", kitap.sayfalar[0].kimlik) is None
        assert len(kitap.adlar) == 1                           # silinmedi
        kitap.sayfa_geri_koy(s2, indeks)
        assert kitap.ad_bul("yerel", s2.kimlik).formul == "=5"

    def test_ad_olaylari(self, kitap):
        olaylar = olaylari_topla(kitap)
        a = TanimliAd("X", "=1")
        kitap.ad_yaz(a)
        kitap.ad_yaz(a)                                        # aynı: olay yok
        b = replace(a, formul="=2")
        kitap.ad_yaz(b)
        kitap.ad_yaz(None, a.anahtar())
        kitap.ad_yaz(None, a.anahtar())                        # zaten yok: olay yok
        ad_olaylari = [o for o in olaylar if o.tur == "ad"]
        assert [(o["eski"], o["yeni"]) for o in ad_olaylari] == [(None, a), (a, b), (b, None)]
        assert all(o.sayfa is None for o in ad_olaylari)

    def test_yeniden_adlandirma_eski_anahtari_kaldirir(self, kitap):
        a = TanimliAd("Eski", "=1")
        kitap.ad_yaz(a)
        kitap.ad_yaz(replace(a, ad="Yeni"), a.anahtar())
        assert kitap.ad_bul("eski") is None and kitap.ad_bul("yeni").formul == "=1"

    def test_durum_yukle(self, kitap):
        kitap.ad_yaz(TanimliAd("A1x", "=1"))
        durum = kitap.ad_durumu()
        kitap.ad_yaz(TanimliAd("B", "=2"))
        kitap.ad_yaz(TanimliAd("A1x", "=9"))
        olaylar = olaylari_topla(kitap)
        kitap.ad_durumu_yukle(durum)
        assert kitap.ad_bul("a1x").formul == "=1" and kitap.ad_bul("b") is None
        assert len([o for o in olaylar if o.tur == "ad"]) == 2

    def test_ad_olayi_motoru_yeniden_hesaplatir_ve_ek_yok_sayilir(self, kitap, sayfa):
        motor = Hesaplayici(kitap)
        sayfa.ata(1, 1, Hucre(None, "=1+1"))
        motor.tumunu_hesapla()
        cagrilar = []
        asil = motor.tumunu_hesapla
        motor.tumunu_hesapla = lambda: (cagrilar.append(1), asil())[1]
        kitap.ad_yaz(TanimliAd("Z", "=3"))                     # sayfa=None olayı patlamadan işlenir
        assert cagrilar == [1]
        sayfa.ek_durumu_yukle(({(1, 1): "n"}, [], [], None))   # ek: motor yok sayar
        assert cagrilar == [1]
        assert sayfa.deger(1, 1) == 2.0


class TestEkKomutlari:
    """Satır/sütun ekle-sil komutu ek verileri geri almada aynen yükler; formülleri düzeltir."""

    def test_satir_ekle_geri_al_yinele(self, kitap, sayfa):
        sayfa.notlar = {(5, 1): "n"}
        sayfa.dogrulamalar = [Kural((A(2, 1, 8, 1),), formul1="=$A$10")]
        sayfa.kosullu = [Kural((A(1, 1, 3, 3),), formul1="=A1>5")]
        sayfa.filtre = FiltreT(A(1, 1, 8, 3), {2: "x"})
        yigin = GeriAlYigini()
        once = sayfa.ek_durumu()
        yigin.calistir(SatirEkleSil(sayfa, 3, 2, True))
        assert sayfa.notlar == {(7, 1): "n"}
        assert sayfa.dogrulamalar[0].araliklar == (A(2, 1, 10, 1),)
        assert sayfa.dogrulamalar[0].formul1 == "=$A$12"       # formül başvurusu da kaydı
        assert sayfa.filtre.aralik == A(1, 1, 10, 3)
        yigin.geri_al()
        assert sayfa.ek_durumu() == once
        yigin.yinele()
        assert sayfa.notlar == {(7, 1): "n"} and sayfa.dogrulamalar[0].formul1 == "=$A$12"
        yigin.geri_al()
        assert sayfa.ek_durumu() == once

    def test_satir_sil_geri_al_silinen_notu_ve_kurali_geri_getirir(self, kitap, sayfa):
        sayfa.notlar = {(4, 2): "silinecek", (9, 2): "kalacak"}
        sayfa.dogrulamalar = [Kural((A(3, 1, 5, 1),)), Kural((A(9, 1, 9, 1),))]
        sayfa.filtre = FiltreT(A(3, 1, 8, 2), {})
        yigin = GeriAlYigini()
        once = sayfa.ek_durumu()
        yigin.calistir(SatirEkleSil(sayfa, 3, 3, False))       # 3-5 silinir
        assert sayfa.notlar == {(6, 2): "kalacak"} and sayfa.silinen_notlar == {(4, 2): "silinecek"}
        assert len(sayfa.dogrulamalar) == 1 and sayfa.filtre is None
        yigin.geri_al()
        assert sayfa.ek_durumu() == once

    def test_sutun_komutu_ad_formullerini_duzeltir_ve_geri_alir(self, kitap, sayfa):
        kid = sayfa.kimlik
        kitap.ad_yaz(TanimliAd("Fiyat", f"=[{kid}]!$C$2:$D$9"))
        kitap.ad_yaz(TanimliAd("Sabit", "=0.18"))
        kitap.ad_yaz(TanimliAd("Yerel", f"=[{kid}]!$B$1", kapsam=kid))
        once = kitap.ad_durumu()
        yigin = GeriAlYigini()
        yigin.calistir(SutunEkleSil(sayfa, 2, 1, True))
        assert kitap.ad_bul("fiyat").formul == f"=[{kid}]!$D$2:$E$9"
        assert kitap.ad_bul("sabit").formul == "=0.18"
        assert kitap.ad_bul("yerel", kid).formul == f"=[{kid}]!$C$1"
        yigin.geri_al()
        assert kitap.ad_durumu() == once
        yigin.calistir(SutunEkleSil(sayfa, 3, 2, False))       # C-D silinir → #REF!
        assert "#REF!" in kitap.ad_bul("fiyat").formul
        yigin.geri_al()
        assert kitap.ad_durumu() == once

    def test_baska_sayfadaki_dogrulama_formulu_de_duzelir(self, kitap, sayfa):
        s2 = kitap.sayfa_ekle("Ikinci")
        s2.dogrulamalar = [Kural((A(1, 1, 3, 1),), formul1=f"=[{sayfa.kimlik}]!$A$1:$A$5")]
        yigin = GeriAlYigini()
        yigin.calistir(SatirEkleSil(sayfa, 2, 1, True))
        assert s2.dogrulamalar[0].formul1 == f"=[{sayfa.kimlik}]!$A$1:$A$6"
        yigin.geri_al()
        assert s2.dogrulamalar[0].formul1 == f"=[{sayfa.kimlik}]!$A$1:$A$5"

    def test_ek_duzeltmeleri_degisiklik_yoksa_false(self, kitap, sayfa):
        assert ek_duzeltmeleri(kitap, sayfa, "satir", 1, 1) is False
        sayfa.dogrulamalar = [Kural((A(1, 1, 1, 1),), formul1="=10")]
        assert ek_duzeltmeleri(kitap, sayfa, "satir", 1, 1) is False


def test_birlesim_davranisi_degismedi(sayfa):
    """`_birlesimleri_kaydir` artık `aralik_kaydir` kullanır; mevcut davranış aynı."""
    sayfa.birlesimleri_yaz([A(2, 2, 3, 4)], [])
    sayfa.satir_ekle(3, 1)
    assert sayfa.birlesimler == [A(2, 2, 4, 4)]
    sayfa.satir_sil(2, 2)
    assert sayfa.birlesimler == [A(2, 2, 2, 4)]
    sayfa.satir_sil(2, 1)
    assert sayfa.birlesimler == []
    sayfa.birlesimleri_yaz([A(1, 1, 2, 2)], [])
    sayfa.satir_sil(1, 1)                                       # tek satıra iner → 1x2 hâlâ birleşim
    assert sayfa.birlesimler == [A(1, 1, 1, 2)]
    sayfa.sutun_sil(2, 1)                                       # tek hücreye iner → kalkar
    assert sayfa.birlesimler == []


# ---------------------------------------------------------------- arayüz iskeleti (Düzen / Veri menüleri)
def test_duzen_ve_veri_menu_iskeleti_ve_olaylar_pencereyi_bozmaz():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from tabcel.ui.window import Pencere
    app = QApplication.instance() or QApplication([])
    k = CalismaKitabi()
    p = Pencere(k)
    try:
        assert p.duzen_dugmesi.text() == "Düzen" and p.veri_dugmesi.text() == "Veri"
        assert set(p.duzen_eylemleri) == {"bul", "degistir", "git"}
        assert {"artan", "azalan", "ozel_sirala", "filtre", "filtre_temizle", "filtre_yeniden",
                "dogrulama", "ad_tanimla", "ad_yoneticisi"} <= set(p.veri_eylemleri)
        assert all(not e.isEnabled() for e in p.duzen_eylemleri.values())     # 5b…5g bağlayıp açar
        # None sayfalı `ad` ve `ek` olayları pencereyi/motoru bozmaz
        s = k.sayfalar[0]
        s.ata(1, 1, Hucre(None, "=1+2"))
        k.ad_yaz(TanimliAd("Z", "=1"))
        s.ek_durumu_yukle(({(1, 1): "n"}, [], [], None))
        app.processEvents()
        assert s.deger(1, 1) == 3.0
    finally:
        p.close()
