"""Faz 10b: şablon üretici (tanım + cevaplar → kitap). Tüm cevap kombinasyonlarında Tablo Sağlık Kontrolü 0 bulgu (kural 22)."""
import itertools
from pathlib import Path

import pytest

from tabcel.formul import saglik
from tabcel.formul.motor import Hesaplayici
from tabcel.model import deger as D
from tabcel.model.dogrulama import liste_sabiti_ogeleri
from tabcel.model.sayfa import Hucre
from tabcel.sablon import sema, uretici, yukleyici
from tabcel.sablon.uretici import UretimHatasi, uret

SORULAR = ("varyant", "depo", "fiyat", "cari")


@pytest.fixture(scope="module")
def sablon():
    d = yukleyici.depo_yukle(yukleyici.yerlesik_klasor(), Path("yok_klasor"))
    return d.bul("yerlesik:stok_takibi")


def tum_cevaplar():
    for kombo in itertools.product([False, True], repeat=len(SORULAR)):
        yield dict(zip(SORULAR, kombo))


def sayfa_(sonuc, ad):
    return next(s for s in sonuc.kitap.sayfalar if s.ad == ad)


# ---------------------------------------------------------------- yapı
def test_varsayilan_cevaplar(sablon):
    r = uret(sablon)
    assert [s.ad for s in r.kitap.sayfalar] == ["Ürünler", "Stok Hareketleri", "Stok Durumu", "Ayarlar", "Nasıl Kullanılır"]
    assert r.bayraklar["fiyat_takibi"] is True and r.bayraklar["coklu_depo"] is False
    urun = sayfa_(r, "Ürünler")
    basliklar = [urun.deger(1, c) for c in range(1, 9)]
    assert basliklar[:7] == ["Ürün kodu", "Ürün adı", "Barkod", "Birim", "Alış fiyatı", "Satış fiyatı", "Kritik stok"]
    assert urun.dondur == (2, 1)


@pytest.mark.parametrize("cevap", list(tum_cevaplar()), ids=lambda c: "".join("1" if v else "0" for v in c.values()))
def test_her_kombinasyonda_saglik_0_bulgu(sablon, cevap):
    r = uret(sablon, cevap, ornek_veri=True)
    motor = Hesaplayici(r.kitap)
    bulgular = saglik.Tarayici(r.kitap, motor).tara()
    assert bulgular == [], [(b.kontrol, b.sayfa_ad, b.baslik) for b in bulgular]
    beklenen = ["Ürünler", "Stok Hareketleri", "Stok Durumu"] + (["Varyantlar"] if cevap["varyant"] else []) + \
               (["Depolar"] if cevap["depo"] else []) + (["Cariler"] if cevap["cari"] else []) + ["Ayarlar", "Nasıl Kullanılır"]
    assert [s.ad for s in r.kitap.sayfalar] == beklenen
    urun = sayfa_(r, "Ürünler")
    assert ("Alış fiyatı" in [urun.deger(1, c) for c in range(1, 9)]) == cevap["fiyat"]
    hareket = sayfa_(r, "Stok Hareketleri")
    h = [hareket.deger(1, c) for c in range(1, 9)]
    assert ("Depo" in h) == cevap["depo"] and ("Cari" in h) == cevap["cari"]
    for s in r.kitap.sayfalar:                                           # hiçbir hücrede hata değeri yok
        for (satir, sutun), _ in s._hucreler.items():
            assert not isinstance(s.deger(satir, sutun), D.Hata), (s.ad, satir, sutun)


def test_stok_hesabi_ornek_veriyle(sablon):
    r = uret(sablon, ornek_veri=True)
    Hesaplayici(r.kitap)
    sd = sayfa_(r, "Stok Durumu")
    assert [sd.deger(2, c) for c in range(1, 6)] == ["U001", 50.0, 8.0, 42.0, "Yeterli"]
    assert [sd.deger(3, c) for c in range(1, 6)] == ["U002", 100.0, 0.0, 100.0, "Yeterli"]
    assert sd.deger(4, 1) == "" and sd.deger(4, 4) == ""                 # ürün olmayan satır boş görünür
    assert r.ornek_satirlar == {"urunler": [2, 3], "stok_hareketleri": [2, 3, 4]}


