import os
import tempfile
import logging
from flask import Blueprint, request, jsonify

bp = Blueprint("upload", __name__)

ALLOWED_EXTENSIONS = {"pdf", "txt", "md"}

def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def clean_extracted_text(text: str) -> str:
    """Strip extra whitespace, normalize line breaks, remove empty lines."""
    lines = text.split('\n')
    cleaned_lines = [line.strip() for line in lines if line.strip()]
    return "\n".join(cleaned_lines)

def _extract_text(filepath: str, ext: str) -> tuple[str, str]:
    if ext == "pdf":
        text = ""
        # 1. Try PyMuPDF
        try:
            import fitz
            doc = fitz.open(filepath)
            for page in doc:
                text += page.get_text()
            doc.close()
        except Exception as e:
            print("PyMuPDF import or extraction failed:", e)
            # 2. Fallback to pdfplumber
            try:
                import pdfplumber
                with pdfplumber.open(filepath) as doc:
                    for page in doc.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            except Exception as fallback_e:
                print("pdfplumber fallback failed:", fallback_e)
                return "", "PDF engine initialization failed. PyMuPDF dependency missing."
        
        cleaned = clean_extracted_text(text)
        if not cleaned:
            return "", "PDF contains no readable text or is an image-only scan."
        return cleaned, ""
    else:
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            cleaned = clean_extracted_text(text)
            if not cleaned:
                return "", "Text file is empty or contains no readable characters."
            return cleaned, ""
        except Exception as e:
            return "", f"Text extraction failed: {str(e)}"

@bp.route("/upload/", methods=["POST"])
def upload_route():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    if not _allowed(file.filename):
        return jsonify({"error": "Unsupported file type"}), 415

    ext = file.filename.rsplit(".", 1)[1].lower()
    
    print(f"Uploaded file: {file.filename} (Type: {ext})")

    tmp_path = ""
    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        file.save(tmp_path)
        text, error_msg = _extract_text(tmp_path, ext)
    except Exception as e:
        text, error_msg = "", f"Failed to save temporary file: {str(e)}"
    finally:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logging.getLogger(__name__).warning(f"Failed to delete temp file: {e}")

    if not text:
        print(f"Extraction failed for {file.filename}: {error_msg}")
        return jsonify({"error": error_msg or "Unable to extract readable text"}), 400

    word_count = len(text.split())
    print(f"Extracted length: {len(text)} chars, {word_count} words")
    
    # Optional check for minimum threshold
    if len(text) < 10:
        return jsonify({"error": "Text too short to be meaningful"}), 400

    return jsonify({
        "text": text,
        "filename": file.filename,
        "word_count": word_count,
        "char_count": len(text)
    })
