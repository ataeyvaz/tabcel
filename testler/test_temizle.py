"""Faz 9d: KVKK Paylaşım Temizleyici çekirdeği (model/temizle.py) ve dosya düzeyi (io/temiz_dosya.py). Yalnız sentetik veri (kural 19)."""
import os
import zipfile

import pytest
from openpyxl import Workbook

from sentetik import iban_bicimli, iban_uret, kart_uret, tc_uret, vkn_uret
from tabcel.formul.motor import Hesaplayici
from tabcel.io import temiz_dosya, xlsx_io
from tabcel.model import deger as D
from tabcel.model import kimlik, temizle
from tabcel.model.adres import Aralik
from tabcel.model.ad import TanimliAd
from tabcel.model.dogrulama import Dogrulama
from tabcel.model.grafik import Grafik, Referans, Seri
from tabcel.model.notlar import Not
from tabcel.model.sayfa import CalismaKitabi, Hucre

TC = tc_uret()
TC2 = tc_uret(rnd=__import__("random").Random(77))
VKN = vkn_uret()
IBAN = iban_uret()
KART = kart_uret("4")
EPOSTA = "ornek.kisi@ornek-sirket.com"
TEL = "0532 123 45 67"


def _kitap():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre("Ad Soyad"))
    s.ata(1, 2, Hucre("TC"))
    s.ata(1, 3, Hucre("Maaş"))
    s.ata(2, 1, Hucre("Ayşe Örnek"))
    s.ata(2, 2, Hucre(TC))
    s.ata(2, 3, Hucre(1000.0))
    s.ata(3, 1, Hucre("Veli Deneme"))
    s.ata(3, 2, Hucre(TC2))
    s.ata(3, 3, Hucre(2500.0))
    s.ata(4, 3, Hucre(None, "=SUM(C2:C3)"))
    s.ata(5, 1, Hucre(f"İletişim: {EPOSTA} / {TEL}"))
    s.ata(6, 1, Hucre(IBAN))
    s.ata(7, 1, Hucre(iban_bicimli(IBAN)))
    return k


def _tara(k):
    return temizle.Tarayici(k).tara()


def _turler(kayitlar):
    return sorted((x.tur, x.yer.adres) for x in kayitlar)


# ---------------------------------------------------------------- tarama
def test_hucre_bulgulari_ve_ad_sutunu():
    k = _kitap()
    kay = _tara(k)
    t = _turler(kay)
    assert (kimlik.TC, "B2") in t and (kimlik.TC, "B3") in t
    assert (kimlik.EPOSTA, "A5") in t and (kimlik.TELEFON, "A5") in t
    assert (kimlik.IBAN, "A6") in t and (kimlik.IBAN, "A7") in t
    # ad-soyad: yalnız başlığı "Ad Soyad" olan sütunun altı (başlığın kendisi ve diğer sütunlar değil)
    adlar = sorted(x.yer.adres for x in kay if x.tur == kimlik.AD)
    assert adlar == ["A2", "A3"]
    assert not any(x.yer.adres == "A1" for x in kay) and not any(x.yer.adres == "C2" for x in kay)


def test_ad_bulgusu_yalniz_basliga_bagli():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre("Şehir"))
    s.ata(2, 1, Hucre("Ankara"))
    s.ata(1, 2, Hucre("Müşteri Adı"))
    s.ata(2, 2, Hucre("Ali Veli"))
    kay = _tara(k)
    assert [(x.tur, x.yer.adres) for x in kay] == [(kimlik.AD, "B2")]


def test_benzer_ama_degil_yanlis_alarm_yok():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre(tc_uret()[:-1] + str((int(tc_uret()[-1]) + 1) % 10)))    # geçersiz TC
    s.ata(2, 1, Hucre("12345678901"))
    s.ata(3, 1, Hucre(1234567.0))
    s.ata(4, 1, Hucre("Toplantı 12.10.2026 saat 14:30"))
    s.ata(5, 1, Hucre("a@b"))
    s.ata(6, 1, Hucre(3.14159))
    assert _tara(k) == []


