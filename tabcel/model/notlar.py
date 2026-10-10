"""Hücre notları (Excel'de "Not", eski adıyla "Açıklama"). Qt yok. Tasarım: faz5_tasarim.md §5."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Not:
    """Değişmez not: `metin` + `yazar` (boş olabilir). Yazar notun ilk satırında kalın gösterilir."""
    metin: str
    yazar: str = ""

    def bos_mu(self) -> bool:
        return self.metin == "" and self.yazar == ""

    def kutu_metni(self) -> str:
        """Fare üstü kutuda gösterilen metin: yazar varsa ilk satırda `Yazar:` ve ardından not."""
        return f"{self.yazar}:\n{self.metin}" if self.yazar else self.metin


def varsayilan_yazar() -> str:
    """Yeni notun yazarı: Windows kullanıcı adı (ayar yok). Alınamazsa boş."""
    import os
    try:
        return os.getlogin()
    except OSError:
        return os.environ.get("USERNAME", "")
