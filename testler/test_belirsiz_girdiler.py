"""T5b: belirsiz sayı/tarih girdileri — beklenen sonuçlar GERÇEK Excel'den (Türkçe bölgesel ayar, 2026-10-11,
`araclar/excel_girdi_karsilastir.ps1`, `Range.FormulaLocal`; ABD ayrıştırması `Value2` kullanılmadı). Tarihler seri sayı.
`FARK`lar bilinçli/bekleyen Excel farkları (strict xfail: düzelince testi güncelleyin)."""
import pytest

from tabcel.model.girdi import akilli_coz

# (girdi, tür, değer) — tür: sayi | metin
ESIT = [
    ('1.5', 'sayi', '46143'),
    ('1,5.2', 'metin', '1,5.2'),
    ('1/2', 'sayi', '46054'),
    ('3-4', 'sayi', '46115'),
    ('00123', 'sayi', '123'),
    ('0123', 'sayi', '123'),
    ('1.234', 'sayi', '1234'),
    ('1.234,5', 'sayi', '1234.5'),
    ('1,234', 'sayi', '1.234'),
    ('1,234.56', 'metin', '1,234.56'),
    ('12.5.2026', 'sayi', '46154'),
    ('1e3', 'sayi', '1000'),
    ('+5', 'sayi', '5'),
    ('-5', 'sayi', '-5'),
    ('(5)', 'sayi', '-5'),
    ('5-', 'metin', '5-'),
    ('%5', 'sayi', '0.05'),
    ('5%', 'sayi', '0.05'),
    ('1 234', 'metin', '1 234'),
    ('1 234,5', 'metin', '1 234,5'),
    ('0,5', 'sayi', '0.5'),
    ('0.5', 'metin', '0.5'),
    ('.5', 'metin', '.5'),
    (',5', 'sayi', '0.5'),
    ('1.', 'metin', '1.'),
    ('1,', 'sayi', '1'),
    ('₺5', 'sayi', '5'),
    ('5 TL', 'metin', '5 TL'),
    ('€5', 'sayi', '5'),
    ('10/10/2026', 'sayi', '46305'),
    ('10.10', 'sayi', '46305'),
    ('1.1.2026', 'sayi', '46023'),
    ('31.12.2026', 'sayi', '46387'),
    ('2026-01-02', 'sayi', '46024'),
    ('12:30', 'sayi', '0.520833333333333'),
    ('1,5,5', 'metin', '1,5,5'),
    ('1.234.567', 'sayi', '1234567'),
    ('1 2', 'metin', '1 2'),
    ('13/1', 'sayi', '46035'),
    ('30/2', 'metin', '30/2'),
    ('0/1', 'metin', '0/1'),
    ('5.', 'metin', '5.'),
    ('--5', 'metin', '--5'),
    ('1e', 'metin', '1e'),
    ('3:45 PM', 'sayi', '0.65625'),
]

FARK = [
    ('$5', 'metin', '$5'),
    ('1/2/3', 'sayi', '37653'),
    ('1/13', 'sayi', '41275'),
    ('1-2-3', 'sayi', '37653'),
    ('- 5', 'sayi', '-5'),
    ('12:3', 'sayi', '0.502083333333333'),
    ('25:00', 'sayi', '1.04166666666667'),
]


def _al(girdi):
    h, _ = akilli_coz(girdi)
    if isinstance(h.deger, str):
        return "metin", h.deger
    return "sayi", h.deger


@pytest.mark.parametrize("girdi,tur,deger", ESIT)
def test_excel_ile_ayni(girdi, tur, deger):
    t, d = _al(girdi)
    assert t == tur
    if tur == "sayi":
        assert d == pytest.approx(float(deger), abs=1e-9)
    else:
        assert d == deger


@pytest.mark.xfail(strict=True, reason="Excel farkı (surec.md → T5b Kararlar)")
@pytest.mark.parametrize("girdi,tur,deger", FARK)
def test_excel_farki(girdi, tur, deger):
    t, d = _al(girdi)
    assert t == tur and (tur == "metin" or d == pytest.approx(float(deger), abs=1e-9))


def test_baslangic_sifir_excel_gibi_sayi_olur():
    """Karar (T5b): elle yazılan 0123 → 123 (Excel gibi); sıfırı korumak için Metin biçimi ya da başta '."""
    assert _al("0123") == ("sayi", 123.0) and _al("'0123") == ("metin", "0123")
