import pytest

from tabcel.model.adres import MAX_ROW, AdresHatasi
from tabcel.model.komutlar import (
    GeriAlYigini, Grup, HucrelerDegis, SatirEkleSil, SutunEkleSil,
)
from tabcel.model.sayfa import CalismaKitabi, Hucre, Sayfa


def H(d):
    return Hucre(d)


def dolu(s):
    return {(a, b): h.deger for a, b, h in s.dolu_hucreler()}


def test_ata_oku_sil():
    s = Sayfa("S")
    assert s.hucre(1, 1) is None and s.deger(1, 1) is None
    assert s.ata(1, 1, H(5.0)) is None
    assert s.deger(1, 1) == 5.0
    assert s.ata(1, 1, Hucre()) == H(5.0)      # boş hücre = silme
    assert s.hucre(1, 1) is None
    assert s.kullanilan_aralik() is None


def test_aralik_disi():
    s = Sayfa("S")
    with pytest.raises(AdresHatasi):
        s.ata(MAX_ROW + 1, 1, H(1.0))
    with pytest.raises(AdresHatasi):
        s.ata(1, 0, H(1.0))


def test_kullanilan_aralik_ve_formul():
    s = Sayfa("S")
    s.ata(2, 3, H("a"))
    s.ata(5, 1, Hucre(None, "=SUM(A1:A3)"))
    s.sonuc_ata(5, 1, 7.0)
    assert s.kullanilan_aralik() == (2, 1, 5, 3)
    assert s.hucre(5, 1).formul == "=SUM(A1:A3)"


def test_satir_ekle_sil():
    s = Sayfa("S")
    for r in (1, 2, 3, 4):
        s.ata(r, 1, H(float(r)))
    s.satir_yukseklik[3] = 40
    s.satir_ekle(2, 2)
    assert dolu(s) == {(1, 1): 1.0, (4, 1): 2.0, (5, 1): 3.0, (6, 1): 4.0}
    assert s.yukseklik(5) == 40
    silinen = s.satir_sil(4, 2)
    assert {k: h.deger for k, h in silinen.items()} == {(4, 1): 2.0, (5, 1): 3.0}
    assert dolu(s) == {(1, 1): 1.0, (4, 1): 4.0}


def test_sutun_sil_olcu():
    s = Sayfa("S")
    s.ata(1, 1, H("a")); s.ata(1, 2, H("b")); s.ata(1, 3, H("c"))
    s.sutun_genislik[2] = 100
    s.sutun_genislik[3] = 120
    s.sutun_sil(2)
    assert dolu(s) == {(1, 1): "a", (1, 2): "c"}
    assert s.sutun_genislik == {2: 120}


def test_kitap_sayfalari():
    k = CalismaKitabi()
    assert [s.ad for s in k.sayfalar] == ["Sayfa1"]
    s2 = k.sayfa_ekle()
    assert s2.ad == "Sayfa2"
    with pytest.raises(ValueError):
        k.sayfa_ekle("sayfa1")                 # büyük/küçük harf duyarsız
    k.yeniden_adlandir(s2, "Özet")
    with pytest.raises(ValueError):
        k.yeniden_adlandir(s2, "SAYFA1")
    k.sayfa_sil(s2)
    with pytest.raises(ValueError):
        k.sayfa_sil(k.sayfalar[0])             # son sayfa silinemez


def test_geri_al_yinele_hucre():
    s = Sayfa("S")
    y = GeriAlYigini()
    y.calistir(HucrelerDegis(s, {(1, 1): H(1.0), (1, 2): H(2.0)}))
    y.calistir(HucrelerDegis(s, {(1, 1): H(9.0), (1, 2): None}))
    assert dolu(s) == {(1, 1): 9.0}
    assert y.geri_al() and dolu(s) == {(1, 1): 1.0, (1, 2): 2.0}
    assert y.geri_al() and dolu(s) == {}
    assert not y.geri_al()
    assert y.yinele() and y.yinele() and dolu(s) == {(1, 1): 9.0}
    assert not y.yinele()