def test_stok_degisince_yeniden_hesaplanir_kritik_uyari(sablon):
    r = uret(sablon, ornek_veri=True)
    Hesaplayici(r.kitap)
    hareket, sd = sayfa_(r, "Stok Hareketleri"), sayfa_(r, "Stok Durumu")
    # U001: 42 mevcut, kritik 10 → 35 adet çıkış: 7 ≤ 10 → Kritik
    hareket.ata(5, 1, Hucre(46000.0))
    hareket.ata(5, 2, Hucre("U001"))
    hareket.ata(5, 3, Hucre("Çıkış"))
    hareket.ata(5, 4, Hucre(35.0))
    assert sd.deger(2, 4) == 7.0 and sd.deger(2, 5) == "Kritik"


def test_ornek_veri_istege_bagli(sablon):
    r = uret(sablon, ornek_veri=False)
    assert r.ornek_satirlar == {} and sayfa_(r, "Ürünler").deger(2, 1) is None
    r = uret(sablon)                                                      # akış kararı: ornek_veri true
    assert sayfa_(r, "Ürünler").deger(2, 1) == "U001"


def test_tanimli_adlar(sablon):
    r = uret(sablon, {"depo": True})
    k = r.kitap
    urun = sayfa_(r, "Ürünler")
    assert k.ad_bul("TR_M_urunler_urun_kodu").formul == f"=[{urun.kimlik}]!$A$2:$A$20001"
    assert k.ad_bul("TR_MOD_urunler").formul == f"=[{urun.kimlik}]!$A$1:$G$1"
    assert k.ad_bul("TR_V_urunler").formul == f"=[{urun.kimlik}]!$A$2:$G$20001"
    ayar = sayfa_(r, "Ayarlar")
    assert k.ad_bul("TR_AYAR_kdv").formul == f"=[{ayar.kimlik}]!$B$2"
    assert ayar.deger(2, 2) == 0.2 and ayar.deger(3, 2) == "TRY"
    assert r.ayar_yerleri["kdv"] == (ayar.kimlik, 2)
    assert k.ad_bul("TR_M_depolar_depo_adi") is not None
    r2 = uret(sablon)                                                      # depo kapalı: ad yok
    assert r2.kitap.ad_bul("TR_M_depolar_depo_adi") is None


def test_formuller_kanonik_ve_yer_tutucusuz(sablon):
    r = uret(sablon)
    sd = sayfa_(r, "Stok Durumu")
    assert sd._hucreler[(2, 4)].formul == '=IF($A2="","",$B2-$C2)'
    assert sd._hucreler[(5, 2)].formul.startswith('=IF($A5="","",SUMIFS(TR_M_stok_hareketleri_miktar,TR_M_stok_hareketleri_urun,$A5,')
    assert sd._hucreler[(2, 1)].formul == '=IFERROR(INDEX(TR_M_urunler_urun_kodu,ROW()-1)&"","")'
    for s in r.kitap.sayfalar:
        for h in s._hucreler.values():
            assert h.formul is None or ("[" not in h.formul and "AYAR." not in h.formul), h.formul
    assert sd._hucreler.get((201, 2)) is not None and sd._hucreler.get((202, 2)) is None       # formul_satiri = 200


def test_sayi_bicimleri(sablon):
    r = uret(sablon)
    urun = sayfa_(r, "Ürünler")
    kod = lambda sutun: urun.havuz.stil(urun.sutun_stil.get(sutun, 0)).sayi_bicimi              # noqa: E731
    assert kod(3) == "@" and kod(5) == '"₺"#,##0.00' and kod(7) == "#,##0" and kod(1) == "General"
    h = sayfa_(r, "Stok Hareketleri")
    assert h.havuz.stil(h.sutun_stil[1]).sayi_bicimi == "dd.mm.yyyy"
    # para birimi ayarı üretimde okunur
    from copy import deepcopy
    s2 = deepcopy(sablon)
    s2.akis.ayarlar[1].varsayilan = "USD"
    r2 = uret(s2)
    u2 = sayfa_(r2, "Ürünler")
    assert u2.havuz.stil(u2.sutun_stil[5]).sayi_bicimi == '"$"#,##0.00'
    s2.akis.ayarlar[1].varsayilan = "CHF"
    assert sayfa_(uret(s2), "Ürünler").havuz.stil(sayfa_(uret(s2), "Ürünler").sutun_stil[5]).sayi_bicimi == '#,##0.00 "CHF"'


