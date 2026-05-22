from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32 MB

    CORS(app)  # Allow all origins during development

    # Dependency Validation on Startup
    print("Initializing NoteBot AI Platform...")
    try:
        import fitz
        print("[OK] PyMuPDF engine initialized")
    except Exception as e:
        try:
            import pdfplumber
            print(f"[WARN] PyMuPDF missing - Falling back to pdfplumber ({e})")
        except Exception:
            print("[FAIL] PDF extraction engine missing")

    try:
        import spacy
        print("[OK] spaCy NLP engine initialized")
    except Exception as e:
        print(f"[FAIL] spaCy engine missing: {e}")


    from .routes.summarize import bp as summarize_bp
    from .routes.flashcards import bp as flashcards_bp
    from .routes.quiz import bp as quiz_bp
    from .routes.upload import bp as upload_bp
    from .routes.export import bp as export_bp

    app.register_blueprint(summarize_bp, url_prefix='/api')
    app.register_blueprint(flashcards_bp, url_prefix='/api')
    app.register_blueprint(quiz_bp, url_prefix='/api')
    app.register_blueprint(upload_bp, url_prefix='/api')
    app.register_blueprint(export_bp, url_prefix='/api')

    @app.route('/')
    def home():
        return jsonify({"status": "Backend Running Successfully"})

    @app.route('/api/health')
    def health():
        return {'status': 'ok', 'version': '1.0.0'}

    return app
