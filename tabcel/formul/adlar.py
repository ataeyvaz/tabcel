"""Fonksiyon adları: kanonik İngilizce ⇄ Türkçe Excel. Qt yok.

CLAUDE.md kural 4: yalnız Microsoft'un tr-tr belgesiyle DOĞRULANMIŞ adlar yazılır.
Dikkat: support.microsoft.com/tr-tr "Excel işlevleri (alfabetik)" sayfası makine çevirisi
hataları içeriyor (ör. PMT için "FAİZ_ORANI", "ADRESİMİZ"); her ad o işlevin kendi tr-tr
sayfasındaki sözdizimi satırından doğrulanmalı. Doğrulanamayan → surec.md §8b-6.
Türkçesi yazılmamış fonksiyon İngilizce adıyla gösterilir ve yazılabilir.
"""
from typing import Dict, Optional

from .yerel import tr_buyuk

# İngilizce → Türkçe. Doğrulama: işlevin tr-tr sayfası (tarih).
EN_TR: Dict[str, str] = {
    "SUM": "TOPLA",          # 2026-10-09, tr-tr alfabetik liste + "TOPLA işlevi"
    "IF": "EĞER",            # 2026-10-09, tr-tr alfabetik liste + "EĞER işlevi"
}

TR_EN: Dict[str, str] = {tr_buyuk(tr): en for en, tr in EN_TR.items()}


def turkcesi(en: str) -> str:
    return EN_TR.get(en.upper(), en.upper())


def ingilizcesi(yazilan: str) -> Optional[str]:
    """Kullanıcının yazdığı Türkçe adın kanonik karşılığı (yoksa None)."""
    return TR_EN.get(tr_buyuk(yazilan))