def test_sayi_olarak_yazilmis_tc_bulunur():
    k = CalismaKitabi()
    k.sayfalar[0].ata(1, 1, Hucre(float(TC)))
    kay = _tara(k)
    assert [(x.tur, x.yer.adres) for x in kay] == [(kimlik.TC, "A1")]
    tk = temizle.temiz_kopya(k, kay, temizle.Plan(), motor_kur=False)
    assert tk.kitap.sayfalar[0].deger(1, 1) == "12*******" + TC[-2:] or tk.kitap.sayfalar[0].deger(1, 1).endswith(TC[-2:])


def test_gizli_yerler_isaretlenir():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre(TC))
    s.ata(2, 1, Hucre(TC2))
    s.ata(3, 1, Hucre(f"x {EPOSTA}"))
    s.gizli_satir.add(2)
    s.gizli_sutun.add(1)                        # tüm A sütunu gizli: 1. ve 3. satır "gizli sütun"
    s2 = k.sayfa_ekle("Ek")
    s2.ata(1, 1, Hucre(VKN))
    s2.gizli = True
    g = {(x.sayfa_ad, x.yer.adres): x.yer.gizli for x in _tara(k)}
    assert g[(s.ad, "A1")] == "gizli sütun" and g[(s.ad, "A2")] == "gizli satır"
    assert g[("Ek", "A1")] == "gizli sayfa"


def test_notlar_adlar_grafik_dogrulama_formul_sabiti():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre(None, f'="{IBAN}"'))
    s.notlari_yaz({(2, 1): Not(f"TC: {TC}", "Ayşe Örnek")})
    k.ad_yaz(TanimliAd("Kisi", f'="{EPOSTA}"', None, f"iletişim {TEL}"))
    s.dogrulamalar.append(Dogrulama((Aralik(1, 2, 3, 2),), tur="liste", formul1=f'"{EPOSTA},baska"'))
    g = Grafik(baslik=f"Rapor {TC}", seriler=(Seri(ad=EPOSTA, deger=Referans(s.kimlik, Aralik(1, 1, 3, 1))),))
    s.nesne_ekle(g)
    yerler = sorted({x.yer.tur for x in _tara(k)})
    assert yerler == sorted([temizle.FORMUL, temizle.NOT, temizle.NOT_YAZAR, temizle.AD, temizle.DOGRULAMA, temizle.GRAFIK])


def test_sayfa_adi_ve_resim_sayisi():
    k = CalismaKitabi()
    k.yeniden_adlandir(k.sayfalar[0], f"M-{EPOSTA}"[:31])
    t = temizle.Tarayici(k)
    t.tara()
    assert t.resim_sayisi == 0
    k2 = CalismaKitabi()
    k2.yeniden_adlandir(k2.sayfalar[0], "05321234567")
    assert any(x.yer.tur == temizle.SAYFA_ADI for x in _tara(k2))


# ---------------------------------------------------------------- uygulama: ÖZGÜN DEĞİŞMEZ
def test_ozgun_kitap_degismez_ve_maske_uygulanir():
    k = _kitap()
    onceki = {(r, c): (h.deger, h.formul) for r, c, h in k.sayfalar[0].dolu_hucreler()}
    kay = _tara(k)
    tk = temizle.temiz_kopya(k, kay, temizle.Plan(), motor_kur=False)
    ks = tk.kitap.sayfalar[0]
    assert ks.deger(2, 2) == kimlik.maskele(kimlik.TC, TC) and ks.deger(2, 2).startswith(TC[:2]) and ks.deger(2, 2).endswith(TC[-2:])
    assert "*" in ks.deger(2, 2) and TC not in str(ks.deger(2, 2))
    assert EPOSTA not in ks.deger(5, 1) and TEL not in ks.deger(5, 1)
    # özgün kitap aynen duruyor
    assert k.sayfalar[0].deger(2, 2) == TC
    assert {(r, c): (h.deger, h.formul) for r, c, h in k.sayfalar[0].dolu_hucreler()} == onceki
    assert tk.kitap is not k and tk.kitap.sayfalar[0] is not k.sayfalar[0]