def test_yeni_komut_yinele_yiginini_temizler():
    s = Sayfa("S")
    y = GeriAlYigini()
    y.calistir(HucrelerDegis(s, {(1, 1): H(1.0)}))
    y.geri_al()
    y.calistir(HucrelerDegis(s, {(2, 2): H(2.0)}))
    assert not y.yinelenebilir()


def test_satir_sil_geri_al():
    s = Sayfa("S")
    for r in (1, 2, 3):
        s.ata(r, 1, H(float(r)))
    s.satir_yukseklik[2] = 50
    y = GeriAlYigini()
    y.calistir(SatirEkleSil(s, 2, 1, ekle=False))
    assert dolu(s) == {(1, 1): 1.0, (2, 1): 3.0} and s.satir_yukseklik == {}
    y.geri_al()
    assert dolu(s) == {(1, 1): 1.0, (2, 1): 2.0, (3, 1): 3.0}
    assert s.satir_yukseklik == {2: 50}
    y.yinele()
    assert dolu(s) == {(1, 1): 1.0, (2, 1): 3.0}


def test_sutun_ekle_geri_al_ve_grup():
    s = Sayfa("S")
    s.ata(1, 1, H("a")); s.ata(1, 2, H("b"))
    y = GeriAlYigini()
    y.calistir(Grup([SutunEkleSil(s, 2, 1, ekle=True),
                     HucrelerDegis(s, {(1, 2): H("yeni")})]))
    assert dolu(s) == {(1, 1): "a", (1, 2): "yeni", (1, 3): "b"}
    y.geri_al()                                 # grup tek adım
    assert dolu(s) == {(1, 1): "a", (1, 2): "b"}


def test_yigin_siniri():
    s = Sayfa("S")
    y = GeriAlYigini(sinir=2)
    for i in range(5):
        y.calistir(HucrelerDegis(s, {(1, 1): H(float(i))}))
    assert y.geri_al() and y.geri_al() and not y.geri_al()
    assert s.deger(1, 1) == 2.0


def test_sayfa_adi_dogrulama():
    from tabcel.model.sayfa import sayfa_adi_dogrula
    sayfa_adi_dogrula("Gelir Gider")
    sayfa_adi_dogrula("A" * 31)
    for kotu in ("", "   ", "A" * 32, "a/b", "a\\b", "a?b", "a*b", "a[b", "a]b", "a:b",
                 "'ab", "ab'"):
        with pytest.raises(ValueError):
            sayfa_adi_dogrula(kotu)
    k = CalismaKitabi()
    with pytest.raises(ValueError):
        k.sayfa_ekle("a/b")
    with pytest.raises(ValueError):
        k.yeniden_adlandir(k.sayfalar[0], "x:y")


def test_sayfa_tasi():
    k = CalismaKitabi()
    a = k.sayfalar[0]
    b = k.sayfa_ekle()
    c = k.sayfa_ekle()
    k.sayfa_tasi(c, 0)
    assert k.sayfalar == [c, a, b]
    k.sayfa_tasi(c, 2)
    assert k.sayfalar == [a, b, c]
    with pytest.raises(ValueError):
        k.sayfa_tasi(a, 3)


def test_gizli_satir_sutun_genislik_sifir():
    s = Sayfa("S")
    s.gizli_sutun.add(2)
    s.gizli_satir.add(3)
    s.sutun_genislik[2] = 100
    assert s.genislik(2) == 0 and s.yukseklik(3) == 0
    s.gizli_sutun.clear()
    assert s.genislik(2) == 100          # özgün genişlik korunur


def test_gizli_ekle_sil_ile_kayar():
    s = Sayfa("S")
    s.gizli_satir.update({2, 5, 6})
    s.satir_ekle(3, 2)
    assert s.gizli_satir == {2, 7, 8}
    s.satir_sil(7, 1)
    assert s.gizli_satir == {2, 7}
    s.gizli_sutun.update({1, 4})
    s.sutun_sil(1, 1)
    assert s.gizli_sutun == {3}


