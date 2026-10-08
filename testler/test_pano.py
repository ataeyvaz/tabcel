import pytest

from tabcel.model.adres import MAX_COL, MAX_ROW, AdresHatasi, Aralik
from tabcel.model.pano import (
    PanoVerisi, html_tablo_coz, html_yaz, metin_satirlari, metinden_pano_verisi,
    pano_araligi, pano_verisi_al, tsv_coz, tsv_yaz, yapistirma_plani,
)
from tabcel.model.sayfa import Hucre, Sayfa


def H(d):
    return Hucre(d)


# --- TSV ---
def test_tsv_yaz_basit_ve_tirnak():
    assert tsv_yaz([["a", "b"], ["1,5", ""]]) == "a\tb\r\n1,5\t\r\n"
    assert tsv_yaz([['x"y', "p\tq", "i\nj"]]) == '"x""y"\t"p\tq"\t"i\nj"\r\n'


@pytest.mark.parametrize("satirlar", [
    [["a", "b"], ["c", "d"]],
    [["", "x"], ["y", ""]],
    [['tırnak"lı', "sekme\tli", "satır\nlı"]],
    [["tek"]],
    [['"', '""', ' "x" ']],
])
def test_tsv_gidis_donus(satirlar):
    assert tsv_coz(tsv_yaz(satirlar)) == satirlar


def test_tsv_coz_bicimleri():
    assert tsv_coz("a\tb\nc\td") == [["a", "b"], ["c", "d"]]          # sondaki satır sonu yok
    assert tsv_coz("a\tb\r\nc\td\r\n") == [["a", "b"], ["c", "d"]]
    assert tsv_coz("tek") == [["tek"]]
    assert tsv_coz("") == []
    assert tsv_coz("a\t\tb") == [["a", "", "b"]]
    assert tsv_coz('"a\nb"\tc') == [["a\nb", "c"]]
    assert tsv_coz("a\tb\n\nc") == [["a", "b"], [""], ["c"]]          # boş satır korunur


# --- HTML ---
def test_html_yaz_ve_coz_gidis_donus():
    satirlar = [["a<b", "x&y"], ["çok\nsatır", ""]]
    assert html_tablo_coz(html_yaz(satirlar)) == satirlar


def test_html_excel_benzeri_tablo():
    html = ("<html><body><!--StartFragment--><table style='border:1px'>"
            "<tr><td style='x'>Ürün</td><td>Adet</td></tr>\r\n"
            "<tr><td>Kalem&nbsp;1</td><td align=right>1.234,5</td></tr>"
            "</table><!--EndFragment--></body></html>")
    assert html_tablo_coz(html) == [["Ürün", "Adet"], ["Kalem 1", "1.234,5"]]


def test_html_colspan_baslik_ic_ice_tablo_ve_bosluklar():
    html = ("<table><tr><th colspan=2>Başlık</th></tr>"
            "<tr><td>  a\n   b  </td><td><table><tr><td>iç</td></tr></table></td></tr></table>")
    s = html_tablo_coz(html)
    assert s[0] == ["Başlık", ""]
    assert s[1][0] == "a b"          # kaynak satır sonu/boşluk tek boşluk


def test_html_tablo_yok_ya_da_bozuk():
    assert html_tablo_coz("<p>sadece metin</p>") == []
    assert html_tablo_coz("") == []
    assert html_tablo_coz("<table><tr><td>a") == []      # kapanmamış satır eklenmez, çökmez


def test_html_script_icerigi_yoksayilir():
    assert html_tablo_coz("<table><tr><td>a<script>var x=1;</script></td></tr></table>") == [["a"]]


# --- kopyalanan veri ---
def dolu_sayfa():
    s = Sayfa("S")
    s.ata(2, 2, H("ad"))
    s.ata(2, 3, H(1.5))
    s.ata(3, 2, Hucre(None, "=B2"))
    s.ata(5, 5, H(True))
    return s


def test_pano_verisi_al_goreli_konum():
    v = pano_verisi_al(dolu_sayfa(), Aralik(2, 2, 3, 3))
    assert (v.satir_sayisi, v.sutun_sayisi) == (2, 2)
    assert v.hucreler == {(0, 0): H("ad"), (0, 1): H(1.5), (1, 0): Hucre(None, "=B2")}


def test_pano_araligi_kullanilanla_sinirlanir():
    s = dolu_sayfa()
    assert pano_araligi(s, Aralik(1, 1, MAX_ROW, MAX_COL)) == Aralik(1, 1, 5, 5)
    assert pano_araligi(s, Aralik(2, 3, MAX_ROW, 3)) == Aralik(2, 3, 5, 3)      # tam sütun
    assert pano_araligi(Sayfa("B"), Aralik(4, 4, 9, 9)) == Aralik(4, 4, 4, 4)   # boş sayfa
    assert pano_araligi(s, Aralik(20, 20, 30, 30)) == Aralik(20, 20, 20, 20)    # veri dışı