def test_sil_ve_birak_eylemleri():
    k = _kitap()
    kay = _tara(k)
    plan = temizle.Plan()
    plan.eylem[kimlik.TC] = temizle.SIL
    plan.eylem[kimlik.IBAN] = temizle.BIRAK
    plan.eylem[kimlik.AD] = temizle.BIRAK
    tk = temizle.temiz_kopya(k, kay, plan, motor_kur=False)
    ks = tk.kitap.sayfalar[0]
    assert ks.hucre(2, 2) is None                              # tüm hücre TC idi → silindi
    assert ks.deger(6, 1) == IBAN                              # bırakıldı
    assert ks.deger(2, 1) == "Ayşe Örnek"                      # ad bırakıldı
    assert TC in tk.yasak and IBAN not in tk.yasak               # silinen yasak, bırakılan değil


def test_haric_tek_kayit_dışarıda_kalir():
    k = _kitap()
    kay = _tara(k)
    idx = next(i for i, x in enumerate(kay) if x.tur == kimlik.TC and x.yer.adres == "B2")
    plan = temizle.Plan(haric={idx})
    tk = temizle.temiz_kopya(k, kay, plan, motor_kur=False)
    ks = tk.kitap.sayfalar[0]
    assert ks.deger(2, 2) == TC and "*" in ks.deger(3, 2)


def test_hucre_icinde_kismi_maske_metin_korunur():
    k = _kitap()
    tk = temizle.temiz_kopya(k, _tara(k), temizle.Plan(), motor_kur=False)
    m = tk.kitap.sayfalar[0].deger(5, 1)
    assert m.startswith("İletişim: ") and " / " in m


def test_not_ad_grafik_dogrulama_formul_temizlenir():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre(None, f'="{IBAN}"&"x"'))
    s.notlari_yaz({(2, 1): Not(f"TC: {TC}", "Ayşe Örnek")})
    k.ad_yaz(TanimliAd("Kisi", f'="{EPOSTA}"', None, f"iletişim {TEL}"))
    s.dogrulamalar.append(Dogrulama((Aralik(1, 2, 3, 2),), tur="liste", formul1=f'"{EPOSTA},baska"'))
    s.nesne_ekle(Grafik(baslik=f"Rapor {TC}", seriler=(Seri(ad=EPOSTA, deger=Referans(s.kimlik, Aralik(1, 1, 3, 1))),)))
    tk = temizle.temiz_kopya(k, _tara(k), temizle.Plan(), motor_kur=False)
    ks = tk.kitap.sayfalar[0]
    assert IBAN not in ks.hucre(1, 1).formul and ks.hucre(1, 1).formul.startswith('="TR')
    assert TC not in ks.notlar[(2, 1)].metin and ks.notlar[(2, 1)].yazar != "Ayşe Örnek"
    ad = next(iter(tk.kitap.adlar.values()))
    assert EPOSTA not in ad.formul and TEL not in ad.aciklama
    assert EPOSTA not in ks.dogrulamalar[0].formul1 and "baska" in ks.dogrulamalar[0].formul1
    g = ks.nesneler[0]
    assert TC not in g.baslik and EPOSTA not in g.seriler[0].ad
    # özgün
    assert k.sayfalar[0].notlar[(2, 1)].yazar == "Ayşe Örnek" and IBAN in k.sayfalar[0].hucre(1, 1).formul


