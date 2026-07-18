import io
import os
import zipfile
import pypdf
import pypdfium2 as pdfium
from PIL import Image
from docx import Document
import openpyxl
import pandas as pd
from xhtml2pdf import pisa
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
import pdfplumber

# ─── Group 1: PDF Organizing & Page Editors ──────────────────────────────────

def merge_pdfs(pdf_files_bytes: list[bytes]) -> bytes:
    merger = pypdf.PdfMerger()
    for f_bytes in pdf_files_bytes:
        merger.append(io.BytesIO(f_bytes))
    out_buf = io.BytesIO()
    merger.write(out_buf)
    merger.close()
    return out_buf.getvalue()


def split_pdf(pdf_bytes: bytes, page_ranges: list[tuple[int, int]]) -> list[bytes]:
    # page_ranges is list of 1-indexed (start_page, end_page) inclusive
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    total_pages = len(reader.pages)
    output_files = []
    
    for start, end in page_ranges:
        writer = pypdf.PdfWriter()
        # clamp ranges
        start_idx = max(0, start - 1)
        end_idx = min(total_pages, end)
        
        for i in range(start_idx, end_idx):
            writer.add_page(reader.pages[i])
            
        out_buf = io.BytesIO()
        writer.write(out_buf)
        output_files.append(out_buf.getvalue())
        writer.close()
        
    return output_files


def delete_pdf_pages(pdf_bytes: bytes, pages_to_delete: list[int]) -> bytes:
    # pages_to_delete is list of 1-indexed page numbers
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    writer = pypdf.PdfWriter()
    delete_set = set(pages_to_delete)
    
    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        if page_num not in delete_set:
            writer.add_page(page)
            
    out_buf = io.BytesIO()
    writer.write(out_buf)
    writer.close()
    return out_buf.getvalue()


def rotate_pdf_pages(pdf_bytes: bytes, pages_to_rotate: list[int], angle: int) -> bytes:
    # pages_to_rotate is list of 1-indexed page numbers, angle is 90, 180, or 270
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    writer = pypdf.PdfWriter()
    rotate_set = set(pages_to_rotate)
    
    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        if page_num in rotate_set or not rotate_set: # if rotate_set is empty, rotate all
            page.rotate(angle)
        writer.add_page(page)
        
    out_buf = io.BytesIO()
    writer.write(out_buf)
    writer.close()
    return out_buf.getvalue()


def crop_pdf_pages(pdf_bytes: bytes, pages: list[int], left: float, right: float, top: float, bottom: float) -> bytes:
    # pages is list of 1-indexed, left, right, top, bottom are points or margins
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    writer = pypdf.PdfWriter()
    page_set = set(pages)
    
    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        if page_num in page_set or not page_set:
            # Crop box coordinates
            box = page.mediabox
            box.lower_left = (box.left + left, box.bottom + bottom)
            box.upper_right = (box.right - right, box.top - top)
        writer.add_page(page)
        
    out_buf = io.BytesIO()
    writer.write(out_buf)
    writer.close()
    return out_buf.getvalue()


def extract_pdf_pages(pdf_bytes: bytes, pages_to_extract: list[int]) -> bytes:
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    writer = pypdf.PdfWriter()
    total = len(reader.pages)
    
    for p_num in pages_to_extract:
        if 1 <= p_num <= total:
            writer.add_page(reader.pages[p_num - 1])
            
    out_buf = io.BytesIO()
    writer.write(out_buf)
    writer.close()
    return out_buf.getvalue()


def rearrange_pdf_pages(pdf_bytes: bytes, page_order: list[int]) -> bytes:
    # page_order is a list of 1-indexed page numbers in the new order
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    writer = pypdf.PdfWriter()
    total = len(reader.pages)
    
    for p_num in page_order:
        if 1 <= p_num <= total:
            writer.add_page(reader.pages[p_num - 1])
            
    out_buf = io.BytesIO()
    writer.write(out_buf)
    writer.close()
    return out_buf.getvalue()


