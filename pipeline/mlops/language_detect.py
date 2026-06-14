"""Language detection and translation — multi-method with fallback."""

from ..core.models import ContentItem
from datetime import datetime, timedelta
from collections import defaultdict
import json
import os
import re
import urllib.request
import urllib.parse


SUPPORTED_LANGUAGES = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Portuguese", "ru": "Russian", "zh": "Chinese",
    "ja": "Japanese", "ko": "Korean", "ar": "Arabic", "hi": "Hindi",
    "bn": "Bengali", "nl": "Dutch", "sv": "Swedish", "no": "Norwegian",
    "da": "Danish", "fi": "Finnish", "pl": "Polish", "tr": "Turkish",
    "th": "Thai", "vi": "Vietnamese",
}

CJK_RANGES = [
    (0x4E00, 0x9FFF),
    (0x3400, 0x4DBF),
    (0x2E80, 0x2EFF),
    (0x3000, 0x303F),
    (0xFF00, 0xFFEF),
    (0xF900, 0xFAFF),
]

HIRAGANA_RANGE = (0x3040, 0x309F)
KATAKANA_RANGE = (0x30A0, 0x30FF)
HANGUL_RANGE = (0xAC00, 0xD7AF)
CYRILLIC_RANGE = (0x0400, 0x04FF)
ARABIC_RANGE = (0x0600, 0x06FF)
THAI_RANGE = (0x0E00, 0x0E7F)