# ---------------------------------------------------------------- doğrulama
def dv(sayfa, satir, sutun):
    return sayfa.dogrulama(satir, sutun)


def test_dogrulamalar(sablon):
    r = uret(sablon, {"depo": True, "cari": True})
    urun, hareket, cari = sayfa_(r, "Ürünler"), sayfa_(r, "Stok Hareketleri"), sayfa_(r, "Cariler")
    kod = dv(urun, 2, 1)                                                   # zorunlu + benzersiz metin
    assert kod.tur == "ozel" and kod.formul1 == "=AND(LEN(A2)>0,COUNTIF($A$2:$A$20001,A2)=1)" and not kod.bos_yoksay
    assert dv(urun, 20001, 1) is kod and dv(urun, 20002, 1) is None and dv(urun, 1, 1) is None      # başlık kapsam dışı
    assert dv(urun, 2, 3).formul1 == "=COUNTIF($C$2:$C$20001,C2)=1" and dv(urun, 2, 3).bos_yoksay      # barkod benzersiz, zorunlu değil
    assert dv(urun, 2, 5).tur == "ondalik" and dv(urun, 2, 5).islec == "buyuk_esit" and dv(urun, 2, 5).formul1 == "=0"
    assert dv(urun, 2, 4) is None                                           # serbest metin, açıklamasız
    assert dv(urun, 2, 7).tur == "tam_sayi" and dv(urun, 2, 7).giris == (True, "Kritik stok", "Stok bu sayıya düşünce Stok Durumu'nda uyarı çıkar.")
    tur = dv(hareket, 2, 3)
    assert tur.tur == "liste" and liste_sabiti_ogeleri(tur.formul1) == ["Giriş", "Çıkış"]
    assert dv(hareket, 2, 2).tur == "liste" and dv(hareket, 2, 2).formul1 == "=TR_M_urunler_urun_kodu"
    assert dv(hareket, 2, 5).formul1 == "=TR_M_depolar_depo_adi"
    assert dv(hareket, 2, 4).islec == "buyuk_esit" and dv(hareket, 2, 4).formul1 == "=1" and not dv(hareket, 2, 4).bos_yoksay
    assert dv(hareket, 2, 1).tur == "tarih" and not dv(hareket, 2, 1).bos_yoksay
    assert dv(cari, 2, 3).formul1 == "=TR_VALIDATE_PHONE(C2)" and dv(cari, 2, 4).formul1 == "=TR_VALIDATE_EMAIL(D2)"
    assert dv(cari, 2, 5).formul1 == "=TR_VALIDATE_VKN(E2)"
    assert liste_sabiti_ogeleri(dv(cari, 2, 2).formul1) == ["Müşteri", "Tedarikçi"]
    assert dv(sayfa_(r, "Stok Durumu"), 2, 2) is None                      # hesaplanan sütun: doğrulama yok


def test_kimlik_turu_sutunlari_metin_ve_dogrulayici():
    """tc_kimlik / iban sütunları: metin biçimi (baştaki sıfır), kimlik.py tabanlı özel doğrulama (kural 15, 18)."""
    s = sema.Sutun("tc", "T.C. kimlik no", "tc_kimlik", zorunlu=True)
    assert uretici.sayi_bicimi(s, {}) == "@"
    d = uretici._dogrulama(s, "B", 2, 100)
    assert d.formul1 == "=AND(LEN(B2)>0,TR_VALIDATE_TCKN(B2))" and not d.bos_yoksay
    d = uretici._dogrulama(sema.Sutun("ib", "IBAN", "iban"), "C", 3, 100)
    assert d.formul1 == "=TR_VALIDATE_IBAN(C2)" and d.bos_yoksay


def test_dogrulama_kisit_birlesimleri():
    kisit = lambda **k: sema.Sutun("x", "X", "tam_sayi", kisit=k)                                  # noqa: E731
    d = uretici._dogrulama(kisit(min=1, max=9), "A", 1, 10)
    assert (d.tur, d.islec, d.formul1, d.formul2) == ("tam_sayi", "arasinda", "=1", "=9")
    d = uretici._dogrulama(kisit(max=2.5), "A", 1, 10)
    assert d.islec == "kucuk_esit" and d.formul1 == "=2.5"
    d = uretici._dogrulama(sema.Sutun("x", "X", "metin", kisit={"uzunluk": 5}), "A", 1, 10)
    assert d.tur == "metin_uzunlugu" and d.formul1 == "=5"
    d = uretici._dogrulama(sema.Sutun("x", "X", "ondalik", benzersiz=True, kisit={"min": 0}), "A", 1, 10)
    assert d.tur == "ozel" and d.formul1 == "=AND(COUNTIF($A$2:$A$11,A2)=1,A2>=0)"
    assert uretici._dogrulama(sema.Sutun("x", "X", "metin"), "A", 1, 10) is None


