"""Doldurma (Faz 3 / 3h): seri tanıma, desen kopyası, Ctrl+D/R planları. Qt yok.

`seri_plani(sayfa, kaynak, hedef)` hedef bölgenin içeriğini ve biçimini üretir; hedef kaynağın tam
genişliğinde/yüksekliğinde bitişik bir bölgedir (aşağı, yukarı, sağa, sola). Her sütun (dikey doldurma)
ya da satır (yatay) ayrı bir şerit olarak ele alınır; yukarı/sola doldurmada seri geriye devam eder.

Şerit türleri (sıra önemli): formül içeren → desen kopyası (formül göreli kayar); tümü sayı → tarihse
gün/ay adımı, değilse tek değer kopya / iki değer sabit adım / üç+ doğrusal eğilim; ay/gün adı →
döngüsel; metin + sayı (`Ürün 1`) → sayı artar; diğer → desen yinelenir. Doğrulanamayanlar surec.md
§8b-42'dedir.
"""
import math
from typing import Dict, List, Optional, Tuple

from .adres import Aralik
from .sayfa import Anahtar, Hucre, Sayfa
from .sayi_bicimi import AY_KISA, AYLAR, GUN_KISA, GUNLER, BicimHatasi, kod_coz
from .tarihseri import ay_gun_sayisi, seri_ymd, ymd_seri

import re

_SAYILI_METIN = re.compile(r"^(.*?)(\d+)(\D*)$", re.DOTALL)
_ADLAR = (AYLAR, AY_KISA, GUNLER, GUN_KISA)


def _tr_kucuk(s: str) -> str:
    return s.replace("I", "ı").replace("İ", "i").lower()


def _tr_buyuk(s: str) -> str:
    return s.replace("i", "İ").replace("ı", "I").upper()


def _temiz(v: float) -> float:
    """Kayan nokta artığını at (1,0000000000002 → 1)."""
    return float(f"{v:.12g}")


def _yon_ve_serit(kaynak: Aralik, hedef: Aralik) -> Tuple[bool, bool]:
    """(dikey mi, geri mi). Hedef kaynağa bitişik ve aynı genişlik/yükseklikte olmalı, yoksa ValueError."""
    if (hedef.ilk_sutun, hedef.son_sutun) == (kaynak.ilk_sutun, kaynak.son_sutun):
        if hedef.ilk_satir == kaynak.son_satir + 1:
            return True, False
        if hedef.son_satir == kaynak.ilk_satir - 1:
            return True, True
    if (hedef.ilk_satir, hedef.son_satir) == (kaynak.ilk_satir, kaynak.son_satir):
        if hedef.ilk_sutun == kaynak.son_sutun + 1:
            return False, False
        if hedef.son_sutun == kaynak.ilk_sutun - 1:
            return False, True
    raise ValueError("Doldurma hedefi kaynağa bitişik ve aynı boyutta olmalı")


def _tarih_mi(kod: str) -> bool:
    try:
        return kod_coz(kod).tarih_mi
    except BicimHatasi:
        return False


# ------------------------------------------------------------------ seri üreticileri (ileri yönde)
def _sayisal(deg: List[float], n: int, geri: bool) -> List[float]:
    m = len(deg)
    if m == 1:
        return [deg[0]] * n
    if m == 2:
        adim = deg[1] - deg[0]
        return [_temiz(deg[1] + adim * (j + 1)) for j in range(n)]
    xs = range(m)
    xo, yo = (m - 1) / 2, sum(deg) / m
    payda = sum((x - xo) ** 2 for x in xs)
    egim = sum((x - xo) * (y - yo) for x, y in zip(xs, deg)) / payda
    return [_temiz(yo + egim * (m + j - xo)) for j in range(n)]


def _tarih_serisi(deg: List[float], n: int, geri: bool) -> List[float]:
    m = len(deg)
    if m == 1:
        return [deg[0] + (-1 if geri else 1) * (j + 1) for j in range(n)]
    if all(float(d).is_integer() for d in deg) and all(d >= 1 for d in deg):
        ymd = [seri_ymd(int(d)) for d in deg]
        gunler = {g for _, _, g in ymd}
        if len(gunler) == 1:
            aylar = [y * 12 + a for y, a, _ in ymd]
            fark = {aylar[i + 1] - aylar[i] for i in range(m - 1)}
            if len(fark) == 1 and fark != {0}:
                adim, g, cikti = fark.pop(), ymd[0][2], []
                for j in range(n):
                    toplam = aylar[-1] + adim * (j + 1)
                    y, a = divmod(toplam - 1, 12)
                    a += 1
                    if y < 1900:
                        break
                    cikti.append(float(ymd_seri(y, a, min(g, ay_gun_sayisi(y, a)))))
                if len(cikti) == n:
                    return cikti
    return _sayisal(deg, n, geri)