def test_olcu_degis_geri_al_yinele():
    from tabcel.model.komutlar import OlcuDegis
    s = Sayfa("S")
    y = GeriAlYigini()
    y.calistir(OlcuDegis(s, lambda sy: sy.sutun_genislik.update({2: 120})))
    y.calistir(OlcuDegis(s, lambda sy: sy.gizli_satir.add(4)))
    assert s.genislik(2) == 120 and s.yukseklik(4) == 0
    y.geri_al()
    assert s.yukseklik(4) == 20 and s.genislik(2) == 120
    y.geri_al()
    assert s.genislik(2) == 64
    y.yinele(); y.yinele()
    assert s.genislik(2) == 120 and s.yukseklik(4) == 0


def test_olcu_degis_onceden_uygulanmis_durum():
    from tabcel.model.komutlar import OlcuDegis
    s = Sayfa("S")
    eski = s.boyut_durumu()
    s.sutun_genislik[1] = 90                    # fare sürüklemesi sırasında doğrudan değişti
    y = GeriAlYigini()
    y.calistir(OlcuDegis(s, eski=eski, yeni=s.boyut_durumu()))
    y.geri_al()
    assert s.genislik(1) == 64
    y.yinele()
    assert s.genislik(1) == 90


def test_satir_sil_geri_al_gizli_doner():
    s = Sayfa("S")
    s.gizli_satir.update({2, 3})
    y = GeriAlYigini()
    y.calistir(SatirEkleSil(s, 2, 1, ekle=False))
    assert s.gizli_satir == {2}
    y.geri_al()
    assert s.gizli_satir == {2, 3}


# --- performans destek yapıları: aralikta, sırasız gezme, kullanılan aralık önbelleği ---
def test_aralikta_iki_strateji_ayni_sonucu_verir():
    from tabcel.model.adres import Aralik
    s = Sayfa("S")
    for r in range(1, 31):
        for c in range(1, 6):
            if (r + c) % 3 == 0:
                s.ata(r, c, H(float(r * c)))
    kucuk = Aralik(2, 2, 4, 3)                       # alan < hücre sayısı → aralığı gezer
    buyuk = Aralik(1, 1, 1_000_000, 1_000)           # alan > hücre sayısı → sözlüğü gezer
    for ar in (kucuk, buyuk, Aralik(5, 1, 20, 2)):
        beklenen = {(r, c) for r, c, _ in s.dolu_hucreler()
                    if ar.ilk_satir <= r <= ar.son_satir and ar.ilk_sutun <= c <= ar.son_sutun}
        assert {(r, c) for r, c, _ in s.aralikta(ar)} == beklenen
    assert {(r, c) for r, c, _ in s.aralikta(buyuk)} == {(r, c) for r, c, _ in s.dolu_hucreler()}


def test_dolu_hucreler_sirali_ve_sirasiz():
    s = Sayfa("S")
    s.ata(3, 1, H(1.0)); s.ata(1, 2, H(2.0)); s.ata(1, 1, H(3.0))
    assert [(r, c) for r, c, _ in s.dolu_hucreler()] == [(1, 1), (1, 2), (3, 1)]
    assert {(r, c) for r, c, _ in s.dolu_hucreler(sirali=False)} == {(1, 1), (1, 2), (3, 1)}


def test_kullanilan_aralik_onbellegi_dogru_kalir():
    s = Sayfa("S")
    assert s.kullanilan_aralik() is None
    s.ata(5, 5, H(1.0))
    assert s.kullanilan_aralik() == (5, 5, 5, 5)
    s.ata(2, 8, H(1.0))
    assert s.kullanilan_aralik() == (2, 5, 5, 8)           # genişler
    s.ata(3, 6, H(1.0))
    assert s.kullanilan_aralik() == (2, 5, 5, 8)           # içeride: değişmez
    s.ata(2, 8, None)                                      # sınırdaki hücre silinir → daralır
    assert s.kullanilan_aralik() == (3, 5, 5, 6)
    s.ata(3, 6, None); s.ata(5, 5, None)
    assert s.kullanilan_aralik() is None
    s.ata(4, 4, H(1.0))
    s.satir_ekle(1, 10)                                    # kaydırma önbelleği geçersiz kılar
    assert s.kullanilan_aralik() == (14, 4, 14, 4)
    s.sutun_sil(4, 1)
    assert s.kullanilan_aralik() is None


