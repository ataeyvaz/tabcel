"""Otomatik kurtarma kopyaları (Faz 4 / 4e). Qt yok.

Excel'in AutoRecover'ı gibi: değişmiş belgenin kopyası kullanıcının dosyasına DOKUNMADAN
`veri_klasoru()/recovery/<kimlik>.xlsx` (+ `<kimlik>.json` üst verisi) olarak yazılır. Belge kaydedilince ya
da bilerek kapatılınca silinir; uygulama çökerse (sahibi süreç artık yoksa) bir sonraki açılışta önerilir.
"""
import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import List, Optional

from .. import veri_klasoru
from . import xlsx_io


@dataclass(frozen=True)
class Kurtarilabilir:
    kimlik: str
    ad: str                      # belge adı (başlıkta görünen)
    yol: Optional[str]           # özgün dosya yolu (varsa)
    zaman: float                 # son kopya zamanı (epoch)
    dosya: str                   # kopyanın .xlsx yolu


def klasor() -> str:
    return str(veri_klasoru() / "recovery")


def yeni_kimlik() -> str:
    return uuid.uuid4().hex


def _dosya(kimlik: str, uzanti: str) -> str:
    return os.path.join(klasor(), kimlik + uzanti)


def surec_canli_mi(pid: int) -> bool:
    """`pid` numaralı süreç çalışıyor mu (kendi sürecimiz dahil)."""
    if pid == os.getpid():
        return True
    try:
        if os.name == "nt":
            import ctypes
            k = ctypes.windll.kernel32
            h = k.OpenProcess(0x1000, False, pid)            # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return False
            kod = ctypes.c_ulong()
            ok = k.GetExitCodeProcess(h, ctypes.byref(kod))
            k.CloseHandle(h)
            return bool(ok) and kod.value == 259             # STILL_ACTIVE
        os.kill(pid, 0)
        return True
    except (OSError, AttributeError, ValueError):
        return False


def kopya_yaz(kitap, kimlik: str, ad: str, yol: Optional[str]) -> None:
    """Kitabın kurtarma kopyasını yazar (xlsx önce, üst veri sonra: üst verisi olan kopya her zaman tamdır).
    Yazılamazsa OSError/XlsxHatasi; çağıran sessizce geçer (otomatik işlem kullanıcıyı bölmez)."""
    os.makedirs(klasor(), exist_ok=True)
    xlsx_io.kaydet(kitap, _dosya(kimlik, ".xlsx"))
    gecici = _dosya(kimlik, ".json.tmp")
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump({"ad": ad, "yol": yol, "zaman": time.time(), "pid": os.getpid()}, f, ensure_ascii=False)
    os.replace(gecici, _dosya(kimlik, ".json"))


def sil(kimlik: str) -> None:
    for u in (".json", ".xlsx", ".json.tmp"):
        try:
            os.remove(_dosya(kimlik, u))
        except OSError:
            pass


def bekleyenler() -> List[Kurtarilabilir]:
    """Sahibi çalışmayan (çökmüş/öldürülmüş) süreçlerden kalan kopyalar, en yeni önce. Bozuk üst veri atlanır
    (dosyaya dokunulmaz)."""
    sonuc: List[Kurtarilabilir] = []
    try:
        adlar = os.listdir(klasor())
    except OSError:
        return sonuc
    for a in adlar:
        if not a.endswith(".json"):
            continue
        kimlik = a[:-5]
        try:
            with open(_dosya(kimlik, ".json"), encoding="utf-8") as f:
                m = json.load(f)
            xlsx = _dosya(kimlik, ".xlsx")
            if not os.path.exists(xlsx) or surec_canli_mi(int(m["pid"])):
                continue
            sonuc.append(Kurtarilabilir(kimlik, str(m.get("ad") or "Adsız"), m.get("yol"),
                                        float(m.get("zaman") or 0), xlsx))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return sorted(sonuc, key=lambda k: -k.zaman)


def ac(k: Kurtarilabilir):
    """(kitap, rapor); okunamazsa `xlsx_io.XlsxHatasi`."""
    return xlsx_io.ac(k.dosya)


def sahiplen(kimlik: str) -> None:
    """Kurtarılan kopyayı bu sürece bağlar (üst verideki pid güncellenir): belge kaydedilene dek korunur."""
    try:
        with open(_dosya(kimlik, ".json"), encoding="utf-8") as f:
            m = json.load(f)
        m["pid"] = os.getpid()
        gecici = _dosya(kimlik, ".json.tmp")
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False)
        os.replace(gecici, _dosya(kimlik, ".json"))
    except (OSError, ValueError):
        pass