def test_json_gidis_donus_turleri_korur():
    v = pano_verisi_al(dolu_sayfa(), Aralik(2, 2, 5, 5))
    geri = PanoVerisi.json_oku(v.json_yaz())
    assert geri == v
    assert geri.hucreler[(3, 3)].deger is True
    assert isinstance(geri.hucreler[(0, 1)].deger, float)


def test_metin_satirlari_gosterim():
    v = pano_verisi_al(dolu_sayfa(), Aralik(2, 2, 3, 3))
    assert metin_satirlari(v) == [["ad", "1,5"], ["=B2", ""]]


def test_metinden_pano_verisi_girdi_gibi_cozer():
    v = metinden_pano_verisi([["Ürün", "1.234,5", "doğru"], ["=A1", "'007"]])
    assert v.hucreler[(0, 0)] == H("Ürün")
    assert v.hucreler[(0, 1)] == H(1234.5)
    assert v.hucreler[(0, 2)] == H(True)
    assert v.hucreler[(1, 0)] == Hucre(None, "=A1")
    assert v.hucreler[(1, 1)] == H("007")
    assert (v.satir_sayisi, v.sutun_sayisi) == (2, 3)
    assert metinden_pano_verisi([]) is None


def test_duzensiz_satirlar_dikdortgen_olur():
    v = metinden_pano_verisi([["a"], ["b", "c", "d"]])
    assert (v.satir_sayisi, v.sutun_sayisi) == (2, 3)


# --- yapıştırma planı ---
def test_plan_ust_sol_koseye():
    v = metinden_pano_verisi([["a", ""], ["", "d"]])
    plan = yapistirma_plani(v, 4, 2)
    assert plan == {(4, 2): H("a"), (4, 3): None, (5, 2): None, (5, 3): H("d")}


def test_plan_tek_hucre_secime_yayilir():
    v = metinden_pano_verisi([["x"]])
    plan = yapistirma_plani(v, 1, 1, Aralik(2, 2, 3, 4))
    assert set(plan) == {(r, c) for r in (2, 3) for c in (2, 3, 4)}
    assert all(h == H("x") for h in plan.values())


def test_plan_desen_tam_kat_ise_yinelenir():
    v = metinden_pano_verisi([["a", "b"]])
    plan = yapistirma_plani(v, 1, 1, Aralik(1, 1, 2, 4))
    assert plan[(1, 1)] == H("a") and plan[(1, 2)] == H("b")
    assert plan[(1, 3)] == H("a") and plan[(2, 4)] == H("b")


def test_plan_kat_degilse_ust_sol_koseye():
    v = metinden_pano_verisi([["a", "b"]])
    plan = yapistirma_plani(v, 7, 7, Aralik(7, 7, 8, 9))           # 3 sütun, 2'nin katı değil
    assert set(plan) == {(7, 7), (7, 8)}


def test_plan_sinir_asimi():
    v = metinden_pano_verisi([["a"], ["b"]])
    with pytest.raises(AdresHatasi):
        yapistirma_plani(v, MAX_ROW, 1)
    v2 = metinden_pano_verisi([["a", "b"]])
    with pytest.raises(AdresHatasi):
        yapistirma_plani(v2, 1, MAX_COL)
    yapistirma_plani(v2, 1, MAX_COL - 1)                            # tam sığar


def test_plan_tam_sutun_secimine_tek_hucre_asiri_yayilmaz():
    v = metinden_pano_verisi([["x"]])
    plan = yapistirma_plani(v, 3, 3, Aralik(1, 3, MAX_ROW, 3))      # 1 milyon hücre > sınır
    assert plan == {(3, 3): H("x")}


def test_k4_pano_formul_sonucunu_metin_olarak_verir_girdiyi_json_ile():
    from tabcel.model.deger import BOL0
    s = Sayfa("S")
    s.ata(1, 1, Hucre(None, "=A2*2"))
    s.sonuc_ata(1, 1, 10.0)
    s.ata(1, 2, Hucre(None, "=1/0"))
    s.sonuc_ata(1, 2, BOL0)
    s.ata(1, 3, Hucre(None, "=ABC"))                           # henüz hesaplanmamış
    v = pano_verisi_al(s, Aralik(1, 1, 1, 3))
    assert metin_satirlari(v) == [["10", "#BÖL/0!", "=ABC"]]
    geri = PanoVerisi.json_oku(v.json_yaz())
    assert geri.hucreler[(0, 0)] == Hucre(None, "=A2*2")       # kendi biçimimiz yalnız girdiyi taşır
    assert geri.sonuclar == {}
