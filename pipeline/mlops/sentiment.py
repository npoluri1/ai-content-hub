"""Content sentiment analysis — VADER with keyword-based fallback."""

from ..core.models import ContentItem
from datetime import datetime, timedelta
from collections import defaultdict
import math
import re


POSITIVE_WORDS = [
    "amazing", "awesome", "beautiful", "brilliant", "breakthrough", "celebrate", "champion",
    "delight", "dynamic", "eager", "efficient", "empower", "excellent", "exceptional",
    "exciting", "fantastic", "flourish", "fluent", "fortunate", "free", "fresh", "friendly",
    "generous", "genius", "glorious", "good", "graceful", "grateful", "great", "growing",
    "happy", "harmonious", "healthy", "heartwarming", "helpful", "hopeful", "ideal",
    "impress", "improve", "incredible", "inspired", "innovate", "insightful", "inspire",
    "intuitive", "invigorate", "joy", "joyful", "kind", "leading", "legendary", "light",
    "lively", "love", "lucky", "magical", "marvelous", "meaningful", "mesmerize", "mighty",
    "motivate", "nurture", "open", "optimistic", "outperform", "paradigm", "passion",
    "peaceful", "perfect", "pioneer", "playful", "pleasant", "pleased", "polished",
    "popular", "positive", "powerful", "pragmatic", "praise", "premier", "premium",
    "proactive", "profound", "progress", "promising", "prosper", "proud", "rapid",
    "recommend", "refined", "refreshing", "reliable", "remarkable", "resilient", "resolve",
    "reward", "robust", "scalable", "seamless", "secure", "simplify", "skillful",
    "smooth", "splendid", "stable", "stellar", "strategic", "strength", "strike",
    "strong", "success", "superb", "support", "surpass", "sustainable", "swift",
    "talented", "terrific", "thorough", "thriving", "top-notch", "transform", "trust",
    "unified", "unique", "uplift", "useful", "valuable", "versatile", "vibrant",
    "victory", "visionary", "vivid", "warm", "welcoming", "wonderful", "worthwhile",
    "worthy", "zeal", "zen", "groundbreaking", "state-of-the-art", "cutting-edge",
    "world-class", "best-in-class", "award-winning", "industry-leading", "feature-rich",
]

NEGATIVE_WORDS = [
    "abysmal", "aggravate", "angry", "annoy", "anxious", "appalling", "atrocious",
    "awful", "bad", "bankrupt", "boring", "broken", "brutal", "burden", "chaotic",
    "collapse", "complaint", "complex", "concern", "confuse", "critical", "damage",
    "danger", "dead", "deadlock", "defect", "deficit", "degrade", "deny", "depress",
    "despair", "destroy", "detrimental", "devastate", "difficult", "dirty", "disappoint",
    "disaster", "discard", "disconnect", "discourage", "disgrace", "dismal", "dismiss",
    "disrupt", "dissatisfy", "distant", "distort", "distress", "disturb", "doubt",
    "downfall", "dreadful", "dreary", "dull", "error", "escape", "evil", "exploit",
    "fail", "failure", "fake", "fatal", "fault", "fear", "feeble", "flaw", "fragile",
    "frustrate", "glitch", "gloomy", "grave", "greed", "grim", "guilt", "hack",
    "harsh", "hate", "havoc", "hazard", "heavy", "helpless", "horrible", "hostile",
    "hurt", "ignorant", "ill", "illegal", "immature", "imminent", "impair", "imperfect",
    "impose", "impossible", "impractical", "inadequate", "incident", "incompetent",
    "inefficient", "inferior", "inflate", "insecure", "instability", "insufficient",
    "intense", "interrupt", "intolerable", "irritate", "isolate", "jealous", "junk",
    "lack", "lag", "leak", "liability", "limit", "lose", "loss", "lousy", "malware",
    "manipulate", "massive", "mediocre", "meltdown", "menace", "mess", "miserable",
    "misleading", "mistake", "misuse", "monopoly", "muddy", "neglect", "nervous",
    "nightmare", "notorious", "obsolete", "obstacle", "offend", "ominous", "outage",
    "outdated", "outrage", "overcharge", "overcome", "overload", "overpriced",
    "oversight", "panic", "pathetic", "penalty", "peril", "pessimistic", "petty",
    "plague", "poor", "problem", "prohibit", "protest", "punish", "questionable",
    "ransom", "rarely", "ratings", "redundant", "refund", "regret", "reject", "reluctant",
    "remedy", "remote", "remove", "resent", "resign", "restrict", "retaliate", "revenge",
    "risk", "risky", "rude", "ruin", "sabotage", "sacrifice", "sad", "scam", "scandal",
    "scare", "severe", "shame", "shatter", "shock", "shortage", "sloppy", "slow",
    "sluggish", "sorry", "spam", "stagnant", "strain", "strange", "struggle", "stuck",
    "suffer", "suspicious", "suck", "taint", "tedious", "tense", "terrible", "threat",
    "tough", "tragedy", "traumatic", "trouble", "ugly", "unacceptable", "unavoidable",
    "unbalanced", "uncertain", "unclear", "uncomfortable", "undermine", "unfair",
    "unfortunate", "unhappy", "unhealthy", "unintuitive", "unjust", "unlikely",
    "unpleasant", "unpredictable", "unreliable", "unsafe", "unsatisfactory", "unstable",
    "unsustainable", "unwanted", "unwelcome", "unwise", "upset", "useless", "vague",
    "vandalize", "vicious", "violate", "violent", "vulnerable", "waste", "weak",
    "worsen", "worst", "worthless", "wound", "wreck", "wrong",
]

