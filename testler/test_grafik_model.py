"""Faz 6 / 6a: yüzen nesneler (grafik/resim) — model, olay, komutlar, ekle-sil (çapa + başvuru), geri al (Qt'siz)."""
import pytest

from tabcel.formul.motor import Hesaplayici
from tabcel.model.adres import MAX_COL, MAX_ROW, Aralik
from tabcel.model.grafik import (
    Grafik, Konum, Referans, Resim, Seri, grafik_aralik_kesisir, grafik_referanslarini_kaydir, konum_kaydir,
    nesne_baslangic_olcusu, referans_metni,
)
from tabcel.model.komutlar import (
    GeriAlYigini, NesneDegis, NesneEkle, NesneSil, NesneSirala, SatirEkleSil, SayfaSil, SutunEkleSil, ana_sayfa,
)
from tabcel.model.sayfa import CalismaKitabi, Hucre


@pytest.fixture
def kitap():
    return CalismaKitabi()


@pytest.fixture
def sayfa(kitap):
    return kitap.sayfalar[0]


def olaylar(kitap):
    liste = []
    kitap.dinle(liste.append)
    return liste


def nesne_olaylari(liste):
    return [(o.ayrinti["islem"], o.ayrinti["kimlik"]) for o in liste if o.tur == "nesne"]


def seri(sayfa, aralik, **kw):
    return Seri(deger=Referans(sayfa.kimlik, aralik), **kw)


def grafik(sayfa, **kw):
    kw.setdefault("seriler", (seri(sayfa, Aralik(2, 2, 5, 2)),))
    return Grafik(**kw)


# ------------------------------------------------------------------ nesneler
def test_grafik_dogrulama():
    with pytest.raises(ValueError):
        Grafik(tur="radar")
    with pytest.raises(ValueError):
        Grafik(alt_tur="yan_yana")
    with pytest.raises(ValueError):
        Grafik(gosterge="orta")
    with pytest.raises(ValueError):
        Grafik(boyut=(0, 10))
    assert Grafik(gosterge=None).gosterge is None


def test_konum_dogrulama():
    with pytest.raises(ValueError):
        Konum(0, 1)
    with pytest.raises(ValueError):
        Konum(1, MAX_COL + 1)
    with pytest.raises(ValueError):
        Konum(1, 1, dx=-1)


def test_degistir_ve_esitlik():
    g = Grafik(baslik="A")
    assert g.degistir(baslik="A") == g
    assert g.degistir(baslik="B") != g and g.baslik == "A"
    r = Resim(veri=b"x", ad="a")
    assert r.degistir(ad="b").ad == "b" and r.degistir(ad="a") == r
    assert "veri" not in repr(r)                         # büyük baytlar günlüğe taşmaz


def test_seriler_demet_olur():
    assert isinstance(Grafik(seriler=[Seri(ad="x")]).seriler, tuple)


def test_referans_metni(sayfa):
    assert referans_metni(Referans(1, Aralik(2, 2, 5, 2)), "Sayfa1") == "Sayfa1!$B$2:$B$5"
    assert referans_metni(Referans(1, Aralik(2, 2, 2, 2)), "Satış Raporu") == "'Satış Raporu'!$B$2"
    assert referans_metni(None, "x") == ""


def test_resim_baslangic_olcusu():
    assert nesne_baslangic_olcusu(300, 200) == (300, 200)
    assert nesne_baslangic_olcusu(1200, 600) == (600, 300)         # en çok 600 genişlik, oran korunur
    assert nesne_baslangic_olcusu(0, 0) == (480, 288)


# ------------------------------------------------------------------ sayfa depoları + olaylar
def test_ekle_kimlik_atar_ve_sirayi_korur(kitap, sayfa):
    liste = olaylar(kitap)
    a = sayfa.nesne_ekle(grafik(sayfa))
    b = sayfa.nesne_ekle(Resim(veri=b"x"))
    c = sayfa.nesne_ekle(grafik(sayfa), indeks=0)
    assert (a.kimlik, b.kimlik, c.kimlik) == (1, 2, 3)
    assert [n.kimlik for n in sayfa.nesneler] == [3, 1, 2]
    assert nesne_olaylari(liste) == [("ekle", 1), ("ekle", 2), ("ekle", 3)]
    assert sayfa.nesne(2) is b and sayfa.nesne(99) is None