def _ad_serisi(metinler: List[str], n: int, geri: bool) -> Optional[List[str]]:
    for liste in _ADLAR:
        kucuk = [_tr_kucuk(a) for a in liste]
        if all(_tr_kucuk(t) in kucuk for t in metinler):
            idx = [kucuk.index(_tr_kucuk(t)) for t in metinler]
            L = len(liste)
            if len(idx) == 1:
                adim = -1 if geri else 1
            else:
                farklar = {(idx[i + 1] - idx[i]) % L for i in range(len(idx) - 1)}
                if len(farklar) != 1:
                    return None
                adim = farklar.pop()
                if adim == 0:
                    return None
            ilk = metinler[0]
            buyuk = ilk == _tr_buyuk(ilk) and len(ilk) > 1
            kucuk_h = ilk == _tr_kucuk(ilk)
            sonuc = []
            for j in range(n):
                ad = liste[(idx[-1] + adim * (j + 1)) % L]
                sonuc.append(_tr_buyuk(ad) if buyuk else _tr_kucuk(ad) if kucuk_h else ad)
            return sonuc
    return None


def _sayili_metin_serisi(metinler: List[str], n: int, geri: bool) -> Optional[List[str]]:
    es = [_SAYILI_METIN.match(t) for t in metinler]
    if not all(es):
        return None
    onek, sonek = es[0].group(1), es[0].group(3)
    if any(e.group(1) != onek or e.group(3) != sonek for e in es):
        return None
    sayilar = [int(e.group(2)) for e in es]
    if len(sayilar) == 1:
        adim = -1 if geri else 1
    else:
        farklar = {sayilar[i + 1] - sayilar[i] for i in range(len(sayilar) - 1)}
        if len(farklar) != 1:
            return None
        adim = farklar.pop()
    hane = len(es[-1].group(2)) if es[-1].group(2).startswith("0") else 0
    sonuc = []
    for j in range(n):
        v = sayilar[-1] + adim * (j + 1)
        if v < 0:
            return None
        sonuc.append(onek + str(v).zfill(hane) + sonek)
    return sonuc


def _serit_degerleri(girdiler: List[Optional[Hucre]], kodlar: List[str], n: int,
                     geri: bool) -> Optional[List[Optional[Hucre]]]:
    """Şerit seri olarak tanınırsa `n` yeni hücre (ileri yönde, kaynağın devamı), yoksa None (desen
    kopyası). `girdiler` ilerleme yönünde sıralıdır (geri doldurmada ters çevrilmiş)."""
    if any(h is None or h.formul is not None or h.deger is None for h in girdiler):
        return None
    deg = [h.deger for h in girdiler]
    if all(isinstance(v, float) for v in deg):
        if all(_tarih_mi(k) for k in kodlar):
            return [Hucre(v) for v in _tarih_serisi(deg, n, geri)]
        if len(deg) == 1:
            return None                                   # tek sayı: kopya (Excel, Ctrl'siz sürükleme)
        return [Hucre(v) for v in _sayisal(deg, n, geri)]
    if all(isinstance(v, str) for v in deg):
        s = _ad_serisi(deg, n, geri) or _sayili_metin_serisi(deg, n, geri)
        if s is not None:
            return [Hucre(t) for t in s]
    return None


def _kaydirilmis(h: Optional[Hucre], dr: int, dc: int) -> Optional[Hucre]:
    if h is None or h.formul is None or (dr == 0 and dc == 0):
        return h
    from ..formul.kaydir import kopyala                   # model → formul yalnız burada
    yeni = kopyala(h.formul, dr, dc)
    return h if yeni == h.formul else Hucre(None, yeni)


kaydirilmis = _kaydirilmis


