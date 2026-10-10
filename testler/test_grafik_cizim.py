"""Faz 6 / 6c: grafik çizim listesi — eksen ölçeği, düzen, 7 tür (Qt'siz, sayısal geometri)."""
import time

import pytest

from tabcel.model.grafik import Grafik
from tabcel.model.grafik_cizim import (
    ARKA_PLAN, PALET, VERI_YOK, Cizgi, Cokgen, Dikdortgen, Dilim, Dizi, Isaret, Metin, cizim_listesi,
    etiket_metni, guzel_olcek, min_max_bosalt, palet_rengi, ton,
)
from tabcel.model.grafik_verisi import GrafikVerisi, SeriVerisi

W, H = 480, 288


def olcer(metin, pt):
    """Sabit genişlikli sahte ölçer: karakter başı 0,6 × pt, yükseklik 1,4 × pt."""
    return (len(metin) * pt * 0.6, pt * 1.4)


def seri(ad, degerler, kat=None, x=None, renk=None):
    kat = kat if kat is not None else [str(i + 1) for i in range(len(degerler))]
    return SeriVerisi(ad, tuple(degerler), kat, tuple(x) if x is not None else None, renk)


def veri(*seriler, bicim="General"):
    return GrafikVerisi(tuple(seriler), bicim)


def ciz(v, **kw):
    boyut = kw.pop("boyut", (W, H))
    olcek = kw.pop("olcek", 1.0)
    return cizim_listesi(v, Grafik(**kw), boyut, olcer, olcek)


def tur(liste, sinif):
    return [o for o in liste if isinstance(o, sinif)]


def metinler(liste):
    return [o.metin for o in tur(liste, Metin)]


def cubuklar(liste):
    """Grafik alanındaki çubuklar (arka plan ve gösterge kutuları hariç)."""
    x, y, w, h = liste.grafik_alani
    return [d for d in tur(liste, Dikdortgen) if d.dolgu not in (ARKA_PLAN,) and d.w > 0 and d.h > 0
            and x - 0.5 <= d.x and d.x + d.w <= x + w + 0.5 and y - 0.5 <= d.y and d.y + d.h <= y + h + 0.5]


# ------------------------------------------------------------------ güzel ölçek
@pytest.mark.parametrize("lo,hi,hedef,beklenen", [
    (0, 97, 5, (0, 100, 20)),
    (0, 10, 5, (0, 10, 2)),
    (0, 100, 5, (0, 100, 20)),
    (-5, 12, 5, (-5, 15, 5)),
    (3, 97, 5, (0, 100, 20)),
    (0, 1, 5, (0, 1, 0.2)),
    (0, 0.07, 5, (0, 0.08, 0.02)),
    (0, 1_234_567, 5, (0, 1_250_000, 250_000)),
    (0, 3, 5, (0, 3, 1)),
    (1, 2, 4, (1, 2, 0.25)),
    (0, 0, 5, (0, 1, 0.2)),
    (5, 5, 5, (4.4, 5.6, 0.2)),
])
def test_guzel_olcek_tablosu(lo, hi, hedef, beklenen):
    alt, ust, adim = guzel_olcek(lo, hi, hedef)
    assert (alt, ust) == pytest.approx(beklenen[:2]) and adim == pytest.approx(beklenen[2])
    assert alt <= lo + 1e-9 and ust >= hi - 1e-9


def test_guzel_olcek_ters_aralik_ve_adim_hizasi():
    assert guzel_olcek(10, 0, 5) == guzel_olcek(0, 10, 5)
    for lo, hi in ((0, 17), (-3, 41), (123, 987), (0.013, 0.094)):
        alt, ust, adim = guzel_olcek(lo, hi, 5)
        assert round((ust - alt) / adim, 6) == round((ust - alt) / adim)       # adım ölçeği tam böler


def test_etiket_metni():
    assert etiket_metni(1500.0) == "1500" and etiket_metni(0.25) == "0,25"
    assert etiket_metni(0.5, "0%") == "50%"
    assert etiket_metni(0.30000000000000004) == "0,3"                          # kayan nokta temizlenir


def test_palet_ve_ton():
    assert [palet_rengi(i) for i in range(6)] == list(PALET)
    assert palet_rengi(6) == ton(PALET[0], -0.25) and palet_rengi(6) != palet_rengi(0)
    assert ton("#808080", 1.0) == "#FFFFFF" and ton("#808080", -1.0) == "#000000"
    assert len({palet_rengi(i) for i in range(30)}) == 30