def test_dolu_kimlik_korunur_cakisma_reddedilir(sayfa):
    n = sayfa.nesne_ekle(Grafik(kimlik=7))
    assert n.kimlik == 7
    with pytest.raises(ValueError):
        sayfa.nesne_ekle(Grafik(kimlik=7))
    assert sayfa.nesne_ekle(Grafik()).kimlik == 8                  # sayaç yüksek kimliği aşar


def test_kimlik_yeniden_kullanilmaz(sayfa):
    a = sayfa.nesne_ekle(Grafik())
    sayfa.nesne_sil(a.kimlik)
    assert sayfa.nesne_ekle(Grafik()).kimlik != a.kimlik


def test_sil_indeks_dondurur_ve_olay(kitap, sayfa):
    sayfa.nesne_ekle(Grafik()), sayfa.nesne_ekle(Grafik()), sayfa.nesne_ekle(Grafik())
    liste = olaylar(kitap)
    n, i = sayfa.nesne_sil(2)
    assert (n.kimlik, i) == (2, 1) and [x.kimlik for x in sayfa.nesneler] == [1, 3]
    assert nesne_olaylari(liste) == [("sil", 2)]
    with pytest.raises(KeyError):
        sayfa.nesne_sil(2)


def test_degistir_olay_yalniz_degisince(kitap, sayfa):
    n = sayfa.nesne_ekle(Grafik(baslik="A"))
    liste = olaylar(kitap)
    assert sayfa.nesne_degistir(n) is n and liste == []             # aynı değer: olay yok
    eski = sayfa.nesne_degistir(n.degistir(baslik="B"))
    assert eski.baslik == "A" and sayfa.nesne(n.kimlik).baslik == "B"
    assert nesne_olaylari(liste) == [("degis", n.kimlik)]
    with pytest.raises(ValueError):
        sayfa.nesne_degistir(Resim(kimlik=n.kimlik))               # tür değişemez
    with pytest.raises(KeyError):
        sayfa.nesne_degistir(Grafik(kimlik=99))


def test_sirala_ve_sinirlar(kitap, sayfa):
    for _ in range(4):
        sayfa.nesne_ekle(Grafik())
    liste = olaylar(kitap)
    assert sayfa.nesne_sirala(1, 99) == 0                          # en üste (sınırlanır)
    assert [n.kimlik for n in sayfa.nesneler] == [2, 3, 4, 1]
    assert sayfa.nesne_sirala(1, 3) == 3 and nesne_olaylari(liste) == [("sira", 1)]   # zaten orada: olay yok
    sayfa.nesne_sirala(4, -5)
    assert [n.kimlik for n in sayfa.nesneler] == [4, 2, 3, 1]


def test_durum_yukle_tek_olay(kitap, sayfa):
    sayfa.nesne_ekle(Grafik()), sayfa.nesne_ekle(Grafik())
    once = sayfa.nesne_durumu()
    sayfa.nesne_sil(1), sayfa.nesne_ekle(Grafik(baslik="y"))
    liste = olaylar(kitap)
    sayfa.nesne_durumu_yukle(once)
    assert nesne_olaylari(liste) == [("hepsi", None)] and [n.kimlik for n in sayfa.nesneler] == [1, 2]
    sayfa.nesne_durumu_yukle(once)                                 # değişmedi: olay yok
    assert len(nesne_olaylari(liste)) == 1
    assert sayfa.nesne_ekle(Grafik()).kimlik == 4                  # sayaç geri sarmaz (kimlik 3 kullanıldı)