def test_sayfa_adi_maskelenir_gecerli_ve_benzersiz():
    k = CalismaKitabi()
    k.yeniden_adlandir(k.sayfalar[0], "05321234567")
    k.sayfa_ekle("05321234999")
    tk = temizle.temiz_kopya(k, _tara(k), temizle.Plan(), motor_kur=False)
    adlar = [s.ad for s in tk.kitap.sayfalar]
    assert len(set(a.casefold() for a in adlar)) == 2 and all("*" not in a for a in adlar)
    assert "05321234567" not in adlar


# ---------------------------------------------------------------- formül etkisi
def test_formul_etkisi_ve_degere_cevir():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre(float(TC)))                       # sayı olarak yazılmış TC → maskelenince metin
    s.ata(1, 2, Hucre(None, "=A1+1"))                   # hataya döner (#DEĞER!)
    s.ata(2, 1, Hucre(10.0))
    s.ata(2, 2, Hucre(None, "=A2*2"))                   # etkilenmez
    s.ata(3, 2, Hucre(None, "=LEN(A1)"))                # değeri değişir (11 → 11 maske uzunluğu aynı) → değişmeyebilir
    Hesaplayici(k)
    tk = temizle.temiz_kopya(k, _tara(k), temizle.Plan())
    try:
        adresler = {e.adres: e for e in tk.etkiler}
        assert "B1" in adresler and adresler["B1"].hataya_dondu
        assert "B2" not in adresler
        e = adresler["B1"]
        # özgün sonuç TC'den bir fazla bir sayı: yasak değeri (TC) içermiyor ama TC+1 başka bir sayı → değere çevrilebilir
        assert e.degere_cevrilebilir is True and e.eski == float(TC) + 1
        assert tk.degere_cevir([e]) == 1
        h = tk.kitap.sayfalar[0].hucre(1, 2)
        assert h.formul is None and h.deger == float(TC) + 1
    finally:
        tk.kapat()


def test_degere_cevir_sizdirirsa_reddedilir():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre(float(TC)))
    s.ata(1, 2, Hucre(None, "=A1"))                     # sonuç TC'nin kendisi → değere çevirmek sızdırır
    Hesaplayici(k)
    tk = temizle.temiz_kopya(k, _tara(k), temizle.Plan())
    try:
        e = next(x for x in tk.etkiler if x.adres == "B1")
        assert not e.degere_cevrilebilir
        assert tk.degere_cevir([e]) == 0
        assert tk.kitap.sayfalar[0].hucre(1, 2).formul == "=A1"
    finally:
        tk.kapat()


# ---------------------------------------------------------------- dosya düzeyi
def _ozgun_xlsx(tmp_path):
    k = _kitap()
    k.sayfalar[0].notlari_yaz({(2, 1): Not(f"TC {TC}", "Ayşe Örnek")})
    k.sayfa_ekle("Gizli").ata(1, 1, Hucre(f"{VKN} {KART}"))
    k.sayfalar[1].gizli = True
    yol = str(tmp_path / "ozgun.xlsx")
    xlsx_io.kaydet(k, yol)
    return yol


def test_temiz_dosya_ozgun_deger_icermez(tmp_path):
    yol = _ozgun_xlsx(tmp_path)
    k, _ = xlsx_io.ac(yol)
    Hesaplayici(k)
    kay = _tara(k)
    assert any(x.yer.gizli == "gizli sayfa" for x in kay)                      # gizli sayfadaki veri bulundu
    tk = temizle.temiz_kopya(k, kay, temizle.Plan())
    hedef = str(tmp_path / "temiz.xlsx")
    temiz_dosya.temiz_yaz(tk, hedef, ozgun_yol=yol)
    tk.kapat()
    with zipfile.ZipFile(hedef) as z:
        butun = b"".join(z.read(a) for a in z.namelist()).decode("utf-8", "ignore")
    for v in (TC, TC2, EPOSTA, IBAN, KART, VKN, "Ayşe Örnek", "Veli Deneme"):
        assert v not in butun, v
    # özgün dosya baytı baytına aynı kaldı
    k2, _ = xlsx_io.ac(yol)
    assert k2.sayfalar[0].deger(2, 2) == TC


