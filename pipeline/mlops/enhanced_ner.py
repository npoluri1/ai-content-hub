"""Enhanced named entity recognition with rule-based + knowledge base lookup."""

from ..core.models import ContentItem
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import json
import math
import re


AI_COMPANIES = {
    "openai", "anthropic", "google deepmind", "google ai", "meta ai", "hugging face",
    "mistral ai", "cohere", "ai21 labs", "stability ai", "midjourney", "runway",
    "synthesia", "replit", "github copilot", "cursor", "langchain", "llamaindex",
    "weaviate", "pinecone", "chromadb", "qdrant", "milvus", "vectara",
    "scale ai", "databricks", "anyscale", "together ai", "fireworks ai",
    "perplexity ai", "character ai", "inflection ai", "adept", "xai",
    "deepseek", "baidu ai", "tencent ai", "alibaba damo", "bytedance ai",
    "naver ai", "kakaobrain", "samsung ai", "lg ai", "sony ai",
    "ibm watson", "microsoft ai", "amazon ai", "apple ai", "nvidia ai",
    "tesla ai", "meta", "google", "microsoft", "amazon", "apple", "nvidia",
    "ibm", "oracle", "salesforce", "intel", "amd", "qualcomm", "samsung",
    "uber ai", "lyft ai", "airbnb ai", "netflix ai", "spotify ai",
    "twitter ai", "linkedin ai", "pinterest ai", "snapchat ai",
    "alibaba cloud", "tencent cloud", "baidu cloud", "huawei cloud",
    "datadog", "new relic", "splunk", "elastic", "grafana",
    "jina ai", "mozilla ai", "allen institute for ai", "eleuther ai",
    "cerebras", "graphcore", "samba nova", "groq", "d-matrix",
    "octo ml", "baseten", "replicate", "modal", "banana dev",
    "fixie ai", "build ai", "dust", "cognition ai", "devin",
}

AI_PRODUCTS = {
    "gpt-4", "gpt-4o", "gpt-4o-mini", "gpt-4o1", "gpt-4.5", "gpt-5",
    "gpt-3.5", "chatgpt", "dall-e", "dall-e 2", "dall-e 3",
    "whisper", "clip", "openai o1", "openai o3", "openai o4-mini",
    "claude", "claude 3", "claude 3.5", "claude 4", "claude opus", "claude sonnet", "claude haiku",
    "gemini", "gemini 1.5", "gemini 2.0", "gemini 2.5", "bard",
    "llama", "llama 2", "llama 3", "llama 4", "llama 3.1", "llama 3.2", "llama 3.3",
    "mistral", "mixtral", "mistral large", "mistral medium", "mistral small",
    "codestral", "mathstral", "pixtral",
    "midjourney", "stable diffusion", "stable diffusion 3", "sd3",
    "sora", "veo", "runway gen-3", "pika",
    "langchain", "langgraph", "langserve", "langsmith",
    "llamaindex", "llamahub",
    "haystack", "semantic kernel", "spring ai",
    "pytorch", "tensorflow", "jax", "keras", "scikit-learn", "xgboost", "lightgbm",
    "transformers", "diffusers", "accelerate", "peft", "trl",
    "vllm", "tgi", "triton", "tensorrt-llm",
    "rag", "mcp", "api", "sdk", "rest", "graphql", "grpc",
    "kubernetes", "docker", "terraform", "ansible",
    "spark", "flink", "kafka", "airflow", "prefect", "dagster",
    "ray", "dask", "modin",
    "mlflow", "kubeflow", "tensorboard", "wandb", "neptune", "comet",
    "grafana", "prometheus", "datadog", "sentry",
    "postgres", "redis", "mongodb", "elasticsearch", "neo4j",
    "pinecone", "weaviate", "chroma", "qdrant", "milvus",
    "snowflake", "bigquery", "redshift", "databricks",
    "supabase", "firebase", "appwrite",
    "cursor", "copilot", "codeium", "tabnine", "replit",
    "vercel ai sdk", "genkit", "genai",
    "autogen", "crewai", "pydantic ai", "instructor",
    "chainlit", "gradio", "streamlit",
    "numpy", "pandas", "matplotlib", "seaborn", "plotly",
}