def add_blank_pages(pdf_bytes: bytes, positions: list[int]) -> bytes:
    # positions is list of 1-indexed page positions to insert blank pages (A4 size)
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    writer = pypdf.PdfWriter()
    total = len(reader.pages)
    
    # We will build mapping of page additions
    insert_after = set(positions)
    
    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        writer.add_page(page)
        if page_num in insert_after:
            writer.add_blank_page()
            
    out_buf = io.BytesIO()
    writer.write(out_buf)
    writer.close()
    return out_buf.getvalue()


def add_page_numbers(pdf_bytes: bytes, style: str = "bottom_right") -> bytes:
    # style can be bottom_right, bottom_center, bottom_left, top_right, top_center, top_left
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    writer = pypdf.PdfWriter()
    total_pages = len(reader.pages)
    
    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        
        # Create a single-page PDF containing just the page number
        num_buf = io.BytesIO()
        c = canvas.Canvas(num_buf, pagesize=(page.mediabox.width, page.mediabox.height))
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0.5, 0.5, 0.6) # Muted text
        
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)
        
        text = f"{page_num} of {total_pages}"
        
        # Position mapping
        if style == "bottom_right":
            c.drawRightString(w - 36, 36, text)
        elif style == "bottom_center":
            c.drawCentredString(w / 2, 36, text)
        elif style == "bottom_left":
            c.drawString(36, 36, text)
        elif style == "top_right":
            c.drawRightString(w - 36, h - 36, text)
        elif style == "top_center":
            c.drawCentredString(w / 2, h - 36, text)
        elif style == "top_left":
            c.drawString(36, h - 36, text)
        else:
            c.drawCentredString(w / 2, 36, text)
            
        c.showPage()
        c.save()
        num_buf.seek(0)
        
        # Merge the stamp PDF with the current page
        stamp_reader = pypdf.PdfReader(num_buf)
        page.merge_page(stamp_reader.pages[0])
        writer.add_page(page)
        
    out_buf = io.BytesIO()
    writer.write(out_buf)
    writer.close()
    return out_buf.getvalue()


# ─── Group 2: Convert From PDF ───────────────────────────────────────────────

def pdf_to_images(pdf_bytes: bytes, image_format: str = "PNG") -> list[bytes]:
    # Render PDF pages to images using pypdfum2
    images_list = []
    pdf = pdfium.PdfDocument(pdf_bytes)
    
    for i in range(len(pdf)):
        page = pdf.get_page(i)
        # Render page at 2.0x scale (~150 DPI) for clarity
        pil_img = page.render(scale=2).to_pil()
        
        img_buf = io.BytesIO()
        pil_img.save(img_buf, format=image_format.upper())
        images_list.append(img_buf.getvalue())
        page.close()
        
    pdf.close()
    return images_list


