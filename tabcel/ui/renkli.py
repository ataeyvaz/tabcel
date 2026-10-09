"""Formül yazarken metin kutusunda başvuruları kendi renginde çizme (K7).

QLineEdit parça parça renk vermez: normal çizimden sonra her başvurunun yazısı, zemin rengiyle
silinip kendi renginde yeniden çizilir. Başlangıç x'i içerik dikdörtgeni + QLineEdit iç boşluğundan (2 px) bulunur; metin kutuya
sığmayıp kayıyorsa renklendirme yapılmaz. Seçili metin varken çizilmez (seçim vurgusu bozulmasın)."""
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QLineEdit

from ..formul import isaretleme
from . import theme


def renkli_ciz(e: QLineEdit, ek_x: int = 0) -> None:
    """`ek_x`: stil sayfasının eklediği kenarlık + iç boşluk (contentsRect'e yansımıyorsa)."""
    metin = e.text()
    if not metin.startswith("=") or e.hasSelectedText():
        return
    aralar = isaretleme.renkli_basvurular(metin)
    if not aralar:
        return
    fm = e.fontMetrics()
    alan = e.contentsRect()
    if fm.horizontalAdvance(metin) > alan.width() - 4 - 2 * ek_x:
        return                                  # metin kutudan taşıp kayıyor: konum güvenilmez, çizme
    x0 = alan.left() + e.textMargins().left() + 2 + ek_x
    imlec = e.cursorRect()
    taban = imlec.y() + (imlec.height() - fm.height()) // 2 + fm.ascent()
    p = QPainter(e)
    p.setFont(e.font())
    zemin = QColor(theme.SURFACE)
    for bas, son, _, renk in aralar:
        x = x0 + fm.horizontalAdvance(metin[:bas])
        w = fm.horizontalAdvance(metin[bas:son])
        p.fillRect(x, imlec.y(), w, imlec.height(), zemin)
        p.setPen(QColor(renk))
        p.drawText(x, taban, metin[bas:son])
    p.end()
