"""Faz 9c: Tablo Sağlık Kontrolü çekirdeği (formul/saglik.py). Her kontrol için hem “sorun var” hem “benziyor ama sorun değil”
vakaları (yanlış alarm denetimi); düzeltmeler yalnız komut olarak üretilir (denetçi kendisi hücre değiştirmez).
Yalnız sentetik veri (kural 19)."""
import random

import pytest

from sentetik import iban_bicimli, iban_uret, tc_bozuk, tc_uret, vkn_uret
from tabcel.formul import ceviri, saglik
from tabcel.formul.motor import Hesaplayici
from tabcel.model.komutlar import GeriAlYigini
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.stil import Stil


def kur():
    k = CalismaKitabi()
    return k, k.sayfalar[0], Hesaplayici(k)


def tara(k, m, kontrol=None, **ayar):
    a = saglik.Ayarlar()
    for ad, v in ayar.items():
        setattr(a, ad, v)
    b = saglik.Tarayici(k, m, a).tara()
    return [x for x in b if kontrol is None or x.kontrol == kontrol]


def sayilar(s, sutun, ilk, son, f=lambda r: float(r)):
    for r in range(ilk, son + 1):
        s.ata(r, sutun, Hucre(f(r)))


# ================================================================ 1. eksik aralık
def test_eksik_aralik_sorun_var_ve_duzeltme():
    k, s, m = kur()
    sayilar(s, 1, 2, 12)                                                  # A2:A12 sayı
    s.ata(14, 1, Hucre(formul="=SUM(A2:A10)"))                            # A11:A12 katılmıyor
    (b,) = tara(k, m, "eksik_aralik")
    assert b.onem == saglik.KRITIK and b.konum == (14, 1) and "A11:A12" in b.aciklama and b.duzeltme.tur == "aralik_genislet"
    assert "A2:A12" in b.duzeltme.aciklama
    y = GeriAlYigini()
    assert s.deger(14, 1) == sum(range(2, 11))
    y.calistir(saglik.duzeltme_komutu(k, b))                              # kullanıcı onayı = komutu çalıştırmak
    assert s.hucre(14, 1).formul == "=SUM(A2:A12)" and s.deger(14, 1) == sum(range(2, 13))
    y.geri_al()
    assert s.hucre(14, 1).formul == "=SUM(A2:A10)"


def test_eksik_aralik_duzeltme_sonrasi_yeniden_taranirsa_bulgu_yok():
    k, s, m = kur()
    sayilar(s, 1, 2, 6)
    s.ata(8, 1, Hucre(formul="=AVERAGE(A2:A5)"))
    (b,) = tara(k, m, "eksik_aralik")
    GeriAlYigini().calistir(saglik.duzeltme_komutu(k, b))
    assert tara(k, m, "eksik_aralik") == []


def test_eksik_aralik_satir_yonu():
    k, s, m = kur()
    for c in range(2, 7):
        s.ata(1, c, Hucre(float(c)))                                      # B1:F1
    s.ata(1, 8, Hucre(formul="=SUM(B1:E1)"))                              # F1 katılmıyor
    (b,) = tara(k, m, "eksik_aralik")
    assert "F1" in b.aciklama and "sağında" in b.baslik


def test_eksik_aralik_sayfalar_arasi():
    k, s, m = kur()
    v = k.sayfa_ekle("Veri")
    sayilar(v, 1, 2, 8)
    s.ata(1, 1, ceviri.hucre_girdisi("=SUM(Veri!A2:A7)", k))             # sayfa başvurusu kimliğe bağlanır (arayüzdeki gibi)
    s.ata(2, 1, Hucre(formul="=SUM(Veri!A2:A7)"))                         # ada bağlı yazım da çözülür
    b = tara(k, m, "eksik_aralik")
    assert [x.konum for x in b] == [(1, 1), (2, 1)] and all(x.sayfa_ad == "Sayfa1" and "A8" in x.aciklama for x in b)
    assert "A2:A8" in b[0].duzeltme.aciklama