def pdf_to_text(pdf_bytes: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    text_list = []
    for idx, page in enumerate(reader.pages):
        text = page.extract_text()
        text_list.append(f"--- Page {idx + 1} ---\n{text or ''}")
    return "\n\n".join(text_list)


def pdf_to_word(pdf_bytes: bytes) -> bytes:
    # Basic PDF to Docx conversion: extract text lines and write paragraphs
    doc = Document()
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    
    for idx, page in enumerate(reader.pages):
        doc.add_heading(f"Page {idx + 1}", level=2)
        text = page.extract_text()
        if text:
            for line in text.split("\n"):
                if line.strip():
                    doc.add_paragraph(line)
        doc.add_page_break()
        
    out_buf = io.BytesIO()
    doc.save(out_buf)
    return out_buf.getvalue()


def pdf_to_excel(pdf_bytes: bytes) -> bytes:
    # Extracts tables from PDF using pdfplumber and dumps to xlsx sheets
    out_buf = io.BytesIO()
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        with pd.ExcelWriter(out_buf, engine="openpyxl") as writer:
            for idx, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                if not tables:
                    # Write page text as single cell if no table found
                    text = page.extract_text() or ""
                    df = pd.DataFrame([{"Page Content": text}])
                    df.to_excel(writer, sheet_name=f"Page_{idx + 1}", index=False)
                    continue
                
                for t_idx, table in enumerate(tables):
                    df = pd.DataFrame(table)
                    sheet_name = f"Page_{idx + 1}_Table_{t_idx + 1}"[:31]  # Excel 31 char limit
                    df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
                    
    return out_buf.getvalue()


def pdf_to_html(pdf_bytes: bytes) -> str:
    # Convert PDF text content into formatted semantic HTML
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    html_lines = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        "<style>",
        "body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #333; }",
        ".page-break { border-bottom: 2px dashed #ccc; margin: 40px 0; padding-bottom: 10px; color: #888; font-size: 12px; }",
        "p { margin-bottom: 16px; white-space: pre-wrap; }",
        "</style>",
        "</head>",
        "<body>"
    ]
    
    for idx, page in enumerate(reader.pages):
        html_lines.append(f"<div class='page-break'>Page {idx + 1}</div>")
        text = page.extract_text()
        if text:
            # simple line breaks grouping
            paragraphs = text.split("\n\n")
            for p in paragraphs:
                if p.strip():
                    html_lines.append(f"<p>{p.strip()}</p>")
                    
    html_lines.extend(["</body>", "</html>"])
    return "\n".join(html_lines)


# ─── Group 3: Convert To PDF ─────────────────────────────────────────────────

def images_to_pdf(images_bytes_list: list[bytes]) -> bytes:
    pil_images = []
    for img_bytes in images_bytes_list:
        try:
            img = Image.open(io.BytesIO(img_bytes))
            # Convert to RGB mode (required for PDF formatting)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            pil_images.append(img)
        except Exception:
            continue
            
    if not pil_images:
        raise ValueError("No valid images found for conversion.")
        
    out_buf = io.BytesIO()
    # Save the first image, and append the rest as secondary pages
    pil_images[0].save(out_buf, format="PDF", save_all=True, append_images=pil_images[1:])
    return out_buf.getvalue()


def text_to_pdf(text_str: str) -> bytes:
    # Convert plain text to PDF using ReportLab
    out_buf = io.BytesIO()
    c = canvas.Canvas(out_buf, pagesize=letter)
    width, height = letter
    
    # 0.5 inch margins
    margin = 36
    y_position = height - margin
    c.setFont("Courier", 10)
    
    for line in text_str.split("\n"):
        if y_position < margin:
            c.showPage()
            c.setFont("Courier", 10)
            y_position = height - margin
        c.drawString(margin, y_position, line)
        y_position -= 13 # line height
        
    c.showPage()
    c.save()
    return out_buf.getvalue()


def docx_to_pdf(docx_bytes: bytes) -> bytes:
    # Docx to PDF: parse text paragraphs and generate PDF using xhtml2pdf
    doc = Document(io.BytesIO(docx_bytes))
    html_content = ["<html><body>"]
    for p in doc.paragraphs:
        # Check headings
        if p.style.name.startswith("Heading"):
            html_content.append(f"<h2>{p.text}</h2>")
        else:
            html_content.append(f"<p>{p.text}</p>")
    html_content.append("</body></html>")
    
    out_buf = io.BytesIO()
    pisa.CreatePDF("\n".join(html_content), dest=out_buf)
    return out_buf.getvalue()


