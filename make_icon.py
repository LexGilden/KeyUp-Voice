from pathlib import Path

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen


def main() -> None:
    size = 256
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(23, 27, 35))
    painter.drawRoundedRect(QRectF(4, 4, 248, 248), 58, 58)

    green = QColor(57, 208, 132)
    painter.setBrush(green)
    painter.drawRoundedRect(QRectF(91, 40, 74, 116), 37, 37)

    pen = QPen(green, 18)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(pen)
    painter.drawArc(QRectF(64, 92, 128, 105), 180 * 16, 180 * 16)
    painter.drawLine(QPoint(128, 197), QPoint(128, 222))
    painter.drawLine(QPoint(94, 222), QPoint(162, 222))
    painter.end()

    output = Path(__file__).resolve().parent / "keyup-voice.ico"
    if not image.save(str(output), "ICO"):
        raise RuntimeError("Qt could not write keyup-voice.ico")
    print(output)


if __name__ == "__main__":
    main()
