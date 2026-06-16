# qr_utils.py

import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image, ImageDraw, ImageFont


def _load_font(name: str, size: int):
    """Safely load a TrueType font with a fallback."""
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


def make_qr(
    url: str,
    label: str,
    short_url: str | None = None,
    size: int = 180,
    foreground: str = "#1B3A2D",
    background: str = "white",
    muted: str = "#555555",
) -> Image.Image:
    """
    Generate a QR code image with a label and optional short URL.

    Parameters
    ----------
    url : str
        URL to encode in the QR code.
    label : str
        Title displayed below the QR code.
    short_url : str, optional
        Shortened URL displayed below the label.
    size : int, default=180
        Width and height of the QR code in pixels.
    foreground : str, default='#1B3A2D'
        QR code and label color.
    background : str, default='white'
        Background color.
    muted : str, default='#555555'
        Color of the short URL text.

    Returns
    -------
    PIL.Image.Image
        QR code image with annotations.
    """
    f_label = _load_font("DejaVuSans-Bold.ttf", 12)
    f_url = _load_font("DejaVuSans.ttf", 10)

    qr = qrcode.QRCode(
        version=2,
        error_correction=ERROR_CORRECT_H,
        box_size=6,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    qr_img = (
        qr.make_image(fill_color=foreground, back_color=background)
        .convert("RGB")
        .resize((size, size), Image.LANCZOS)
    )

    label_height = 42
    canvas = Image.new(
        "RGB",
        (size, size + label_height),
        background,
    )
    canvas.paste(qr_img, (0, 0))

    draw = ImageDraw.Draw(canvas)
    draw.text(
        (size // 2, size + 4),
        label,
        font=f_label,
        fill=foreground,
        anchor="mt",
    )

    if short_url:
        draw.text(
            (size // 2, size + 20),
            short_url,
            font=f_url,
            fill=muted,
            anchor="mt",
        )

    return canvas