def test_ek_durumu_demeti_degismedi(sayfa):
    assert len(sayfa.ek_durumu()) == 4                             # mevcut testler 4'lüye dayanır (D6)


def test_motor_nesne_olayini_yok_sayar(kitap, sayfa):
    motor = Hesaplayici(kitap)
    sayfa.ata(1, 1, Hucre(None, "=1+2"))
    assert sayfa.deger(1, 1) == 3.0
    sayfa.nesne_ekle(Grafik())
    sayfa.nesne_durumu_yukle([])
    assert sayfa.deger(1, 1) == 3.0 and motor is not None


# ------------------------------------------------------------------ komutlar
def test_nesne_ekle_komutu_geri_al_yinele_ayni_kimlik(sayfa):
    y = GeriAlYigini()
    y.calistir(NesneEkle(sayfa, grafik(sayfa, baslik="A")))
    kimlik = sayfa.nesneler[0].kimlik
    y.geri_al()
    assert sayfa.nesneler == []
    y.yinele()
    assert [n.kimlik for n in sayfa.nesneler] == [kimlik] and sayfa.nesneler[0].baslik == "A"
    y.geri_al(), y.yinele(), y.geri_al(), y.yinele()
    assert [n.kimlik for n in sayfa.nesneler] == [kimlik]


def test_nesne_ekle_indeks_korunur(sayfa):
    y = GeriAlYigini()
    y.calistir(NesneEkle(sayfa, Grafik())), y.calistir(NesneEkle(sayfa, Grafik()))
    y.calistir(NesneEkle(sayfa, Grafik(), indeks=0))
    sira = [n.kimlik for n in sayfa.nesneler]
    y.geri_al(), y.yinele()
    assert [n.kimlik for n in sayfa.nesneler] == sira == [3, 1, 2]


def test_nesne_sil_geri_al_ayni_yer(sayfa):
    for _ in range(3):
        sayfa.nesne_ekle(Grafik())
    y = GeriAlYigini()
    y.calistir(NesneSil(sayfa, 2))
    assert [n.kimlik for n in sayfa.nesneler] == [1, 3]
    y.geri_al()
    assert [n.kimlik for n in sayfa.nesneler] == [1, 2, 3]
    y.yinele()
    assert [n.kimlik for n in sayfa.nesneler] == [1, 3]


def test_nesne_degis_bos_mu_ve_geri_al(sayfa):
    n = sayfa.nesne_ekle(Grafik(baslik="A"))
    assert NesneDegis(sayfa, n).bos_mu()
    k = NesneDegis(sayfa, n.degistir(baslik="B", konum=Konum(3, 3, 5, 5)))
    assert not k.bos_mu()
    y = GeriAlYigini()
    y.calistir(k)
    assert sayfa.nesne(n.kimlik).baslik == "B"
    y.geri_al()
    assert sayfa.nesne(n.kimlik) == n
    y.yinele()
    assert sayfa.nesne(n.kimlik).konum == Konum(3, 3, 5, 5)


@pytest.mark.parametrize("yon,beklenen", [
    ("one_getir", [2, 3, 1]), ("arkaya_gonder", [1, 2, 3]), ("bir_one", [2, 3, 1]), ("bir_arkaya", [1, 2, 3])])
def test_nesne_sirala_komutu(sayfa, yon, beklenen):
    for _ in range(3):
        sayfa.nesne_ekle(Grafik())
    sayfa.nesne_sirala(1, 1)                                       # başlangıç z sırası: [2, 1, 3] (1 ortada)
    y = GeriAlYigini()
    k = NesneSirala(sayfa, 1, yon)
    assert not k.bos_mu()
    y.calistir(k)
    assert [n.kimlik for n in sayfa.nesneler] == beklenen
    y.geri_al()
    assert [n.kimlik for n in sayfa.nesneler] == [2, 1, 3]
    y.yinele()
    assert [n.kimlik for n in sayfa.nesneler] == beklenen


