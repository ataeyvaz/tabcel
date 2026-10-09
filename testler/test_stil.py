"""Faz 3 / 3a: stil modeli, havuz, Sayfa stil depoları, bicim olayı, BicimDegis, ekle-sil (Qt yok)."""
import time

import pytest

from tabcel.model.adres import MAX_COL, MAX_ROW, AdresHatasi, Aralik
from tabcel.model.komutlar import (BicimDegis, GeriAlYigini, SatirEkleSil, SutunEkleSil, ana_sayfa,
                                   bicim_komutu)
from tabcel.model.sayfa import CalismaKitabi, Hucre, Sayfa
from tabcel.model.stil import Kenarlik, Stil, StilHavuzu, StilYama

KALIN = StilYama(kalin=True)
SARI = StilYama(dolgu="#ffff00")


@pytest.fixture
def kitap():
    return CalismaKitabi()


@pytest.fixture
def s(kitap):
    return kitap.sayfalar[0]


def olaylar(kitap):
    liste = []
    kitap.dinle(liste.append)
    return liste


# ------------------------------------------------------------ Stil / StilYama / havuz
def test_stil_varsayilanlari_excel_gibi():
    st = Stil()
    assert (st.kalin, st.italik, st.alti_cizili, st.yatay, st.dikey, st.girinti, st.kaydir) == \
        (False, False, "yok", "genel", "alt", 0, False)
    assert st.sayi_bicimi == "General" and st.varsayilan_mi() and st.kenar.bos_mu()


def test_stil_dogrulama_ve_renk_normallestirme():
    assert Stil(yazi_rengi="#ff0000").yazi_rengi == "#FF0000"
    for kotu in (dict(yatay="x"), dict(dikey="x"), dict(alti_cizili="x"), dict(girinti=16),
                 dict(dolgu="kırmızı"), dict(boyut=0), dict(sayi_bicimi="")):
        with pytest.raises(ValueError):
            Stil(**kotu)
    with pytest.raises(ValueError):
        Kenarlik(ust=("yok_boyle", "#000000"))


def test_stil_yama_kismi_ve_kenar_birlestirme():
    st = Stil(kalin=True, kenar=Kenarlik(sol=("ince", "#000000")))
    y = StilYama(italik=True, kenar={"ust": ("kalin", "#ff0000")})
    yeni = y.uygula(st)
    assert yeni.kalin and yeni.italik                       # eski alan korunur
    assert yeni.kenar.sol == ("ince", "#000000")            # adı geçmeyen kenar korunur
    assert yeni.kenar.ust == ("kalin", "#FF0000")
    assert StilYama(kenar={"sol": None}).uygula(yeni).kenar.sol is None
    with pytest.raises(ValueError):
        StilYama(bilinmeyen=1)
    with pytest.raises(ValueError):
        StilYama(kenar={"yukari": ("ince", "#000000")})


def test_stil_yama_hash_ve_esitlik():
    assert StilYama(kalin=True, italik=True) == StilYama(italik=True, kalin=True)
    assert len({StilYama(kalin=True), StilYama(kalin=True), StilYama(italik=True)}) == 2


def test_havuz_interning_ve_yama_onbellegi():
    h = StilHavuzu()
    assert h.kimlik(Stil()) == 0 and len(h) == 1
    a = h.kimlik(Stil(kalin=True))
    assert a == h.kimlik(Stil(kalin=True)) == 1 and len(h) == 2
    assert h.yama_uygula(0, KALIN) == a                      # aynı stil → aynı kimlik
    assert h.yama_uygula(a, KALIN) == a                      # zaten kalın
    b = h.yama_uygula(a, SARI)
    assert h.stil(b) == Stil(kalin=True, dolgu="#FFFF00")
    assert h.yama_uygula(a, SARI) == b


# ------------------------------------------------------------ Sayfa: etkin stil önceliği
def test_etkin_stil_hucre_satir_sutun_sirasi(s):
    k_hucre = s.havuz.kimlik(Stil(kalin=True))
    k_satir = s.havuz.kimlik(Stil(italik=True))
    k_sutun = s.havuz.kimlik(Stil(dolgu="#00FF00"))
    s.bicim_yaz(sutunlar={2: k_sutun})
    assert s.stil_kimligi(5, 2) == k_sutun and s.stil_kimligi(5, 3) == 0
    s.bicim_yaz(satirlar={5: k_satir})
    assert s.stil_kimligi(5, 2) == k_satir                   # satır sütunu ezer
    s.bicim_yaz(hucreler={(5, 2): k_hucre})
    assert s.stil_kimligi(5, 2) == k_hucre                   # hücre hepsini ezer
    assert s.stil(5, 2).kalin and s.stil(6, 2).dolgu == "#00FF00"
    assert s.ham_stil_kimligi(5, 3) is None and s.ham_stil_kimligi(5, 2) == k_hucre