def xlsx_to_pdf(xlsx_bytes: bytes) -> bytes:
    # Convert Excel table sheet grid to clean PDF table using HTML + xhtml2pdf
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), data_only=True)
    html_content = [
        "<html><head><style>",
        "table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 10px; }",
        "th, td { border: 1px solid #ccc; padding: 6px; text-align: left; }",
        "th { background-color: #f2f2f2; }",
        "h2 { font-size: 14px; margin-top: 20px; }",
        "</style></head><body>"
    ]
    
    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        html_content.append(f"<h2>Sheet: {sheet_name}</h2>")
        html_content.append("<table>")
        
        for r_idx, row in enumerate(sheet.iter_rows(values_only=True)):
            if all(v is None for v in row):
                continue
            html_content.append("<tr>")
            for val in row:
                cell_val = "" if val is None else str(val)
                if r_idx == 0:
                    html_content.append(f"<th>{cell_val}</th>")
                else:
                    html_content.append(f"<td>{cell_val}</td>")
            html_content.append("</tr>")
            
        html_content.append("</table>")
        
    html_content.append("</body></html>")
    out_buf = io.BytesIO()
    pisa.CreatePDF("\n".join(html_content), dest=out_buf)
    return out_buf.getvalue()


def html_to_pdf(html_str: str) -> bytes:
    out_buf = io.BytesIO()
    pisa.CreatePDF(html_str, dest=out_buf)
    return out_buf.getvalue()


def rtf_to_pdf(rtf_bytes: bytes) -> bytes:
    # Simple RTF text parser helper: extract ASCII text blocks and render to PDF
    # Since Python doesn't have a lightweight RTF-to-PDF engine, we extract plain text lines
    text_content = []
    # Simple RTF parser logic
    in_control = False
    control_word = ""
    current_text = ""
    
    # We decode to ascii and capture alphanumeric characters and basic spacing
    rtf_str = rtf_bytes.decode("ascii", errors="ignore")
    
    # A lightweight extraction of alphanumeric strings that aren't backslashed tags
    lines = rtf_str.split("\n")
    for line in lines:
        cleaned_line = ""
        skip = False
        for char in line:
            if char == "\\":
                skip = True
                continue
            if skip:
                if char.isspace() or char in (";", "}", "{", "\\"):
                    skip = False
                continue
            if char not in ("{", "}"):
                cleaned_line += char
        if cleaned_line.strip():
            text_content.append(cleaned_line.strip())
            
    return text_to_pdf("\n".join(text_content))


# ─── Group 4: PDF Security & Document Signing ────────────────────────────────

def encrypt_pdf(pdf_bytes: bytes, password: str) -> bytes:
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    writer = pypdf.PdfWriter()
    
    for page in reader.pages:
        writer.add_page(page)
        
    writer.encrypt(password)
    out_buf = io.BytesIO()
    writer.write(out_buf)
    writer.close()
    return out_buf.getvalue()


def decrypt_pdf(pdf_bytes: bytes, password: str) -> bytes:
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    if reader.is_encrypted:
        reader.decrypt(password)
        
    writer = pypdf.PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
        
    out_buf = io.BytesIO()
    writer.write(out_buf)
    writer.close()
    return out_buf.getvalue()


def sign_pdf(pdf_bytes: bytes, signature_image_bytes: bytes, page_num: int, x: float, y: float, width: float, height: float) -> bytes:
    # Overlay signature image at x, y, width, height (coordinates in points, 1/72 inch)
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    writer = pypdf.PdfWriter()
    total_pages = len(reader.pages)
    
    target_idx = max(0, min(total_pages - 1, page_num - 1))
    
    for idx, page in enumerate(reader.pages):
        if idx == target_idx:
            # Create a transparent overlay PDF with reportlab containing only the image
            overlay_buf = io.BytesIO()
            p_width = float(page.mediabox.width)
            p_height = float(page.mediabox.height)
            
            c = canvas.Canvas(overlay_buf, pagesize=(p_width, p_height))
            
            # Save bytes to PIL and draw
            from reportlab.lib.utils import ImageReader
            sig_img = ImageReader(Image.open(io.BytesIO(signature_image_bytes)))
            c.drawImage(sig_img, x, y, width=width, height=height, mask="auto")
            c.showPage()
            c.save()
            overlay_buf.seek(0)
            
            overlay_reader = pypdf.PdfReader(overlay_buf)
            page.merge_page(overlay_reader.pages[0])
            
        writer.add_page(page)
        
    out_buf = io.BytesIO()
    writer.write(out_buf)
    writer.close()
    return out_buf.getvalue()