COMMON_WORDS = {
    "en": ["the", "be", "to", "of", "and", "a", "in", "that", "have", "it",
           "for", "not", "on", "with", "he", "as", "you", "do", "at", "this",
           "but", "his", "by", "from", "they", "we", "say", "her", "she", "or",
           "an", "will", "my", "one", "all", "would", "there", "their", "what", "so",
           "up", "out", "if", "about", "who", "get", "which", "go", "me", "when",
           "make", "can", "like", "time", "no", "just", "him", "know", "take", "people",
           "into", "year", "your", "good", "some", "could", "them", "see", "other", "than",
           "then", "now", "look", "only", "come", "its", "over", "think", "also", "back",
           "after", "use", "two", "how", "our", "work", "first", "well", "way", "even",
           "new", "want", "because", "any", "these", "give", "day", "most", "us", "great"],
    "es": ["el", "la", "de", "que", "y", "a", "en", "un", "ser", "se",
           "no", "haber", "por", "con", "su", "para", "como", "más", "pero", "sus",
           "le", "ya", "este", "entre", "todo", "ella", "sí", "sin", "dos", "dar",
           "ver", "vez", "ningún", "tanto", "nos", "ir", "cual", "cuando", "muy", "años",
           "hasta", "desde", "solo", "bien", "eso", "ella", "casa", "hombre", "mismo", "después",
           "tan", "quizás", "donde", "nunca", "mejor", "entonces", "historia", "vida", "otro", "nuevo",
           "ahora", "así", "tener", "hacer", "estar", "decir", "saber", "poder", "creer", "deber"],
    "fr": ["le", "la", "de", "et", "à", "un", "une", "dans", "être", "avoir",
           "ce", "pas", "pour", "sur", "que", "qui", "nous", "vous", "ils", "elles",
           "plus", "avec", "faire", "dire", "pouvoir", "tout", "comme", "mais", "donc", "car",
           "en", "son", "sa", "ses", "au", "aux", "du", "des", "ces", "cette",
           "très", "même", "bien", "sans", "autre", "monde", "temps", "grand", "petit", "aussi",
           "alors", "encore", "aussi", "peu", "deux", "après", "avant", "entre", "toujours", "déjà",
           "chaque", "notre", "votre", "leur", "où", "quoi", "si", "non", "oui", "merci"],
    "de": ["der", "die", "das", "ist", "und", "zu", "ein", "eine", "in", "den",
           "mit", "sich", "auf", "für", "von", "nicht", "auch", "werden", "an", "aus",
           "bei", "dass", "hat", "nach", "um", "über", "sie", "er", "es", "wir",
           "ihr", "ich", "du", "wie", "zum", "zur", "durch", "gegen", "schon", "noch",
           "nur", "vor", "bis", "aber", "oder", "dann", "wenn", "weil", "als", "doch",
           "sehr", "viel", "wenig", "groß", "neu", "gut", "einfach", "richtig", "wichtig", "ganz",
           "wieder", "immer", "heute", "jetzt", "hier", "dort", "also", "allerdings", "natürlich", "zwar"],
    "it": ["il", "la", "lo", "di", "che", "e", "a", "in", "un", "una",
           "per", "con", "su", "da", "non", "si", "è", "ha", "ho", "hai",
           "sono", "hai", "ha", "hanno", "posso", "può", "fare", "detto", "tempo", "anno",
           "questa", "questo", "dove", "come", "quando", "solo", "anche", "molto", "poi", "già",
           "essere", "avere", "stare", "volere", "sapere", "dovere", "potere", "vedere", "dire", "parlare",
           "tutto", "nessuno", "qualche", "ciascun", "ogni", "tale", "altrui", "proprio", "loro", "mio",
           "buono", "grande", "piccolo", "nuovo", "bello", "brutto", "lungo", "corto", "vero", "falso"],
    "pt": ["o", "a", "de", "que", "e", "do", "da", "em", "um", "uma",
           "para", "com", "não", "um", "os", "as", "no", "na", "se", "por",
           "mais", "como", "mas", "foi", "ao", "ele", "das", "tem", "seu", "sua",
           "ou", "ser", "entre", "era", "todo", "também", "bem", "sem", "casa", "ano",
           "ter", "estar", "haver", "fazer", "dizer", "poder", "saber", "dever", "ficar", "ir",
           "muito", "pouco", "grande", "novo", "bom", "velho", "primeiro", "último", "melhor", "pior",
           "já", "ainda", "agora", "depois", "antes", "sempre", "nunca", "aqui", "ali", "lá"],
    "ru": ["и", "в", "на", "с", "по", "от", "для", "из", "о", "к",
           "за", "не", "что", "он", "она", "это", "как", "так", "но", "а",
           "его", "ее", "их", "быть", "сказать", "мочь", "знать", "хотеть", "видеть", "думать",
           ",", "—", "–", "все", "еще", "уже", "если", "когда", "чтобы", "даже",
           "потом", "сейчас", "здесь", "там", "очень", "большой", "новый", "хороший", "маленький", "старый",
           "первый", "последний", "самый", "другой", "такой", "каждый", "весь", "наш", "ваш", "свой"],
    "zh": ["的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
           "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
           "你", "会", "着", "没有", "看", "好", "自己", "这", "他", "她",
           "为", "以", "能", "而", "之", "与", "其", "所", "被", "把",
           "还", "但", "从", "又", "对", "将", "可", "更", "最", "让",
           "什么", "怎么", "为什么", "时候", "知道", "可以", "应该", "已经", "正在", "过来"],
    "ja": ["の", "に", "は", "を", "が", "で", "と", "た", "て", "する",
           "ない", "ある", "いる", "ます", "した", "いう", "こと", "これ", "それ", "ため",
           "から", "まで", "より", "へ", "や", "など", "も", "か", "ね", "よ",
           "ので", "のに", "けど", "でも", "また", "まだ", "もう", "よく", "すぐ", "とても",
           "思う", "言う", "見る", "聞く", "食べる", "行く", "来る", "分かる", "できる", "使う",
           "新しい", "古い", "大きい", "小さい", "高い", "安い", "長い", "短い", "早い", "遅い"],
    "ko": ["의", "에", "는", "을", "를", "이", "가", "과", "와", "도",
           "에서", "로", "으로", "하다", "있다", "되다", "같이", "같은", "수", "것",
           "잘", "더", "정말", "너무", "많이", "아주", "진짜", "조금", "먼저", "다시",
           "없다", "크다", "작다", "길다", "짧다", "높다", "낮다", "많다", "적다", "좋다",
           "나쁘다", "싸다", "비싸다", "가다", "오다", "사다", "주다", "보다", "먹다", "만들다",
           "사람", "시간", "일", "곳", "집", "회사", "나라", "이름", "생각", "안녕"],
    "ar": ["في", "من", "على", "إلى", "عن", "مع", "كان", "هذا", "هذه", "ذلك",
           "هو", "هي", "هم", "ما", "لا", "هل", "إن", "أن", "قد", "لقد",
           "عند", "بين", "تحت", "فوق", "بعد", "قبل", "فقط", "أيضاً", "لكن", "أو",
           "كل", "بعض", "جميع", "أكثر", "أقل", "نفس", "مثل", "غير", "دون", "حتى",
           "إن", "لن", "لم", "لما", "سوف", "الذي", "التي", "الذين", "اللذان", "اللواتي"],
    "hi": ["का", "के", "की", "में", "से", "को", "पर", "है", "हैं", "था",
           "थी", "थे", "और", "एक", "यह", "इस", "उस", "वह", "वे", "उन",
           "करना", "होना", "जाना", "आना", "देना", "लेना", "सकना", "चाहिए", "सकता", "सकते",
           "बहुत", "कुछ", "सब", "कोई", "क्या", "कैसे", "कब", "कहाँ", "क्यों", "तक",
           "लिए", "बिना", "द्वारा", "बारे", "साथ", "यहाँ", "वहाँ", "अब", "तब", "फिर",
           "अच्छा", "बुरा", "बड़ा", "छोटा", "नया", "पुराना", "पहला", "आखिरी", "हर", "अपना"],
}