@pytest.mark.parametrize("ad, kur_fn", [
    ("toplam satırı hemen altında, devamı başka blok", lambda s: (sayilar(s, 1, 2, 10), s.ata(11, 1, Hucre(formul="=SUM(A2:A10)")),
                                                                  sayilar(s, 1, 12, 16))),
    ("bitişik hücre başka bir toplam", lambda s: (sayilar(s, 1, 2, 10), s.ata(11, 1, Hucre(formul="=SUM(A2:A5)")),
                                                    s.ata(12, 1, Hucre(formul="=SUM(A6:A10)")))),
    ("bilerek bölünmüş toplamlar (bitişik hücre başka toplamın aralığında)", lambda s: (
        sayilar(s, 1, 2, 9), s.ata(12, 1, Hucre(formul="=SUM(A2:A5)")), s.ata(13, 1, Hucre(formul="=SUM(A6:A9)")))),
    ("aralığın altı boşlukla ayrılmış", lambda s: (sayilar(s, 1, 2, 6), sayilar(s, 1, 8, 10), s.ata(12, 1, Hucre(formul="=SUM(A2:A6)")))),
    ("bitişikte metin var", lambda s: (sayilar(s, 1, 2, 6), s.ata(7, 1, Hucre("not")), s.ata(9, 1, Hucre(formul="=SUM(A2:A6)")))),
    ("başlık satırında sayı (yıl)", lambda s: (s.ata(1, 1, Hucre("Ürün")), s.ata(1, 2, Hucre(2023.0)), s.ata(1, 3, Hucre(2024.0)),
                                               sayilar(s, 2, 2, 8), s.ata(10, 2, Hucre(formul="=SUM(B2:B8)")))),
])
def test_eksik_aralik_yanlis_alarm_yok(ad, kur_fn):
    k, s, m = kur()
    kur_fn(s)
    assert tara(k, m, "eksik_aralik") == [], ad


def test_eksik_aralik_toplam_satirindan_sonra_sayi_var_ama_toplam_yukarida():
    k, s, m = kur()
    sayilar(s, 1, 2, 10)
    s.ata(1, 1, Hucre("Tutar"))
    s.ata(12, 1, Hucre(formul="=SUM(A2:A10)"))
    s.ata(13, 1, Hucre(formul="=AVERAGE(A2:A10)"))                        # ardışık özetler birbirini engellemez
    assert tara(k, m, "eksik_aralik") == []


# ================================================================ 2. tutarsız formül
def test_tutarsiz_formul_var_ve_duzeltme():
    k, s, m = kur()
    sayilar(s, 1, 2, 12)
    for r in range(2, 13):
        s.ata(r, 3, Hucre(formul=f"=A{r}*2"))
    s.ata(7, 3, Hucre(formul="=A7*A6"))
    (b,) = tara(k, m, "tutarsiz_formul")
    assert b.onem == saglik.UYARI and b.konum == (7, 3) and b.duzeltme.tur == "formul_esitle" and "=A7*2" in b.duzeltme.aciklama
    y = GeriAlYigini()
    y.calistir(saglik.duzeltme_komutu(k, b))
    assert s.hucre(7, 3).formul == "=A7*2" and s.deger(7, 3) == 14.0
    assert tara(k, m, "tutarsiz_formul") == []
    y.geri_al()
    assert s.hucre(7, 3).formul == "=A7*A6"


def test_tutarsiz_formul_satir_yonu():
    k, s, m = kur()
    for c in range(2, 9):
        s.ata(2, c, Hucre(float(c)))
    for c in range(2, 9):
        s.ata(1, c, Hucre(formul=f"={saglik.sutun_harfe(c)}2*2"))
    s.ata(1, 5, Hucre(formul="=F2*2"))                                    # bir sütun kaymış başvuru
    assert [b.konum for b in tara(k, m, "tutarsiz_formul")] == [(1, 5)]


def test_tutarsiz_formul_mutlak_ve_goreli_karisimi():
    k, s, m = kur()
    s.ata(1, 1, Hucre(2.0))
    sayilar(s, 2, 2, 9)
    for r in range(2, 10):
        s.ata(r, 3, Hucre(formul=f"=B{r}*$A$1"))
    s.ata(6, 3, Hucre(formul="=B6*A1"))                                   # $A$1 yerine göreli A1: aşağı kopyalanınca kayar
    assert [b.konum for b in tara(k, m, "tutarsiz_formul")] == [(6, 3)]