# ------------------------------------------------------------------ sütun
def test_sutun_tek_seri_orantili_yukseklikler():
    liste = ciz(veri(seri("A", [10, 20, 30])), tur="sutun", gosterge=None)
    c = sorted(cubuklar(liste), key=lambda d: d.x)
    assert len(c) == 3
    assert c[1].h == pytest.approx(2 * c[0].h) and c[2].h == pytest.approx(3 * c[0].h)
    assert len({round(d.y + d.h, 6) for d in c}) == 1                           # hepsi aynı taban çizgisinde
    assert len({round(d.w, 6) for d in c}) == 1 and all(d.dolgu == PALET[0] for d in c)
    assert c[0].x < c[1].x < c[2].x
    x, y, w, h = liste.grafik_alani
    assert c[0].x > x and c[2].x + c[2].w < x + w                               # boşluk bırakılır


def test_sutun_kume_genisligi_excel_varsayilani():
    liste = ciz(veri(seri("A", [1, 2]), seri("B", [3, 4])), tur="sutun", gosterge=None)
    c = sorted(cubuklar(liste), key=lambda d: (d.x))
    assert len(c) == 4
    kat_g = liste.grafik_alani[2] / 2
    assert c[0].w == pytest.approx(kat_g / (2 + 1.5))                           # boşluk genişliği %150
    assert c[0].dolgu == PALET[0] and c[1].dolgu == PALET[1]
    assert c[0].x + c[0].w == pytest.approx(c[1].x)                             # çakışma %0, bitişik


def test_sutun_negatif_deger_tabanin_altina():
    liste = ciz(veri(seri("A", [10, -10])), tur="sutun", gosterge=None)
    c = sorted(cubuklar(liste), key=lambda d: d.x)
    taban = c[0].y + c[0].h
    assert c[1].y == pytest.approx(taban) and c[1].h == pytest.approx(c[0].h)


def test_sutun_yigili_yukseklikler_toplanir():
    liste = ciz(veri(seri("A", [10, 5]), seri("B", [20, 5])), tur="sutun", alt_tur="yigili", gosterge=None)
    c = cubuklar(liste)
    k1 = sorted([d for d in c if d.x < liste.grafik_alani[0] + liste.grafik_alani[2] / 2], key=lambda d: d.y)
    assert len(k1) == 2
    assert k1[0].y + k1[0].h == pytest.approx(k1[1].y)                          # üst üste, aralıksız
    assert k1[0].h == pytest.approx(2 * k1[1].h)                                # B (20) A'nın (10) iki katı


def test_sutun_yuzde_yigili_hepsi_ayni_toplam_yukseklik():
    liste = ciz(veri(seri("A", [1, 30]), seri("B", [3, 10])), tur="sutun", alt_tur="yuzde_yigili", gosterge=None)
    c = cubuklar(liste)
    x, y, w, h = liste.grafik_alani
    for ilk in (True, False):
        sut = [d for d in c if (d.x < x + w / 2) == ilk]
        assert sum(d.h for d in sut) == pytest.approx(h)                        # %100: alan yüksekliğini doldurur
    assert any(m.endswith("%") for m in metinler(liste)) and "100%" in metinler(liste)


def test_sutun_deger_etiketi_ve_eksen_basliklari():
    liste = ciz(veri(seri("A", [10, 20])), tur="sutun", gosterge=None, deger_etiketi=True,
                x_baslik="Ay", y_baslik="Adet", baslik="Satış")
    m = metinler(liste)
    assert "10" in m and "20" in m and "Ay" in m and "Adet" in m and "Satış" in m
    adet = [o for o in tur(liste, Metin) if o.metin == "Adet"][0]
    assert adet.aci == -90.0 and adet.x < liste.grafik_alani[0]                 # sol kenarda, döndürülmüş
    ay = [o for o in tur(liste, Metin) if o.metin == "Ay"][0]
    assert ay.y > liste.grafik_alani[1] + liste.grafik_alani[3] and ay.dikey == "alt"
    baslik = [o for o in tur(liste, Metin) if o.metin == "Satış"][0]
    assert baslik.kalin and baslik.x == pytest.approx(W / 2) and baslik.y < liste.grafik_alani[1]


def test_deger_ekseni_etiketleri_sayi_bicimiyle():
    liste = ciz(veri(seri("A", [0.2, 0.5]), bicim="0%"), tur="sutun", gosterge=None)
    m = metinler(liste)
    assert "0%" in m and "50%" in m and all(not e.endswith(",5") for e in m)