AI_RESEARCHERS = {
    "andrej karpathy", "ilya sutskever", "yann lecun", "geoffrey hinton",
    "demis hassabis", "sam altman", "greg brockman", "dario amodei",
    "daniela amodei", "jensen huang", "sundar pichai", "satya nadella",
    "tim cook", "mark zuckerberg", "elon musk",
    "fei-fei li", "andrew ng", "sebastian thrun", "yoshua bengio",
    "ian goodfellow", "alex krizhevsky", "sutskever", "lecun",
    "kaiming he", "ross girshick", "peter abbeel", "pieter abbeel",
    "sergey levine", "chelsea finn", "timnit gebru", "joy buolamwini",
    "francois chollet", "jeremy howard", "rachel thomas",
    "david ha", "lex fridman", "adrià garriga-alonso",
    "tom brown", "jared kaplan", "jack clark",
    "alex graves", "juergen schmidhuber", "richard sutton",
    "john schulman", "paul christian", "jan leike",
    "nathan lambert", "will fedus", "barret zoph",
    "quoc le", "jeff dean", "corinna cortes",
    "yuval neiman", "hugo larochelle", "katherine lee",
    "sylvain gugger", "thomas wolf", "omer levy",
    "chen liang", "yi tay", "mostafa dehghani",
    "ashish vaswani", "noam shazeer", "lukasz kaiser",
    "aiden gomez", "llion jones", "jakob uszkoreit",
    "mike schuster", "daniel li", "chris olah",
    "shan carter", "ludwig schmidt", "nando de freitas",
    "raia hadsell", "koray kavukcuoglu", "alex graves",
}

TECH_COMPANIES = {
    "microsoft", "google", "apple", "amazon", "nvidia", "meta", "tesla",
    "ibm", "oracle", "salesforce", "adobe", "intel", "amd", "qualcomm",
    "cisco", "dell", "hp", "lenovo", "asus", "acer",
    "samsung", "lg", "sony", "panasonic", "philips",
    "vmware", "red hat", "canonical", "ubuntu",
    "sap", "siemens", "bosch", "general electric",
    "uber", "lyft", "airbnb", "netflix", "spotify",
    "twitter", "x corp", "linkedin", "pinterest", "snapchat",
    "tiktok", "bytedance", "tencent", "alibaba", "baidu",
    "jd.com", "meituan", "didichuxing", "pinduoduo",
    "shopify", "stripe", "square", "block", "paypal",
    "zoom", "slack", "notion", "figma", "atlassian",
    "github", "gitlab", "bitbucket", "sourceforge",
    "datadog", "splunk", "elastic", "new relic", "databricks",
    "snowflake", "confluent", "hashicorp", "mongodb",
    "cloudflare", "fastly", "akamai", "digitalocean",
    "vercel", "netlify", "render", "railway",
    "palantir", "crowdstrike", "palo alto", "fortinet",
    "robinhood", "coinbase", "binance", "kraken",
    "openai", "anthropic", "hugging face", "cohere", "mistral",
    "unity", "unreal", "epic games", "roblox",
    "arista", "juniper", "broadcom", "micron",
    "asml", "tsmc", "samsung foundry", "intel foundry",
    "oracle", "workday", "servicenow", "splunk",
    "twilio", "sendgrid", "mailchimp",
    "hubspot", "zoho", "freshworks",
}

ALL_PRODUCT_KEYS = {}
for p in AI_PRODUCTS:
    ALL_PRODUCT_KEYS[p.lower()] = "PRODUCT"
for c in AI_COMPANIES:
    ALL_PRODUCT_KEYS[c.lower()] = "ORGANIZATION"
for c in TECH_COMPANIES:
    ALL_PRODUCT_KEYS[c.lower()] = "ORGANIZATION"
for r in AI_RESEARCHERS:
    ALL_PRODUCT_KEYS[r.lower()] = "PERSON"