def test_tutarsiz_formul_uc_hucre():
    k, s, m = kur()
    sayilar(s, 1, 2, 8)
    for r in range(2, 8):
        s.ata(r, 3, Hucre(formul=f"=A{r}+1"))
    s.ata(8, 3, Hucre(formul="=A7+1"))                                    # son hücre bir üstü gibi kopyalanmış (aynı iskelet)
    assert [b.konum for b in tara(k, m, "tutarsiz_formul")] == [(8, 3)]


@pytest.mark.parametrize("ad, kur_fn", [
    ("toplam satırı (iskelet farklı)", lambda s: ([s.ata(r, 3, Hucre(formul=f"=A{r}*2")) for r in range(2, 8)],
                                                  s.ata(8, 3, Hucre(formul="=SUM(C2:C7)")))),
    ("ilk satır farklı", lambda s: (s.ata(2, 3, Hucre(formul="=A2")), [s.ata(r, 3, Hucre(formul=f"=C{r - 1}+A{r}")) for r in range(3, 8)])),
    ("sürekli aynı desen", lambda s: [s.ata(r, 3, Hucre(formul=f"=A{r}*B{r}")) for r in range(2, 10)]),
    ("dönüşümlü iki desen", lambda s: [s.ata(r, 3, Hucre(formul=f"=A{r}*2" if r % 2 else f"=A{r}*3")) for r in range(2, 12)]),
    ("tek formül", lambda s: s.ata(2, 3, Hucre(formul="=A2*2"))),
])
def test_tutarsiz_formul_yanlis_alarm_yok(ad, kur_fn):
    k, s, m = kur()
    sayilar(s, 1, 2, 12)
    sayilar(s, 2, 2, 12)
    kur_fn(s)
    assert tara(k, m, "tutarsiz_formul") == [], ad


# ================================================================ 3. metin olarak saklanan sayı
def test_metin_sayi_var_ve_duzeltme():
    k, s, m = kur()
    s.ata(1, 1, Hucre("Tutar"))
    sayilar(s, 1, 2, 8)
    s.ata(9, 1, Hucre("1.234,50"))
    s.ata(10, 1, Hucre("12,5"))
    s.ata(11, 1, Hucre("%15"))
    (b,) = tara(k, m, "metin_sayi")
    assert b.onem == saglik.UYARI and b.adet == 3 and b.hucreler == [(9, 1), (10, 1), (11, 1)]
    y = GeriAlYigini()
    y.calistir(saglik.duzeltme_komutu(k, b))
    assert [s.deger(r, 1) for r in (9, 10, 11)] == [1234.5, 12.5, 0.15] and s.stil(11, 1).sayi_bicimi == "0%"
    assert tara(k, m, "metin_sayi") == []
    y.geri_al()
    assert s.deger(9, 1) == "1.234,50" and s.stil(11, 1).sayi_bicimi == "General"


def test_metin_sayi_butun_sutun_metinse_bilgi_duzeyi():
    k, s, m = kur()
    for r in range(2, 7):
        s.ata(r, 1, Hucre(f"{r}00"))
    (b,) = tara(k, m, "metin_sayi")
    assert b.onem == saglik.BILGI and b.adet == 5


def test_metin_sayi_yanlis_alarm_yok():
    k, s, m = kur()
    s.ata(1, 1, Hucre("Kayıt"))
    sayilar(s, 1, 2, 10)
    istisnalar = [tc_uret(), iban_uret(), "0532 123 45 67", "+90 532 123 45 67", "00123", "12345678901234567", "abc", "01.02.2024",
                  "3 adet", "1-2", "A12"]
    for i, v in enumerate(istisnalar, 11):
        s.ata(i, 1, Hucre(v))
    s.ata(30, 1, Hucre("500"))
    s.bicim_yaz({(30, 1): k.stil_havuzu.kimlik(Stil(sayi_bicimi="@"))}, {}, {})          # bilerek Metin biçimli
    assert tara(k, m, "metin_sayi") == []


