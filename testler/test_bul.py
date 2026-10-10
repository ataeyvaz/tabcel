"""Faz 5 / 5b: Bul / Değiştir modeli (Qt'siz)."""
import time

import pytest

from tabcel.formul.ceviri import hucre_girdisi_akilli, hucre_metni
from tabcel.formul.fonksiyonlar.ortak import metin_deseni
from tabcel.formul.motor import Hesaplayici
from tabcel.model.adres import Aralik
from tabcel.model.bul import (
    BulSecenek, degistir_komutu, degistirme_plani, eslesmeler, gorunen_metin, joker_alt_dize,
    not_metni, yeni_metin,
)
from tabcel.model.komutlar import GeriAlYigini
from tabcel.model.sayfa import CalismaKitabi, Hucre


@pytest.fixture
def kitap():
    return CalismaKitabi()


@pytest.fixture
def sayfa(kitap):
    return kitap.sayfalar[0]


def metin_al(s, r, c, bakilan):
    if bakilan == "not":
        return not_metni(s, r, c)
    if bakilan == "deger":
        return gorunen_metin(s, r, c)
    return hucre_metni(s.hucre(r, c), s.kitap, s.stil(r, c).sayi_bicimi)


def coz(s, r, c, metin):
    h, kod = hucre_girdisi_akilli(metin, s.kitap)
    if kod is not None and s.stil(r, c).sayi_bicimi != "General":
        kod = None
    return h, kod


def bul(kitap, sayfa, metin, secim=None, baslangic=None, **kw):
    sec = BulSecenek(metin, **kw)
    return [(s.ad, r, c) for s, r, c in eslesmeler(kitap, sayfa, secim, sec, metin_al, baslangic)]


def doldur(sayfa, veri):
    for (r, c), v in veri.items():
        sayfa.ata(r, c, Hucre(v))


class TestJoker:
    def test_alt_dize_ve_buyuk_kucuk_turkce(self):
        f = joker_alt_dize("ışık")
        assert f("IŞIK lambası") and f("bir Işık") and not f("işık")
        assert joker_alt_dize("İZMİR")("izmir")

    def test_buyuk_kucuk_duyarli(self):
        f = joker_alt_dize("Ali", buyuk_kucuk=True)
        assert f("Ali Veli") and not f("ali veli")

    def test_jokerler(self):
        assert joker_alt_dize("a*c")("xxabbbcxx")
        assert joker_alt_dize("a?c")("abc") and not joker_alt_dize("a?c")("ac")
        assert joker_alt_dize("~*")("2*3") and not joker_alt_dize("~*")("23")
        assert joker_alt_dize("~?")("sor?") and not joker_alt_dize("~?")("sor")
        assert joker_alt_dize("~~")("a~b")

    def test_tam_hucre(self):
        f = joker_alt_dize("kalem", tam=True)
        assert f("Kalem") and not f("kalemlik")
        assert joker_alt_dize("k*m", tam=True)("kalem") and not joker_alt_dize("k*m", tam=True)("kalemx")

    def test_ortak_modulle_ayni_kurallar(self):
        # tam eşleşmede `metin_deseni` ile aynı karar
        for desen in ("a*c", "a?c", "~*x", "abc", "*", "?", "ı*", "İ?"):
            for s in ("abc", "ac", "abbc", "*x", "ax", "ıa", "ia", "", "İk", "ık"):
                assert joker_alt_dize(desen, tam=True)(s) == metin_deseni(desen)(s), (desen, s)


