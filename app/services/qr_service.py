"""
QR Code Generation & Physical Sticker Label Service for Book Bridge.
Generates unique scannable QR codes and printable physical book stickers.
"""
import base64
import io
import json
from typing import Any, Dict, Optional

import qrcode
from PIL import Image, ImageDraw, ImageFont


def create_qr_payload(book_id: int, base_url: str = "http://127.0.0.1:8000") -> str:
    """Create standard payload encoded into the physical book QR code."""
    payload = {
        "app": "BookBridge",
        "type": "book",
        "book_id": book_id,
        "scan_url": f"{base_url}/books/{book_id}/scan",
    }
    return json.dumps(payload, separators=(",", ":"))


def generate_book_qr_image(
    book_id: int,
    base_url: str = "http://127.0.0.1:8000",
    box_size: int = 10,
    border: int = 2,
    fill_color: str = "#111827",
    back_color: str = "#ffffff",
) -> Image.Image:
    """
    Generate a raw PIL Image containing the QR code for a given Book ID.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    payload = create_qr_payload(book_id, base_url)
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color=fill_color, back_color=back_color).convert("RGB")
    return img


def generate_book_qr_bytes(book_id: int, base_url: str = "http://127.0.0.1:8000") -> bytes:
    """Return raw PNG bytes of the book QR code."""
    img = generate_book_qr_image(book_id, base_url)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def generate_printable_book_sticker(
    book: Any,
    base_url: str = "http://127.0.0.1:8000",
    width: int = 560,
    height: int = 300,
) -> Image.Image:
    """
    Generate a formatted, high-resolution printable physical sticker label for a book.
    Includes:
    - Book Bridge header with brand badge
    - Crisp scannable QR Code
    - Book Title, Author, ISBN
    - Prominent Physical Location: RACK & SHELF badge
    - Barcode Book ID
    """
    # Background canvas
    canvas = Image.new("RGB", (width, height), color="#ffffff")
    draw = ImageDraw.Draw(canvas)

    # Outer border
    draw.rounded_rectangle([(8, 8), (width - 8, height - 8)], radius=14, outline="#4f46e5", width=3)
    
    # Top banner
    draw.rounded_rectangle([(10, 10), (width - 10, 48)], radius=10, fill="#4f46e5")
    
    # Fonts (fallback to default if system font is unavailable)
    try:
        font_header = ImageFont.truetype("arial.ttf", 16)
        font_title = ImageFont.truetype("arialbd.ttf", 16)
        font_meta = ImageFont.truetype("arial.ttf", 13)
        font_badge = ImageFont.truetype("arialbd.ttf", 14)
        font_tiny = ImageFont.truetype("arial.ttf", 11)
    except Exception:
        font_header = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_meta = ImageFont.load_default()
        font_badge = ImageFont.load_default()
        font_tiny = ImageFont.load_default()

    # Header text
    draw.text((22, 18), "📚 BOOK BRIDGE SMART LIBRARY", fill="#ffffff", font=font_header)
    book_id_text = f"ID: #{getattr(book, 'id', 1):04d}"
    draw.text((width - 95, 18), book_id_text, fill="#e0e7ff", font=font_header)

    # Generate QR Code for left column
    qr_img = generate_book_qr_image(getattr(book, "id", 1), base_url, box_size=6, border=1)
    qr_size = 190
    qr_resized = qr_img.resize((qr_size, qr_size), Image.Resampling.NEAREST)
    canvas.paste(qr_resized, (24, 62))

    # Frame around QR Code
    draw.rectangle([(22, 60), (22 + qr_size + 4, 60 + qr_size + 4)], outline="#cbd5e1", width=1)

    # Bottom helper under QR
    draw.text((36, 262), "SCAN FOR LIVE LOCATION", fill="#64748b", font=font_tiny)

    # Right side: Book Metadata & Location
    start_x = 236
    
    title = str(getattr(book, "title", "Library Book"))
    if len(title) > 34:
        title_line1 = title[:32] + "..."
    else:
        title_line1 = title

    author = f"Author: {getattr(book, 'author', 'Unknown')}"
    if len(author) > 38:
        author = author[:35] + "..."

    isbn = f"ISBN: {getattr(book, 'isbn', 'N/A') or 'N/A'}"
    category = f"Category: {getattr(book, 'category', 'General') or 'General'}"
    rack = getattr(book, "rack", None) or "Not recorded"
    shelf = getattr(book, "shelf", None) or "Not recorded"

    # Draw Title & Author
    draw.text((start_x, 62), title_line1, fill="#0f172a", font=font_title)
    draw.text((start_x, 88), author, fill="#334155", font=font_meta)
    draw.text((start_x, 108), isbn, fill="#64748b", font=font_tiny)
    draw.text((start_x, 126), category, fill="#64748b", font=font_tiny)

    # Physical Rack & Shelf Location Badge (Highlighted Box)
    badge_rect = [(start_x, 150), (width - 24, 218)]
    draw.rounded_rectangle(badge_rect, radius=8, fill="#eff6ff", outline="#3b82f6", width=2)
    
    draw.text((start_x + 12, 158), "📍 PHYSICAL LOCATION", fill="#1d4ed8", font=font_tiny)
    location_str = f"{rack.upper()}  •  {shelf.upper()}"
    draw.text((start_x + 12, 178), location_str, fill="#1e3a8a", font=font_badge)
    draw.text((start_x + 12, 198), "Book Bridge Precision Shelf Mapping", fill="#60a5fa", font=font_tiny)

    # Availability Tag
    avail = getattr(book, "available_copies", 1)
    tot = getattr(book, "total_copies", 1)
    avail_text = f"Stock: {avail}/{tot} Available"
    draw.text((start_x, 240), avail_text, fill="#059669" if avail > 0 else "#dc2626", font=font_meta)
    draw.text((start_x, 262), "Scan for current availability", fill="#94a3b8", font=font_tiny)

    return canvas


def get_sticker_base64(book: Any, base_url: str = "http://127.0.0.1:8000") -> str:
    """Generate and return base64 data URL string for the sticker image."""
    sticker = generate_printable_book_sticker(book, base_url)
    buffer = io.BytesIO()
    sticker.save(buffer, format="PNG")
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"


def get_qr_base64(book_id: int, base_url: str = "http://127.0.0.1:8000") -> str:
    """Generate and return base64 data URL string for raw QR code."""
    img = generate_book_qr_image(book_id, base_url)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"
