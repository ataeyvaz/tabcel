"""Faz 10a: şablon şeması, doğrulayıcı, yükleyici (yerleşik + kullanıcı klasörü, sürüm göçü, rapor), eşleştirici."""
import copy
import json
import shutil
from pathlib import Path

import pytest

from tabcel.sablon import eslestirici, sema, yukleyici

YERLESIK = yukleyici.yerlesik_klasor()
YERLESIK_KIMLIKLER = ["yerlesik:apartman_aidat", "yerlesik:cari_hesap", "yerlesik:cek_senet", "yerlesik:not_cizelgesi",
                      "yerlesik:stok_takibi", "yerlesik:teklif_formu"]          # Faz 10e: 6 akış


def _json(yol):
    return json.loads(Path(yol).read_text(encoding="utf-8"))


def yaz(yol: Path, d):
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(d if isinstance(d, str) else json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return yol


@pytest.fixture(scope="module")
def depo():
    return yukleyici.depo_yukle(YERLESIK, Path("yok_klasor"))


MODUL = _json(YERLESIK / "moduller" / "urunler.json")
AKIS = _json(YERLESIK / "akislar" / "stok_takibi.json")


def hatalar_(h):
    return [str(x) for x in h if not x.uyari]


# ---------------------------------------------------------------- yerleşik tanımlar
def test_yerlesik_temiz_yuklenir(depo):
    assert depo.rapor.temiz, depo.rapor.metin()
    assert [s.ic_kimlik for s in depo.sablonlar] == YERLESIK_KIMLIKLER
    s = depo.bul("yerlesik:stok_takibi")
    assert s.etiket == "Stok takibi" and len(s.akis.sorular) == 4 and len(s.moduller) == 6
    assert s.moduller["urunler"].sutun("alis_fiyati").para_birimi == "ayar:para_birimi"
    assert s.moduller["stok_hareketleri"].kurallar[0].siddet == "durdur"


def test_yerlesik_dosyalarda_surum_ve_aciklama():
    """Kural 22: her tanımda `surum` ve `aciklama`."""
    dosyalar = list(YERLESIK.rglob("*.json"))
    assert len(dosyalar) >= 7
    for p in dosyalar:
        d = _json(p)
        assert d["surum"] == sema.SURUM and d["aciklama"].strip(), p.name
        assert not [x for x in (sema.akis_ayristir(d) if d["tur"] == "akis" else sema.modul_ayristir(d))[1]], p.name  # uyarı da yok


def test_tc_kimlik_turleri_metin_turu_kumesinde():
    assert {"tc_kimlik", "vergi_no", "iban", "telefon", "eposta"} <= set(sema.TURLER)


# ---------------------------------------------------------------- modül doğrulayıcı
def degistir(d, *yol, deger):
    d = copy.deepcopy(d)
    hedef = d
    for k in yol[:-1]:
        hedef = hedef[k]
    if deger is KALDIR:
        del hedef[yol[-1]]
    else:
        hedef[yol[-1]] = deger
    return d


KALDIR = object()


@pytest.mark.parametrize("yol, deger, beklenen", [
    (("kimlik",), "Urunler", "geçersiz kimlik"),                               # büyük harf
    (("kimlik",), KALDIR, "zorunlu alan eksik"),
    (("aciklama",), "  ", "boş olmayan metin"),
    (("surum",), "1", "surum"),
    (("tur",), "akis", '"modul" olmalı'),
    (("sayfa_adi",), "Ürün:ler", "içeremez"),
    (("sayfa_adi",), "x" * 32, "31 karakter"),
    (("sutunlar",), [], "boş olamaz"),
    (("sutunlar", 0, "tur"), "para2", 'bilinmeyen tür "para2"'),
    (("sutunlar", 1, "kimlik"), "urun_kodu", "yinelendi"),
    (("sutunlar", 0, "formul"), "=1", 'yalnız "hesaplanan"'),
    (("sutunlar", 0, "baglanti"), {"modul": "a", "alan": "b"}, 'yalnız "baglanti"'),
    (("sutunlar", 4, "para_birimi"), "tl", "üç harfli"),
    (("sutunlar", 3, "para_birimi"), "TRY", 'yalnız "para"'),
    (("sutunlar", 6, "kisit"), {"min": 5, "max": 1}, "min, max'tan büyük"),
    (("sutunlar", 6, "kisit"), {"min": "a"}, "sayı olmalı"),
    (("sutunlar", 0, "zorunlu"), "evet", "doğru/yanlış"),
    (("sutunlar", 0, "eger"), "Fiyat Takibi", "bayrak adı"),
    (("gorunen",), ["yok_sutun"], "adlı sütun yok"),
    (("ornek_veri", 0, "yok"), 1, "böyle bir sütun yok"),
    (("ornek_veri", 0, "ad"), [1], "değer metin, sayı"),
])
def test_modul_hatalari(yol, deger, beklenen):
    d = degistir(MODUL, *yol, deger=deger)
    m, h = sema.modul_ayristir(d)
    assert m is None and any(beklenen in x for x in hatalar_(h)), hatalar_(h)


def test_modul_liste_ve_baglanti_zorunlulugu():
    d = copy.deepcopy(AKIS)                       # kullanılmayan; yalnız modül sözlükleri
    hm = _json(YERLESIK / "moduller" / "stok_hareketleri.json")
    d = degistir(hm, "sutunlar", 2, "secenekler", deger=["A", "A"])
    assert any("yinelenen seçenek" in x for x in hatalar_(sema.modul_ayristir(d)[1]))
    d = degistir(hm, "sutunlar", 2, "secenekler", deger=KALDIR)
    assert any("boş olmayan metin listesi" in x for x in hatalar_(sema.modul_ayristir(d)[1]))
    d = degistir(hm, "sutunlar", 1, "baglanti", deger=KALDIR)
    assert any('"baglanti" türünde' in x for x in hatalar_(sema.modul_ayristir(d)[1]))


def test_formul_yer_tutucu_hatalari():
    sd = _json(YERLESIK / "moduller" / "stok_durumu.json")
    for formul, beklenen in [("=[@yok]+1", 'bu modülde "yok" sütunu yok'), ('=IF([@giris]="a', "kapanmamış tırnak"),
                             ("=SUM([@giris]", "parantezler"), ("=[@Giris]", "geçersiz yer tutucu"),
                             ("=[a.b.c]", "geçersiz yer tutucu")]:
        d = degistir(sd, "sutunlar", 3, "formul", deger=formul)
        assert any(beklenen in x for x in hatalar_(sema.modul_ayristir(d)[1])), (formul, beklenen)
    d = degistir(sd, "sutunlar", 3, "formul", deger="1+1")
    assert any('"=" ile başlayan' in x for x in hatalar_(sema.modul_ayristir(d)[1]))


def test_kural_hatalari():
    hm = _json(YERLESIK / "moduller" / "stok_hareketleri.json")
    for yol, deger, beklenen in [(("kurallar", 0, "siddet"), "ciddi", '"durdur" ya da "uyar"'),
                                 (("kurallar", 0, "ileti"), KALDIR, "zorunlu alan eksik"),
                                 (("kurallar", 0, "formul"), "1=1", '"=" ile başlamalı')]:
        d = degistir(hm, *yol, deger=deger)
        assert any(beklenen in x for x in hatalar_(sema.modul_ayristir(d)[1])), (yol, beklenen)


def test_bilinmeyen_alan_uyari_modul_yuklenir():
    d = degistir(MODUL, "gelecek_alan", deger=1)
    m, h = sema.modul_ayristir(d)
    assert m is not None and [x.uyari for x in h] == [True] and "bilinmeyen alan" in str(h[0])


def test_modul_ust_duzey_nesne_degil():
    m, h = sema.modul_ayristir([1, 2])
    assert m is None and "nesne" in str(h[0])


# ---------------------------------------------------------------- akış doğrulayıcı
@pytest.mark.parametrize("yol, deger, beklenen", [
    (("kategori",), KALDIR, "zorunlu alan eksik"),
    (("anahtar_kelimeler",), KALDIR, "zorunlu alan eksik"),
    (("anahtar_kelimeler", "kokler"), [], "boş olamaz"),
    (("anahtar_kelimeler", "kokler"), ["ab"], "en az 3 harf"),
    (("anahtar_kelimeler", "agirlik"), 0, "sıfırdan büyük"),
    (("sorular", 0, "kimlik"), "depo", "yinelendi"),
    (("sorular", 0, "tur"), "sayi", "evet_hayir"),
    (("sorular", 0, "eger"), "yok_bayrak", "bilinmeyen bayrak"),
    (("moduller",), [], "boş olamaz"),
    (("moduller", 3, "eger"), "yok_bayrak", "bilinmeyen bayrak"),
    (("moduller", 1, "modul"), "urunler", "yinelendi"),
    (("bayraklar", "fiyat_takibi"), "yok_soru", "adlı soru yok"),
    (("bayraklar", "depo"), "fiyat", "soru kimliğiyle aynı olamaz"),
    (("ayarlar", 0, "tur"), "renk", "bilinmeyen ayar türü"),
    (("ayarlar", 1, "kimlik"), "kdv", "yinelendi"),
    (("nasil_kullanilir", 0, "metin"), "", "boş olmayan metin"),
    (("ornek_veri",), "evet", "doğru/yanlış"),
])
def test_akis_hatalari(yol, deger, beklenen):
    d = degistir(AKIS, *yol, deger=deger)
    a, h = sema.akis_ayristir(d)
    assert a is None and any(beklenen in x for x in hatalar_(h)), hatalar_(h)


def test_akis_en_cok_yedi_soru():
    d = copy.deepcopy(AKIS)
    d["sorular"] = [{"kimlik": f"s{i}", "metin": "?"} for i in range(8)]
    d["bayraklar"] = {}
    d["moduller"] = [{"modul": "urunler"}]
    assert any("en çok 7 soru" in x for x in hatalar_(sema.akis_ayristir(d)[1]))


# ---------------------------------------------------------------- akış × modül uyumu
def _akis_ve_moduller():
    a, _ = sema.akis_ayristir(AKIS)
    moduller = {}
    for p in (YERLESIK / "moduller").glob("*.json"):
        m, _ = sema.modul_ayristir(_json(p))
        moduller[m.kimlik] = m
    return a, moduller


def test_akis_modul_uyumu_temiz():
    a, m = _akis_ve_moduller()
    assert sema.akis_modul_denetle(a, m) == []


def test_akis_modul_uyumsuzluklari():
    a, m = _akis_ve_moduller()
    eksik = {k: v for k, v in m.items() if k != "depolar"}
    h = [str(x) for x in sema.akis_modul_denetle(a, eksik)]
    assert any('"depolar" modülü bulunamadı' in x for x in h)
    assert any('"depolar" modülü bu akışta yok' in x for x in h)                          # stok_hareketleri.depo bağlantısı
    m2 = copy.deepcopy(m)
    m2["stok_durumu"].sutunlar[1].formul = "=[urunler.yok_alan]+AYAR.yok_ayar+[hayali.x]"
    h = [str(x) for x in sema.akis_modul_denetle(a, m2)]
    assert any('"urunler" modülünde "yok_alan" sütunu yok' in x for x in h)
    assert any('"yok_ayar" ayarı yok' in x for x in h)
    assert any('"hayali" modülü bu akışta yok' in x for x in h)
    m3 = copy.deepcopy(m)
    m3["urunler"].sutun("alis_fiyati").eger = "bilinmeyen"
    assert any("bilinmeyen bayrak" in str(x) for x in sema.akis_modul_denetle(a, m3))
    m4 = copy.deepcopy(m)
    m4["stok_hareketleri"].sutun("urun").baglanti = ("urunler", "yok")
    assert any('"urunler" modülünde "yok" sütunu yok' in str(x) for x in sema.akis_modul_denetle(a, m4))


# ---------------------------------------------------------------- yükleyici: dosya hataları
def test_json_bozuk_ve_kodlama(tmp_path):
    p = yaz(tmp_path / "moduller" / "bozuk.json", '{"surum": 1,')
    d, h = yukleyici.json_oku(p)
    assert d is None and "JSON bozuk: satır 1" in str(h[0])
    p2 = tmp_path / "moduller" / "kod.json"
    p2.write_bytes("{}".encode("utf-16"))
    assert "UTF-8" in str(yukleyici.json_oku(p2)[1][0])
    assert "okunamadı" in str(yukleyici.json_oku(tmp_path / "yok.json")[1][0])
    bom = tmp_path / "bom.json"
    bom.write_bytes(b"\xef\xbb\xbf" + b'{"a": 1}')
    assert yukleyici.json_oku(bom)[0] == {"a": 1}


def _kopya(tmp_path):
    hedef = tmp_path / "yerlesik"
    shutil.copytree(YERLESIK, hedef)
    return hedef


def test_kullanici_klasoru_hatali_dosya_atlanir_digerleri_yuklenir(tmp_path):
    kul = tmp_path / "kul"
    yaz(kul / "akislar" / "bozuk.json", "{kapanmamis")
    yaz(kul / "akislar" / "eksik.json", {"surum": 1, "tur": "akis", "kimlik": "eksik"})
    yaz(kul / "moduller" / "kotu_tur.json", degistir(MODUL, "kimlik", deger="kotu_tur") | {"sutunlar": [
        {"kimlik": "a", "ad": "A", "tur": "para2"}]})
    iyi = degistir(AKIS, "kimlik", deger="kendi_stok")
    iyi = degistir(iyi, "ad", deger="Benim stokum")
    yaz(kul / "akislar" / "iyi.json", iyi)
    yaz(kul / "akislar" / "not.txt", "json değil")                                         # yok sayılır
    depo = yukleyici.depo_yukle(YERLESIK, kul)
    assert {s.ic_kimlik for s in depo.sablonlar} == set(YERLESIK_KIMLIKLER) | {"kullanici:kendi_stok"}
    metin = depo.rapor.metin()
    assert "kullanici/akislar/bozuk.json — JSON bozuk" in metin
    assert "kullanici/akislar/eksik.json — ad: zorunlu alan eksik" in metin
    assert 'kullanici/moduller/kotu_tur.json — sutunlar[0].tur: bilinmeyen tür "para2"' in metin
    assert not depo.rapor.temiz and "not.txt" not in metin


def test_ayni_kimlik_ikisi_de_listelenir(tmp_path):
    kul = tmp_path / "kul"
    benim = degistir(AKIS, "aciklama", deger="Benim sürümüm")
    yaz(kul / "akislar" / "stok_takibi.json", benim)
    depo = yukleyici.depo_yukle(YERLESIK, kul)
    assert [(s.ic_kimlik, s.etiket) for s in depo.sablonlar if "stok_takibi" in s.ic_kimlik] == [
        ("yerlesik:stok_takibi", "Stok takibi"), ("kullanici:stok_takibi", "Stok takibi (benim sürümüm)")]
    assert depo.bul("yerlesik:stok_takibi").akis.aciklama != "Benim sürümüm"           # yerleşik değişmedi
    assert depo.bul("kullanici:stok_takibi").moduller["urunler"].kimlik == "urunler"    # yerleşik modüle düşer
    assert depo.rapor.temiz


def test_kullanici_akisi_eksik_modul_atlanir(tmp_path):
    kul = tmp_path / "kul"
    a = degistir(AKIS, "kimlik", deger="x")
    a["moduller"].append({"modul": "olmayan"})
    yaz(kul / "akislar" / "x.json", a)
    depo = yukleyici.depo_yukle(YERLESIK, kul)
    assert depo.bul("kullanici:x") is None
    assert '"olmayan" modülü bulunamadı' in depo.rapor.metin()


def test_ayni_kimlik_iki_dosyada(tmp_path):
    kul = tmp_path / "kul"
    yaz(kul / "moduller" / "a.json", MODUL)
    yaz(kul / "moduller" / "b.json", MODUL)
    depo = yukleyici.depo_yukle(YERLESIK, kul)
    assert "başka bir dosyada da var" in depo.rapor.metin() and "b.json" in depo.rapor.metin()


def test_kullanici_klasoru_yoksa_sorun_degil(tmp_path):
    depo = yukleyici.depo_yukle(YERLESIK, tmp_path / "hic_yok")
    assert depo.rapor.temiz and len(depo.sablonlar) == len(YERLESIK_KIMLIKLER)


def test_kullanici_klasoru_veri_klasorunden(tmp_path, monkeypatch):
    monkeypatch.setenv("TABCEL_VERI_KLASORU", str(tmp_path))
    assert yukleyici.kullanici_klasoru() == tmp_path / "sablonlar"


# ---------------------------------------------------------------- sürüm / göç
def test_daha_yeni_surum_reddedilir(tmp_path):
    kul = tmp_path / "kul"
    yaz(kul / "akislar" / "yeni.json", degistir(AKIS, "surum", deger=sema.SURUM + 1))
    depo = yukleyici.depo_yukle(YERLESIK, kul)
    assert len(depo.sablonlar) == len(YERLESIK_KIMLIKLER)
    assert "uygulamayı güncelleyin" in depo.rapor.metin()


def test_goc_zinciri(tmp_path, monkeypatch):
    """Şema 3'e çıkmış gibi: v1 → v2 → v3 dönüştürücüleri sırayla çalışır."""
    monkeypatch.setattr(sema, "SURUM", 3)
    sirayla = []

    def g1(d):
        sirayla.append(1)
        d["ad"] = d.pop("eski_ad")
        return d

    def g2(d):
        sirayla.append(2)
        d["tekil_ad"] = d["ad"]
        return d

    monkeypatch.setitem(yukleyici.GOCLER["modul"], 1, g1)
    monkeypatch.setitem(yukleyici.GOCLER["modul"], 2, g2)
    d = degistir(MODUL, "surum", deger=1)
    d["eski_ad"] = d.pop("ad")
    del d["tekil_ad"]
    p = yaz(tmp_path / "m.json", d)
    m, h = yukleyici.tanim_yukle(p, "modul")
    assert sirayla == [1, 2] and m is not None and m.ad == "Ürünler" and m.tekil_ad == "Ürünler" and m.surum == 3
    # eksik göç
    monkeypatch.delitem(yukleyici.GOCLER["modul"], 2)
    m, h = yukleyici.tanim_yukle(p, "modul")
    assert m is None and "dönüştürücü yok" in str(h[0])


def test_goc_hatasi_cokertmez(tmp_path, monkeypatch):
    monkeypatch.setattr(sema, "SURUM", 2)
    monkeypatch.setitem(yukleyici.GOCLER["modul"], 1, lambda d: d["olmayan_anahtar"])
    m, h = yukleyici.tanim_yukle(yaz(tmp_path / "m.json", MODUL), "modul")
    assert m is None and "dönüştürülürken hata" in str(h[0])


# ---------------------------------------------------------------- eşleştirici
@pytest.fixture(scope="module")
def akislar(depo):
    return depo.akislar()


@pytest.mark.parametrize("metin", ["stok takibi yapmak istiyorum", "Stoğumu takip etmek istiyorum", "stoklarımı görmek istiyorum",
                                   "STOKTA ne var", "Envanter tutmak istiyorum", "mal takibi lazım", "Ürünlerimi saymak lazım",
                                   "depoda kaç ürün kaldı"])
def test_eslestirme_stok(akislar, metin):
    oneriler = eslestirici.oneri(metin, akislar)
    assert oneriler and oneriler[0].akis.kimlik == "stok_takibi", metin


@pytest.mark.parametrize("metin", ["", "   ", "bugün hava çok güzel", "ab", "kira ödemesi"])
def test_eslestirme_yok(akislar, metin):
    assert eslestirici.oneri(metin, akislar) == []


def test_eslestirme_turkce_harf_ve_kati_koku(akislar):
    assert eslestirici.katla("İSTANBUL ŞUBESİ") == "istanbul subesi"            # İ → i, I → ı → i
    assert eslestirici.katla("ILIK ÇORUM") == "ilik corum"
    assert eslestirici.sozcukler("Stoğu, stok-ta; ürün!") == ["stogu", "stok", "ta", "urun"]
    e = eslestirici.puanla("stoğu", next(a for a in akislar if a.kimlik == "stok_takibi"))
    assert e.puan == 1.0 and e.nedenler == ["stoğ"]


def test_eslestirme_puan_siralama_ve_yakinlik():
    from tabcel.sablon.sema import Akis

    def akis(kimlik, ad, kokler, es=(), agirlik=1.0):
        return Akis(1, kimlik, ad, "K", "a", list(kokler), list(es), agirlik, [], [("m", None)], {}, [], [])

    a, b, c = akis("a", "Alfa", ["kira"], ["ev kirası"]), akis("b", "Beta", ["kira", "daire"]), akis("c", "Ceta", ["muhasebe"])
    sonuc = eslestirici.eslestir("ev kirası ödemesi", [a, b, c])
    assert [e.akis.kimlik for e in sonuc] == ["a", "b"] and sonuc[0].puan == 2.0 and sonuc[1].puan == 1.0
    assert [e.akis.kimlik for e in eslestirici.oneri("ev kirası ödemesi", [a, b, c])] == ["a"]       # b: 1.0 < 2.0×0.6
    assert [e.akis.kimlik for e in eslestirici.oneri("kira daire", [a, b, c])] == ["b"]
