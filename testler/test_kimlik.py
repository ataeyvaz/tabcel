"""Faz 9a: model/kimlik.py (doğrulayıcılar, bulucu, maskeleyici), VERGİNOGEÇERLİ / IBANGEÇERLİ işlevleri, motor bağımlılık API'si.
Yalnız sentetik veri (kural 19)."""
import random

import pytest

from sentetik import iban_bicimli, iban_uret, kart_uret, tc_bozuk, tc_uret, vkn_uret
from tabcel.formul import adlar
from tabcel.formul.motor import Hesaplayici
from tabcel.model import deger as D
from tabcel.model import kimlik
from tabcel.model.sayfa import CalismaKitabi, Hucre

TC = tc_uret()
VKN = vkn_uret()
IBAN = iban_uret()
KART = kart_uret("4")


# ---------------------------------------------------------------- doğrulayıcılar: geçerli / geçersiz / benzer
def test_tc():
    assert kimlik.tc_gecerli(TC) and kimlik.tc_gecerli(tc_uret(rnd=random.Random(9)))
    assert not kimlik.tc_gecerli(tc_bozuk(TC))
    assert not kimlik.tc_gecerli("01234567890") and not kimlik.tc_gecerli(TC[:10]) and not kimlik.tc_gecerli(TC + "1")
    assert not kimlik.tc_gecerli("abcdefghijk") and not kimlik.tc_gecerli("")


def test_vkn():
    assert kimlik.vkn_gecerli(VKN)
    assert not kimlik.vkn_gecerli(VKN[:9] + str((int(VKN[9]) + 1) % 10))
    assert not kimlik.vkn_gecerli(VKN[:9]) and not kimlik.vkn_gecerli("12345678a0")


def test_iban():
    assert kimlik.iban_gecerli(IBAN) and kimlik.iban_gecerli(iban_bicimli(IBAN)) and kimlik.iban_gecerli(IBAN.lower())
    assert kimlik.iban_gecerli("-".join(IBAN[i:i + 4] for i in range(0, 26, 4)))
    bozuk = IBAN[:25] + str((int(IBAN[25]) + 1) % 10)
    assert not kimlik.iban_gecerli(bozuk)
    assert not kimlik.iban_gecerli(IBAN[:24]) and not kimlik.iban_gecerli("DE89370400440532013000")      # TR değil
    assert kimlik.iban_gecerli("DE89370400440532013000", sadece_tr=False)                              # IBAN standardının kamusal örneği


def test_kart_luhn_ve_on_ek():
    assert kimlik.kart_gecerli(KART) and kimlik.kart_gecerli(" ".join(KART[i:i + 4] for i in range(0, 16, 4)))
    assert kimlik.kart_gecerli(kart_uret("51")) and kimlik.kart_gecerli(kart_uret("37", 15)) and kimlik.kart_gecerli(kart_uret("9792"))
    assert not kimlik.kart_gecerli(KART[:15] + str((int(KART[15]) + 1) % 10))                          # Luhn tutmaz
    assert not kimlik.kart_gecerli(kart_uret("7", 16))                                                  # bilinmeyen ön ek (Luhn geçse de)
    assert not kimlik.kart_gecerli("1234567890123")


@pytest.mark.parametrize("yazim", ["+90 532 123 45 67", "0090 532 123 45 67", "0 (532) 123 45 67", "0532-123-45-67",
                                   "05321234567", "5321234567", "+905321234567", "0212 555 12 34", "90 532 123 45 67"])
def test_telefon_gecerli_biçimler(yazim):
    assert kimlik.telefon_gecerli(yazim)


@pytest.mark.parametrize("yazim", ["+44 532 123 45 67", "0132 123 45 67", "53212345", "5555555555", "abc", "", "1234567890",
                                   "+90 632 123 45 67"])
def test_telefon_gecersiz(yazim):
    assert not kimlik.telefon_gecerli(yazim)


def test_eposta():
    assert kimlik.eposta_gecerli("ali.veli@ornek.com") and kimlik.eposta_gecerli("a+b@alt.ornek.com.tr")
    assert not kimlik.eposta_gecerli("ali@ornek") and not kimlik.eposta_gecerli("@ornek.com") and not kimlik.eposta_gecerli("ali ornek.com")