LOCATIONS = {
    "san francisco", "new york", "london", "tokyo", "beijing", "shanghai",
    "singapore", "berlin", "paris", "toronto", "seattle", "austin",
    "boston", "chicago", "los angeles", "palo alto", "mountain view",
    "menlo park", "cupertino", "sunnyvale", "san jose", "oakland",
    "cambridge", "oxford", "zurich", "munich", "amsterdam", "stockholm",
    "copenhagen", "helsinki", "oslo", "dublin", "barcelona", "madrid",
    "rome", "milan", "vienna", "prague", "warsaw", "budapest",
    "seoul", "busan", "osaka", "kyoto", "hong kong", "taipei",
    "sydney", "melbourne", "mumbai", "delhi", "bangalore", "hyderabad",
    "dubai", "abu dhabi", "doha", "riyadh", "tel aviv",
    "usa", "united states", "uk", "united kingdom", "china", "japan",
    "germany", "france", "canada", "australia", "india", "south korea",
    "singapore", "netherlands", "switzerland", "sweden", "denmark",
    "finland", "norway", "ireland", "spain", "italy", "austria",
    "belgium", "portugal", "poland", "czech republic", "hungary",
    "israel", "uae", "saudi arabia", "qatar", "brazil", "mexico",
    "argentina", "chile", "colombia", "south africa", "nigeria",
    "egypt", "kenya", "indonesia", "vietnam", "thailand", "malaysia",
    "philippines", "taiwan", "new zealand", "russia", "ukraine",
    "silicon valley", "wall street", "bay area",
}

CURRENCY_SYMBOLS = {"$", "€", "£", "¥", "₹", "₩", "₽", "₿"}