class TestEslesmeler:
    def test_sonraki_hucreden_baslar_ve_sarar(self, kitap, sayfa):
        doldur(sayfa, {(1, 1): "elma", (1, 3): "armut", (2, 2): "elma suyu", (4, 1): "Elma"})
        assert bul(kitap, sayfa, "elma") == [("Sayfa1", 1, 1), ("Sayfa1", 2, 2), ("Sayfa1", 4, 1)]
        assert bul(kitap, sayfa, "elma", baslangic=(1, 1)) == \
            [("Sayfa1", 2, 2), ("Sayfa1", 4, 1), ("Sayfa1", 1, 1)]
        assert bul(kitap, sayfa, "elma", baslangic=(3, 3)) == \
            [("Sayfa1", 4, 1), ("Sayfa1", 1, 1), ("Sayfa1", 2, 2)]

    def test_satir_ve_sutun_sirasi(self, kitap, sayfa):
        doldur(sayfa, {(1, 2): "x", (2, 1): "x", (1, 1): "x"})
        assert [(r, c) for _, r, c in bul(kitap, sayfa, "x")] == [(1, 1), (1, 2), (2, 1)]
        assert [(r, c) for _, r, c in bul(kitap, sayfa, "x", yon="sutun")] == [(1, 1), (2, 1), (1, 2)]

    def test_secimde_ara(self, kitap, sayfa):
        doldur(sayfa, {(1, 1): "a", (2, 2): "a", (5, 5): "a"})
        assert bul(kitap, sayfa, "a", secim=[Aralik(1, 1, 3, 3)]) == [("Sayfa1", 1, 1), ("Sayfa1", 2, 2)]
        # tek hücre seçimi = tüm sayfa
        assert len(bul(kitap, sayfa, "a", secim=[Aralik(2, 2, 2, 2)])) == 3
        # çoklu seçim
        assert len(bul(kitap, sayfa, "a", secim=[Aralik(1, 1, 1, 1), Aralik(5, 5, 6, 6)])) == 2

    def test_buyuk_kucuk_ve_tam_hucre(self, kitap, sayfa):
        doldur(sayfa, {(1, 1): "Elma", (2, 1): "elma", (3, 1): "elmalık"})
        assert len(bul(kitap, sayfa, "elma")) == 3
        assert bul(kitap, sayfa, "elma", buyuk_kucuk=True) == [("Sayfa1", 2, 1), ("Sayfa1", 3, 1)]
        assert len(bul(kitap, sayfa, "elma", tam_hucre=True)) == 2

    def test_bos_aranan_bir_sey_bulmaz(self, kitap, sayfa):
        doldur(sayfa, {(1, 1): "a"})
        assert bul(kitap, sayfa, "") == []

    def test_formul_modu_turkce_formul_metninde_arar(self, kitap, sayfa):
        sayfa.ata(1, 1, Hucre(None, "=SUM(B1:B3)"))
        sayfa.ata(2, 1, Hucre(5.0))
        Hesaplayici(kitap).tumunu_hesapla()
        assert bul(kitap, sayfa, "TOPLA") == [("Sayfa1", 1, 1)]        # Türkçe düzenleme metni
        assert bul(kitap, sayfa, "SUM") == []
        assert bul(kitap, sayfa, "0", bakilan="deger") == [("Sayfa1", 1, 1)]   # sonuç 0

    def test_deger_modu_gorunen_metin(self, kitap, sayfa):
        from tabcel.model.komutlar import bicim_komutu
        from tabcel.model.stil import StilYama
        sayfa.ata(1, 1, Hucre(1234.5))
        bicim_komutu(sayfa, [Aralik(1, 1, 1, 1)], StilYama(sayi_bicimi="#,##0.00")).yap()
        assert bul(kitap, sayfa, "1.234,50", bakilan="deger") == [("Sayfa1", 1, 1)]
        assert bul(kitap, sayfa, "1.234,50", bakilan="formul") == []   # düzenleme metni 1234,5
        assert bul(kitap, sayfa, "1234,5", bakilan="formul") == [("Sayfa1", 1, 1)]

    def test_not_modu(self, kitap, sayfa):
        sayfa.notlar = {(3, 3): "Dikkat: eksik", (1, 1): "tamam"}
        sayfa.ata(2, 2, Hucre("dikkat"))
        assert bul(kitap, sayfa, "dikkat", bakilan="not") == [("Sayfa1", 3, 3)]

    def test_birlesim_kapsanan_hucreler_atlanir(self, kitap, sayfa):
        sayfa.ata(1, 1, Hucre("x"))
        sayfa.ata(1, 2, Hucre("x"))             # birleşimin kapsadığı (normalde boş olurdu)
        sayfa.birlesimleri_yaz([Aralik(1, 1, 1, 3)], [])
        assert bul(kitap, sayfa, "x") == [("Sayfa1", 1, 1)]

    def test_kitap_kapsami_sayfa_sirasi(self, kitap, sayfa):
        s2, s3 = kitap.sayfa_ekle("S2"), kitap.sayfa_ekle("S3")
        sayfa.ata(1, 1, Hucre("k")); sayfa.ata(5, 5, Hucre("k"))
        s2.ata(1, 1, Hucre("k")); s3.ata(2, 2, Hucre("k"))
        r = bul(kitap, sayfa, "k", baslangic=(1, 1), kapsam="kitap")
        assert r == [("Sayfa1", 5, 5), ("S2", 1, 1), ("S3", 2, 2), ("Sayfa1", 1, 1)]
        r = bul(kitap, s2, "k", baslangic=(1, 1), kapsam="kitap")
        assert r == [("S3", 2, 2), ("Sayfa1", 1, 1), ("Sayfa1", 5, 5), ("S2", 1, 1)]
        # sayfa kapsamı yalnız kendi sayfası
        assert bul(kitap, s2, "k", kapsam="sayfa") == [("S2", 1, 1)]

    def test_yuz_bin_hucrede_hizli(self, kitap, sayfa):
        veri = {(r, c): Hucre(float(r * 100 + c)) for r in range(1, 5001) for c in range(1, 21)}
        sayfa.toplu_yaz(veri)
        t = time.perf_counter()
        sonuc = bul(kitap, sayfa, "12", bakilan="formul")
        gecen = time.perf_counter() - t
        assert sonuc and gecen < 1.5, f"{gecen:.2f} sn"                # ölçüt ≤ 1 sn; makine yükü payı