def test_acik_varsayilan_hucre_satir_stilini_ezer(s):
    k = s.havuz.kimlik(Stil(kalin=True))
    s.bicim_yaz(satirlar={3: k})
    s.bicim_yaz(hucreler={(3, 4): 0})                        # Biçimleri temizle (satır biçimliyken)
    assert s.stil_kimligi(3, 4) == 0 and s.stil_kimligi(3, 5) == k
    s.bicim_yaz(hucreler={(9, 9): 0})                        # satır/sütun stili yok: kayıt tutulmaz
    assert s.ham_stil_kimligi(9, 9) is None


def test_bicim_yaz_aralik_disi_hata(s):
    with pytest.raises(AdresHatasi):
        s.bicim_yaz(hucreler={(0, 1): 1})
    with pytest.raises(AdresHatasi):
        s.bicim_yaz(satirlar={MAX_ROW + 1: 1})


# ------------------------------------------------------------ olay
def test_toplu_bicim_tek_olay_ve_degismeyen_olay_yok(kitap, s):
    olay = olaylar(kitap)
    k = s.havuz.kimlik(Stil(kalin=True))
    s.bicim_yaz({(r, c): k for r in range(1, 11) for c in range(1, 4)}, {2: k}, {7: k})
    assert len(olay) == 1 and olay[0].tur == "bicim"
    assert len(olay[0]["degisiklikler"]) == 30 and olay[0]["satir"] == {2: (None, k)}
    assert olay[0]["sutun"] == {7: (None, k)}
    assert olay[0]["degisiklikler"][(1, 1)] == (None, k)
    s.bicim_yaz({(1, 1): k})                                 # değişmedi → olay yok
    assert len(olay) == 1


def test_bicim_olayi_formul_motorunu_ve_hucre_olayini_tetiklemez(kitap, s):
    from tabcel.formul.motor import Hesaplayici
    Hesaplayici(kitap)
    s.ata(1, 1, Hucre(None, "=1+1"))
    olay = olaylar(kitap)
    s.bicim_yaz({(1, 1): s.havuz.kimlik(Stil(kalin=True))})
    assert [o.tur for o in olay] == ["bicim"] and s.deger(1, 1) == 2.0
    s.ata(1, 1, None)                                        # içeriği sil: biçim kalır (Delete)
    assert s.stil(1, 1).kalin


def test_bicim_degis_komutu_geri_al_yinele(kitap, s):
    y = GeriAlYigini()
    k = s.havuz.kimlik(Stil(kalin=True))
    y.calistir(BicimDegis(s, hucreler={(1, 1): k}, satirlar={4: k}, sutunlar={3: k}))
    assert s.stil(1, 1).kalin and s.stil(4, 9).kalin and s.stil(9, 3).kalin
    y.geri_al()
    assert s.stil_kimligi(1, 1) == 0 and not s._stil and not s.satir_stil and not s.sutun_stil
    y.yinele()
    assert s.stil(1, 1).kalin and s.satir_stil == {4: k}
    assert ana_sayfa(BicimDegis(s)) is s


# ------------------------------------------------------------ bicim_komutu
def test_bicim_komutu_aralik_ve_coklu_secim(s):
    y = GeriAlYigini()
    y.calistir(bicim_komutu(s, [Aralik(2, 2, 3, 3), Aralik(10, 10, 10, 10)], KALIN))
    assert all(s.stil(r, c).kalin for r in (2, 3) for c in (2, 3)) and s.stil(10, 10).kalin
    assert not s.stil(4, 4).kalin and len(s._stil) == 5
    y.calistir(bicim_komutu(s, [Aralik(2, 2, 3, 3)], KALIN))      # zaten kalın: boş komut
    assert len(s._stil) == 5
    y.geri_al(); y.geri_al()
    assert not s._stil


def test_bicim_komutu_kismi_yama_mevcut_stili_korur(s):
    y = GeriAlYigini()
    y.calistir(bicim_komutu(s, [Aralik(1, 1, 1, 1)], KALIN))
    y.calistir(bicim_komutu(s, [Aralik(1, 1, 1, 2)], SARI))
    assert s.stil(1, 1) == Stil(kalin=True, dolgu="#FFFF00") and s.stil(1, 2) == Stil(dolgu="#FFFF00")