def test_metin_sayi_kimlik_basligi_olan_sutun_atlanir():
    k, s, m = kur()
    s.ata(1, 1, Hucre("Posta Kodu"))
    for r in range(2, 8):
        s.ata(r, 1, Hucre(f"{34000 + r}"))
    assert tara(k, m, "metin_sayi") == []


# ================================================================ 4. formül içinde sabit sayı
def test_sabit_sayi_var_ve_gruplanir():
    k, s, m = kur()
    sayilar(s, 1, 2, 7)
    for r in range(2, 7):
        s.ata(r, 2, Hucre(formul=f"=A{r}*1.18"))
    s.ata(7, 2, Hucre(formul="=A7*0.2"))
    b = tara(k, m, "sabit_sayi")
    assert len(b) == 2 and {x.baslik for x in b} == {"Formülde sabit sayı: 1,18", "Formülde sabit sayı: 0,2"}
    k118 = next(x for x in b if "1,18" in x.baslik)
    assert k118.adet == 5 and k118.onem == saglik.BILGI and k118.duzeltme is None


@pytest.mark.parametrize("formul", ["=A2/100", "=A2*2", "=A2+1", "=ROUND(A2,2)", "=VLOOKUP(A2,A2:B9,3,0)", "=IF(A2>5,1,0)", "=2*3",
                                    "=INDEX(A2:A9,5)", "=A2*10", "=A2/12", "=A2^2"])
def test_sabit_sayi_yaygin_degerler_ve_baglamlar_alarm_vermez(formul):
    k, s, m = kur()
    sayilar(s, 1, 2, 9)
    s.ata(2, 3, Hucre(formul=formul))
    assert tara(k, m, "sabit_sayi") == []


def test_sabit_sayi_yoksayilan_liste_ayarlanabilir():
    k, s, m = kur()
    sayilar(s, 1, 2, 5)
    s.ata(2, 3, Hucre(formul="=A2/100"))
    s.ata(3, 3, Hucre(formul="=A3*1.18"))
    assert [x.baslik for x in tara(k, m, "sabit_sayi")] == ["Formülde sabit sayı: 1,18"]
    assert {x.baslik for x in tara(k, m, "sabit_sayi", sabit_yoksay=())} == {"Formülde sabit sayı: 1,18", "Formülde sabit sayı: 100"}
    assert tara(k, m, "sabit_sayi", sabit_yoksay=(1.18, 100.0)) == []


# ================================================================ 5. hata değerleri
def test_hata_kaynagi_ve_etki():
    k, s, m = kur()
    s.ata(3, 2, Hucre(formul="=1/0"))
    s.ata(1, 3, Hucre(formul="=B3+1"))
    s.ata(1, 4, Hucre(formul="=C1*2"))
    (b,) = tara(k, m, "hata")
    assert b.onem == saglik.KRITIK and b.konum == (3, 2) and "B3" in b.baslik and "3 hücreyi" in b.aciklama


def test_hata_iki_ayri_kaynak_ve_elle_yazilan_ve_sayfalar_arasi():
    k, s, m = kur()
    v = k.sayfa_ekle("Veri")
    v.ata(1, 1, Hucre(formul="=1/0"))
    s.ata(1, 1, Hucre(formul="=Veri!A1+1"))
    s.ata(2, 2, Hucre(formul="=VLOOKUP(5,A1:A3,1,0)"))
    b = tara(k, m, "hata")
    assert {x.sayfa_ad for x in b} == {"Veri", "Sayfa1"} and len(b) == 2
    veri = next(x for x in b if x.sayfa_ad == "Veri")
    assert "2 hücreyi" in veri.aciklama                                    # Veri!A1 hem kendini hem Sayfa1!A1'i etkiliyor


def test_hata_yoksa_bulgu_yok():
    k, s, m = kur()
    sayilar(s, 1, 1, 5)
    s.ata(1, 2, Hucre(formul="=SUM(A1:A5)"))
    assert tara(k, m, "hata") == []


# ================================================================ 6. boş hücreye başvuru
def test_bos_basvuru_veri_arasindaki_delik():
    k, s, m = kur()
    s.ata(5, 1, Hucre(10.0))
    s.ata(5, 3, Hucre(30.0))
    s.ata(5, 4, Hucre(formul="=A5+B5+C5"))
    (b,) = tara(k, m, "bos_basvuru")
    assert b.onem == saglik.BILGI and b.konum == (5, 4) and "B5" in b.aciklama


