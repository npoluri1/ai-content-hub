"""Data enrichment pipeline — keywords, links, mentions, categories, and more."""

from ..core.models import ContentItem
from collections import Counter
from datetime import datetime
import math
import re
import urllib.parse
from typing import Optional


class EnrichmentPipeline:
    def enrich_item(self, item: ContentItem) -> ContentItem:
        text = f"{item.title} {item.content}"

        item.metadata["keywords"] = self.extract_keywords(text)
        item.metadata["links"] = self.extract_links(text)
        item.metadata["mentions"] = self.extract_mentions(text)
        item.metadata["hashtags"] = self.extract_hashtags(text)
        item.metadata["read_time"] = self.estimate_read_time(text)
        item.metadata["meta_description"] = self.generate_meta_description(text)
        item.metadata["category"] = self.categorize_content(item)

        return item

    def enrich_batch(self, items: list[ContentItem]) -> list[ContentItem]:
        return [self.enrich_item(item) for item in items]

    def extract_keywords(self, text: str, top_n: int = 10) -> list[str]:
        if not text:
            return []

        text_lower = text.lower()
        words = re.findall(r'\b[a-zA-Z]\w{2,}\b', text_lower)

        stop_words = {
            "the", "and", "for", "are", "but", "not", "you", "all", "can", "had",
            "her", "was", "one", "our", "out", "has", "have", "been", "some", "same",
            "also", "than", "then", "them", "they", "this", "that", "with", "will", "what",
            "which", "when", "where", "who", "how", "much", "many", "each", "every", "very",
            "just", "about", "into", "over", "such", "only", "other", "more", "most", "some",
            "these", "those", "could", "would", "should", "after", "before", "between", "through", "during",
            "because", "from", "were", "been", "being", "does", "done", "doing", "its", "itself",
            "your", "yours", "yourself", "myself", "himself", "herself", "itself", "ourselves", "themselves",
            "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is",
            "are", "was", "were", "be", "been", "being", "have", "has", "had", "having",
            "do", "does", "did", "doing", "would", "should", "could", "may", "might", "shall",
            "can", "need", "dare", "ought", "used", "must", "here", "there", "when", "where",
            "why", "how", "all", "each", "every", "both", "few", "several", "some", "any",
            "no", "none", "most", "much", "many", "more", "less", "fewer", "enough", "too",
            "very", "so", "quite", "rather", "pretty", "almost", "nearly", "really", "just", "barely",
            "hardly", "scarcely", "nearly", "only", "even", "still", "already", "yet", "again", "also",
            "too", "as", "well", "indeed", "surely", "certainly", "definitely", "absolutely", "obviously", "clearly",
            "simply", "merely", "purely", "truly", "likely", "probably", "possibly", "maybe", "perhaps", "please",
            "let", "us", "get", "way", "see", "make", "like", "know", "take", "come",
            "think", "want", "give", "use", "find", "tell", "ask", "work", "seem", "feel",
            "try", "leave", "call", "keep", "start", "show", "hear", "play", "run", "move",
            "live", "believe", "hold", "bring", "happen", "write", "provide", "sit", "stand", "lose",
            "pay", "meet", "include", "continue", "set", "learn", "change", "lead", "understand", "watch",
            "follow", "stop", "create", "speak", "read", "allow", "add", "spend", "grow", "open",
            "walk", "win", "teach", "offer", "remember", "love", "consider", "appear", "buy", "wait",
            "serve", "die", "send", "expect", "build", "stay", "fall", "cut", "reach", "kill",
            "remain", "suggest", "raise", "pass", "sell", "require", "report", "decide", "pull", "article",
        }

        filtered = [w for w in words if w not in stop_words and len(w) > 2]
        bigrams = [' '.join(filtered[i:i+2]) for i in range(len(filtered) - 1)]

        word_freq = Counter(filtered)
        bigram_freq = Counter(bigrams)

        all_candidates = {}
        for word, freq in word_freq.most_common(30):
            all_candidates[word] = freq
        for bigram, freq in bigram_freq.most_common(20):
            all_candidates[bigram] = freq * 1.5

        sorted_candidates = sorted(all_candidates.items(), key=lambda x: x[1], reverse=True)
        return [c[0] for c in sorted_candidates[:top_n]]

    def extract_links(self, text: str) -> list[dict]:
        if not text:
            return []
        url_pattern = re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[^\s\'"<>)]*)?')
        links = []
        seen = set()

        for match in url_pattern.finditer(text):
            url = match.group().rstrip(".,;:!?)'\"")
            if url in seen:
                continue
            seen.add(url)

            try:
                parsed = urllib.parse.urlparse(url)
                domain = parsed.netloc.lower()
                if domain.startswith("www."):
                    domain = domain[4:]
            except Exception:
                domain = ""

            anchor_text = self._extract_anchor(text, match.start(), match.end())

            links.append({
                "url": url,
                "domain": domain,
                "type": "internal" if domain and "localhost" in domain else "external",
                "anchor_text": anchor_text,
            })

        return links

    def _extract_anchor(self, text: str, start: int, end: int) -> str:
        before = text[max(0, start - 80):start]
        link_text_match = re.search(r'\[([^\]]+)\]\(', before[::-1])
        if link_text_match:
            return link_text_match.group(1)[::-1][:60]
        after = text[end:end+40].strip()
        if after:
            return after[:60]
        return ""

    def extract_mentions(self, text: str) -> list[str]:
        if not text:
            return []
        mentions = re.findall(r'(?:^|\s)@(\w{2,30})', text)
        return list(set(mentions))

    def extract_hashtags(self, text: str) -> list[str]:
        if not text:
            return []
        hashtags = re.findall(r'#(\w{2,50})', text)
        normalized = []
        for h in hashtags:
            normalized.append(h.lower())
        return list(set(normalized))

    def estimate_read_time(self, text: str) -> int:
        if not text:
            return 0
        words = len(text.split())
        minutes = math.ceil(words / 200)
        return max(1, minutes)

    def generate_meta_description(self, text: str, max_length: int = 160) -> str:
        if not text:
            return ""
        clean = re.sub(r'\s+', ' ', text).strip()
        sentences = re.split(r'(?<=[.!?])\s+', clean)
        description = ""
        for sentence in sentences:
            candidate = (description + " " + sentence).strip() if description else sentence
            if len(candidate) <= max_length:
                description = candidate
            else:
                if not description:
                    description = sentence[:max_length].rsplit(" ", 1)[0]
                break
        return description[:max_length]

    def categorize_content(self, item: ContentItem) -> str:
        text = f"{item.title} {item.content}".lower()

        tutorial_keywords = ["how to", "tutorial", "guide", "step by step", "walkthrough",
                             "getting started", "beginner", "hands-on", "example", "demo",
                             "sample code", "implementation", "code along", "workshop",
                             "cheat sheet", "cookbook", "recipe", "intro to"]
        news_keywords = ["announced", "launch", "release", "update", "new feature",
                         "breaking", "just in", "today", "latest", "report",
                         "according to", "sources say", "exclusive", "leak",
                         "rollout", "deprecat", "sunset", "acquisition", "partnership"]
        opinion_keywords = ["i think", "in my opinion", "my take", "imo", "perspective",
                            "viewpoint", "believe", "argue", "stance", "controversial",
                            "hot take", "unpopular opinion", "why i", "the case for",
                            "the case against", "rant", "reflection"]
        research_keywords = ["paper", "research", "study", "arxiv", "experiment",
                             "findings", "methodology", "results show", "we propose",
                             "we present", "state-of-the-art", "sota", "benchmark",
                             "dataset", "evaluation", "ablation", "novel approach",
                             "empirical", "quantitative", "qualitative", "hypothesis"]
        discussion_keywords = ["thoughts", "what do you think", "discussion", "question",
                               "poll", "debate", "cmv", "change my view", "anyone else",
                               "who else", "am i the only", "tell me", "share your",
                               "advice", "recommendation", "suggestion", "feedback"]
        announcement_keywords = ["announcing", "introducing", "we are excited", "we're excited",
                                 "today we", "presenting", "we are proud", "we're proud",
                                 "launching", "shipping", "available now", "now available",
                                 "version", "v1.", "v2.", "new release", "milestone"]
        review_keywords = ["review", "rating", "stars", "verdict", "final thoughts",
                           "worth it", "buy it", "skip it", "comparison", "vs ",
                           "versus", "alternative", "better than", "the best",
                           "hands-on review", "impressions", "first look", "tested"]

        scores = {
            "tutorial": self._match_count(text, tutorial_keywords) * 2,
            "news": self._match_count(text, news_keywords),
            "opinion": self._match_count(text, opinion_keywords) * 1.5,
            "research": self._match_count(text, research_keywords) * 2.5,
            "discussion": self._match_count(text, discussion_keywords) * 1.5,
            "announcement": self._match_count(text, announcement_keywords) * 2,
            "review": self._match_count(text, review_keywords) * 2,
        }

        if item.source_type in ("paper",):
            return "research"
        if item.source_type in ("news",):
            return "news"

        if max(scores.values()) == 0:
            return self._categorize_by_source(item)

        best_category = max(scores, key=scores.get)
        return best_category

    def _categorize_by_source(self, item: ContentItem) -> str:
        source_map = {
            "arxiv": "research",
            "techcrunch": "news",
            "reddit": "discussion",
            "hackernews": "discussion",
            "twitter": "opinion",
            "x": "opinion",
        }
        return source_map.get(item.source.lower().strip(), "news")

    def _match_count(self, text: str, keywords: list[str]) -> int:
        count = 0
        for kw in keywords:
            if kw in text:
                count += 1
        return count
