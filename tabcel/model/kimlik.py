"""Kişisel veri doğrulayıcıları, bulucu ve maskeleyici — TEK kaynak (CLAUDE.md kural 18). Qt yok, ağ yok.

Türler: TC kimlik no, vergi kimlik no, IBAN (TR; mod-97), kredi kartı (Luhn + kart ön eki), telefon (Türkiye biçimleri), e-posta,
ad-soyad (yalnız sütun başlığına göre — metinden algılanmaz).

Güven düzeyi (`Bulgu.guven`):
- `KESIN`: algoritma doğruladı ve rastgele eşleşme ihtimali ihmal edilebilir (TC, IBAN, kart, e-posta; ön ekli telefon).
- `BICIM`: yalnız biçime dayalı (ör. ön eksiz ama gruplu telefon).
- `BELIRSIZ`: başka bir türle karışabilir (10 haneli sayı: vergi no mu telefon mu — rastgele 10 haneli sayının ≈ %10'u vergi no
  algoritmasını geçer). Üst katman sütun başlığı gibi bağlamla yükseltir.

Testlerde yalnız sentetik veri kullanılır (kural 19)."""
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

KESIN, BICIM, BELIRSIZ = "kesin", "bicim", "belirsiz"
TC, VKN, IBAN, TELEFON, EPOSTA, KART, AD = "tc", "vkn", "iban", "telefon", "eposta", "kart", "ad"
TUR_ADLARI = {TC: "T.C. kimlik no", VKN: "Vergi kimlik no", IBAN: "IBAN", TELEFON: "Telefon", EPOSTA: "E-posta",
              KART: "Kredi kartı no", AD: "Ad-soyad"}
TURLER = (TC, VKN, IBAN, KART, TELEFON, EPOSTA, AD)


# ------------------------------------------------------------------ doğrulayıcılar
def _rakam_mi(s: str) -> bool:
    return s.isascii() and s.isdigit()


def tc_gecerli(no: str) -> bool:
    """T.C. kimlik no: 11 hane, ilk hane ≠ 0, 10. ve 11. hane sağlaması."""
    if len(no) != 11 or not _rakam_mi(no) or no[0] == "0":
        return False
    d = [int(k) for k in no]
    if (sum(d[0:9:2]) * 7 - sum(d[1:8:2])) % 10 != d[9]:
        return False
    return sum(d[:10]) % 10 == d[10]


def vkn_gecerli(no: str) -> bool:
    """Vergi kimlik no: 10 hane; GİB sağlama algoritması."""
    if len(no) != 10 or not _rakam_mi(no):
        return False
    d = [int(k) for k in no]
    toplam = 0
    for i in range(9):
        t = (d[i] + (9 - i)) % 10
        v = (t * (2 ** (9 - i))) % 9
        if t != 0 and v == 0:
            v = 9
        toplam += v
    return (10 - toplam % 10) % 10 == d[9]


def iban_sade(s: str) -> str:
    """Boşluk/tireleri atıp büyük harfe çevirir (IBAN ASCII'dir; Türkçe harf kuralı gerekmez)."""
    return re.sub(r"[\s\-]", "", s).upper()


def iban_gecerli(s: str, sadece_tr: bool = True) -> bool:
    """IBAN: `TR` + 24 hane (toplam 26) ve mod-97 = 1; boşluklu/tireli yazım kabul. `sadece_tr=False` diğer ülkeleri (15–34 karakter)
    yalnız mod-97 ile doğrular."""
    i = iban_sade(s)
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}", i):
        return False
    if sadece_tr and not (i.startswith("TR") and len(i) == 26 and _rakam_mi(i[2:])):
        return False
    yeniden = i[4:] + i[:4]
    sayi = "".join(str(int(k, 36)) for k in yeniden)
    return int(sayi) % 97 == 1


def luhn_gecerli(rakamlar: str) -> bool:
    if not _rakam_mi(rakamlar):
        return False
    t = 0
    for i, k in enumerate(reversed(rakamlar)):
        d = int(k)
        if i % 2:
            d *= 2
            if d > 9:
                d -= 9
        t += d
    return t % 10 == 0


_KART_ONEKLERI = (            # (ön ek aralığı, uzunluklar) — Visa, Mastercard, Amex, Troy, Discover, Diners, JCB
    (("4",), (13, 16, 19)),
    (tuple(str(x) for x in range(51, 56)) + tuple(str(x) for x in range(2221, 2721)), (16,)),
    (("34", "37"), (15,)),
    (("9792",), (16,)),
    (("6011", "65") + tuple(str(x) for x in range(644, 650)), (16, 17, 18, 19)),
    (("36", "38") + tuple(str(x) for x in range(300, 306)), (14, 15, 16, 17, 18, 19)),
    (tuple(str(x) for x in range(3528, 3590)), (16, 17, 18, 19)),
)


