"""Sözcükleyici + ayrıştırıcı (Qt yok)."""
import pytest

from tabcel.formul import sozcuk as S
from tabcel.formul.agac import (
    Ad, Bos, Cagri, DiziSabit, Ikili, Ref, Sabit, Tekli, Yuzde, ayristir, formul_ayristir,
)
from tabcel.formul.sozcuk import Basvuru, FormulHatasi, metne, sayfa_oneki, sozcukle
from tabcel.formul.yerel import EN, SAKLI, TR
from tabcel.model.adres import MAX_COL, MAX_ROW
from tabcel.model.deger import Hata


def turler(metin, yerel=EN):
    return [s.tur for s in sozcukle(metin, yerel) if s.tur != S.BOSLUK]


# --- sözcükleyici ---
@pytest.mark.parametrize("metin", [
    "SUM(A1:A3, 2.5)", "  A1 +  $B$2 ", 'IF(A1>0,"a ""b""",FALSE)', "'Gelir Gider'!A1:B2*2",
    "{1,2;3,4}", "-2^2%", "A:A", "1:1", "Sayfa2!$A$1", "#DIV/0!+1",
])
def test_gidis_donus_birebir(metin):
    assert metne(sozcukle(metin, EN)) == metin


def test_tr_gidis_donus():
    m = "TOPLA(A1:A3; 2,5) & \"x;y\" & {1\\2;3\\4}"
    assert metne(sozcukle(m, TR)) == m


def test_sayilar_yerele_gore():
    assert [s.deger for s in sozcukle("1.5", EN)] == [1.5]
    assert [s.deger for s in sozcukle("1,5", TR)] == [1.5]
    assert [s.deger for s in sozcukle("1.5E3", EN)] == [1500.0]
    assert [s.deger for s in sozcukle(".5", EN)] == [0.5]
    # EN'de virgül ayırıcıdır
    assert turler("1,5", EN) == [S.SAYI, S.AYRAC, S.SAYI]


def test_metin_kacisli_tirnak():
    s = sozcukle('"a""b"', EN)[0]
    assert s.tur == S.METIN and s.deger == 'a"b'


def test_kapanmamis_tirnak():
    with pytest.raises(FormulHatasi):
        sozcukle('"abc', EN)


def test_basvuru_turleri():
    b = sozcukle("$B$3", EN)[0].deger
    assert b == Basvuru("hucre", 3, 2, 3, 2, True, True, True, True)
    b = sozcukle("C5:A1", EN)[0].deger              # normalize edilir
    assert (b.tur, b.r1, b.c1, b.r2, b.c2) == ("aralik", 1, 1, 5, 3)
    b = sozcukle("B:$D", EN)[0].deger
    assert (b.tur, b.r1, b.r2, b.c1, b.c2, b.c2m) == ("sutun", 1, MAX_ROW, 2, 4, True)
    b = sozcukle("2:5", EN)[0].deger
    assert (b.tur, b.r1, b.r2, b.c1, b.c2) == ("satir", 2, 5, 1, MAX_COL)


def test_fonksiyon_adi_hucre_gibi():
    # LOG10 bir sütun+satır gibi görünür ama '(' geldiği için fonksiyondur
    assert turler("LOG10(100)") == [S.FONK, S.AC, S.SAYI, S.KAPA]
    assert turler("A1B") == [S.AD]
    assert turler("XFE1") == [S.AD]             # sütun sınırı dışı → ad
    assert turler("A1048577") == [S.AD]         # satır sınırı dışı → ad


def test_sayfa_onekleri():
    b = sozcukle("'Gelir Gider'!A1", EN)[0].deger
    assert b.sayfa == "Gelir Gider"
    b = sozcukle("'Ata''nın'!A1", EN)[0].deger
    assert b.sayfa == "Ata'nın"
    b = sozcukle("Sayfa2!B2", EN)[0].deger
    assert b.sayfa == "Sayfa2"
    b = sozcukle("Şubat!B2", TR)[0].deger
    assert b.sayfa == "Şubat"
    b = sozcukle("[3]!B2", SAKLI)[0].deger
    assert b.sayfa == 3
    with pytest.raises(FormulHatasi):
        sozcukle("[3]!B2", EN)                   # kimlik yalnız saklanan biçimde