@pytest.mark.parametrize("formul", ["=SUM(A5:C5)", "=IF(ISBLANK(B5),0,B5)", "=E1*2", "=VLOOKUP(5,A5:C5,2,0)"])
def test_bos_basvuru_yanlis_alarm_yok(formul):
    k, s, m = kur()
    s.ata(5, 1, Hucre(10.0))
    s.ata(5, 3, Hucre(30.0))
    s.ata(5, 4, Hucre(formul=formul))                                     # E1: tek başına duran (komşusuz) girdi hücresi de alarm vermez
    assert tara(k, m, "bos_basvuru") == []


# ================================================================ 7. yinelenen satırlar
def test_yinelenen_satir_var():
    k, s, m = kur()
    veri = [("Ad", "Şehir", "Tutar"), ("Ali", "Ankara", 10.0), ("Ayşe", "İzmir", 20.0), ("ALİ", "ankara", 10.0), ("Veli", "Bursa", 5.0),
            ("Ayşe", "İzmir", 20.0)]
    for i, satir in enumerate(veri, 1):
        for j, v in enumerate(satir, 1):
            s.ata(i, j, Hucre(v))
    b = tara(k, m, "yinelenen_satir")
    assert len(b) == 2 and b[0].onem == saglik.BILGI
    assert sorted(x.konum for x in b) == [(2, 1), (3, 1)] and b[0].adet == 2                  # Türkçe büyük/küçük harf duyarsız


def test_yinelenen_satir_yanlis_alarm_yok():
    k, s, m = kur()
    for r, v in enumerate([("A", "B", 1.0), ("C", "D", 2.0), ("E", "F", 3.0), ("G", "H", 4.0), ("I", "J", 5.0)], 1):
        for j, x in enumerate(v, 1):
            s.ata(r, j, Hucre(x))
    assert tara(k, m, "yinelenen_satir") == []                              # hepsi farklı
    for r in range(10, 13):                                                  # 3 satırlık küçük blok (< 5): bakılmaz
        for j, x in enumerate(("X", "Y", 1.0), 1):
            s.ata(r, j, Hucre(x))
    assert tara(k, m, "yinelenen_satir") == []
    for r in range(20, 26):                                                  # 2 sütunlu satırlar (< 3 hücre): tablo sayılmaz
        s.ata(r, 1, Hucre("a"))
        s.ata(r, 2, Hucre("b"))
    assert tara(k, m, "yinelenen_satir") == []


# ================================================================ 8. geçersiz kimlik verileri
def test_kimlik_basliktan_gecersiz_tc_ve_vkn_ve_iban():
    k, s, m = kur()
    s.ata(1, 1, Hucre("T.C. Kimlik No"))
    s.ata(1, 2, Hucre("Vergi No"))
    s.ata(1, 3, Hucre("IBAN"))
    for r in range(2, 7):
        s.ata(r, 1, Hucre(float(tc_uret(rnd=random.Random(r)))))        # sayı olarak yazılmış geçerli TC
        s.ata(r, 2, Hucre(vkn_uret(rnd=random.Random(r + 10))))
        s.ata(r, 3, Hucre(iban_bicimli(iban_uret(rnd=random.Random(r + 20)))))
    assert tara(k, m, "gecersiz_kimlik") == []                              # hepsi geçerli
    s.ata(4, 1, Hucre(float(tc_bozuk(tc_uret(rnd=random.Random(4))))))
    s.ata(5, 2, Hucre("1234567891"))
    s.ata(6, 3, Hucre("TR000000000000000000000000"))
    b = tara(k, m, "gecersiz_kimlik")
    assert {x.konum for x in b} == {(4, 1), (5, 2), (6, 3)}
    assert all(x.onem == saglik.KRITIK for x in b)                           # başlıktan anlaşıldı


