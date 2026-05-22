import random, re, logging
from collections import Counter

logger = logging.getLogger(__name__)

# Safely import heavy NLP libraries
try:
    import spacy
except Exception as e:
    spacy = None
    logger.warning(f"spaCy import failed: {e}")

try:
    from nltk.corpus import wordnet as wn
except Exception as e:
    wn = None
    logger.warning(f"NLTK wordnet import failed: {e}")

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
except Exception as e:
    TfidfVectorizer = None
    logger.warning(f"scikit-learn import failed: {e}")

# Load spaCy model only if spacy imported successfully
if spacy is not None:
    try:
        _nlp = spacy.load("en_core_web_sm")
    except Exception as e:
        _nlp = None
        logger.warning(f"spaCy model load failed: {e}")
else:
    _nlp = None

def _clean_text(text: str) -> str:
    """Remove OCR artefacts, stray symbols and very short fragments."""
    # Remove non‑printable characters
    text = re.sub(r"[\x00-\x1f\x7f]+", " ", text)
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text)
    # Strip leading/trailing whitespace
    return text.strip()

# Sentence filter – works even if spaCy is missing
def _sentence_filter(sent) -> bool:
    """Return True if a sentence is suitable for question generation."""
    try:
        words = sent.text.split()
    except Exception:
        return False
    if len(words) < 12:
        return False
    if any(ch in sent.text for ch in "<>#@%$&*"):
        return False
    # If spaCy token attributes are available, check POS tags
    if hasattr(sent, "__iter__"):
        for token in sent:
            if getattr(token, "pos_", None) in {"NOUN", "PROPN", "VERB"}:
                return True
    # Fallback: assume sentence is okay
    return True

# Key‑phrase extraction with optional TF‑IDF
def _extract_key_phrases(doc, top_n: int = 8):
    """Extract candidate key phrases using noun chunks and TF‑IDF ranking."""
    # Noun chunks
    chunks = []
    if hasattr(doc, "noun_chunks"):
        chunks = [chunk.text.strip() for chunk in doc.noun_chunks if len(chunk.text.split()) <= 5]
    
    # TF‑IDF fallback
    sorted_terms = []
    if TfidfVectorizer is not None:
        try:
            vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
            tfidf = vectorizer.fit_transform([doc.text])
            terms = vectorizer.get_feature_names_out()
            scores = tfidf.toarray()[0]
            sorted_terms = [t for _, t in sorted(zip(scores, terms), reverse=True)][:top_n]
        except Exception as e:
            logger.warning(f"TF‑IDF extraction failed: {e}")
            
    candidates = list(dict.fromkeys(chunks + sorted_terms))
    return candidates[:top_n]

# Blank creation – works even if spaCy missing
def _choose_blank(sentence, candidates: list) -> tuple:
    for phrase in candidates:
        if phrase and phrase in sentence.text:
            blanked = sentence.text.replace(phrase, "_____", 1)
            return phrase, blanked
    return None, None

# Distractor generation – guard missing WordNet
def _generate_distractors(correct: str, all_terms: list, count: int = 3) -> list:
    distractors = set()
    if wn is not None:
        try:
            for syn in wn.synsets(correct, pos=wn.NOUN):
                for lemma in syn.lemma_names():
                    if lemma.lower() != correct.lower():
                        distractors.add(lemma.replace('_', ' '))
                for ant in syn.lemmas():
                    for ant_name in ant.antonyms():
                        distractors.add(ant_name.name().replace('_', ' '))
        except Exception:
            pass
            
    # Fill from TF‑IDF terms
    random.shuffle(all_terms)
    for term in all_terms:
        if term.lower() != correct.lower() and term not in distractors:
            distractors.add(term)
        if len(distractors) >= count:
            break
    return list(distractors)[:count]

def generate_quiz(text: str, count: int = 5) -> list:
    """Public API – generate a list of MCQs from *text*."""
    if not text:
        return []
    if _nlp is None:
        logger.warning("spaCy model not available – quiz generation disabled.")
        return []
        
    random.seed(42)
    clean = _clean_text(text)
    try:
        doc = _nlp(clean)
    except Exception as e:
        logger.warning(f"spaCy NLP failed: {e}")
        return []
        
    # Filter sentences
    candidate_sents = [sent for sent in doc.sents if _sentence_filter(sent)]
    if not candidate_sents:
        logger.warning("No suitable sentences found for quiz generation.")
        return []
        
    # Extract global key terms for distractors
    global_terms = _extract_key_phrases(doc, top_n=30)
    
    questions = []
    for sent in candidate_sents[: count * 2]:
        local_terms = _extract_key_phrases(sent, top_n=5)
        correct, question_text = _choose_blank(sent, local_terms)
        if not correct:
            continue
            
        distractors = _generate_distractors(correct, global_terms, count=3)
        if len(distractors) < 3:
            continue
            
        options = distractors + [correct]
        random.shuffle(options)
        difficulty = "hard" if len(sent.text.split()) > 20 else "medium" if len(sent.text.split()) > 15 else "easy"
        
        if len(set(options)) != 4:
            continue
            
        questions.append({
            "question": question_text,
            "options": options,
            "correct": correct,
            "difficulty": difficulty,
        })
        
        if len(questions) >= count:
            break
            
    return questions