def test_bicim_komutu_tam_satir_ve_sutun_stile_yazilir(s):
    y = GeriAlYigini()
    s.ata(5, 3, Hucre(1.0))
    y.calistir(bicim_komutu(s, [Aralik(5, 1, 5, MAX_COL)], KALIN))       # tam satır
    assert s.satir_stil and not s._stil and s.stil(5, 100).kalin and not s.stil(6, 1).kalin
    y.calistir(bicim_komutu(s, [Aralik(1, 2, MAX_ROW, 2)], SARI))         # tam sütun
    assert list(s.sutun_stil) == [2]
    # satır biçimli: kesişimde SON uygulanan (sütun) kazanır → açık kayıt, kalın korunur
    assert s.stil(5, 2) == Stil(kalin=True, dolgu="#FFFF00")
    assert s.stil(7, 2).dolgu == "#FFFF00" and not s.stil(7, 2).kalin
    y.geri_al(); y.geri_al()
    assert not s.satir_stil and not s.sutun_stil and not s._stil


def test_bicim_komutu_tam_satir_acik_kayitli_hucreye_de_uygular(s):
    y = GeriAlYigini()
    y.calistir(bicim_komutu(s, [Aralik(2, 2, 2, 2)], SARI))
    y.calistir(bicim_komutu(s, [Aralik(2, 1, 2, MAX_COL)], KALIN))
    assert s.stil(2, 2) == Stil(kalin=True, dolgu="#FFFF00") and s.stil(2, 9) == Stil(kalin=True)


def test_bicim_komutu_asiri_buyuk_aralik_reddedilir(s):
    with pytest.raises(AdresHatasi):
        bicim_komutu(s, [Aralik(1, 1, 100_000, 100)], KALIN)


def test_100000_hucreye_yama_hizli(s):
    t0 = time.perf_counter()
    kmt = bicim_komutu(s, [Aralik(1, 1, 5000, 20)], KALIN)
    y = GeriAlYigini()
    y.calistir(kmt)
    gecen = time.perf_counter() - t0
    assert len(s._stil) == 100_000 and gecen < 1.5          # hedef 0,3 sn; yavaş makineye pay
    y.geri_al()
    assert not s._stil


# ------------------------------------------------------------ ekle-sil
def test_satir_ekle_ustteki_biclimi_devralir_ve_alttakiler_kayar(s):
    y = GeriAlYigini()
    y.calistir(bicim_komutu(s, [Aralik(2, 1, 2, 3)], KALIN))
    y.calistir(bicim_komutu(s, [Aralik(3, 1, 3, 1)], SARI))
    y.calistir(SatirEkleSil(s, 3, 2, True))                  # 3. satırdan önce 2 satır
    assert all(s.stil(r, 2).kalin for r in (2, 3, 4)) and s.stil(3, 3).kalin   # devralındı
    assert s.stil(5, 1).dolgu == "#FFFF00" and not s.stil(5, 2).kalin          # eski 3. satır 5'e kaydı
    y.geri_al()
    assert s.stil(3, 1).dolgu == "#FFFF00" and not s.stil(4, 1).kalin and len(s._stil) == 4
    y.yinele()
    assert s.stil(5, 1).dolgu == "#FFFF00"


def test_ilk_satira_ekleme_devralmaz(s):
    y = GeriAlYigini()
    y.calistir(bicim_komutu(s, [Aralik(1, 1, 1, 1)], KALIN))
    y.calistir(SatirEkleSil(s, 1, 1, True))
    assert not s.stil(1, 1).kalin and s.stil(2, 1).kalin


def test_satir_stili_ekle_sil_ile_kayar_ve_devralinir(s):
    y = GeriAlYigini()
    y.calistir(bicim_komutu(s, [Aralik(4, 1, 4, MAX_COL)], KALIN))
    y.calistir(SatirEkleSil(s, 5, 1, True))                  # 4. satırın altına satır → 4'ün stilini alır
    assert set(s.satir_stil) == {4, 5}
    y.calistir(SatirEkleSil(s, 1, 1, True))                  # en üste ekleme: hepsi 1 kayar, yeni satır boş
    assert set(s.satir_stil) == {5, 6} and 1 not in s.satir_stil
    y.geri_al(); y.geri_al()
    assert set(s.satir_stil) == {4}