class TestYeniMetin:
    def sec(self, metin, **kw):
        return BulSecenek(metin, **kw)

    def test_her_eslesme_degisir_buyuk_kucuk_duyarsiz(self):
        assert yeni_metin("Elma ve elma", self.sec("elma"), "Armut") == "Armut ve Armut"
        assert yeni_metin("Işık", self.sec("ışık"), "x") == "x"
        assert yeni_metin("abc", self.sec("z"), "x") is None

    def test_buyuk_kucuk_duyarli(self):
        assert yeni_metin("Elma elma", self.sec("elma", buyuk_kucuk=True), "x") == "Elma x"

    def test_tam_hucre_tumunu_degistirir(self):
        assert yeni_metin("Elma", self.sec("elma", tam_hucre=True), "Armut") == "Armut"
        assert yeni_metin("Elmalık", self.sec("elma", tam_hucre=True), "Armut") is None

    def test_joker_ve_bos_yeni_metin(self):
        assert yeni_metin("a123b", self.sec("1*3"), "-") == "a-b"
        assert yeni_metin("a-b-c", self.sec("-"), "") == "abc"          # silme

    def test_yeni_metin_oldugu_gibi_joker_islenmez(self):
        assert yeni_metin("abc", self.sec("b"), "*?") == "a*?c"