def test_nesne_sirala_bos_ve_hatali(sayfa):
    sayfa.nesne_ekle(Grafik()), sayfa.nesne_ekle(Grafik())
    assert NesneSirala(sayfa, 2, "one_getir").bos_mu()             # zaten en üstte
    assert NesneSirala(sayfa, 1, "arkaya_gonder").bos_mu()
    with pytest.raises(ValueError):
        NesneSirala(sayfa, 1, "yana")


def test_ana_sayfa_ve_damga(kitap, sayfa):
    y = GeriAlYigini()
    d0 = y.damga()
    k = NesneEkle(sayfa, Grafik())
    y.calistir(k)
    assert ana_sayfa(k) is sayfa and not y.damga_esit(y.damga(), d0)    # "değişti" işareti komuttan gelir
    y.geri_al()
    assert y.damga_esit(y.damga(), d0)


# ------------------------------------------------------------------ ekle-sil: çapa
@pytest.mark.parametrize("eksen,nerede,fark,once,sonra", [
    (0, 5, 2, Konum(6, 3, 4, 7), Konum(8, 3, 4, 7)),          # çapa ≥ nerede: kayar
    (0, 6, 2, Konum(6, 3, 4, 7), Konum(8, 3, 4, 7)),          # tam çapada ekleme: çapa aşağı iner
    (0, 7, 2, Konum(6, 3, 4, 7), Konum(6, 3, 4, 7)),          # çapadan sonra: değişmez
    (0, 2, -3, Konum(6, 3, 4, 7), Konum(3, 3, 4, 7)),         # çapa silinen bandın ötesinde: yukarı kayar
    (0, 5, -3, Konum(6, 3, 4, 7), Konum(5, 3, 4, 0)),         # çapa silinen bantta: nerede'ye iner, dy = 0
    (0, 7, -2, Konum(6, 3, 4, 7), Konum(6, 3, 4, 7)),
    (1, 2, 1, Konum(6, 3, 4, 7), Konum(6, 4, 4, 7)),          # sütun ekleme
    (1, 2, -2, Konum(6, 3, 4, 7), Konum(6, 2, 0, 7)),         # sütun silme: çapa bantta, dx = 0
    (1, 4, 3, Konum(6, 3, 4, 7), Konum(6, 3, 4, 7)),
])
def test_konum_kaydir_tablosu(eksen, nerede, fark, once, sonra):
    assert konum_kaydir(once, eksen, nerede, fark, MAX_COL if eksen else MAX_ROW) == sonra


def test_konum_kaydir_sinira_sikisir():
    k = konum_kaydir(Konum(MAX_ROW - 1, 1), 0, 1, 5, MAX_ROW)
    assert k.satir == MAX_ROW


def test_sayfada_satir_ekleyince_ve_silince_capa_kayar_geri_al(sayfa):
    sayfa.nesne_ekle(Grafik(konum=Konum(6, 3, 4, 7)))
    y = GeriAlYigini()
    y.calistir(SatirEkleSil(sayfa, 2, 3, True))
    assert sayfa.nesneler[0].konum == Konum(9, 3, 4, 7)
    y.calistir(SatirEkleSil(sayfa, 8, 3, False))                   # çapa (9) silinen bantta (8–10)
    assert sayfa.nesneler[0].konum == Konum(8, 3, 4, 0)
    y.geri_al()
    assert sayfa.nesneler[0].konum == Konum(9, 3, 4, 7)
    y.geri_al()
    assert sayfa.nesneler[0].konum == Konum(6, 3, 4, 7)
    y.yinele(), y.yinele()
    assert sayfa.nesneler[0].konum == Konum(8, 3, 4, 0)


def test_baska_sayfada_ekle_sil_capayi_kaydirmaz(kitap, sayfa):
    s2 = kitap.sayfa_ekle()
    s2.nesne_ekle(Grafik(konum=Konum(6, 3)))
    SatirEkleSil(sayfa, 1, 4, True).yap()
    assert s2.nesneler[0].konum == Konum(6, 3)