def test_kullanilan_aralik_onbellegi_gecmis_rastgele_islemlerle_eslesir():
    import random
    rnd = random.Random(7)
    s = Sayfa("S")
    for _ in range(400):
        r, c = rnd.randint(1, 40), rnd.randint(1, 15)
        s.ata(r, c, H(1.0) if rnd.random() < 0.6 else None)
        if rnd.random() < 0.1:
            s.satir_ekle(rnd.randint(1, 30), 2) if rnd.random() < 0.5 else s.satir_sil(rnd.randint(1, 30), 2)
        gercek = None
        if s._hucreler:
            rs = [k[0] for k in s._hucreler]; cs = [k[1] for k in s._hucreler]
            gercek = (min(rs), min(cs), max(rs), max(cs))
        assert s.kullanilan_aralik() == gercek


# --- Opus Faz 1 gözden geçirmesi: K1 (mantıksal ≠ sayı), K2 (sayfa dışına itme) ---
def test_k1_mantiksal_ile_sayi_esit_degil():
    assert Hucre(True) != Hucre(1.0) and Hucre(False) != Hucre(0.0)
    assert Hucre(1.0) == Hucre(1.0) and Hucre("a") == Hucre("a")
    assert Hucre(None, "=A1") == Hucre(None, "=A1") and Hucre(None, "=A1") != Hucre(None, "=A2")
    assert Hucre(None, "=A1") != Hucre(1.0)
    assert len({Hucre(True), Hucre(1.0), Hucre("1")}) == 3          # hash da türü ayırır
    assert Hucre(1.0) != "1.0"


def test_k2_ekleme_dolu_hucreyi_sayfa_disina_itmez():
    from tabcel.model.adres import MAX_COL
    s = Sayfa("S")
    s.ata(MAX_ROW, 1, H("son"))
    s.ata(1, MAX_COL, H("sag"))
    with pytest.raises(AdresHatasi):
        s.satir_ekle(1, 1)
    with pytest.raises(AdresHatasi):
        s.sutun_ekle(5, 1)
    assert s.deger(MAX_ROW, 1) == "son" and s.deger(1, MAX_COL) == "sag"      # hiçbir şey değişmedi


def test_k2_sinira_tam_sigan_ekleme_calisir_tasan_calismaz():
    s = Sayfa("S")
    s.ata(MAX_ROW - 1, 1, H("x"))
    s.satir_ekle(1, 1)                                  # x tam son satıra gelir
    assert s.deger(MAX_ROW, 1) == "x"
    with pytest.raises(AdresHatasi):
        s.satir_ekle(MAX_ROW, 1)                        # x'in bulunduğu satırdan itme → reddedilir
    s3 = Sayfa("S3")
    s3.ata(5, 1, H("a"))
    s3.satir_ekle(MAX_ROW, 1)                           # verinin altına ekleme: itilecek dolu hücre yok
    assert s3.deger(5, 1) == "a"


def test_k2_komut_reddedilince_yigin_bozulmaz():
    s = Sayfa("S")
    s.ata(MAX_ROW, 1, H("son"))
    y = GeriAlYigini()
    with pytest.raises(AdresHatasi):
        y.calistir(SatirEkleSil(s, 1, 1, ekle=True))
    assert not y.geri_alinabilir() and s.deger(MAX_ROW, 1) == "son"


# --- K4: girdi / sonuç ayrımı ---
def test_k4_hucre_ya_sabit_ya_formul():
    with pytest.raises(ValueError):
        Hucre(7.0, "=A1")
    Hucre(None, "=A1"); Hucre(7.0); Hucre()


