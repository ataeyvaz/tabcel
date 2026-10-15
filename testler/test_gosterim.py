from tabcel.model.gosterim import goster, sayiyi_sigdir


def sigar(n):
    return lambda t: len(t) <= n


def test_goster_genel():
    assert goster(None) == "" and goster(3.0) == "3" and goster(2.5) == "2,5"
    # Genel biçim en çok 11 karakter (işaretsiz): gerçek Excel'de (COM, 2026-10-15) ölçüldü
    assert goster(1.23e-5) == "0,0000123" and goster(1.5e20) == "1,5E+20" and goster(1e-10) == "1E-10"
    assert goster(1 / 3) == "0,333333333" and goster(123456789012.0) == "1,23457E+11" and goster(-123456789012.0) == "-1,23457E+11"
    assert goster(12345678901.2345) == "12345678901" and goster(1.2345678e-6) == "1,23457E-06"
    assert goster(True) == "DOĞRU" and goster("a") == "a"


def test_sigiyorsa_degismez():
    assert sayiyi_sigdir(3.14159, sigar(20)) == "3,14159"
    assert sayiyi_sigdir(42.0, sigar(2)) == "42"


def test_ondalik_yuvarlanir():
    assert sayiyi_sigdir(3.14159265, sigar(6)) == "3,1416"
    assert sayiyi_sigdir(3.14159265, sigar(4)) == "3,14"
    assert sayiyi_sigdir(3.14159265, sigar(2)) == "3"
    assert sayiyi_sigdir(-3.14159265, sigar(5)) == "-3,14"
    assert sayiyi_sigdir(2.5, sigar(1)) == "3"            # yarım değer sıfırdan uzağa
    assert sayiyi_sigdir(-2.5, sigar(2)) == "-3"


def test_tam_kisim_yuvarlanamazsa_bilimsel():
    assert sayiyi_sigdir(123456789.0, sigar(9)) == "123456789"
    assert sayiyi_sigdir(123456789.0, sigar(7)) == "1,2E+08"
    assert sayiyi_sigdir(123456789.0, sigar(5)) == "1E+08"
    assert sayiyi_sigdir(0.0000123, sigar(8)) == "1,23E-05"
    assert sayiyi_sigdir(0.0000123, sigar(7)) == "1,2E-05"
    assert sayiyi_sigdir(0.0000123, sigar(6)) == "1E-05"


def test_hic_sigmazsa_none():
    assert sayiyi_sigdir(123456789.0, sigar(2)) is None
    assert sayiyi_sigdir(-1.5e-20, sigar(3)) is None


def test_sifira_yuvarlanan_sifir_gosterilmez():
    t = sayiyi_sigdir(0.0004, sigar(3))
    assert t is None or t != "0"
    assert sayiyi_sigdir(0.0, sigar(1)) == "0"


def test_hata_turkce_gosterilir():
    from tabcel.model.deger import BASV, BOL0, DEGER_HATASI, Hata
    assert goster(BOL0) == "#SAYI/0!" and goster(BASV) == "#BAŞV!" and goster(DEGER_HATASI) == "#DEĞER!"
    assert goster(Hata("#BILINMEYEN")) == "#BILINMEYEN"       # tanımsız kod olduğu gibi


def test_hata_dahil_tum_degerler_goster_icin_str_doner():
    from tabcel.model.deger import YOK
    for v in (None, "a", 1.5, True, YOK):
        assert isinstance(goster(v), str)