def _plan(sayfa: Sayfa, kaynak: Aralik, hedef: Aralik, seri: bool):
    dikey, geri = _yon_ve_serit(kaynak, hedef)
    havuz = sayfa.havuz
    hucreler: Dict[Anahtar, Optional[Hucre]] = {}
    stiller: Dict[Anahtar, int] = {}
    if dikey:
        seritler = [[(r, c) for r in range(kaynak.ilk_satir, kaynak.son_satir + 1)]
                    for c in range(kaynak.ilk_sutun, kaynak.son_sutun + 1)]
        n = hedef.son_satir - hedef.ilk_satir + 1
    else:
        seritler = [[(r, c) for c in range(kaynak.ilk_sutun, kaynak.son_sutun + 1)]
                    for r in range(kaynak.ilk_satir, kaynak.son_satir + 1)]
        n = hedef.son_sutun - hedef.ilk_sutun + 1
    m = len(seritler[0])
    for serit in seritler:
        girdiler = [sayfa.hucre(*k) for k in serit]
        stil_kimlikleri = [sayfa.stil_kimligi(*k) for k in serit]
        yeni = None
        if seri:
            sirali = list(reversed(range(m))) if geri else list(range(m))
            yeni = _serit_degerleri([girdiler[i] for i in sirali],
                                    [havuz.stil(stil_kimlikleri[i]).sayi_bicimi for i in sirali], n, geri)
        for j in range(n):
            p = -(j + 1) if geri else m + j                # kaynak şeridine göre konum
            src = p % m
            ofset = p - src
            hedef_k = ((hedef.ilk_satir + (n - 1 - j if geri else j), serit[0][1]) if dikey
                       else (serit[0][0], hedef.ilk_sutun + (n - 1 - j if geri else j)))
            if yeni is not None:
                hucreler[hedef_k] = yeni[j]
            else:
                hucreler[hedef_k] = _kaydirilmis(girdiler[src], *( (ofset, 0) if dikey else (0, ofset)))
            stiller[hedef_k] = stil_kimlikleri[src]
    return hucreler, stiller


def seri_plani(sayfa: Sayfa, kaynak: Aralik, hedef: Aralik):
    """Doldurma planı: ({anahtar: Hucre | None}, {anahtar: stil kimliği}). Hedef kaynağa bitişik değilse
    ValueError."""
    return _plan(sayfa, kaynak, hedef, True)


def kopya_plani(sayfa: Sayfa, kaynak: Aralik, hedef: Aralik):
    """Seri tanımadan yalnız kopya (Ctrl+D / Ctrl+R: formül kayar, biçim gelir)."""
    return _plan(sayfa, kaynak, hedef, False)


# ------------------------------------------------------------------ Ctrl+D / Ctrl+R / çift tık
def asagi_yukari_dolu_plani(sayfa: Sayfa, secim: Aralik, dikey: bool):
    """Ctrl+D (dikey=True) / Ctrl+R: seçimin ilk satırı/sütunu kalanına kopyalanır; tek satır/sütun
    seçiliyse üstteki/soldaki hücre kaynak olur. İş yoksa None."""
    if dikey:
        if secim.son_satir > secim.ilk_satir:
            return kopya_plani(sayfa, Aralik(secim.ilk_satir, secim.ilk_sutun, secim.ilk_satir, secim.son_sutun),
                               Aralik(secim.ilk_satir + 1, secim.ilk_sutun, secim.son_satir, secim.son_sutun))
        if secim.ilk_satir > 1:
            return kopya_plani(sayfa, Aralik(secim.ilk_satir - 1, secim.ilk_sutun, secim.ilk_satir - 1, secim.son_sutun),
                               secim)
        return None
    if secim.son_sutun > secim.ilk_sutun:
        return kopya_plani(sayfa, Aralik(secim.ilk_satir, secim.ilk_sutun, secim.son_satir, secim.ilk_sutun),
                           Aralik(secim.ilk_satir, secim.ilk_sutun + 1, secim.son_satir, secim.son_sutun))
    if secim.ilk_sutun > 1:
        return kopya_plani(sayfa, Aralik(secim.ilk_satir, secim.ilk_sutun - 1, secim.son_satir, secim.ilk_sutun - 1),
                           secim)
    return None


def bitisik_son_satir(sayfa: Sayfa, kaynak: Aralik) -> Optional[int]:
    """Çift tıkla aşağı doldur: seçimin solundaki (boşsa sağındaki) sütunun, seçimin son satırından
    aşağı kesintisiz dolu devamının son satırı; devam yoksa None."""
    for c in (kaynak.ilk_sutun - 1, kaynak.son_sutun + 1):
        if c < 1 or c > 16384:
            continue
        if not any((r, c) in sayfa._hucreler and not sayfa._hucreler[(r, c)].bos_mu()
                   for r in range(kaynak.ilk_satir, kaynak.son_satir + 1)):
            continue
        r = kaynak.son_satir
        while r < 1048576 and (r + 1, c) in sayfa._hucreler and not sayfa._hucreler[(r + 1, c)].bos_mu():
            r += 1
        return r if r > kaynak.son_satir else None
    return None
