"""Hücre değerinin ekrandaki/panodaki metni. Qt yok.

Geçici 'Genel' biçim; sayı biçimleri (Para, Tarih, Yüzde…) Faz 3'te gelecek.
"""


def goster(deger) -> str:
    if deger is None:
        return ""
    if isinstance(deger, bool):
        return "DOĞRU" if deger else "YANLIŞ"
    if isinstance(deger, float):
        if deger == int(deger) and abs(deger) < 1e11:
            return str(int(deger))
        return f"{deger:.10g}".replace(".", ",")
    return str(deger)