def test_ozgun_yola_yazma_engellenir(tmp_path):
    yol = _ozgun_xlsx(tmp_path)
    boyut = os.path.getsize(yol)
    icerik = open(yol, "rb").read()
    k, _ = xlsx_io.ac(yol)
    tk = temizle.temiz_kopya(k, _tara(k), temizle.Plan(), motor_kur=False)
    with pytest.raises(temiz_dosya.OzgunYolaYazmaHatasi):
        temiz_dosya.temiz_yaz(tk, yol, ozgun_yol=yol)
    with pytest.raises(temiz_dosya.OzgunYolaYazmaHatasi):                        # farklı yazımla aynı dosya
        temiz_dosya.temiz_yaz(tk, os.path.join(os.path.dirname(yol), ".", "OZGUN.xlsx"), ozgun_yol=yol)
    assert open(yol, "rb").read() == icerik and os.path.getsize(yol) == boyut


def test_dosya_dogrulama_sizinti_yakalar(tmp_path):
    yol = _ozgun_xlsx(tmp_path)
    assert temiz_dosya.dosya_dogrula(yol, {TC})                                   # özgün dosyada var
    assert temiz_dosya.dosya_dogrula(yol, set()) == []
    # cümle içine gömülü e-posta/telefon (hücre metninin parçası) da yakalanır
    assert temiz_dosya.dosya_dogrula(yol, {EPOSTA}) and temiz_dosya.dosya_dogrula(yol, {"05321234567"})
    assert temiz_dosya.dosya_dogrula(yol, {"99999999999"}) == []


def test_gizli_sayfa_temiz_kopyada_gizli_kalir(tmp_path):
    yol = _ozgun_xlsx(tmp_path)
    k, _ = xlsx_io.ac(yol)
    tk = temizle.temiz_kopya(k, _tara(k), temizle.Plan(), motor_kur=False)
    hedef = str(tmp_path / "t.xlsx")
    temiz_dosya.temiz_yaz(tk, hedef, yol)
    k3, _ = xlsx_io.ac(hedef)
    assert [s.gizli for s in k3.sayfalar] == [False, True]


def test_meta_tarama_yazar_ve_ust_alt(tmp_path):
    wb = Workbook()
    wb.active["A1"] = "x"
    wb.properties.creator = "Ayşe Örnek"
    wb.properties.lastModifiedBy = EPOSTA
    wb.active.oddHeader.center.text = f"Gizli {TEL}"
    yol = str(tmp_path / "m.xlsx")
    wb.save(yol)
    m = temiz_dosya.meta_tara(yol)
    d = dict(m.alanlar)
    assert d["Yazar"] == "Ayşe Örnek" and d["Son kaydeden"] == EPOSTA
    assert any(TEL in t or "532" in t for t in m.ust_alt)
    assert {b.tur for b in m.bulgular} >= {kimlik.EPOSTA, kimlik.TELEFON}
    # temiz kopya (Tabcel yazıcısı) bu meta verileri taşımaz
    k, _ = xlsx_io.ac(yol)
    tk = temizle.temiz_kopya(k, [], temizle.Plan(), motor_kur=False)
    hedef = str(tmp_path / "m_temiz.xlsx")
    temiz_dosya.temiz_yaz(tk, hedef, yol)
    m2 = temiz_dosya.meta_tara(hedef)
    assert "Ayşe Örnek" not in [v for _, v in m2.alanlar] and m2.ust_alt == []
    assert EPOSTA not in [v for _, v in m2.alanlar]


def test_saglik_yoksay_kopyaya_tasinmaz():
    k = _kitap()
    k.saglik_yoksay.add("eksik_aralik|Sayfa1|C4")
    tk = temizle.temiz_kopya(k, [], temizle.Plan(), motor_kur=False)
    assert tk.kitap.saglik_yoksay == set() and k.saglik_yoksay