# ---------------------------------------------------------------- hata durumları
def test_bilinmeyen_soru(sablon):
    with pytest.raises(UretimHatasi, match='Bilinmeyen soru: "yok"'):
        uret(sablon, {"yok": True})


def test_kapali_sutuna_basvuru_hatasi(sablon):
    from copy import deepcopy
    s2 = deepcopy(sablon)
    s2.moduller["stok_durumu"].sutunlar[4].formul = "=[@alis_fiyati]"                  # bu modülde böyle sütun yok
    with pytest.raises(UretimHatasi, match="kapalı ya da olmayan bir sütun"):
        uret(s2)
    s3 = deepcopy(sablon)
    s3.moduller["stok_durumu"].sutunlar[4].formul = "=[urunler.alis_fiyati]"            # başka modülün kapalı sütunu
    with pytest.raises(UretimHatasi, match='"alis_fiyati" sütunu bu çalıştırmada kapalı'):
        uret(s3, {"fiyat": False})
    uret(s3, {"fiyat": True})


def test_kapali_modul_basvurusu(sablon):
    from copy import deepcopy
    s2 = deepcopy(sablon)
    s2.moduller["stok_durumu"].sutunlar[1].formul = "=COUNTA([depolar.depo_adi])"
    with pytest.raises(UretimHatasi, match='"depolar" modülü bu çalıştırmada kapalı'):
        uret(s2, {"depo": False})
    uret(s2, {"depo": True})


def test_ayni_sayfa_adi(sablon):
    from copy import deepcopy
    s2 = deepcopy(sablon)
    s2.moduller["stok_durumu"].sayfa_adi = "ÜRÜNLER"
    with pytest.raises(UretimHatasi, match="birden çok kez"):
        uret(s2)


def test_kotu_ornek_veri(sablon):
    from copy import deepcopy
    s2 = deepcopy(sablon)
    s2.moduller["stok_hareketleri"].ornek_veri[0]["tarih"] = "5 Ocak"
    with pytest.raises(UretimHatasi, match="yyyy-aa-gg"):
        uret(s2, ornek_veri=True)


def test_eger_soru_atlanabilir():
    from tabcel.sablon.sema import Akis, Soru
    a = Akis(1, "a", "A", "K", "x", ["abc"], [], 1.0,
             [Soru("ana", "?", varsayilan=True), Soru("alt", "?", varsayilan=True, eger="!ana")], [("m", None)], {"b": "alt"}, [], [])
    assert uretici.bayraklari_coz(a) == {"ana": True, "alt": False, "b": False}                  # alt, ana doğruyken atlanır
    assert uretici.bayraklari_coz(a, {"ana": False}) == {"ana": False, "alt": True, "b": True}


# ---------------------------------------------------------------- gidiş-dönüş
def test_xlsx_gidis_donus(sablon, tmp_path):
    from tabcel.io import xlsx_io
    r = uret(sablon, {"depo": True}, ornek_veri=True)
    yol = str(tmp_path / "stok.xlsx")
    xlsx_io.kaydet(r.kitap, yol)
    k2, rapor = xlsx_io.ac(yol)
    assert not rapor.veri_kaybi, rapor.uyarilar if hasattr(rapor, "uyarilar") else rapor
    assert [s.ad for s in k2.sayfalar] == [s.ad for s in r.kitap.sayfalar]
    Hesaplayici(k2)
    sd = next(s for s in k2.sayfalar if s.ad == "Stok Durumu")
    assert sd.deger(2, 4) == 42.0
    assert k2.ad_bul("TR_M_urunler_urun_kodu") is not None
    urun = next(s for s in k2.sayfalar if s.ad == "Ürünler")
    assert urun.dogrulama(2, 1) is not None and urun.dondur == (2, 1)