class EnhancedNER:
    def __init__(self):
        self._spacy_available = self._check_spacy()
        self._entity_cache = {}
        self._cooccurrence_cache = {}

    def _check_spacy(self) -> bool:
        try:
            import spacy
            return True
        except ImportError:
            return False

    def extract(self, text: str) -> list[dict]:
        if not text or not text.strip():
            return []
        if text in self._entity_cache:
            return self._entity_cache[text]

        entities = []

        entities.extend(self._extract_urls(text))
        entities.extend(self._extract_emails(text))
        entities.extend(self._extract_hashtags(text))
        entities.extend(self._extract_mentions(text))
        entities.extend(self._extract_money(text))
        entities.extend(self._extract_percentages(text))
        entities.extend(self._extract_dates(text))
        entities.extend(self._extract_knowledge_base(text))
        entities.extend(self._extract_persons(text))
        entities.extend(self._extract_locations(text))
        entities.extend(self._extract_technology_terms(text))

        if self._spacy_available:
            try:
                spacy_entities = self._extract_spacy(text)
                existing = {(e["text"].lower(), e["type"]) for e in entities}
                for se in spacy_entities:
                    if (se["text"].lower(), se["type"]) not in existing:
                        entities.append(se)
            except Exception:
                pass

        entities = self._deduplicate_entities(entities)
        entities.sort(key=lambda e: e.get("start", 0))
        self._entity_cache[text] = entities
        return entities

    def _deduplicate_entities(self, entities: list[dict]) -> list[dict]:
        seen = {}
        deduped = []
        for e in entities:
            key = (e["text"].lower(), e["type"])
            if key in seen:
                if e.get("confidence", 0) > seen[key].get("confidence", 0):
                    seen[key] = e
            else:
                seen[key] = e
        return list(seen.values())

    def _extract_urls(self, text: str) -> list[dict]:
        pattern = re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[^\s\'"<>)]*)?')
        entities = []
        for match in pattern.finditer(text):
            url = match.group().rstrip(".,;:!?)'\"")
            entities.append({
                "text": url, "type": "URL", "confidence": 1.0,
                "start": match.start(), "end": match.end(),
                "normalized_form": url.lower(),
            })
        return entities

    def _extract_emails(self, text: str) -> list[dict]:
        pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        entities = []
        for match in pattern.finditer(text):
            entities.append({
                "text": match.group(), "type": "EMAIL", "confidence": 1.0,
                "start": match.start(), "end": match.end(),
                "normalized_form": match.group().lower(),
            })
        return entities

    def _extract_hashtags(self, text: str) -> list[dict]:
        pattern = re.compile(r'#(\w{2,50})')
        entities = []
        for match in pattern.finditer(text):
            entities.append({
                "text": f"#{match.group(1)}", "type": "HASHTAG", "confidence": 0.95,
                "start": match.start(), "end": match.end(),
                "normalized_form": match.group(1).lower(),
            })
        return entities

    def _extract_mentions(self, text: str) -> list[dict]:
        pattern = re.compile(r'(?:^|\s)@(\w{2,30})')
        entities = []
        for match in pattern.finditer(text):
            entities.append({
                "text": f"@{match.group(1)}", "type": "MENTION", "confidence": 0.9,
                "start": match.start(), "end": match.end(),
                "normalized_form": match.group(1).lower(),
            })
        return entities

    def _extract_money(self, text: str) -> list[dict]:
        pattern = re.compile(
            r'(?:'
            r'[\$€£¥₹₩₽₿]\s*\d+(?:,\d{3})*(?:\.\d+)?\s*(?:million|billion|trillion|m|b|t|k)?'
            r'|'
            r'\d+(?:,\d{3})*(?:\.\d+)?\s*(?:million|billion|trillion|dollars|euros|pounds|yen|rupees)\s*(?:USD|EUR|GBP|JPY|INR)?'
            r')',
            re.IGNORECASE
        )
        entities = []
        for match in pattern.finditer(text):
            entities.append({
                "text": match.group().strip(), "type": "MONEY", "confidence": 0.9,
                "start": match.start(), "end": match.end(),
                "normalized_form": match.group().strip().lower(),
            })
        return entities

    def _extract_percentages(self, text: str) -> list[dict]:
        pattern = re.compile(r'\b\d+(?:\.\d+)?\s*(?:%|percent|percentage\s*points?)\b', re.IGNORECASE)
        entities = []
        for match in pattern.finditer(text):
            entities.append({
                "text": match.group(), "type": "PERCENTAGE", "confidence": 0.95,
                "start": match.start(), "end": match.end(),
                "normalized_form": match.group().lower(),
            })
        return entities

    def _extract_dates(self, text: str) -> list[dict]:
        patterns = [
            (r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
             r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
             r'\s+\d{1,2},?\s+\d{4}\b', 0.95),
            (r'\b\d{4}-\d{2}-\d{2}\b', 0.9),
            (r'\b\d{1,2}/\d{1,2}/\d{2,4}\b', 0.85),
            (r'\b(?:last|this|next)\s+(?:week|month|quarter|year)\b', 0.7),
            (r'\bQ[1-4]\s+\d{4}\b', 0.9),
            (r'\b\d{1,2}\s+(?:minutes?|hours?|days?|weeks?|months?)\s+ago\b', 0.7),
            (r'\byesterday\b', 0.6),
            (r'\btoday\b', 0.6),
            (r'\btomorrow\b', 0.6),
            (r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
             r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
             r'\s+\d{4}\b', 0.85),
        ]
        entities = []
        for pattern_str, confidence in patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            for match in pattern.finditer(text):
                entities.append({
                    "text": match.group(), "type": "DATE", "confidence": confidence,
                    "start": match.start(), "end": match.end(),
                    "normalized_form": match.group().lower(),
                })
        return entities

    def _extract_knowledge_base(self, text: str) -> list[dict]:
        text_lower = text.lower()
        entities = []

        known_entities = {}
        for company in AI_COMPANIES:
            known_entities[company.lower()] = ("ORGANIZATION", 0.95)
        for company in TECH_COMPANIES:
            known_entities[company.lower()] = ("ORGANIZATION", 0.92)
        for product in AI_PRODUCTS:
            known_entities[product.lower()] = ("PRODUCT", 0.93)
        for researcher in AI_RESEARCHERS:
            known_entities[researcher.lower()] = ("PERSON", 0.90)

        for name, (etype, confidence) in known_entities.items():
            for match in re.finditer(re.escape(name), text_lower):
                start = match.start()
                end = match.end()
                original = text[start:end]
                entities.append({
                    "text": original, "type": etype, "confidence": confidence,
                    "start": start, "end": end,
                    "normalized_form": name,
                })

        return entities

    def _extract_persons(self, text: str) -> list[dict]:
        pattern = re.compile(r'\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b')
        entities = []
        for match in pattern.finditer(text):
            name = match.group()
            start, end = match.start(), match.end()
            ctx_before = text[max(0, start - 30):start].lower()
            ctx_after = text[end:min(len(text), end + 30)].lower()

            is_person = False
            person_indicators = [
                "ceo", "cto", "cfo", "founder", "co-founder", "president",
                "director", "manager", "engineer", "scientist", "researcher",
                "professor", "dr.", "doctor", "said", "says", "announced",
                "according to", "interview with", "spoke with",
                "wrote", "authored", "presented", "led by",
            ]
            for indicator in person_indicators:
                if indicator in ctx_before or indicator in ctx_after:
                    is_person = True
                    break

            if is_person:
                entities.append({
                    "text": name, "type": "PERSON", "confidence": 0.7,
                    "start": start, "end": end, "normalized_form": name.lower(),
                })
        return entities

    def _extract_locations(self, text: str) -> list[dict]:
        text_lower = text.lower()
        entities = []
        for loc in LOCATIONS:
            pattern = re.compile(r'\b' + re.escape(loc) + r'\b', re.IGNORECASE)
            for match in pattern.finditer(text):
                start = match.start()
                end = match.end()
                original = text[start:end]
                entities.append({
                    "text": original, "type": "LOCATION", "confidence": 0.9,
                    "start": start, "end": end, "normalized_form": loc,
                })
        return entities

    TECH_TERMS = [
        "rag", "mcp", "api", "sdk", "rest", "graphql", "grpc", "restful",
        "llm", "gpt", "ner", "nlp", "cv", "ml", "ai", "genai",
        "cnn", "rnn", "lstm", "transformer", "attention", "gan", "vae",
        "bert", "gpt", "t5", "bart", "roberta", "electra",
        "dnn", "ann", "svm", "knn", "pca", "tsne", "umap",
        "sql", "nosql", "acid", "base", "oltp", "olap",
        "http", "https", "tcp", "udp", "ip", "dns", "ssl", "tls",
        "json", "xml", "yaml", "csv", "parquet", "avro", "protobuf",
        "ci/cd", "devops", "mlops", "llmops", "dataops",
        "sre", "sla", "slo", "sli",
        "k8s", "docker", "containerd", "cri-o",
        "etl", "elt", "dwh", "data lake", "data mesh", "data fabric",
        "crud", "jwt", "oauth", "saml", "oidc", "sso",
        "mvp", "poc", "saas", "paas", "iaas", "faas", "caas",
        "on-prem", "hybrid cloud", "multi-cloud", "edge computing",
        "hpc", "gpgpu", "tpu", "npu", "asic", "fpga",
    ]

    def _extract_technology_terms(self, text: str) -> list[dict]:
        text_lower = text.lower()
        entities = []
        for term in self.TECH_TERMS:
            pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
            for match in pattern.finditer(text):
                entities.append({
                    "text": match.group(), "type": "TECHNOLOGY", "confidence": 0.85,
                    "start": match.start(), "end": match.end(), "normalized_form": term,
                })
        return entities

    def _extract_spacy(self, text: str) -> list[dict]:
        import spacy
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            return []

        doc = nlp(text[:10000])
        type_map = {
            "PERSON": "PERSON", "ORG": "ORGANIZATION", "GPE": "LOCATION",
            "LOC": "LOCATION", "PRODUCT": "PRODUCT", "EVENT": "ORGANIZATION",
            "WORK_OF_ART": "PRODUCT", "MONEY": "MONEY", "DATE": "DATE",
            "PERCENT": "PERCENTAGE", "TIME": "DATE",
        }
        entities = []
        for ent in doc.ents:
            ent_type = type_map.get(ent.label_, ent.label_)
            entities.append({
                "text": ent.text, "type": ent_type, "confidence": 0.85,
                "start": ent.start_char, "end": ent.end_char,
                "normalized_form": ent.text.lower(),
            })
        return entities

    def extract_item(self, item: ContentItem) -> ContentItem:
        text = f"{item.title} {item.content}"
        entities = self.extract(text)
        item.metadata["entities"] = [
            {"text": e["text"], "type": e["type"], "confidence": e["confidence"]}
            for e in entities
        ]
        entity_types = Counter(e["type"] for e in entities)
        item.metadata["entity_count"] = len(entities)
        item.metadata["entity_types"] = dict(entity_types.most_common())

        orgs = [e["text"] for e in entities if e["type"] in ("ORGANIZATION",)]
        products = [e["text"] for e in entities if e["type"] == "PRODUCT"]
        persons = [e["text"] for e in entities if e["type"] == "PERSON"]

        if orgs:
            item.metadata["organizations"] = list(set(orgs))
        if products:
            item.metadata["products"] = list(set(products))
        if persons:
            item.metadata["persons"] = list(set(persons))

        return item

    def extract_batch(self, items: list[ContentItem]) -> list[ContentItem]:
        return [self.extract_item(item) for item in items]

    def get_entity_frequency(self, entity_type: str = None, days: int = 30, limit: int = 30) -> list[dict]:
        from ..storage.sql_store import SQLStore
        store = SQLStore()
        results = store.search("", limit=2000)
        since = (datetime.now() - timedelta(days=days)).isoformat()
        entity_counter = Counter()

        for r in results:
            published = r.get("published_at", "")
            if not published or published < since[:10]:
                continue
            meta_raw = r.get("metadata", "{}")
            if isinstance(meta_raw, str):
                try:
                    meta = json.loads(meta_raw)
                except (json.JSONDecodeError, TypeError):
                    continue
            else:
                meta = meta_raw
            entities = meta.get("entities") or meta.get("entity_types") or {}
            if entity_type:
                for e_text, e_type in entities.items() if isinstance(entities, dict) else []:
                    if isinstance(e_type, str) and e_type == entity_type:
                        entity_counter[e_text] += 1
            else:
                for e in entities if isinstance(entities, list) else []:
                    if isinstance(e, dict):
                        entity_counter[e.get("text", "?")] += 1

        return [{"entity": e, "count": c} for e, c in entity_counter.most_common(limit)]

    def get_entity_cooccurrence(self, entity_a: str, entity_b: str, days: int = 30) -> int:
        from ..storage.sql_store import SQLStore
        store = SQLStore()
        results = store.search("", limit=5000)
        since = (datetime.now() - timedelta(days=days)).isoformat()
        count = 0

        entity_a_lower = entity_a.lower()
        entity_b_lower = entity_b.lower()

        for r in results:
            published = r.get("published_at", "")
            if not published or published < since[:10]:
                continue
            text = (r.get("title", "") + " " + r.get("content", "")).lower()
            if entity_a_lower in text and entity_b_lower in text:
                count += 1

        return count

    def get_entity_network(self, entity_type: str = None, limit: int = 50) -> dict:
        from ..storage.sql_store import SQLStore
        store = SQLStore()
        results = store.search("", limit=2000)

        node_counts = Counter()
        cooccurrences = defaultdict(int)

        for r in results:
            meta_raw = r.get("metadata", "{}")
            if isinstance(meta_raw, str):
                try:
                    meta = json.loads(meta_raw)
                except (json.JSONDecodeError, TypeError):
                    continue
            else:
                meta = meta_raw
            entities = meta.get("entities", [])
            entity_texts = []
            for e in entities:
                if isinstance(e, dict):
                    e_text = e.get("text", "")
                    e_type = e.get("type", "")
                    if entity_type and e_type != entity_type:
                        continue
                    entity_texts.append(e_text)

            for e in entity_texts:
                node_counts[e] += 1

            for i in range(len(entity_texts)):
                for j in range(i + 1, len(entity_texts)):
                    a, b = sorted([entity_texts[i], entity_texts[j]])
                    if a != b:
                        cooccurrences[(a, b)] += 1

        top_nodes = [n for n, _ in node_counts.most_common(limit)]
        top_set = set(top_nodes)

        nodes = [{"name": n, "type": entity_type or "UNKNOWN", "count": node_counts[n]} for n in top_nodes]
        edges = []
        for (a, b), weight in sorted(cooccurrences.items(), key=lambda x: -x[1]):
            if a in top_set and b in top_set:
                edges.append({"source": a, "target": b, "weight": weight})

        return {"nodes": nodes, "edges": edges}

    def search_by_entity(self, entity: str, limit: int = 20) -> list[dict]:
        from ..storage.sql_store import SQLStore
        store = SQLStore()
        results = store.search("", limit=2000)
        entity_lower = entity.lower()
        matches = []

        for r in results:
            text = (r.get("title", "") + " " + r.get("content", "")).lower()
            if entity_lower in text:
                matches.append(r)
                if len(matches) >= limit:
                    break

        return matches