EMOTION_KEYWORDS = {
    "excited": ["breakthrough", "revolutionary", "game-changing", "amazing", "incredible", "thrilled", "excited", "groundbreaking", "spectacular", "unbelievable"],
    "positive": ["great", "good", "excellent", "fantastic", "wonderful", "happy", "love", "beautiful", "brilliant", "delighted"],
    "analytical": ["analysis", "framework", "approach", "methodology", "hypothesis", "evaluate", "assess", "metrics", "benchmark", "comparative"],
    "concerned": ["concern", "worry", "caution", "careful", "problem", "issue", "risk", "danger", "threat", "uncertain"],
    "critical": ["fail", "failure", "mistake", "flaw", "wrong", "bad", "terrible", "awful", "broken", "error"],
    "skeptical": ["skeptical", "doubt", "unlikely", "uncertain", "questionable", "allegedly", "supposedly", "claim", "suspicious", "unproven"],
    "neutral": ["maybe", "perhaps", "possible", "consider", "option", "alternative", "standard", "typical", "common", "general"],
    "enthusiastic": ["love", "incredible", "phenomenal", "extraordinary", "remarkable", "outstanding", "superb", "terrific", "magnificent", "awesome"],
}


class SentimentAnalyzer:
    def __init__(self):
        self._vader_available = self._check_vader()

    def _check_vader(self) -> bool:
        try:
            from nltk.sentiment.vader import SentimentIntensityAnalyzer
            import nltk
            try:
                SentimentIntensityAnalyzer()
            except LookupError:
                nltk.download("vader_lexicon", quiet=True)
            return True
        except ImportError:
            return False

    def analyze(self, text: str) -> dict:
        if self._vader_available:
            return self._vader_sentiment(text)
        return self._keyword_sentiment(text)

    def analyze_item(self, item: ContentItem) -> ContentItem:
        result = self.analyze(item.content or item.title)
        item.metadata["sentiment"] = result
        return item

    def analyze_batch(self, items: list[ContentItem]) -> list[ContentItem]:
        return [self.analyze_item(item) for item in items]

    def get_topic_sentiment(self, topic: str, days: int = 30) -> dict:
        from ..storage.sql_store import SQLStore
        store = SQLStore()
        results = store.get_by_topic(topic, limit=500)

        scores = []
        since = (datetime.now() - timedelta(days=days)).isoformat()
        for r in results:
            published = r.get("published_at", "")
            if published and published >= since[:10]:
                text = f"{r.get('title', '')} {r.get('content', '')}"
                sentiment = self.analyze(text)
                scores.append(sentiment["score"])

        if not scores:
            return {"avg_score": 0, "trend": "stable", "sample_size": 0}

        avg = sum(scores) / len(scores)
        half = len(scores) // 2
        recent_avg = sum(scores[half:]) / max(len(scores[half:]), 1)
        older_avg = sum(scores[:half]) / max(len(scores[:half]), 1)

        diff = recent_avg - older_avg
        if diff > 0.1:
            trend = "rising"
        elif diff < -0.1:
            trend = "falling"
        else:
            trend = "stable"

        return {"avg_score": round(avg, 3), "trend": trend, "sample_size": len(scores)}

    def get_source_sentiment(self, source: str, days: int = 30) -> dict:
        from ..storage.sql_store import SQLStore
        store = SQLStore()
        results = store.get_by_source(source, limit=500)

        scores = []
        since = (datetime.now() - timedelta(days=days)).isoformat()
        for r in results:
            published = r.get("published_at", "")
            if published and published >= since[:10]:
                text = f"{r.get('title', '')} {r.get('content', '')}"
                sentiment = self.analyze(text)
                scores.append(sentiment["score"])

        if not scores:
            return {"avg_score": 0, "sample_size": 0, "distribution": {}}

        avg = sum(scores) / len(scores)
        positive = sum(1 for s in scores if s > 0.05)
        negative = sum(1 for s in scores if s < -0.05)
        neutral = len(scores) - positive - negative

        return {
            "avg_score": round(avg, 3),
            "sample_size": len(scores),
            "distribution": {
                "positive": positive,
                "neutral": neutral,
                "negative": negative,
            }
        }

    def get_sentiment_trend(self, topic: str, days: int = 30) -> list[dict]:
        from ..storage.sql_store import SQLStore
        store = SQLStore()
        results = store.get_by_topic(topic, limit=1000)

        since = (datetime.now() - timedelta(days=days)).isoformat()
        daily = defaultdict(list)

        for r in results:
            published = r.get("published_at", "")
            if published and published >= since[:10]:
                date_key = published[:10]
                text = f"{r.get('title', '')} {r.get('content', '')}"
                sentiment = self.analyze(text)
                daily[date_key].append(sentiment["score"])

        trend = []
        for date_key in sorted(daily.keys()):
            scores = daily[date_key]
            trend.append({
                "date": date_key,
                "avg_score": round(sum(scores) / len(scores), 3),
                "count": len(scores),
            })

        return trend

    def _vader_sentiment(self, text: str) -> dict:
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        sia = SentimentIntensityAnalyzer()
        scores = sia.polarity_scores(text[:10000])
        compound = scores["compound"]
        pos = scores["pos"]
        neg = scores["neg"]

        if compound >= 0.05:
            sentiment = "positive"
        elif compound <= -0.05:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        tone = self._detect_tone(text)

        return {
            "sentiment": sentiment,
            "score": round(compound, 4),
            "confidence": round(max(pos, neg, scores["neu"]), 4),
            "details": {
                "positive_words": [],
                "negative_words": [],
                "emotional_tone": tone,
                "vader_pos": round(pos, 4),
                "vader_neg": round(neg, 4),
                "vader_neu": round(scores["neu"], 4),
            }
        }

    def _keyword_sentiment(self, text: str) -> dict:
        text_lower = text.lower()[:10000]
        words = re.findall(r'\b[a-z]+\b', text_lower)
        word_set = set(words)

        pos_found = [w for w in word_set if w in POSITIVE_WORDS]
        neg_found = [w for w in word_set if w in NEGATIVE_WORDS]

        pos_count = len(pos_found)
        neg_count = len(neg_found)
        total_words = len(words) if words else 1

        raw_score = (pos_count - neg_count) / math.sqrt(total_words + 1)
        score = max(-1.0, min(1.0, raw_score))

        if score >= 0.05:
            sentiment = "positive"
        elif score <= -0.05:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        confidence = min(1.0, (pos_count + neg_count) / max(total_words * 0.1, 1))
        tone = self._detect_tone(text)

        return {
            "sentiment": sentiment,
            "score": round(score, 4),
            "confidence": round(confidence, 4),
            "details": {
                "positive_words": pos_found[:10],
                "negative_words": neg_found[:10],
                "emotional_tone": tone,
            }
        }

    def _detect_tone(self, text: str) -> str:
        text_lower = text.lower()[:5000]
        tone_scores = {}
        for tone, keywords in EMOTION_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                tone_scores[tone] = score
        if not tone_scores:
            return "neutral"
        return max(tone_scores, key=tone_scores.get)

    def _llm_sentiment(self, text: str) -> dict:
        import os
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return self._keyword_sentiment(text)

        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Analyze sentiment. Return JSON: {\"sentiment\": \"positive|negative|neutral\", \"score\": -1.0 to 1.0, \"confidence\": 0-1, \"emotional_tone\": \"excited|positive|analytical|concerned|critical|skeptical|neutral|enthusiastic\"}"},
                    {"role": "user", "content": text[:4000]},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
            import json
            return json.loads(response.choices[0].message.content)
        except Exception:
            return self._keyword_sentiment(text)