def test_y_min_y_max_kullanici_siniri():
    liste = ciz(veri(seri("A", [10, 20])), tur="sutun", gosterge=None, y_min=0, y_max=100)
    m = metinler(liste)
    assert "100" in m and "0" in m and "20" in m                                # 100'e kadar eksen (adım 20)
    c = sorted(cubuklar(liste), key=lambda d: d.x)
    assert c[1].h == pytest.approx(2 * c[0].h) and c[1].h < liste.grafik_alani[3] * 0.3


def test_kategori_etiketleri_seyreltilir():
    kat = [f"Kategori{i:03d}" for i in range(40)]
    liste = ciz(veri(seri("A", list(range(1, 41)), kat)), tur="sutun", gosterge=None)
    cizilen = [e for e in metinler(liste) if e.startswith("Kategori")]
    assert 0 < len(cizilen) < 40 and cizilen[0] == "Kategori000"
    liste2 = ciz(veri(seri("A", [1, 2, 3], ["a", "b", "c"])), tur="sutun", gosterge=None)
    assert [e for e in metinler(liste2) if e in ("a", "b", "c")] == ["a", "b", "c"]


# ------------------------------------------------------------------ çubuk (yatay)
def test_cubuk_yatay_ilk_kategori_altta():
    liste = ciz(veri(seri("A", [10, 20, 30], ["x", "y", "z"])), tur="cubuk", gosterge=None)
    c = sorted(cubuklar(liste), key=lambda d: d.y)                              # yukarıdan aşağı
    assert len(c) == 3
    assert c[0].w == pytest.approx(3 * c[2].w) and c[1].w == pytest.approx(2 * c[2].w)   # z üstte, x altta
    etiketler = sorted([o for o in tur(liste, Metin) if o.metin in ("x", "y", "z")], key=lambda o: o.y)
    assert [o.metin for o in etiketler] == ["z", "y", "x"]
    assert len({round(d.x, 6) for d in c}) == 1                                 # sol kenarları ortak (taban)


# ------------------------------------------------------------------ çizgi
def test_cizgi_bos_deger_cizgiyi_koparir_ve_isaretciler():
    liste = ciz(veri(seri("A", [1, None, 3, 4])), tur="cizgi", gosterge=None)
    d = tur(liste, Dizi)[0]
    assert len(d.noktalar) == 4 and d.noktalar[1] is None
    assert len(tur(liste, Isaret)) == 3                                         # boş değerde işaretçi yok
    xs = [p[0] for p in d.noktalar if p]
    assert xs == sorted(xs)


def test_cizgi_iki_seri_renkleri_ve_gosterge():
    liste = ciz(veri(seri("A", [1, 2, 3]), seri("B", [3, 2, 1])), tur="cizgi", gosterge="sag")
    diziler = tur(liste, Dizi)
    assert [d.renk for d in diziler] == [PALET[0], PALET[1]]
    assert {"A", "B"} <= set(metinler(liste))
    assert len(tur(liste, Cizgi)) > 0


def test_cizgi_eksen_sifirdan_baslamaz_dar_aralikta_excel_kurali():
    dar = ciz(veri(seri("A", [100, 101, 102])), tur="cizgi", gosterge=None)
    assert "0" not in metinler(dar)                                              # (hi−lo)/hi < 1/6: veriye göre
    genis = ciz(veri(seri("A", [10, 50, 90])), tur="cizgi", gosterge=None)
    assert "0" in metinler(genis)


def test_cizgi_yigili_toplam():
    liste = ciz(veri(seri("A", [1, 2]), seri("B", [3, 4])), tur="cizgi", alt_tur="yigili", gosterge=None)
    a, b = tur(liste, Dizi)
    assert b.noktalar[1][1] < a.noktalar[1][1]                                   # B (yığılı) A'nın üstünde (y küçük)


def test_cizgi_100000_nokta_bosaltilir_ve_hizli():
    n = 100_000
    liste_hedef = veri(seri("A", [float((i * 7919) % 1000) for i in range(n)]))
    t = time.perf_counter()
    liste = ciz(liste_hedef, tur="cizgi", gosterge=None)
    gecen = time.perf_counter() - t
    d = tur(liste, Dizi)[0]
    assert len(d.noktalar) <= 4 * W and len(tur(liste, Isaret)) == 0
    assert gecen < 1.0, f"{gecen:.2f} sn"                                       # hedef ≤ 150 ms; yük için gevşek