def test_sayfa_oneki_yaz():
    assert sayfa_oneki("Sayfa2") == "Sayfa2!"
    assert sayfa_oneki("Gelir Gider") == "'Gelir Gider'!"
    assert sayfa_oneki("Ata'nın") == "'Ata''nın'!"
    assert sayfa_oneki("2024") == "'2024'!"
    assert sayfa_oneki("A1") == "'A1'!"         # hücre adresine benzeyen ad tırnaklanır
    assert sayfa_oneki("Şubat") == "Şubat!"


def test_hata_sabitleri():
    assert sozcukle("#N/A", EN)[0].deger == "#N/A"
    assert sozcukle("#yok", TR)[0].deger == "#N/A"
    assert sozcukle("#BÖL/0!", TR)[0].deger == "#DIV/0!"       # eski yazım takma adı
    assert sozcukle("#SAYI/0!", TR)[0].deger == "#DIV/0!" and sozcukle("#SAYI!", TR)[0].deger == "#NUM!"
    assert sozcukle("Sayfa1!#REF!", EN)[0].deger == "#REF!"
    with pytest.raises(FormulHatasi):
        sozcukle("#ABC", EN)


def test_dizi_ayiricilari_tr():
    assert turler("{1\\2;3\\4}", TR) == [
        S.DIZI_AC, S.SAYI, S.DIZI_SUTUN, S.SAYI, S.DIZI_SATIR, S.SAYI, S.DIZI_SUTUN, S.SAYI,
        S.DIZI_KAPA]
    # dizi dışında ';' argüman ayırıcıdır
    assert S.AYRAC in turler("X(1;{1;2})", TR)


def test_konumlar():
    ss = sozcukle("SUM( A1 ,B2)", EN)
    a1 = [s for s in ss if s.tur == S.BASVURU][0]
    assert a1.konum == 5 and a1.metin == "A1"


# --- ayrıştırıcı ---
def ag(metin):
    return formul_ayristir(metin, EN)


def test_oncelik():
    assert ag("1+2*3") == Ikili("+", Sabit(1.0), Ikili("*", Sabit(2.0), Sabit(3.0)))
    # Excel: tekli eksi üs alma işleminden önce: -2^2 = (-2)^2
    assert ag("-2^2") == Ikili("^", Tekli("-", Sabit(2.0)), Sabit(2.0))
    # ^ soldan birleşir
    assert ag("2^3^2") == Ikili("^", Ikili("^", Sabit(2.0), Sabit(3.0)), Sabit(2.0))
    assert ag("1&2=3") == Ikili("=", Ikili("&", Sabit(1.0), Sabit(2.0)), Sabit(3.0))
    assert ag("50%") == Yuzde(Sabit(50.0))
    assert ag("1-2-3") == Ikili("-", Ikili("-", Sabit(1.0), Sabit(2.0)), Sabit(3.0))


def test_parantez_ve_cagri():
    a = ag('IF(A1>0,"x",)')
    assert isinstance(a, Cagri) and a.ad == "IF" and len(a.argumanlar) == 3
    assert a.argumanlar[2] == Bos()
    assert ag("PI()") == Cagri("PI", ())
    assert ag("sum(1)").ad == "SUM"
    assert ag("(1)") == Sabit(1.0)


def test_bos_argumanlar():
    a = ag("F(,1)")
    assert a.argumanlar == (Bos(), Sabit(1.0))


def test_mantiksal_ve_ad():
    assert ag("TRUE") == Sabit(True)
    assert ag("false") == Sabit(False)
    assert ag("Satislar") == Ad("Satislar")


def test_kesisim_ve_aralik_islec():
    a = ag("A1:B2 B1:C3")
    assert isinstance(a, Ikili) and a.islec == " "
    a = ag("A1 + B1")                           # işleç çevresindeki boşluk kesişim değildir
    assert a.islec == "+"
    a = ag("A1:INDEX(B:B,2)")
    assert a.islec == ":"


def test_dizi_sabiti():
    assert ag('{1,-2;"a",TRUE}') == DiziSabit(((1.0, -2.0), ("a", True)))
    with pytest.raises(FormulHatasi):
        ag("{1,2;3}")
    with pytest.raises(FormulHatasi):
        ag("{A1}")


@pytest.mark.parametrize("hatali", ["", "1+", "(1", "1)", "SUM(1", "SUM(1 2", "*1", "{1,"])
def test_sozdizimi_hatalari(hatali):
    with pytest.raises(FormulHatasi):
        ag(hatali)


def test_hata_sabiti_dugumu():
    assert ag("#N/A") == Sabit(Hata("#N/A"))


def test_formul_esittir_ile():
    assert formul_ayristir("=1+1") == Ikili("+", Sabit(1.0), Sabit(1.0))
