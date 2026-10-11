"""Sentetik kişisel veri üreticileri (CLAUDE.md kural 19): algoritmaya göre GEÇERLİ ama rastgele/uydurma değerler; gerçek kişiye ait
veri değildir. Testler ve örnek dosyalar yalnız bunları kullanır."""
import random


def tc_uret(ilk9: str = None, rnd: random.Random = None) -> str:
    r = rnd or random.Random(1)
    ilk9 = ilk9 or str(r.randint(1, 9)) + "".join(str(r.randint(0, 9)) for _ in range(8))
    d = [int(x) for x in ilk9]
    d10 = (sum(d[0:9:2]) * 7 - sum(d[1:8:2])) % 10
    return ilk9 + str(d10) + str((sum(d) + d10) % 10)


def vkn_uret(ilk9: str = None, rnd: random.Random = None) -> str:
    r = rnd or random.Random(2)
    ilk9 = ilk9 or "".join(str(r.randint(0, 9)) for _ in range(9))
    d = [int(x) for x in ilk9]
    t = 0
    for i in range(9):
        x = (d[i] + (9 - i)) % 10
        v = (x * 2 ** (9 - i)) % 9
        if x != 0 and v == 0:
            v = 9
        t += v
    return ilk9 + str((10 - t % 10) % 10)


def iban_uret(bban: str = None, rnd: random.Random = None) -> str:
    """TR IBAN (26 karakter, mod-97 geçerli); `bban` 22 hane (banka 5 + rezerv 1 + hesap 16)."""
    r = rnd or random.Random(3)
    bban = bban or "".join(str(r.randint(0, 9)) for _ in range(22))
    return f"TR{98 - int(bban + '292700') % 97:02d}" + bban


def iban_bicimli(iban: str) -> str:
    return " ".join([iban[:4]] + [iban[i:i + 4] for i in range(4, 24, 4)] + [iban[24:]])


def kart_uret(onek: str = "4", uzunluk: int = 16, rnd: random.Random = None) -> str:
    """Luhn geçerli sentetik kart no (varsayılan Visa biçimi)."""
    r = rnd or random.Random(4)
    govde = onek + "".join(str(r.randint(0, 9)) for _ in range(uzunluk - len(onek) - 1))
    t = 0
    for i, k in enumerate(reversed(govde)):
        d = int(k)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        t += d
    return govde + str((10 - t % 10) % 10)


def tc_bozuk(tc: str) -> str:
    """Son haneyi değiştirerek geçersiz yapar."""
    return tc[:-1] + str((int(tc[-1]) + 1) % 10)