def kart_gecerli(s: str) -> bool:
    """Kredi/banka kartı: 13–19 hane, bilinen kart ön eki ve Luhn (rastgele uzun sayıların çoğu elenir)."""
    d = re.sub(r"[\s\-]", "", s)
    if not _rakam_mi(d) or not 13 <= len(d) <= 19:
        return False
    if not any(len(d) in uz and any(d.startswith(o) for o in oneks) for oneks, uz in _KART_ONEKLERI):
        return False
    return luhn_gecerli(d)


def telefon_ulusal(s: str) -> Optional[str]:
    """Türkiye telefonunu 10 haneli ulusal biçime (`5321234567`) çevirir; telefon değilse None. Kabul: `+90 532 123 45 67`,
    `0090…`, `0 (532) 123 45 67`, `0532-123-45-67`, `5321234567`; cep (5xx) ve sabit (2xx/3xx/4xx) hatlar, 850 hatları."""
    a = s.strip()
    if not re.fullmatch(r"[+\d\s().\-]+", a):
        return None
    d = re.sub(r"\D", "", a)
    if a.startswith("+"):
        if not d.startswith("90"):
            return None
        d = d[2:]
    elif d.startswith("0090"):
        d = d[4:]
    elif len(d) == 12 and d.startswith("90"):
        d = d[2:]
    elif len(d) == 11 and d.startswith("0"):
        d = d[1:]
    if len(d) != 10 or not re.fullmatch(r"(?:[2345]\d{2}|850)\d{7}", d):
        return None
    if len(set(d)) == 1:                                    # 5555555555 gibi
        return None
    return d


def telefon_gecerli(s: str) -> bool:
    return telefon_ulusal(s) is not None


_EPOSTA = re.compile(r"[\w.%+\-]+@[\w\-]+(?:\.[\w\-]+)*\.[^\W\d_]{2,}")


def eposta_gecerli(s: str) -> bool:
    return bool(_EPOSTA.fullmatch(s.strip()))


# ------------------------------------------------------------------ metinde bulma
@dataclass(frozen=True)
class Bulgu:
    tur: str
    bas: int
    son: int            # dışlayıcı
    metin: str
    guven: str

    @property
    def tur_adi(self) -> str:
        return TUR_ADLARI[self.tur]


_ADAYLAR = (
    (EPOSTA, re.compile(r"[\w.%+\-]+@[\w\-]+(?:\.[\w\-]+)+")),
    (IBAN, re.compile(r"(?<![A-Za-z0-9])[Tt][Rr]\s?\d{2}(?:[\s\-]?\d{4}){5}[\s\-]?\d{2}(?![A-Za-z0-9])")),
    (KART, re.compile(r"(?<!\d)(?:\d[ \-]?){12,18}\d(?!\d)")),
    (TELEFON, re.compile(r"(?<![\d.,])(?:\+|00)?\d[\d\s().\-]{8,17}\d(?!\d)")),
    (TC, re.compile(r"(?<![\d.,\-])\d{11}(?![\d.,\-]?\d)")),
    (VKN, re.compile(r"(?<![\d.,\-])\d{10}(?![\d.,\-]?\d)")),
)