# ------------------------------------------------------------------ alan
def test_alan_cokgen_ve_yigili():
    liste = ciz(veri(seri("A", [1, 2, 3]), seri("B", [1, 1, 1])), tur="alan", alt_tur="yigili", gosterge=None)
    pol = tur(liste, Cokgen)
    assert len(pol) == 2 and len(pol[0].noktalar) == 6
    x, y, w, h = liste.grafik_alani
    assert min(p[0] for p in pol[0].noktalar) == pytest.approx(x)               # tik işaretleri üzerinde: kenardan kenara
    assert max(p[0] for p in pol[0].noktalar) == pytest.approx(x + w)
    ust_b = [p[1] for p in pol[1].noktalar[:3]]
    ust_a = [p[1] for p in pol[0].noktalar[:3]]
    assert all(b < a for b, a in zip(ust_b, ust_a))                              # yığılı B, A'nın üstünde


# ------------------------------------------------------------------ pasta / halka
def test_pasta_acilari_toplam_360_ve_oranli():
    liste = ciz(veri(seri("A", [1, 1, 2], ["a", "b", "c"])), tur="pasta", gosterge="sag")
    d = tur(liste, Dilim)
    assert len(d) == 3 and d[0].aci0 == 0.0                                      # 12 yönünden başlar
    assert [round(x.aci1 - x.aci0, 6) for x in d] == [90.0, 90.0, 180.0]
    assert d[-1].aci1 == pytest.approx(360.0) and all(x.r_ic == 0 for x in d)
    assert [x.dolgu for x in d] == [PALET[0], PALET[1], PALET[2]]                # dilim başına renk
    assert {"a", "b", "c"} <= set(metinler(liste))                               # gösterge kategori adları


def test_pasta_sifir_ve_negatif_dilim_yok_deger_etiketi_yuzde():
    liste = ciz(veri(seri("A", [1, 0, -5, 3], ["a", "b", "c", "d"])), tur="pasta", gosterge=None, deger_etiketi=True)
    d = tur(liste, Dilim)
    assert len(d) == 2 and d[1].aci1 == pytest.approx(360.0)
    assert "25%" in metinler(liste) and "75%" in metinler(liste)


def test_halka_ic_yaricap():
    liste = ciz(veri(seri("A", [1, 1])), tur="halka", gosterge=None)
    d = tur(liste, Dilim)
    assert all(x.r_ic == pytest.approx(x.r_dis * 0.5) for x in d)
    x, y, w, h = liste.grafik_alani
    assert w == h and d[0].r_dis == pytest.approx(w / 2)


def test_pasta_yalniz_ilk_seri():
    liste = ciz(veri(seri("A", [1, 1]), seri("B", [5, 5, 5])), tur="pasta", gosterge=None)
    assert len(tur(liste, Dilim)) == 2


def test_pasta_hepsi_sifirsa_veri_yok():
    assert VERI_YOK in metinler(ciz(veri(seri("A", [0, 0])), tur="pasta"))


# ------------------------------------------------------------------ dağılım
def test_dagilim_isaretler_ve_eksenler():
    liste = ciz(veri(seri("A", [10, 20, None, 40], x=[1, 2, 3, 4])), tur="dagilim", gosterge=None)
    i = tur(liste, Isaret)
    assert len(i) == 3                                                           # boş Y'de nokta yok
    assert [p.x for p in i] == sorted(p.x for p in i)
    assert i[0].dolgu == PALET[0]
    assert len(tur(liste, Dizi)) == 0                                            # yalnız işaretçi
    x, y, w, h = liste.grafik_alani
    assert all(x - 1e-6 <= p.x <= x + w + 1e-6 and y - 1e-6 <= p.y <= y + h + 1e-6 for p in i)
    assert len([m for m in metinler(liste)]) >= 6                                # her iki eksende etiket


def test_dagilim_x_eksik_nokta_cizilmez_ve_x_ekseni_sayisal():
    liste = ciz(veri(seri("A", [5, 6], x=[None, 2.0])), tur="dagilim", gosterge=None)
    assert len(tur(liste, Isaret)) == 1


def test_dagilim_ayni_piksel_tekilles():
    n = 5000
    liste = ciz(veri(seri("A", [1.0] * n, x=[1.0] * n)), tur="dagilim", gosterge=None)
    assert len(tur(liste, Isaret)) == 1