# ---------------------------------------------------------------- metinde bulma (yanlış alarm denetimi dahil)
def turler(metin):
    return [(b.tur, b.guven) for b in kimlik.tara_metin(metin)]


def test_tara_metin_birden_cok_tur():
    m = f"TC {TC}, IBAN {iban_bicimli(IBAN)}, tel 0532 123 45 67, mail a.b@ornek.com, kart {KART}"
    assert turler(m) == [("tc", "kesin"), ("iban", "kesin"), ("telefon", "kesin"), ("eposta", "kesin"), ("kart", "kesin")]
    b = kimlik.tara_metin(m)[0]
    assert m[b.bas:b.son] == TC


def test_yanlis_alarm_vermemeli():
    assert turler("Sipariş no 12345678901 tarihi 01.02.2024") == []                    # algoritma tutmaz
    assert turler("Barkod 8690000000013") == []                                         # 13 hane: kart ön eki/Luhn tutmaz
    assert turler("Toplam 1.234.567,89 TL") == []
    assert turler(f"ID-{TC}-01") == []                                                  # tire ile bitişik (başka kod parçası)
    assert turler("2024 yılı 3 çeyrek") == [] and turler("") == []
    assert turler(f"Tutar {TC[:5]}.{TC[5:]} TL") == []                                  # noktayla bölünmüş sayı


def test_cipak_10_hane_belirsiz():
    assert ("telefon", "belirsiz") in turler("5321234567")                               # çıplak 10 hane: telefon mu vergi no mu
    v = turler(VKN)
    assert ("vkn", "belirsiz") in v and not any(g == "kesin" for _, g in v)


def test_tum_hucre():
    assert [b.tur for b in kimlik.tum_hucre(f"  {TC} ")] == ["tc"]
    assert kimlik.tum_hucre(f"TC: {TC}") == []                                           # hücrenin tamamı değil
    assert kimlik.tum_hucre("   ") == []


# ---------------------------------------------------------------- maskeleme: kullanıcı örnekleri
def test_maskeleme_varsayilanlari():
    assert kimlik.maskele("tc", TC) == TC[:2] + "*" * 7 + TC[-2:]
    assert kimlik.maskele("iban", IBAN) == f"{IBAN[:4]} **** **** **** **** **{IBAN[22:24]} {IBAN[24:]}"
    assert kimlik.maskele("iban", iban_bicimli(IBAN)) == kimlik.maskele("iban", IBAN)
    assert kimlik.maskele("telefon", "0532 123 45 67") == "0532 *** ** 67"
    assert kimlik.maskele("telefon", "+90 532 123 45 67") == "0532 *** ** 67"
    assert kimlik.maskele("eposta", "ali@ornek.com") == "a***@ornek.com"
    assert kimlik.maskele("kart", KART) == f"**** **** **** {KART[-4:]}"
    assert kimlik.maskele("vkn", VKN) == VKN[:2] + "*" * 6 + VKN[-2:]
    assert kimlik.maskele("ad", "Ali Yılmaz") == "A*** Y***"


def test_maske_ayarlanabilir():
    assert kimlik.maskele("tc", TC, kimlik.MaskeAyari(0, 0, "X")) == "X" * 11
    assert kimlik.maskele("tc", TC, kimlik.MaskeAyari(3, 3, "#")) == TC[:3] + "#" * 5 + TC[-3:]
    assert kimlik.maskele("eposta", "ali@ornek.com", kimlik.MaskeAyari(0, 0, "x")) == "xxx@ornek.com"


def test_maske_kisa_deger_tamamen_maskelenir():
    assert kimlik.maskele("tc", "12345", kimlik.MaskeAyari(3, 3)) == "*****"
    assert kimlik.maskele("ad", "A") == "*"


# ---------------------------------------------------------------- işlevler (kural 11: normal, boş, hata, metin/sayı)
def hesapla(formul, hucreler=None):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for (r, c), v in (hucreler or {}).items():
        s.ata(r, c, Hucre(v))
    Hesaplayici(k)
    s.ata(10, 10, Hucre(formul=formul))
    return s.deger(10, 10)


