"""Son kullanılan dosyalar listesi (Faz 4 / 4b): `veri_klasoru()/son_dosyalar.json`. Qt yok."""
import json
import os
from typing import List

from .. import veri_klasoru

SINIR = 10


def _yol() -> str:
    return str(veri_klasoru() / "son_dosyalar.json")


def oku() -> List[str]:
    """Kayıtlı listeyi (en yeni önce) verir; bozuk/yok dosya boş liste. Artık var olmayan dosyalar elenmez
    (ağ/çıkarılabilir sürücü geçici yok olabilir); menü açılırken tıklanınca hata gösterilir."""
    try:
        with open(_yol(), encoding="utf-8") as f:
            v = json.load(f)
        return [y for y in v if isinstance(y, str)][:SINIR] if isinstance(v, list) else []
    except (OSError, ValueError):
        return []


def _yaz(liste: List[str]) -> None:
    try:
        os.makedirs(os.path.dirname(_yol()), exist_ok=True)
        gecici = _yol() + ".tmp"
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(liste[:SINIR], f, ensure_ascii=False)
        os.replace(gecici, _yol())
    except OSError:
        pass                                  # liste önemli değil; kaydedememek işi engellemez


def ekle(yol: str) -> None:
    yol = os.path.abspath(yol)
    liste = [y for y in oku() if os.path.normcase(y) != os.path.normcase(yol)]
    _yaz([yol] + liste)


def sil(yol: str) -> None:
    _yaz([y for y in oku() if os.path.normcase(y) != os.path.normcase(os.path.abspath(yol))])


def temizle() -> None:
    _yaz([])