def test_k4_gorunen_deger_sonuctur_girdi_degil():
    s = Sayfa("S")
    s.ata(1, 1, H(5.0))
    s.ata(1, 2, Hucre(None, "=A1*2"))
    assert s.deger(1, 1) == 5.0
    assert s.deger(1, 2) is None                               # henüz hesaplanmadı
    s.sonuc_ata(1, 2, 10.0)
    assert s.deger(1, 2) == 10.0 and s.sonuc(1, 2) == 10.0
    assert s.hucre(1, 2) == Hucre(None, "=A1*2")               # girdi sonuçtan etkilenmez
    assert [(r, c) for r, c, _ in s.dolu_hucreler()] == [(1, 1), (1, 2)]


def test_k4_sonuc_yalniz_formul_hucresine_yazilir():
    s = Sayfa("S")
    s.ata(1, 1, H(5.0))
    with pytest.raises(ValueError):
        s.sonuc_ata(1, 1, 9.0)
    with pytest.raises(ValueError):
        s.sonuc_ata(7, 7, 9.0)


def test_k4_girdi_degisince_eski_sonuc_atilir():
    s = Sayfa("S")
    s.ata(1, 1, Hucre(None, "=1+1"))
    s.sonuc_ata(1, 1, 2.0)
    s.ata(1, 1, Hucre(None, "=1+1"))                           # aynı girdi: sonuç kalır
    assert s.sonuc(1, 1) == 2.0
    s.ata(1, 1, Hucre(None, "=2+2"))                           # farklı formül
    assert s.sonuc(1, 1) is None
    s.sonuc_ata(1, 1, 4.0)
    s.ata(1, 1, None)
    assert s.sonuc(1, 1) is None and s.deger(1, 1) is None


def test_k4_geri_al_yalniz_girdiyi_geri_yukler_sonuc_atilir():
    s = Sayfa("S")
    y = GeriAlYigini()
    y.calistir(HucrelerDegis(s, {(1, 1): Hucre(None, "=1+1")}))
    s.sonuc_ata(1, 1, 2.0)
    y.calistir(HucrelerDegis(s, {(1, 1): Hucre(None, "=3+3")}))
    s.sonuc_ata(1, 1, 6.0)
    y.geri_al()
    assert s.hucre(1, 1) == Hucre(None, "=1+1")
    assert s.sonuc(1, 1) is None                               # bayat sonuç geri gelmez; motor yeniden hesaplar
    y.geri_al()
    assert s.hucre(1, 1) is None


def test_k4_sonuclar_satir_ekle_sil_ile_kayar():
    s = Sayfa("S")
    s.ata(3, 1, Hucre(None, "=1"))
    s.sonuc_ata(3, 1, 1.0)
    s.ata(5, 2, Hucre(None, "=2"))
    s.sonuc_ata(5, 2, 2.0)
    s.satir_ekle(2, 2)
    assert s.sonuc(5, 1) == 1.0 and s.sonuc(7, 2) == 2.0 and s.sonuc(3, 1) is None
    s.satir_sil(5, 1)                                          # sonucu olan satır silinir
    assert s.sonuc(5, 1) is None and s.sonuc(6, 2) == 2.0
    s.sutun_sil(1, 1)
    assert s.sonuc(6, 1) == 2.0


def test_k4_hata_degeri():
    from tabcel.model.deger import BASV, BOL0, HATALAR, Hata, hata_bul
    assert BOL0 == Hata("#DIV/0!") and BOL0 != BASV and hash(BOL0) != hash(BASV)
    assert hata_bul("#ref!") is BASV and hata_bul("yok") is None
    assert len(HATALAR) == 7
    s = Sayfa("S")
    s.ata(1, 1, Hucre(None, "=1/0"))
    s.sonuc_ata(1, 1, BOL0)
    assert s.deger(1, 1) is BOL0
    assert Hucre(None, "=1/0") != Hucre(True)