def test_satir_sil_stilleri_kaydirir_ve_geri_alinca_aynen_doner(s):
    y = GeriAlYigini()
    for r, st in ((2, KALIN), (3, SARI), (6, KALIN)):
        y.calistir(bicim_komutu(s, [Aralik(r, 1, r, 2)], st))
    y.calistir(bicim_komutu(s, [Aralik(3, 1, 3, MAX_COL)], StilYama(italik=True)))   # satır stili + açık kayıtlar
    onceki = (dict(s._stil), dict(s.satir_stil))
    y.calistir(SatirEkleSil(s, 2, 2, False))                  # 2–3. satırları sil
    assert s.stil(4, 1).kalin and 6 not in {k[0] for k in s._stil} and 3 not in s.satir_stil
    assert s.stil(4, 1).kalin                                  # eski 6. satır 4'e kaydı
    y.geri_al()
    assert (dict(s._stil), dict(s.satir_stil)) == onceki      # silinen stiller aynen geri geldi
    y.yinele(); y.geri_al()
    assert (dict(s._stil), dict(s.satir_stil)) == onceki


def test_sutun_ekle_sil_stil(s):
    y = GeriAlYigini()
    y.calistir(bicim_komutu(s, [Aralik(1, 2, MAX_ROW, 2)], KALIN))      # tam B sütunu
    y.calistir(bicim_komutu(s, [Aralik(1, 4, 2, 4)], SARI))
    y.calistir(SutunEkleSil(s, 3, 1, True))                   # C önüne sütun: B'nin stilini alır
    assert set(s.sutun_stil) == {2, 3} and s.stil(1, 5).dolgu == "#FFFF00"
    y.geri_al()
    assert set(s.sutun_stil) == {2} and s.stil(1, 4).dolgu == "#FFFF00"
    y.calistir(SutunEkleSil(s, 2, 1, False))                  # B'yi sil
    assert not s.sutun_stil and s.stil(1, 3).dolgu == "#FFFF00"
    y.geri_al()
    assert set(s.sutun_stil) == {2} and s.stil(1, 4).dolgu == "#FFFF00"


def test_ekleme_sayfa_sonuna_iterse_stil_kaybolur_degil_kayit_atilir(s):
    s.bicim_yaz({(MAX_ROW, 1): s.havuz.kimlik(Stil(kalin=True))})
    s.satir_ekle(5, 1)                                        # son satırdaki biçim sayfa dışına itilir (hücre boş)
    assert not s._stil


# ------------------------------------------------------------ kullanilan_aralik / havuz kitap
def test_kullanilan_aralik_bicim_dahil(s):
    assert s.kullanilan_aralik(bicim_dahil=True) is None
    s.bicim_yaz({(7, 8): s.havuz.kimlik(Stil(kalin=True))})
    assert s.kullanilan_aralik() is None                      # içerik tabanlı değişmez
    assert s.kullanilan_aralik(bicim_dahil=True) == (7, 8, 7, 8)
    s.ata(2, 3, Hucre(1.0))
    assert s.kullanilan_aralik() == (2, 3, 2, 3) and s.kullanilan_aralik(bicim_dahil=True) == (2, 3, 7, 8)
    s.bicim_yaz(satirlar={50: 1})                             # tam satır stili sayılmaz
    assert s.kullanilan_aralik(bicim_dahil=True) == (2, 3, 7, 8)


def test_sayfa_baska_kitaba_baglaninca_kimlikler_cevrilir():
    k1, k2 = CalismaKitabi(), CalismaKitabi()
    k1.stil_havuzu.kimlik(Stil(italik=True))                  # k1'de 1 numara başka stil
    x = Sayfa("Yabanci")                                      # kendi havuzu
    kimlik = x.havuz.kimlik(Stil(kalin=True))
    x.bicim_yaz({(1, 1): kimlik}, {2: kimlik}, {3: kimlik})
    k1._baglan(x)
    assert x.havuz is k1.stil_havuzu and x.stil(1, 1) == Stil(kalin=True)
    assert x.stil(2, 9).kalin and x.stil(9, 3).kalin
    assert k1.stil_havuzu.stil(x.ham_stil_kimligi(1, 1)).kalin and not k2.stil_havuzu.stil(0).kalin


def test_sayfa_silinip_geri_gelince_stilleri_korur(kitap):
    from tabcel.model.komutlar import SayfaEkle, SayfaSil
    y = GeriAlYigini()
    y.calistir(SayfaEkle(kitap))
    s2 = kitap.sayfalar[1]
    s2.bicim_yaz({(1, 1): s2.havuz.kimlik(Stil(kalin=True))})
    y.calistir(SayfaSil(kitap, s2))
    y.geri_al()
    assert kitap.sayfalar[1].stil(1, 1).kalin