LT_URL = "https://libretranslate.com/translate"


class LanguageDetector:
    def __init__(self):
        self._langdetect_available = self._check_langdetect()

    def _check_langdetect(self) -> bool:
        try:
            import langdetect
            return True
        except ImportError:
            return False

    def detect(self, text: str) -> dict:
        if not text or not text.strip():
            return {"language": "en", "confidence": 1.0, "code": "en"}

        if self._langdetect_available:
            return self._detect_with_langdetect(text)

        return self._detect_with_heuristics(text)

    def detect_item(self, item: ContentItem) -> ContentItem:
        result = self.detect(item.content or item.title)
        item.metadata["language"] = result["language"]
        item.metadata["language_code"] = result["code"]
        item.metadata["language_confidence"] = result["confidence"]
        return item

    def detect_batch(self, items: list[ContentItem]) -> list[ContentItem]:
        return [self.detect_item(item) for item in items]

    def translate(self, text: str, target_language: str = "en", source_language: str = None) -> str:
        if not text or not text.strip():
            return text

        if source_language and source_language == target_language:
            return text

        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            return self._llm_translate(text, target_language, source_language)

        return self._libretranslate(text, target_language, source_language)

    def translate_item(self, item: ContentItem, target_language: str = "en") -> ContentItem:
        item.metadata["original_language"] = item.metadata.get("language_code", "en")
        translated = self.translate(item.content or item.title, target_language)
        if target_language == "en":
            item.content_cleaned = translated
        item.metadata["translated_language"] = target_language
        return item

    def get_language_distribution(self, days: int = 30) -> list[dict]:
        from ..storage.sql_store import SQLStore
        store = SQLStore()
        results = store.search("", limit=1000)

        since = (datetime.now() - timedelta(days=days)).isoformat()
        lang_counts = defaultdict(int)
        total = 0

        for r in results:
            published = r.get("published_at", "")
            if published and published >= since[:10]:
                text = f"{r.get('title', '')} {r.get('content', '')}"
                if not text.strip():
                    continue
                detection = self.detect(text[:1000])
                lang_counts[detection["code"]] += 1
                total += 1

        distribution = []
        for code, count in sorted(lang_counts.items(), key=lambda x: x[1], reverse=True):
            distribution.append({
                "language": SUPPORTED_LANGUAGES.get(code, code),
                "code": code,
                "count": count,
                "percentage": round(count / total * 100, 1) if total > 0 else 0,
            })

        return distribution

    def filter_by_language(self, items: list[ContentItem], language: str) -> list[ContentItem]:
        return [item for item in items if self.detect(item.content or item.title)["code"] == language]

    def _detect_with_langdetect(self, text: str) -> dict:
        from langdetect import detect, detect_langs
        try:
            code = detect(text[:1000])
            confidences = detect_langs(text[:1000])
            confidence = max((float(c.prob) for c in confidences), default=0.95)
            return {
                "language": SUPPORTED_LANGUAGES.get(code, code),
                "confidence": round(confidence, 4),
                "code": code,
            }
        except Exception:
            return self._detect_with_heuristics(text)

    def _detect_with_heuristics(self, text: str) -> dict:
        text_sample = text[:2000]

        script_scores = self._score_by_script(text_sample)
        if script_scores:
            code, confidence = script_scores
            return {"language": SUPPORTED_LANGUAGES.get(code, code), "confidence": confidence, "code": code}

        return self._score_by_common_words(text_sample)

    def _score_by_script(self, text: str) -> tuple:
        cjk_count = 0
        hiragana_count = 0
        katakana_count = 0
        hangul_count = 0
        cyrillic_count = 0
        arabic_count = 0
        thai_count = 0
        total = 0

        for char in text:
            cp = ord(char)
            total += 1
            if self._in_range(cp, HIRAGANA_RANGE):
                hiragana_count += 1
            elif self._in_range(cp, KATAKANA_RANGE):
                katakana_count += 1
            elif self._in_range(cp, HANGUL_RANGE):
                hangul_count += 1
            elif self._in_range(cp, CYRILLIC_RANGE):
                cyrillic_count += 1
            elif self._in_range(cp, ARABIC_RANGE):
                arabic_count += 1
            elif self._in_range(cp, THAI_RANGE):
                thai_count += 1
            elif any(self._in_range(cp, r) for r in CJK_RANGES):
                cjk_count += 1

        if total == 0:
            return None

        if hiragana_count > total * 0.05:
            return ("ja", min(0.95, hiragana_count / max(total, 1)))
        if katakana_count > total * 0.05:
            return ("ja", min(0.90, katakana_count / max(total, 1)))
        if hangul_count > total * 0.1:
            return ("ko", min(0.95, hangul_count / max(total, 1)))
        if cyrillic_count > total * 0.1:
            return ("ru", min(0.90, cyrillic_count / max(total, 1)))
        if arabic_count > total * 0.1:
            return ("ar", min(0.90, arabic_count / max(total, 1)))
        if thai_count > total * 0.1:
            return ("th", min(0.90, thai_count / max(total, 1)))
        if cjk_count > total * 0.1:
            return self._disambiguate_cjk(text, cjk_count, total)

        return None

    def _disambiguate_cjk(self, text: str, cjk_count: int, total: int) -> tuple:
        confidence = min(0.85, cjk_count / max(total, 1) + 0.1)
        ja_hits = sum(1 for char in text if self._in_range(ord(char), HIRAGANA_RANGE))
        ko_hits = sum(1 for char in text if self._in_range(ord(char), HANGUL_RANGE))

        if ja_hits > 3:
            return ("ja", 0.85)
        if ko_hits > 3:
            return ("ko", 0.85)
        return ("zh", confidence)

    def _score_by_common_words(self, text: str) -> dict:
        text_lower = text.lower()
        words = re.findall(r'\b[a-z]+\b', text_lower)
        if not words:
            return {"language": "en", "confidence": 0.5, "code": "en"}

        word_count = len(words)
        scores = {}

        for code, common in COMMON_WORDS.items():
            matches = sum(1 for w in words if w in common)
            scores[code] = matches / max(word_count, 1)

        if not scores:
            return {"language": "en", "confidence": 0.5, "code": "en"}

        best_code = max(scores, key=scores.get)
        best_score = scores[best_code]
        second_score = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0
        confidence = min(0.95, best_score * 3)

        if best_score < 0.01:
            return {"language": "en", "confidence": 0.5, "code": "en"}

        return {"language": SUPPORTED_LANGUAGES.get(best_code, best_code), "confidence": round(confidence, 4), "code": best_code}

    def _in_range(self, cp: int, range_tuple: tuple) -> bool:
        return range_tuple[0] <= cp <= range_tuple[1]

    def _llm_translate(self, text: str, target: str, source: str = None) -> str:
        import os
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return self._libretranslate(text, target, source)

        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            source_info = f" from {source}" if source else ""
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"Translate the following text{source_info} to {target}. Return only the translated text, no explanations."},
                    {"role": "user", "content": text[:4000]},
                ],
                temperature=0.1,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return self._libretranslate(text, target, source)

    def _libretranslate(self, text: str, target: str, source: str = None) -> str:
        try:
            data = {
                "q": text[:4000],
                "target": target,
                "format": "text",
            }
            if source:
                data["source"] = source

            payload = urllib.parse.urlencode(data).encode()
            req = urllib.request.Request(LT_URL, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                return result.get("translatedText", text)
        except Exception:
            return text