def tara_metin(metin: str) -> List[Bulgu]:
    """Metindeki kişisel verileri (doğrulanmış) bulur; aynı yeri iki tür sahiplenirse yalnız önceliklisi (e-posta > IBAN > kart >
    telefon > TC > vergi no) döner, 10 haneli sayıda telefon/vergi no çakışması `BELIRSIZ` olarak ikisi birden."""
    bulgular: List[Bulgu] = []
    dolu: List[Tuple[int, int]] = []

    def cakisir(b, s):
        return any(b < y and d < s for d, y in dolu)
    for tur, desen in _ADAYLAR:
        for m in desen.finditer(metin):
            b, s = m.start(), m.end()
            if cakisir(b, s):
                continue
            ham = m.group(0)
            if tur == EPOSTA:
                if eposta_gecerli(ham):
                    bulgular.append(Bulgu(tur, b, s, ham, KESIN))
                    dolu.append((b, s))
            elif tur == IBAN:
                if iban_gecerli(ham):
                    bulgular.append(Bulgu(tur, b, s, ham, KESIN))
                    dolu.append((b, s))
            elif tur == KART:
                if kart_gecerli(ham):
                    bulgular.append(Bulgu(tur, b, s, ham, KESIN))
                    dolu.append((b, s))
            elif tur == TELEFON:
                n = telefon_ulusal(ham)
                if n is None:
                    continue
                duz = ham.strip()
                oneki_var = duz.startswith(("+", "0"))
                gruplu = bool(re.search(r"[\s().\-]", duz))
                if oneki_var or gruplu:
                    # ön ekli ya da gruplu yazım: telefon
                    bulgular.append(Bulgu(tur, b, s, ham, KESIN if oneki_var else BICIM))
                    dolu.append((b, s))
                else:                                          # çıplak 10 hane: vergi no ile karışabilir
                    bulgular.append(Bulgu(tur, b, s, ham, BELIRSIZ))
                    if vkn_gecerli(ham):
                        bulgular.append(Bulgu(VKN, b, s, ham, BELIRSIZ))
                    dolu.append((b, s))
            elif tur == TC:
                if tc_gecerli(ham):
                    bulgular.append(Bulgu(tur, b, s, ham, KESIN))
                    dolu.append((b, s))
            elif tur == VKN:
                if vkn_gecerli(ham):
                    bulgular.append(Bulgu(tur, b, s, ham, BELIRSIZ))
                    dolu.append((b, s))
    return sorted(bulgular, key=lambda x: (x.bas, x.tur))


def tum_hucre(metin: str) -> List[Bulgu]:
    """Hücrenin TÜM içeriği (kenar boşlukları hariç) kişisel veriyse onun bulguları; değilse boş."""
    kes = metin.strip()
    if not kes:
        return []
    return [b for b in tara_metin(kes) if b.bas == 0 and b.son == len(kes)]


# ------------------------------------------------------------------ maskeleme
@dataclass(frozen=True)
class MaskeAyari:
    """Başta `bas`, sonda `son` karakter açık kalır, kalanı `karakter` olur (e-posta/ad için `bas` yerel kısmın/sözcüğün ilk
    harfidir)."""
    bas: int = 0
    son: int = 0
    karakter: str = "*"


VARSAYILAN_MASKELER: Dict[str, MaskeAyari] = {
    TC: MaskeAyari(2, 2), VKN: MaskeAyari(2, 2), IBAN: MaskeAyari(4, 4), KART: MaskeAyari(0, 4),
    TELEFON: MaskeAyari(4, 2), EPOSTA: MaskeAyari(1, 0), AD: MaskeAyari(1, 0),
}


def _ort(s: str, ayar: MaskeAyari) -> str:
    """`s`'nin başta/sonda açık kalan kısımları dışını maskeler (kısa metinde tamamı maskelenir)."""
    n = len(s)
    if ayar.bas + ayar.son >= n:
        return ayar.karakter * n
    return s[:ayar.bas] + ayar.karakter * (n - ayar.bas - ayar.son) + (s[n - ayar.son:] if ayar.son else "")


def _grupla(s: str, boyutlar) -> str:
    parcalar, i = [], 0
    for b in boyutlar:
        parcalar.append(s[i:i + b])
        i += b
    if i < len(s):
        parcalar.append(s[i:])
    return " ".join(p for p in parcalar if p)


def maskele(tur: str, metin: str, ayar: Optional[MaskeAyari] = None) -> str:
    """Değeri türüne uygun biçimde maskeler. Örnekler (varsayılan): TC `12*******34`; IBAN `TR12 **** **** **** **** **34 56`;
    telefon `0532 *** ** 67`; kart `**** **** **** 1234`; e-posta `a***@ornek.com`; ad `A*** Y***`."""
    ayar = ayar or VARSAYILAN_MASKELER.get(tur, MaskeAyari(1, 1))
    if tur in (TC, VKN):
        return _ort(re.sub(r"\D", "", metin) or metin, ayar)
    if tur == IBAN:
        return _grupla(_ort(iban_sade(metin), ayar), (4, 4, 4, 4, 4, 4, 2))
    if tur == KART:
        d = re.sub(r"\D", "", metin)
        return _grupla(_ort(d, ayar), (4, 4, 4, 4, 4))
    if tur == TELEFON:
        n = telefon_ulusal(metin)
        if n is None:
            return _ort(metin, ayar)
        return _grupla(_ort("0" + n, ayar), (4, 3, 2, 2))
    if tur == EPOSTA:
        yerel, _, alan = metin.strip().partition("@")
        return yerel[:ayar.bas] + ayar.karakter * 3 + "@" + alan
    if tur == AD:
        return " ".join(s[:ayar.bas] + ayar.karakter * 3 if len(s) > ayar.bas else ayar.karakter * len(s)
                        for s in metin.split())
    return _ort(metin, ayar)