# ------------------------------------------------------------------ ekle-sil: başvurular (kitap düzeyi)
def test_ayni_sayfa_basvuru_kayar_ve_geri_alinir(sayfa):
    sayfa.nesne_ekle(grafik(sayfa, seriler=(
        seri(sayfa, Aralik(2, 2, 5, 2), kategori=Referans(sayfa.kimlik, Aralik(2, 1, 5, 1)),
             ad_ref=Referans(sayfa.kimlik, Aralik(1, 2, 1, 2))),)))
    y = GeriAlYigini()
    y.calistir(SatirEkleSil(sayfa, 3, 2, True))                    # 3. satırdan 2 satır ekle: aralıklar büyür
    s = sayfa.nesneler[0].seriler[0]
    assert s.deger.aralik == Aralik(2, 2, 7, 2) and s.kategori.aralik == Aralik(2, 1, 7, 1)
    assert s.ad_ref.aralik == Aralik(1, 2, 1, 2)                   # başlık üstte kaldı
    y.calistir(SutunEkleSil(sayfa, 1, 1, True))                    # soldan sütun ekle: hepsi bir sütun sağa
    s = sayfa.nesneler[0].seriler[0]
    assert s.deger.aralik == Aralik(2, 3, 7, 3) and s.kategori.aralik == Aralik(2, 2, 7, 2)
    y.geri_al(), y.geri_al()
    s = sayfa.nesneler[0].seriler[0]
    assert s.deger.aralik == Aralik(2, 2, 5, 2) and s.kategori.aralik == Aralik(2, 1, 5, 1)
    y.yinele(), y.yinele()
    assert sayfa.nesneler[0].seriler[0].deger.aralik == Aralik(2, 3, 7, 3)


def test_baska_sayfadaki_grafigin_basvurusu_kayar(kitap, sayfa):
    s2 = kitap.sayfa_ekle()
    s2.nesne_ekle(Grafik(seriler=(seri(sayfa, Aralik(2, 2, 5, 2)),), konum=Konum(1, 1)))
    y = GeriAlYigini()
    y.calistir(SatirEkleSil(sayfa, 1, 1, True))                    # Sayfa1'e satır eklendi → Sayfa2'deki başvuru kayar
    assert s2.nesneler[0].seriler[0].deger.aralik == Aralik(3, 2, 6, 2)
    assert s2.nesneler[0].konum == Konum(1, 1)                     # kendi sayfasına dokunulmadı
    y.geri_al()
    assert s2.nesneler[0].seriler[0].deger.aralik == Aralik(2, 2, 5, 2)


def test_baska_sayfaya_bakan_basvuru_kendi_sayfasindaki_ekle_silden_etkilenmez(kitap, sayfa):
    s2 = kitap.sayfa_ekle()
    s2.nesne_ekle(Grafik(seriler=(seri(sayfa, Aralik(2, 2, 5, 2)),)))
    SatirEkleSil(s2, 1, 3, True).yap()                             # Sayfa2'ye ekleme: başvuru Sayfa1'de
    assert s2.nesneler[0].seriler[0].deger.aralik == Aralik(2, 2, 5, 2)


def test_degeri_tamamen_silinen_seri_duser_grafik_kalir(sayfa):
    sayfa.nesne_ekle(grafik(sayfa, seriler=(
        seri(sayfa, Aralik(2, 2, 5, 2)), seri(sayfa, Aralik(2, 3, 5, 3)))))
    y = GeriAlYigini()
    y.calistir(SutunEkleSil(sayfa, 2, 1, False))                   # B sütunu silindi: 1. seri düşer
    assert [s.deger.aralik for s in sayfa.nesneler[0].seriler] == [Aralik(2, 2, 5, 2)]
    y.calistir(SatirEkleSil(sayfa, 1, 10, False))                  # tüm satırlar silindi: grafik silinmez
    assert len(sayfa.nesneler) == 1 and sayfa.nesneler[0].seriler == ()
    y.geri_al(), y.geri_al()
    assert len(sayfa.nesneler[0].seriler) == 2