class TestDegistir:
    def _calistir(self, kitap, sayfa, aranan, yeni, **kw):
        sec = BulSecenek(aranan, **kw)
        bulunan = list(eslesmeler(kitap, sayfa, None, sec, metin_al))
        plan, atlanan = degistirme_plani(bulunan, sec, yeni, metin_al, coz)
        return degistir_komutu(plan), atlanan

    def test_tumunu_degistir_tek_geri_al(self, kitap, sayfa):
        doldur(sayfa, {(1, 1): "elma", (2, 1): "Elma suyu", (3, 1): "armut"})
        yigin = GeriAlYigini()
        komut, atlanan = self._calistir(kitap, sayfa, "elma", "kiraz")
        yigin.calistir(komut)
        assert atlanan == 0
        assert [sayfa.deger(r, 1) for r in (1, 2, 3)] == ["kiraz", "kiraz suyu", "armut"]
        yigin.geri_al()
        assert [sayfa.deger(r, 1) for r in (1, 2, 3)] == ["elma", "Elma suyu", "armut"]
        yigin.yinele()
        assert sayfa.deger(1, 1) == "kiraz"

    def test_sayiya_donusur_elle_yazilmis_gibi(self, kitap, sayfa):
        doldur(sayfa, {(1, 1): "x5"})
        yigin = GeriAlYigini()
        komut, _ = self._calistir(kitap, sayfa, "x", "")
        yigin.calistir(komut)
        assert sayfa.deger(1, 1) == 5.0                               # metin "5" → sayı
        yigin.geri_al()
        assert sayfa.deger(1, 1) == "x5"

    def test_tarih_genel_hucreye_sayi_bicimi_oner(self, kitap, sayfa):
        doldur(sayfa, {(1, 1): "d"})
        yigin = GeriAlYigini()
        komut, _ = self._calistir(kitap, sayfa, "d", "12.10.2026", tam_hucre=True)
        yigin.calistir(komut)
        assert isinstance(sayfa.deger(1, 1), float)
        assert sayfa.stil(1, 1).sayi_bicimi != "General"
        yigin.geri_al()
        assert sayfa.stil(1, 1).sayi_bicimi == "General" and sayfa.deger(1, 1) == "d"

    def test_formulde_degistirir_ve_hesaplanir(self, kitap, sayfa):
        Hesaplayici(kitap)
        sayfa.ata(1, 1, Hucre(None, "=SUM(B1:B2)"))
        doldur(sayfa, {(1, 2): 1.0, (2, 2): 2.0, (1, 3): 10.0, (2, 3): 20.0})
        komut, atlanan = self._calistir(kitap, sayfa, "B", "C", bakilan="formul")
        komut.yap()
        assert atlanan == 0
        assert sayfa.hucre(1, 1).formul == "=SUM(C1:C2)"
        assert sayfa.deger(1, 1) == 30.0

    def test_gecersiz_formul_atlanir_ve_sayilir(self, kitap, sayfa):
        sayfa.ata(1, 1, Hucre(None, "=SUM(B1:B2)"))
        doldur(sayfa, {(2, 1): "TOPLA"})
        # "(" → "" formülü bozar; "TOPLA" metin hücresi sorunsuz değişir
        sec = BulSecenek("(")
        bulunan = list(eslesmeler(kitap, sayfa, None, sec, metin_al))
        plan, atlanan = degistirme_plani(bulunan, sec, "", metin_al, coz)
        assert atlanan == 1 and plan == {}
        komut, atlanan = self._calistir(kitap, sayfa, "TOPLA", "SUM", tam_hucre=True)
        assert atlanan == 0

    def test_not_ve_deger_modunda_degistirilmez(self, kitap, sayfa):
        doldur(sayfa, {(1, 1): "a"})
        sec = BulSecenek("a", bakilan="deger")
        bulunan = list(eslesmeler(kitap, sayfa, None, sec, metin_al))
        assert degistirme_plani(bulunan, sec, "b", metin_al, coz) == ({}, 0)
        assert degistir_komutu({}) is None

    def test_degisim_yoksa_komut_yok(self, kitap, sayfa):
        doldur(sayfa, {(1, 1): "a"})
        komut, _ = self._calistir(kitap, sayfa, "a", "a")
        assert komut is None

    def test_coklu_sayfa_tek_adim(self, kitap, sayfa):
        s2 = kitap.sayfa_ekle("S2")
        doldur(sayfa, {(1, 1): "x"}); doldur(s2, {(1, 1): "x"})
        yigin = GeriAlYigini()
        komut, _ = self._calistir(kitap, sayfa, "x", "y", kapsam="kitap")
        yigin.calistir(komut)
        assert sayfa.deger(1, 1) == "y" and s2.deger(1, 1) == "y"
        yigin.geri_al()
        assert sayfa.deger(1, 1) == "x" and s2.deger(1, 1) == "x"