def test_kimlik_icerikten_anlasilirsa_uyari():
    k, s, m = kur()
    for r in range(1, 9):
        s.ata(r, 1, Hucre(tc_uret(rnd=random.Random(r))))
    s.ata(9, 1, Hucre("12345678900"))                                          # başlıksız; sütunun %70'i geçerli
    (b,) = tara(k, m, "gecersiz_kimlik")
    assert b.onem == saglik.UYARI and b.konum == (9, 1)


def test_kimlik_yanlis_alarm_yok():
    k, s, m = kur()
    s.ata(1, 1, Hucre("Barkod"))
    for r in range(2, 10):
        s.ata(r, 1, Hucre(f"{86900000000 + r * 7}"))                           # 11 haneli ama kimlik sütunu değil, geçerli oranı düşük
    s.ata(1, 2, Hucre("Telefon"))
    for r in range(2, 8):
        s.ata(r, 2, Hucre(f"0532 123 45 {60 + r}"))
    assert tara(k, m, "gecersiz_kimlik") == []


# ================================================================ ayarlar, yoksayma, ilerleme, salt okunurluk
def test_her_kontrol_ayrica_kapatilabilir():
    k, s, m = kur()
    sayilar(s, 1, 2, 6)
    s.ata(8, 1, Hucre(formul="=SUM(A2:A5)"))
    s.ata(8, 2, Hucre(formul="=1/0"))
    assert {b.kontrol for b in tara(k, m)} == {"eksik_aralik", "hata"}
    a = saglik.Ayarlar()
    a.acik["eksik_aralik"] = False
    assert {b.kontrol for b in saglik.Tarayici(k, m, a).tara()} == {"hata"}
    a.acik["hata"] = False
    assert saglik.Tarayici(k, m, a).tara() == []


def test_yoksayilan_bulgu_tekrar_gelmez():
    k, s, m = kur()
    sayilar(s, 1, 2, 6)
    s.ata(8, 1, Hucre(formul="=SUM(A2:A5)"))
    (b,) = tara(k, m, "eksik_aralik")
    assert b.anahtar == "eksik_aralik|Sayfa1|A8"
    t = saglik.Tarayici(k, m, saglik.Ayarlar(), {b.anahtar})
    assert t.tara() == [] and t.yoksayilan == 1


def test_ilerleme_ureteci_ve_iptal():
    k, s, m = kur()
    for _ in range(3):
        k.sayfa_ekle()
    t = saglik.Tarayici(k, m)
    olaylar = list(t.calistir())
    ilerleme = [o[1] for o in olaylar if o[0] == "ilerleme"]
    assert ilerleme == sorted(ilerleme) and ilerleme[0] == 0.0 and ilerleme[-1] == 1.0
    g = saglik.Tarayici(k, m).calistir()
    next(g)
    g.close()                                                                  # iptal: üreteç bırakılır, kaynak kalmaz


def test_denetci_hucre_degistirmez():
    k, s, m = kur()
    sayilar(s, 1, 2, 12)
    s.ata(14, 1, Hucre(formul="=SUM(A2:A10)"))
    s.ata(1, 1, Hucre("x"))
    s.ata(9, 2, Hucre("1.234,5"))
    s.ata(3, 3, Hucre(formul="=A3*1.18"))
    once = {a: (h.deger, h.formul) for a, h in s._hucreler.items()}
    yigin_once = GeriAlYigini()
    tara(k, m)
    assert {a: (h.deger, h.formul) for a, h in s._hucreler.items()} == once and not yigin_once.geri_alinabilir()


def test_ayarlar_kaydedilir_okunur(tmp_path, monkeypatch):
    monkeypatch.setenv("TABCEL_VERI_KLASORU", str(tmp_path))
    a = saglik.Ayarlar()
    a.acik["sabit_sayi"] = False
    a.sabit_yoksay = (1.0, 100.0)
    saglik.ayarlari_yaz(a)
    b = saglik.ayarlari_oku()
    assert b.acik["sabit_sayi"] is False and b.acik["hata"] is True and b.sabit_yoksay == (1.0, 100.0)
    (tmp_path / "saglik_ayarlari.json").write_text("{bozuk", encoding="utf-8")
    assert saglik.ayarlari_oku().sabit_yoksay == saglik.VARSAYILAN_SABITLER      # bozuk dosya: varsayılan