def test_kategorisi_silinen_seri_kalir_kategorisiz(sayfa):
    sayfa.nesne_ekle(grafik(sayfa, seriler=(
        seri(sayfa, Aralik(2, 2, 5, 2), kategori=Referans(sayfa.kimlik, Aralik(2, 1, 5, 1))),)))
    SutunEkleSil(sayfa, 1, 1, False).yap()                         # A (kategori) silindi
    s = sayfa.nesneler[0].seriler[0]
    assert s.kategori is None and s.deger.aralik == Aralik(2, 1, 5, 1)


def test_silinen_sayfaya_basvuru_geri_alinca_duzelir(kitap, sayfa):
    s2 = kitap.sayfa_ekle()
    s2.nesne_ekle(Grafik(seriler=(seri(sayfa, Aralik(2, 2, 5, 2)),)))
    y = GeriAlYigini()
    y.calistir(SayfaSil(kitap, sayfa))
    assert s2.nesneler[0].seriler[0].deger.sayfa_kimlik == sayfa.kimlik   # başvuru kimlikle: silinen sayfa #BAŞV!
    y.geri_al()
    assert kitap.sayfalar[0] is sayfa
    assert s2.nesneler[0].seriler[0].deger == Referans(sayfa.kimlik, Aralik(2, 2, 5, 2))


def test_sayfa_silme_nesneleri_korur(kitap, sayfa):
    sayfa.nesne_ekle(Grafik(baslik="x"))
    y = GeriAlYigini()
    kitap.sayfa_ekle()
    y.calistir(SayfaSil(kitap, sayfa))
    y.geri_al()
    assert sayfa.nesneler[0].baslik == "x"


def test_basvuru_kaydirma_olayi_tek(kitap, sayfa):
    sayfa.nesne_ekle(grafik(sayfa))
    sayfa.nesne_ekle(grafik(sayfa))
    liste = olaylar(kitap)
    SatirEkleSil(sayfa, 1, 1, True).yap()
    assert nesne_olaylari(liste) == [("hepsi", None)]               # iki grafik, TEK nesne olayı
    liste.clear()
    SatirEkleSil(sayfa, 100, 1, True).yap()                         # başvurulara dokunmayan ekleme: nesne olayı yok
    assert nesne_olaylari(liste) == []


def test_referans_ve_grafik_kaydirma_yardimcilari(sayfa):
    r = Referans(1, Aralik(2, 2, 5, 2))
    from tabcel.model.grafik import referans_kaydir
    assert referans_kaydir(r, 2, 0, 3, 3, MAX_ROW) is r              # başka sayfa
    assert referans_kaydir(r, 1, 0, 3, 3, MAX_ROW) == Referans(1, Aralik(2, 2, 8, 2))
    assert referans_kaydir(r, 1, 0, 2, -4, MAX_ROW) is None
    assert referans_kaydir(None, 1, 0, 1, 1, MAX_ROW) is None
    g = Grafik(seriler=(Seri(ad="sabit"),))                          # değersiz seri korunur
    assert grafik_referanslarini_kaydir(g, 1, 0, 1, 1, MAX_ROW) is g


def test_grafik_aralik_kesisir(sayfa):
    g = grafik(sayfa, seriler=(seri(sayfa, Aralik(2, 2, 5, 2),
                                    kategori=Referans(sayfa.kimlik, Aralik(2, 1, 5, 1))),))
    assert grafik_aralik_kesisir(g, sayfa.kimlik, Aralik(3, 2, 3, 2))
    assert grafik_aralik_kesisir(g, sayfa.kimlik, Aralik(5, 1, 9, 1))      # kategoriye değiyor
    assert not grafik_aralik_kesisir(g, sayfa.kimlik, Aralik(6, 1, 9, 9))
    assert not grafik_aralik_kesisir(g, sayfa.kimlik + 1, Aralik(3, 2, 3, 2))