# ------------------------------------------------------------------ gösterge / boş / düzen
@pytest.mark.parametrize("konum", ["sag", "sol", "ust", "alt"])
def test_gosterge_konumlari_alani_daraltir(konum):
    v = veri(seri("Birinci", [1, 2]), seri("İkinci", [2, 1]))
    bos = ciz(v, tur="sutun", gosterge=None)
    liste = ciz(v, tur="sutun", gosterge=konum)
    ax, ay, aw, ah = bos.grafik_alani
    x, y, w, h = liste.grafik_alani
    if konum in ("sag", "sol"):
        assert w < aw
    else:
        assert h < ah
    ad = [o for o in tur(liste, Metin) if o.metin == "Birinci"][0]
    assert {"sag": ad.x > x + w, "sol": ad.x < x, "ust": ad.y < y, "alt": ad.y > y + h}[konum]   # gösterge çizim alanının dışında


def test_tek_seri_gosterge_acik_ise_cizilir_kapaliysa_cizilmez():
    v = veri(seri("Tek", [1, 2]))
    assert "Tek" in metinler(ciz(v, tur="sutun", gosterge="sag"))
    assert "Tek" not in metinler(ciz(v, tur="sutun", gosterge=None))


def test_veri_yok_mesaji_ve_baslik():
    liste = ciz(veri(), tur="sutun", baslik="Boş")
    assert VERI_YOK in metinler(liste) and "Boş" in metinler(liste)
    assert len(tur(liste, Dikdortgen)) == 1                                      # yalnız grafik alanı
    assert VERI_YOK in metinler(ciz(veri(seri("A", [None, None])), tur="cizgi"))


def test_tum_ogeler_grafik_sinirlari_icinde():
    v = veri(seri("Ocak Şubat Mart", [10, -20, 30], ["Kategori bir", "Kategori iki", "Kategori üç"]),
             seri("B", [5, 5, 5]))
    for t in ("sutun", "cubuk", "cizgi", "alan"):
        liste = ciz(v, tur=t, baslik="Başlık", x_baslik="X", y_baslik="Y", gosterge="sag")
        for o in liste:
            if isinstance(o, Metin):
                assert -1 <= o.x <= W + 1 and -1 <= o.y <= H + 1, (t, o)
            elif isinstance(o, Dikdortgen):
                assert -1 <= o.x and o.x + o.w <= W + 1 and -1 <= o.y and o.y + o.h <= H + 1, (t, o)
            elif isinstance(o, Cizgi):
                assert -1 <= min(o.x1, o.x2) and max(o.x1, o.x2) <= W + 1, (t, o)


def test_olcek_boyutlari_ve_yazilari_carpar():
    v = veri(seri("A", [1, 2]))
    k = ciz(v, tur="sutun", gosterge=None, baslik="B")
    b = ciz(v, tur="sutun", gosterge=None, baslik="B", boyut=(2 * W, 2 * H), olcek=2.0)
    assert [o.pt for o in tur(b, Metin) if o.metin == "B"][0] == 2 * [o.pt for o in tur(k, Metin) if o.metin == "B"][0]
    assert b.grafik_alani[2] == pytest.approx(2 * k.grafik_alani[2], rel=0.05)


def test_seri_renk_gecersiz_kilma():
    liste = ciz(veri(seri("A", [1, 2], renk="#112233")), tur="sutun", gosterge=None)
    assert all(d.dolgu == "#112233" for d in cubuklar(liste))


def test_ayni_veri_ayni_liste_deterministik():
    v = veri(seri("A", [3, 1, 2]), seri("B", [1, 2, 3]))
    assert ciz(v, tur="sutun") == ciz(v, tur="sutun")


# ------------------------------------------------------------------ min/max boşaltma
def test_min_max_bosalt_uc_degerler_korunur_ve_sira():
    xs = [i * 0.1 for i in range(1000)]
    ys = [(i % 10) for i in range(1000)]
    out = min_max_bosalt(xs, ys, 1.0)
    assert len(out) <= 2 * 100 + 2
    assert min(p[1] for p in out) == 0 and max(p[1] for p in out) == 9
    px = [p[0] for p in out]
    assert px == sorted(px)


def test_min_max_bosalt_bosluk_korunur_ve_sondaki_atilir():
    out = min_max_bosalt([0, 1, 2, 3, 4], [1, None, None, 2, None], 0.5)
    assert out == [(0, 1), None, (3, 2)]
    assert min_max_bosalt([], [], 1.0) == []
