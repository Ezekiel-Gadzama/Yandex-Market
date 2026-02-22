"""Utilities for exporting content as TXT/PDF and extracting text from uploaded files."""
import io
import re
from pathlib import Path
from typing import Optional

from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT


def extract_text_from_file(content: bytes, filename: str) -> str:
    """Extract plain text from uploaded TXT or PDF file."""
    name_lower = filename.lower() if filename else ""
    if name_lower.endswith(".pdf"):
        return _extract_text_from_pdf(content)
    # Default: treat as text (utf-8, with fallbacks)
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return content.decode("latin-1")
        except Exception:
            return content.decode("utf-8", errors="replace")


def _extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF bytes."""
    try:
        reader = PdfReader(io.BytesIO(content))
        parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        return "\n\n".join(parts).strip() or "(No text extracted from PDF)"
    except Exception as e:
        return f"(Could not extract PDF text: {e})"


def strip_html(html: str) -> str:
    """Simple HTML to plain text: remove tags and decode common entities."""
    if not html:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    return text.strip()


def build_txt_documentation(name: str, description: Optional[str], content: Optional[str], file_note: Optional[str] = None) -> str:
    """Build plain text for a documentation export."""
    lines = [f"# {name}", ""]
    if description:
        lines.append(description)
        lines.append("")
    if content:
        lines.append(strip_html(content))
    elif file_note:
        lines.append(file_note)
    return "\n".join(lines)


def build_txt_activation(name: str, body: str) -> str:
    """Build plain text for an activation template export."""
    return f"# {name}\n\n{strip_html(body)}"


def build_txt_marketing(name: str, subject: str, body: str) -> str:
    """Build plain text for a marketing email template export."""
    return f"# {name}\n\nSubject: {subject}\n\n{strip_html(body)}"


def build_pdf_bytes(title: str, body_plain: str) -> bytes:
    """Generate PDF bytes from a title and plain text body."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )
    styles = getSampleStyleSheet()
    custom = ParagraphStyle(
        name="Body",
        parent=styles["Normal"],
        fontSize=11,
        leading=14,
        alignment=TA_LEFT,
    )
    story = []
    story.append(Paragraph(title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), styles["Heading1"]))
    story.append(Spacer(1, 0.2 * inch))
    for para in body_plain.split("\n\n"):
        para = (para or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if para.strip():
            story.append(Paragraph(para.replace("\n", "<br/>"), custom))
            story.append(Spacer(1, 0.1 * inch))
    doc.build(story)
    buffer.seek(0)
    return buffer.read()
