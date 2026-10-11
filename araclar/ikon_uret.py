"""Uygulama ikonunu (tabcel.ico) üretir: Excel yeşili sayfa, ızgara ve "T".

Kullanım: .venv\\Scripts\\python.exe araclar\\ikon_uret.py
Çok boyutlu ICO dosyası yazılır (16-256 px), böylece görev çubuğunda ve masaüstünde keskin görünür.
"""

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SIZES = [256, 128, 64, 48, 32, 16]
TARGET = Path(__file__).resolve().parent.parent / "tabcel.ico"
ACCENT = "#217346"
PAPER = "#ffffff"


def render(size):
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)
    unit = size / 32

    # yuvarlatılmış köşeli sayfa
    page = QRectF(4 * unit, 2 * unit, 24 * unit, 28 * unit)
    path = QPainterPath()
    path.addRoundedRect(page, 3 * unit, 3 * unit)
    painter.fillPath(path, QColor(PAPER))
    painter.setPen(QColor(0, 0, 0, 40))
    painter.drawPath(path)

    # yeşil şerit + altında ızgara: sayfanın içine kırpılır
    painter.save()
    painter.setClipPath(path)
    painter.fillRect(QRectF(4 * unit, 2 * unit, 24 * unit, 8 * unit), QColor(ACCENT))
    if size >= 48:   # küçük boyutlarda çizgiler lekeye dönüşüyor
        painter.setPen(QColor("#cfe3d8"))
        for index in range(1, 3):
            y = (10 + index * 6.7) * unit
            painter.drawLine(QPointF(4 * unit, y), QPointF(28 * unit, y))
        painter.drawLine(QPointF(16 * unit, 10 * unit), QPointF(16 * unit, 30 * unit))
    painter.restore()

    # "T": yazı tipinden bağımsız (ekransız ortamda yazı tipi olmayabilir) — iki dikdörtgen
    renk = QColor(PAPER if size < 48 else ACCENT)
    if size < 48:
        ust, alt, sol, sag = 3.2, 9.0, 11, 21
    else:
        ust, alt, sol, sag = 13, 27, 9, 23
    kalin = (sag - sol) / 3.2
    orta = (sol + sag) / 2
    painter.fillRect(QRectF(sol * unit, ust * unit, (sag - sol) * unit, kalin * unit * 0.8), renk)
    painter.fillRect(QRectF((orta - kalin / 2) * unit, ust * unit, kalin * unit, (alt - ust) * unit), renk)

    painter.end()
    return image


def png_bytes(image):
    data = QByteArray()
    buffer = QBuffer(data)          # QByteArray'i ayrı tutmak gerekiyor: geçici nesne silinince çöküyor
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(data)


def write_ico(path, images):
    """PNG gömülü çok boyutlu ICO (Vista ve sonrası)."""
    entries, data, offset = [], [], 6 + 16 * len(images)
    for image in images:
        blob = png_bytes(image)
        size = image.width()
        entries.append(struct.pack("<BBBBHHII", 0 if size >= 256 else size, 0 if size >= 256 else size,
                                   0, 0, 1, 32, len(blob), offset))
        data.append(blob)
        offset += len(blob)
    with open(path, "wb") as handle:
        handle.write(struct.pack("<HHH", 0, 1, len(images)))
        for entry in entries:
            handle.write(entry)
        for blob in data:
            handle.write(blob)


app = None


def main():
    global app
    app = QApplication.instance() or QApplication(sys.argv)   # QPainter/QFont için gerekli
    write_ico(TARGET, [render(size) for size in SIZES])
    print(f"{TARGET} ({TARGET.stat().st_size / 1024:.0f} KB, {len(SIZES)} boyut)")


if __name__ == "__main__":
    main()
