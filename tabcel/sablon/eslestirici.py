"""Serbest metin → akış eşleştirme (anahtar kelime; yapay zekâ ve bulut yok). Qt yok.

Yöntem (`sablon_tasarim.md` §3.8): `metin_tr.kucuk` + ASCII katlama (`stoğu` → `stogu`) + sözcük bölme; her `kök` sözcüğe
**önek** olarak eşleşir (ekler: stoklarımı, stoğu, stokta); ünsüz yumuşaması tanımda ikinci kök olarak verilir (`stok`,
`stoğ`). Eş anlamlılar çok sözcüklü olabilir ve sözcük sınırında aranır. Puan = eşleşen kök/eş anlamlı sayısı × ağırlık.
"""
import re
from dataclasses import dataclass
from typing import List, Sequence

from .. import metin_tr
from .sema import Akis

_KATLA = str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u"})
_SOZCUK = re.compile(r"[a-z0-9]+")
ESIK = 1.0                      # bundan düşük puan "eşleşme yok"
YAKIN_ORAN = 0.6                # en iyi puanın bu oranı ve üstü "yakın" sayılır


def katla(metin: str) -> str:
    """Türkçe küçük harf + ASCII katlama (yalnız eşleştirme için; kullanıcıya gösterilmez)."""
    return metin_tr.kucuk(metin).translate(_KATLA)


def sozcukler(metin: str) -> List[str]:
    return _SOZCUK.findall(katla(metin))


@dataclass
class Eslesme:
    akis: Akis
    puan: float
    nedenler: List[str]


def _ifade_var(parcalar, soz) -> bool:
    """Ardışık sözcüklerin her biri, metindeki sözcüğün **öneki** ise eşleşir (`teklif hazırla` ↔ `teklif hazırlamak`)."""
    n = len(parcalar)
    return any(all(soz[i + j].startswith(parcalar[j]) for j in range(n)) for i in range(len(soz) - n + 1))


def puanla(metin: str, akis: Akis) -> Eslesme:
    soz = sozcukler(metin)
    puan, nedenler = 0.0, []
    for kok in akis.kokler:
        k = katla(kok)
        if any(s.startswith(k) for s in soz):
            puan += akis.agirlik
            nedenler.append(kok)
    for es in akis.es_anlamlilar:
        e = " ".join(sozcukler(es))
        if not e:
            continue
        if _ifade_var(e.split(), soz):
            puan += akis.agirlik
            nedenler.append(es)
    return Eslesme(akis, puan, nedenler)


def eslestir(metin: str, akislar: Sequence[Akis]) -> List[Eslesme]:
    """Eşik üstündeki akışlar, yüksek puandan düşüğe (eşitlikte ad sırası, Türkçe)."""
    sonuc = [e for e in (puanla(metin, a) for a in akislar) if e.puan >= ESIK]
    sonuc.sort(key=lambda e: (-e.puan, katla(e.akis.ad)))
    return sonuc


def oneri(metin: str, akislar: Sequence[Akis], en_cok: int = 3) -> List[Eslesme]:
    """Arayüzde gösterilecek öneriler: en iyi ve ona yakın puanlılar; hiç eşleşme yoksa boş liste (kategori düğmeleri)."""
    sonuc = eslestir(metin, akislar)
    if not sonuc:
        return []
    en_iyi = sonuc[0].puan
    return [e for e in sonuc if e.puan >= en_iyi * YAKIN_ORAN][:en_cok]