def test_vkn_islevi():
    assert hesapla(f'=TR_VALIDATE_VKN("{VKN}")') is True                                 # normal
    assert hesapla("=TR_VALIDATE_VKN(A1)") is False                                      # boş hücre
    assert hesapla("=TR_VALIDATE_VKN(A1)", {(1, 1): D.YOK}) == D.YOK                      # hata girdisi olduğu gibi döner
    assert hesapla('=TR_VALIDATE_VKN("12x")') is False                                   # metin/sayı karışımı
    v2 = vkn_uret("123456789")
    assert hesapla(f"=TR_VALIDATE_VKN({int(v2)})") is True                               # sayı olarak yazılmış (baştaki sıfır olmayan)
    assert hesapla('=TR_VALIDATE_VKN("' + vkn_uret("012345678") + '")') is True                  # sıfırla başlayan vergi no metin olarak yazılınca geçerli


def test_iban_islevi():
    assert hesapla(f'=TR_VALIDATE_IBAN("{iban_bicimli(IBAN)}")') is True
    assert hesapla("=TR_VALIDATE_IBAN(A1)") is False
    assert hesapla("=TR_VALIDATE_IBAN(A1)", {(1, 1): D.BASV}) == D.BASV
    assert hesapla('=TR_VALIDATE_IBAN("TR00")') is False
    assert hesapla("=TR_VALIDATE_IBAN(5)") is False                                       # sayı


def test_telefon_islevi():
    assert hesapla('=TR_VALIDATE_PHONE("+90 532 123 45 67")') is True                     # normal
    assert hesapla('=TR_VALIDATE_PHONE("0 (212) 123 45 67")') is True                      # sabit hat
    assert hesapla("=TR_VALIDATE_PHONE(A1)") is False                                     # boş hücre
    assert hesapla("=TR_VALIDATE_PHONE(A1)", {(1, 1): D.BASV}) == D.BASV                  # hata girdisi
    assert hesapla('=TR_VALIDATE_PHONE("0532 abc 45 67")') is False                        # metin/sayı karışımı
    assert hesapla("=TR_VALIDATE_PHONE(5321234567)") is True                               # sayı olarak yazılmış


def test_eposta_islevi():
    assert hesapla('=TR_VALIDATE_EMAIL("ali.veli@ornek.com")') is True
    assert hesapla("=TR_VALIDATE_EMAIL(A1)") is False
    assert hesapla("=TR_VALIDATE_EMAIL(A1)", {(1, 1): D.YOK}) == D.YOK
    assert hesapla('=TR_VALIDATE_EMAIL("ali@")') is False
    assert hesapla("=TR_VALIDATE_EMAIL(5)") is False


def test_turkce_adlar():
    assert adlar.turkcesi("TR_VALIDATE_VKN") == "VERGİNOGEÇERLİ" and adlar.ingilizcesi("VERGİNOGEÇERLİ") == "TR_VALIDATE_VKN"
    assert adlar.turkcesi("TR_VALIDATE_IBAN") == "IBANGEÇERLİ" and adlar.ingilizcesi("IBANGEÇERLİ") == "TR_VALIDATE_IBAN"
    assert adlar.turkcesi("TR_VALIDATE_PHONE") == "TELEFONGEÇERLİ" and adlar.ingilizcesi("EPOSTAGEÇERLİ") == "TR_VALIDATE_EMAIL"


# ---------------------------------------------------------------- motor: öncüller / bağımlılar
def test_motor_onculler_ve_bagimlilar():
    k = CalismaKitabi()
    s = k.sayfalar[0]
    m = Hesaplayici(k)
    s.ata(1, 1, Hucre(2.0))
    s.ata(2, 1, Hucre(3.0))
    s.ata(1, 3, Hucre(formul="=A1*2+SUM(A1:A2)"))
    s.ata(1, 4, Hucre(formul="=C1+1"))
    kim = s.kimlik
    hucreler, araliklar = m.onculler((kim, 1, 3))
    assert hucreler == [(kim, 1, 1)] and araliklar == [(kim, (1, 1, 2, 1))]
    assert m.onculler((kim, 1, 1)) == ([], []) and m.onculler((kim, 99, 99)) == ([], [])
    assert m.bagimlilar((kim, 1, 1)) == {(kim, 1, 3)}                                    # doğrudan + aralık üzerinden
    assert m.bagimlilar((kim, 2, 1)) == {(kim, 1, 3)}                                    # aralık içindeki hücre
    assert m.bagimlilar((kim, 1, 3)) == {(kim, 1, 4)} and m.bagimlilar((kim, 1, 4)) == set()


