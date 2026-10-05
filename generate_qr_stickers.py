"""
Book Bridge — Physical Book QR Code & Printable Sticker Generation CLI.
Run this utility to generate printable physical QR stickers for all books in PostgreSQL.

Usage:
    python generate_qr_stickers.py --all
    python generate_qr_stickers.py --book-id 1 --out-dir ./qr_stickers
"""
import argparse
import os
import sys
from pathlib import Path

# Ensure backend root is on Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import SessionLocal
from app.models.book import Book
from app.services.qr_service import generate_printable_book_sticker, generate_book_qr_image


def generate_stickers(book_id=None, all_books=False, out_dir="./generated_stickers", base_url="http://127.0.0.1:8000"):
    output_path = Path(out_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        if book_id:
            books = db.query(Book).filter(Book.id == book_id).all()
            if not books:
                print(f"[ERROR] Book with ID #{book_id} not found in database.")
                return
        elif all_books:
            books = db.query(Book).all()
            if not books:
                print("[WARNING] No books found in database. Seed sample data or add books first.")
                return
        else:
            print("[INFO] No book specified. Fetching all available books...")
            books = db.query(Book).all()

        print("=" * 65)
        print(f"  BOOK BRIDGE — PHYSICAL QR STICKER GENERATOR")
        print(f"  Target Output Directory: {output_path.resolve()}")
        print(f"  Total Books to Process: {len(books)}")
        print("=" * 65)

        generated_files = []

        for book in books:
            sticker = generate_printable_book_sticker(book, base_url=base_url)
            filename = f"book_{book.id:04d}_sticker_{book.rack or 'RACK'}_{book.shelf or 'SHELF'}.png"
            filename = filename.replace(" ", "_").replace("/", "-")
            file_path = output_path / filename

            sticker.save(file_path, format="PNG")
            generated_files.append((book, file_path.name))
            
            print(f"  [OK] [ID #{book.id:03d}] {book.title[:30]:<30} | {book.rack or 'N/A':<12} | {book.shelf or 'N/A'} -> {filename}")

        # Create an HTML printable catalog sheet
        html_sheet_path = output_path / "printable_sticker_sheet.html"
        with open(html_sheet_path, "w", encoding="utf-8") as f:
            f.write(generate_html_sheet(generated_files))

        print("=" * 65)
        print(f"[SUCCESS] {len(books)} physical QR stickers generated successfully!")
        print(f"[PRINT SHEET] Printable HTML Sheet: {html_sheet_path.resolve()}")
        print("=" * 65)

    finally:
        db.close()


def generate_html_sheet(book_files):
    cards_html = ""
    for book, filename in book_files:
        cards_html += f"""
        <div class="sticker-wrapper">
          <img src="{filename}" alt="Sticker for Book {book.id}">
        </div>
        """

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Book Bridge — Printable Physical Book Sticker Sheet</title>
  <style>
    body {{ font-family: sans-serif; background: #f1f5f9; padding: 20px; text-align: center; }}
    h1 {{ color: #1e1b4b; }}
    .actions {{ margin-bottom: 20px; }}
    .btn-print {{ background: #4f46e5; color: #fff; border: none; padding: 10px 20px; font-size: 16px; border-radius: 8px; cursor: pointer; }}
    .grid {{ display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; }}
    .sticker-wrapper {{ background: #fff; padding: 10px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
    .sticker-wrapper img {{ width: 340px; height: auto; display: block; }}
    @media print {{
      body {{ background: #fff; padding: 0; }}
      .actions {{ display: none; }}
      .grid {{ gap: 10px; }}
    }}
  </style>
</head>
<body>
  <h1>📚 Book Bridge — Physical Book QR Labels</h1>
  <div class="actions">
    <button class="btn-print" onclick="window.print()">🖨️ Print Sticker Sheet</button>
  </div>
  <div class="grid">
    {cards_html}
  </div>
</body>
</html>
"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Book Bridge Physical QR Sticker Generator")
    parser.add_argument("--book-id", type=int, help="Specific Book ID to generate sticker for")
    parser.add_argument("--all", action="store_true", help="Generate QR stickers for all books in database")
    parser.add_argument("--out-dir", default="./generated_stickers", help="Output directory for PNG stickers")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base API scan URL")

    args = parser.parse_args()
    generate_stickers(
        book_id=args.book_id,
        all_books=args.all,
        out_dir=args.out_dir,
        base_url=args.base_url,
    )
