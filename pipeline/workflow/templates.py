import copy
import json
import uuid
from datetime import datetime


class WorkflowTemplates:
    def __init__(self):
        self._builtin_templates = self._init_builtins()
        self._custom_templates: dict[str, dict] = {}

    def _init_builtins(self) -> dict:
        return {
            "daily_news_digest": self._build_daily_news_digest(),
            "competitor_intel": self._build_competitor_intel(),
            "research_paper_monitor": self._build_research_paper_monitor(),
            "social_trend_tracker": self._build_social_trend_tracker(),
            "content_enrichment_pipeline": self._build_content_enrichment_pipeline(),
            "weekly_executive_report": self._build_weekly_executive_report(),
        }

    def _build_daily_news_digest(self) -> dict:
        return {
            "id": "tpl_daily_news_digest",
            "name": "Daily News Digest",
            "description": "Collect news from all sources, classify, filter relevant, notify via Slack and Email",
            "category": "news",
            "version": "1.0",
            "tags": ["news", "digest", "notification", "daily"],
            "workflow": {
                "id": "wf_daily_news_digest",
                "name": "Daily News Digest Pipeline",
                "description": "Collects news from multiple sources, classifies, filters, and sends digest",
                "nodes": [
                    {
                        "id": "schedule_trigger",
                        "type": "trigger",
                        "trigger_type": "schedule",
                        "schedule": "0 6 * * *",
                        "label": "Daily Schedule Trigger",
                    },
                    {
                        "id": "collect_rss",
                        "type": "source",
                        "source_type": "rss",
                        "urls": ["https://feeds.bbci.co.uk/news/rss.xml", "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"],
                        "max_items": 50,
                        "label": "RSS Collector",
                    },
                    {
                        "id": "collect_newsapi",
                        "type": "source",
                        "source_type": "newsapi",
                        "query": "technology OR AI OR business",
                        "max_items": 50,
                        "label": "NewsAPI Collector",
                    },
                    {
                        "id": "classify_articles",
                        "type": "transform",
                        "transform_type": "classify",
                        "categories": ["technology", "business", "science", "politics", "health"],
                        "label": "Article Classifier",
                    },
                    {
                        "id": "filter_relevant",
                        "type": "filter",
                        "filter_type": "keyword",
                        "keywords": ["AI", "machine learning", "cloud", "startup", "funding", "innovation"],
                        "min_confidence": 0.6,
                        "label": "Relevance Filter",
                    },
                    {
                        "id": "notify_slack",
                        "type": "action",
                        "action_type": "slack_notify",
                        "channel": "#news-digest",
                        "message_template": "📰 Daily News Digest - {{ date }}\n\n{{ summary }}",
                        "label": "Slack Notifier",
                    },
                    {
                        "id": "notify_email",
                        "type": "action",
                        "action_type": "email",
                        "recipients": ["team@company.com"],
                        "subject_template": "Daily News Digest - {{ date }}",
                        "label": "Email Notifier",
                    },
                ],
                "edges": [
                    {"from": "schedule_trigger", "to": "collect_rss"},
                    {"from": "schedule_trigger", "to": "collect_newsapi"},
                    {"from": "collect_rss", "to": "classify_articles"},
                    {"from": "collect_newsapi", "to": "classify_articles"},
                    {"from": "classify_articles", "to": "filter_relevant"},
                    {"from": "filter_relevant", "to": "notify_slack"},
                    {"from": "filter_relevant", "to": "notify_email"},
                ],
            },
        }

    def _build_competitor_intel(self) -> dict:
        return {
            "id": "tpl_competitor_intel",
            "name": "Competitor Intelligence",
            "description": "Collect competitor news, filter by competitor keywords, analyze sentiment, notify Slack, store",
            "category": "intelligence",
            "version": "1.0",
            "tags": ["competitor", "intelligence", "monitoring", "sentiment"],
            "workflow": {
                "id": "wf_competitor_intel",
                "name": "Competitor Intel Pipeline",
                "description": "Monitors competitors across news sources, analyzes sentiment, sends alerts",
                "nodes": [
                    {
                        "id": "schedule_trigger",
                        "type": "trigger",
                        "trigger_type": "schedule",
                        "schedule": "0 */4 * * *",
                        "label": "4-Hour Schedule Trigger",
                    },
                    {
                        "id": "collect_rss",
                        "type": "source",
                        "source_type": "rss",
                        "urls": [
                            "https://techcrunch.com/feed/",
                            "https://www.theverge.com/rss/index.xml",
                            "https://www.wired.com/feed/rss",
                        ],
                        "max_items": 30,
                        "label": "RSS Feed Collector",
                    },
                    {
                        "id": "collect_newsapi",
                        "type": "source",
                        "source_type": "newsapi",
                        "query": "competitor OR industry AND trends",
                        "max_items": 30,
                        "label": "NewsAPI Collector",
                    },
                    {
                        "id": "filter_competitors",
                        "type": "filter",
                        "filter_type": "keyword",
                        "keywords": ["OpenAI", "Anthropic", "Google", "Microsoft", "Meta", "competitor"],
                        "mode": "any",
                        "label": "Competitor Keyword Filter",
                    },
                    {
                        "id": "sentiment_analysis",
                        "type": "transform",
                        "transform_type": "sentiment",
                        "label": "Sentiment Analyzer",
                    },
                    {
                        "id": "notify_slack_alert",
                        "type": "action",
                        "action_type": "slack_notify",
                        "channel": "#competitor-alerts",
                        "message_template": "🚨 Competitor Alert - {{ title }}\n{{ url }}\nSentiment: {{ sentiment }}",
                        "label": "Slack Alert",
                    },
                    {
                        "id": "store_results",
                        "type": "sink",
                        "sink_type": "database",
                        "collection": "competitor_intel",
                        "label": "Database Store",
                    },
                ],
                "edges": [
                    {"from": "schedule_trigger", "to": "collect_rss"},
                    {"from": "schedule_trigger", "to": "collect_newsapi"},
                    {"from": "collect_rss", "to": "filter_competitors"},
                    {"from": "collect_newsapi", "to": "filter_competitors"},
                    {"from": "filter_competitors", "to": "sentiment_analysis"},
                    {"from": "sentiment_analysis", "to": "notify_slack_alert"},
                    {"from": "sentiment_analysis", "to": "store_results"},
                ],
            },
        }

    def _build_research_paper_monitor(self) -> dict:
        return {
            "id": "tpl_research_paper_monitor",
            "name": "Research Paper Monitor",
            "description": "Monitor ArXiv for new papers, classify by topic, summarize, notify via Telegram, store",
            "category": "research",
            "version": "1.0",
            "tags": ["research", "arxiv", "academic", "papers", "AI"],
            "workflow": {
                "id": "wf_research_paper_monitor",
                "name": "Research Paper Monitor Pipeline",
                "description": "Fetches new papers from ArXiv, classifies, summarizes, and notifies",
                "nodes": [
                    {
                        "id": "schedule_trigger",
                        "type": "trigger",
                        "trigger_type": "schedule",
                        "schedule": "0 8,20 * * *",
                        "label": "Twice Daily Schedule",
                    },
                    {
                        "id": "collect_arxiv",
                        "type": "source",
                        "source_type": "arxiv",
                        "categories": ["cs.AI", "cs.LG", "cs.CL", "cs.CV", "stat.ML"],
                        "max_results": 100,
                        "label": "ArXiv Collector",
                    },
                    {
                        "id": "classify_papers",
                        "type": "transform",
                        "transform_type": "classify",
                        "categories": ["NLP", "Computer Vision", "Reinforcement Learning", "Generative AI", "Optimization"],
                        "label": "Paper Classifier",
                    },
                    {
                        "id": "summarize_papers",
                        "type": "transform",
                        "transform_type": "summarize",
                        "max_summary_length": 200,
                        "label": "Paper Summarizer",
                    },
                    {
                        "id": "notify_telegram",
                        "type": "action",
                        "action_type": "telegram",
                        "channel": "@research_updates",
                        "message_template": "📄 New Paper: {{ title }}\nCategory: {{ category }}\n{{ summary }}",
                        "label": "Telegram Notifier",
                    },
                    {
                        "id": "store_papers",
                        "type": "sink",
                        "sink_type": "database",
                        "collection": "research_papers",
                        "label": "Paper Database Store",
                    },
                ],
                "edges": [
                    {"from": "schedule_trigger", "to": "collect_arxiv"},
                    {"from": "collect_arxiv", "to": "classify_papers"},
                    {"from": "classify_papers", "to": "summarize_papers"},
                    {"from": "summarize_papers", "to": "notify_telegram"},
                    {"from": "summarize_papers", "to": "store_papers"},
                ],
            },
        }

    def _build_social_trend_tracker(self) -> dict:
        return {
            "id": "tpl_social_trend_tracker",
            "name": "Social Trend Tracker",
            "description": "Track trends from Reddit, Hacker News, and Medium, classify, export to CSV, notify Slack",
            "category": "social",
            "version": "1.0",
            "tags": ["social", "trends", "reddit", "hackernews", "medium"],
            "workflow": {
                "id": "wf_social_trend_tracker",
                "name": "Social Trend Tracker Pipeline",
                "description": "Collects trending content from social platforms, analyzes trends, exports data",
                "nodes": [
                    {
                        "id": "schedule_trigger",
                        "type": "trigger",
                        "trigger_type": "schedule",
                        "schedule": "0 */6 * * *",
                        "label": "6-Hour Schedule",
                    },
                    {
                        "id": "collect_reddit",
                        "type": "source",
                        "source_type": "reddit",
                        "subreddits": ["artificial", "MachineLearning", "technology", "programming"],
                        "sort": "hot",
                        "limit": 25,
                        "label": "Reddit Collector",
                    },
                    {
                        "id": "collect_hackernews",
                        "type": "source",
                        "source_type": "hackernews",
                        "endpoint": "topstories",
                        "limit": 30,
                        "label": "Hacker News Collector",
                    },
                    {
                        "id": "collect_medium",
                        "type": "source",
                        "source_type": "medium",
                        "tags": ["AI", "machine-learning", "data-science", "technology"],
                        "limit": 20,
                        "label": "Medium Collector",
                    },
                    {
                        "id": "classify_content",
                        "type": "transform",
                        "transform_type": "classify",
                        "categories": ["AI/ML", "Programming", "DevOps", "Cybersecurity", "Data Science"],
                        "label": "Content Classifier",
                    },
                    {
                        "id": "trend_analysis",
                        "type": "transform",
                        "transform_type": "trend_analysis",
                        "window_hours": 24,
                        "min_mentions": 3,
                        "label": "Trend Analyzer",
                    },
                    {
                        "id": "export_csv",
                        "type": "action",
                        "action_type": "export",
                        "format": "csv",
                        "output_path": "./exports/social_trends_{{ date }}.csv",
                        "fields": ["title", "source", "category", "score", "url", "timestamp"],
                        "label": "CSV Exporter",
                    },
                    {
                        "id": "notify_slack",
                        "type": "action",
                        "action_type": "slack_notify",
                        "channel": "#trends",
                        "message_template": "📊 Social Trend Report - {{ date }}\nTop Topics: {{ top_topics }}",
                        "label": "Slack Reporter",
                    },
                ],
                "edges": [
                    {"from": "schedule_trigger", "to": "collect_reddit"},
                    {"from": "schedule_trigger", "to": "collect_hackernews"},
                    {"from": "schedule_trigger", "to": "collect_medium"},
                    {"from": "collect_reddit", "to": "classify_content"},
                    {"from": "collect_hackernews", "to": "classify_content"},
                    {"from": "collect_medium", "to": "classify_content"},
                    {"from": "classify_content", "to": "trend_analysis"},
                    {"from": "trend_analysis", "to": "export_csv"},
                    {"from": "trend_analysis", "to": "notify_slack"},
                ],
            },
        }

    def _build_content_enrichment_pipeline(self) -> dict:
        return {
            "id": "tpl_content_enrichment_pipeline",
            "name": "Content Enrichment Pipeline",
            "description": "Trigger on new item, extract full text, summarize, sentiment, tag, enrich, store",
            "category": "content",
            "version": "1.0",
            "tags": ["content", "enrichment", "nlp", "metadata"],
            "workflow": {
                "id": "wf_content_enrichment",
                "name": "Content Enrichment Pipeline",
                "description": "Enriches content items with full text extraction, summaries, sentiment, and tags",
                "nodes": [
                    {
                        "id": "trigger_new_item",
                        "type": "trigger",
                        "trigger_type": "webhook",
                        "endpoint": "/api/ingest",
                        "method": "POST",
                        "label": "Webhook Trigger",
                    },
                    {
                        "id": "full_text_extract",
                        "type": "transform",
                        "transform_type": "extract",
                        "extraction_method": "trafilatura",
                        "label": "Full Text Extractor",
                    },
                    {
                        "id": "summarize",
                        "type": "transform",
                        "transform_type": "summarize",
                        "max_length": 300,
                        "min_length": 50,
                        "label": "Content Summarizer",
                    },
                    {
                        "id": "sentiment_analysis",
                        "type": "transform",
                        "transform_type": "sentiment",
                        "label": "Sentiment Analyzer",
                    },
                    {
                        "id": "tag_generation",
                        "type": "transform",
                        "transform_type": "tag",
                        "max_tags": 10,
                        "label": "Tag Generator",
                    },
                    {
                        "id": "enrich_metadata",
                        "type": "transform",
                        "transform_type": "enrich",
                        "fields": ["word_count", "reading_time", "language", "has_images"],
                        "label": "Metadata Enricher",
                    },
                    {
                        "id": "store_enriched",
                        "type": "sink",
                        "sink_type": "database",
                        "collection": "enriched_content",
                        "label": "Enriched Content Store",
                    },
                ],
                "edges": [
                    {"from": "trigger_new_item", "to": "full_text_extract"},
                    {"from": "full_text_extract", "to": "summarize"},
                    {"from": "full_text_extract", "to": "sentiment_analysis"},
                    {"from": "full_text_extract", "to": "tag_generation"},
                    {"from": "summarize", "to": "enrich_metadata"},
                    {"from": "sentiment_analysis", "to": "enrich_metadata"},
                    {"from": "tag_generation", "to": "enrich_metadata"},
                    {"from": "enrich_metadata", "to": "store_enriched"},
                ],
            },
        }

    def _build_weekly_executive_report(self) -> dict:
        return {
            "id": "tpl_weekly_executive_report",
            "name": "Weekly Executive Report",
            "description": "Weekly collection, classification, quality scoring, report generation, email to execs, PDF export",
            "category": "reporting",
            "version": "1.0",
            "tags": ["report", "executive", "weekly", "email", "pdf"],
            "workflow": {
                "id": "wf_weekly_exec_report",
                "name": "Weekly Executive Report Pipeline",
                "description": "Generates comprehensive weekly executive reports with quality scoring and PDF export",
                "nodes": [
                    {
                        "id": "schedule_trigger",
                        "type": "trigger",
                        "trigger_type": "schedule",
                        "schedule": "0 7 * * 1",
                        "label": "Weekly Monday Schedule",
                    },
                    {
                        "id": "collect_all_sources",
                        "type": "source",
                        "source_type": "aggregator",
                        "sources": ["rss", "newsapi", "reddit", "hackernews", "medium", "arxiv"],
                        "label": "Multi-Source Collector",
                    },
                    {
                        "id": "classify_all",
                        "type": "transform",
                        "transform_type": "classify",
                        "categories": ["AI/ML", "Business", "Competitors", "Industry Trends", "Regulatory"],
                        "label": "Comprehensive Classifier",
                    },
                    {
                        "id": "quality_scoring",
                        "type": "transform",
                        "transform_type": "quality_score",
                        "factors": ["source_reliability", "engagement", "recency", "relevance"],
                        "label": "Quality Scorer",
                    },
                    {
                        "id": "generate_report",
                        "type": "transform",
                        "transform_type": "report_gen",
                        "sections": ["Executive Summary", "Key Insights", "Competitor Activity", "Trend Analysis", "Recommendations"],
                        "max_items_per_section": 5,
                        "label": "Report Generator",
                    },
                    {
                        "id": "email_execs",
                        "type": "action",
                        "action_type": "email",
                        "recipients": ["ceo@company.com", "cto@company.com", "vp-eng@company.com", "vp-product@company.com"],
                        "subject_template": "Weekly Executive Report - Week {{ week_number }}",
                        "label": "Executive Email",
                    },
                    {
                        "id": "export_pdf",
                        "type": "action",
                        "action_type": "export",
                        "format": "pdf",
                        "output_path": "./reports/weekly_exec_report_{{ week_number }}.pdf",
                        "template": "executive_report",
                        "label": "PDF Exporter",
                    },
                ],
                "edges": [
                    {"from": "schedule_trigger", "to": "collect_all_sources"},
                    {"from": "collect_all_sources", "to": "classify_all"},
                    {"from": "classify_all", "to": "quality_scoring"},
                    {"from": "quality_scoring", "to": "generate_report"},
                    {"from": "generate_report", "to": "email_execs"},
                    {"from": "generate_report", "to": "export_pdf"},
                ],
            },
        }

    def list(self, category: str = None) -> list[dict]:
        results = []
        for tid, tpl in {**self._builtin_templates, **self._custom_templates}.items():
            if category is None or tpl.get("category") == category:
                results.append({
                    "id": tid,
                    "name": tpl.get("name"),
                    "description": tpl.get("description"),
                    "category": tpl.get("category"),
                    "version": tpl.get("version"),
                    "tags": tpl.get("tags", []),
                    "is_builtin": tid in self._builtin_templates,
                })
        return results

    def get(self, template_id: str) -> dict:
        tpl = self._builtin_templates.get(template_id) or self._custom_templates.get(template_id)
        if not tpl:
            raise ValueError(f"Template '{template_id}' not found")
        return copy.deepcopy(tpl)

    def instantiate(self, template_id: str, config: dict) -> dict:
        tpl = self.get(template_id)
        workflow = copy.deepcopy(tpl["workflow"])
        new_id = f"wf_{uuid.uuid4().hex[:12]}"
        workflow["id"] = new_id
        workflow["name"] = config.get("name", workflow.get("name", template_id))
        workflow["created_at"] = datetime.utcnow().isoformat()
        workflow["template_id"] = template_id
        workflow["template_version"] = tpl.get("version", "1.0")

        if "schedule" in config:
            for node in workflow.get("nodes", []):
                if node.get("trigger_type") == "schedule":
                    node["schedule"] = config["schedule"]

        if "sources" in config:
            for node in workflow.get("nodes", []):
                if node.get("type") in ("source",):
                    for key, value in config["sources"].items():
                        if key in node:
                            node[key] = value

        if "notifications" in config:
            for node in workflow.get("nodes", []):
                if node.get("type") == "action":
                    for key, value in config["notifications"].items():
                        if key in node:
                            node[key] = value

        if "overrides" in config:
            for override in config["overrides"]:
                node_id = override.get("node_id")
                for node in workflow.get("nodes", []):
                    if node["id"] == node_id:
                        for key, value in override.items():
                            if key != "node_id":
                                node[key] = value

        return workflow

    def save_as_template(self, workflow: dict, category: str = "custom") -> str:
        template_id = f"tpl_{uuid.uuid4().hex[:12]}"
        template = {
            "id": template_id,
            "name": workflow.get("name", "Untitled Template"),
            "description": workflow.get("description", ""),
            "category": category,
            "version": "1.0",
            "tags": ["custom"],
            "workflow": copy.deepcopy(workflow),
            "created_at": datetime.utcnow().isoformat(),
        }
        self._custom_templates[template_id] = template
        return template_id

    def delete_template(self, template_id: str) -> bool:
        if template_id in self._custom_templates:
            del self._custom_templates[template_id]
            return True
        return False