# ---------------------------------------------------------------- 10-ön: TRTAMİŞGÜNÜ / TRİŞGÜNÜ (resmî tatilli iş günü)
from tabcel.model.tarihseri import ymd_seri
from tabcel.model import tatiller


def S(y, m, g):
    return float(ymd_seri(y, m, g))


def test_tatil_verisi():
    assert tatiller.yukle()["surum"] == 1 and tatiller.yukle()["aciklama"]
    assert tatiller.yil_araligi() == (2024, 2028)
    assert ymd_seri(2026, 4, 23) in tatiller.tatiller() and ymd_seri(2026, 3, 20) in tatiller.tatiller()
    assert ymd_seri(2026, 3, 19) not in tatiller.tatiller()                                 # arife tam iş günü


def test_tr_tamisgunu():
    # 2026-04-20 Pzt … 2026-04-24 Cum: 23 Nisan Perşembe tatil → 4 (Excel TAMİŞGÜNÜ 5 verir)
    assert hesapla("=TR_NETWORKDAYS(DATE(2026,4,20),DATE(2026,4,24))") == 4.0               # normal
    assert hesapla("=NETWORKDAYS(DATE(2026,4,20),DATE(2026,4,24))") == 5.0                  # Excel davranışı değişmedi
    assert hesapla("=TR_NETWORKDAYS(DATE(2026,4,20),DATE(2026,4,24),A1)") == 4.0            # boş ek liste
    assert hesapla("=TR_NETWORKDAYS(DATE(2026,4,20),DATE(2026,4,24),A1)", {(1, 1): S(2026, 4, 21)}) == 3.0   # ek tatil
    assert hesapla("=TR_NETWORKDAYS(A1,DATE(2026,4,24))", {(1, 1): D.YOK}) == D.YOK          # hata girdisi
    assert hesapla('=TR_NETWORKDAYS("x",DATE(2026,4,24))') == D.DEGER_HATASI                  # metin
    assert hesapla("=TR_NETWORKDAYS(DATE(2026,4,24),DATE(2026,4,20))") == -4.0               # ters sıra
    assert hesapla("=TR_NETWORKDAYS(DATE(2023,12,28),DATE(2024,1,3))") == D.SAYI            # veri kapsamı dışı


def test_tr_isgunu():
    assert hesapla("=TR_WORKDAY(DATE(2026,4,22),1)") == S(2026, 4, 24)                       # 23 Nisan atlanır
    assert hesapla("=WORKDAY(DATE(2026,4,22),1)") == S(2026, 4, 23)                          # Excel değişmedi
    assert hesapla("=TR_WORKDAY(DATE(2026,3,18),2)") == S(2026, 3, 23)                       # 19 arife iş günü; 20 Cuma bayram, 21–22 hafta sonu
    assert hesapla("=TR_WORKDAY(DATE(2026,4,24),-1)") == S(2026, 4, 22)                      # geri
    assert hesapla("=TR_WORKDAY(DATE(2026,4,22),A1)", {(1, 1): D.BASV}) == D.BASV            # hata
    assert hesapla("=TR_WORKDAY(DATE(2026,4,22),1,A1)", {(1, 1): S(2026, 4, 24)}) == S(2026, 4, 27)   # ek tatil
    assert hesapla("=TR_WORKDAY(DATE(2028,12,28),5)") == D.SAYI


def test_tr_tatil_adlari():
    assert adlar.turkcesi("TR_NETWORKDAYS") == "TRTAMİŞGÜNÜ" and adlar.ingilizcesi("TRİŞGÜNÜ") == "TR_WORKDAY"
