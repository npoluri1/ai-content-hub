from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # === General ===
    APP_NAME: str = "AI Content Hub"
    DATA_DIR: str = "./data"
    LOG_LEVEL: str = "INFO"

    # === Sources ===
    SOURCES_ENABLED: str = "linkedin,reddit,techcrunch,techgig,arxiv,youtube,hackernews,medium,rss,newsapi,devto"

    # === LinkedIn ===
    LINKEDIN_EMAIL: str = ""
    LINKEDIN_PASSWORD: str = ""
    LINKEDIN_PROXYCURL_API_KEY: str = ""
    LINKEDIN_SCRAPE_INTERVAL_MINUTES: int = 360

    # === Reddit ===
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "AI-Content-Hub/1.0"
    REDDIT_SCRAPE_INTERVAL_MINUTES: int = 60
    REDDIT_SUBREDDITS: str = "artificial,artificialintelligence,MachineLearning,LangChain,LocalLLaMA,Rag,vectordatabase"

    # === TechCrunch ===
    TECHCRUNCH_SCRAPE_INTERVAL_MINUTES: int = 120

    # === TechGig ===
    TECHGIG_SCRAPE_INTERVAL_MINUTES: int = 360

    # === ArXiv ===
    ARXIV_SCRAPE_INTERVAL_MINUTES: int = 180
    ARXIV_CATEGORIES: str = "cs.AI,cs.LG,cs.CL,cs.CV,cs.RO,cs.IR"

    # === YouTube ===
    YOUTUBE_API_KEY: str = ""
    YOUTUBE_SCRAPE_INTERVAL_MINUTES: int = 120
    YOUTUBE_CHANNELS: str = "UCsBjURrPoezykLs9EqgamOA,UC0rRQ3pGgF3NQ0JhIQiv4tg,UC_Wz6HwE1tLtFz4oVHq0sZg"

    # === Hacker News ===
    HN_SCRAPE_INTERVAL_MINUTES: int = 30

    # === Medium ===
    MEDIUM_SCRAPE_INTERVAL_MINUTES: int = 180
    MEDIUM_TAGS: str = "artificial-intelligence,machine-learning,deep-learning,llm,agent,langchain"

    # === RSS ===
    RSS_SCRAPE_INTERVAL_MINUTES: int = 120
    RSS_FEED_URLS: str = "https://feeds.feedburner.com/TheAIDaily,https://a16z.com/feed,https://news.ycombinator.com/rss,https://blog.google/technology/ai/rss"

    # === NewsAPI ===
    NEWSAPI_API_KEY: str = ""
    NEWSAPI_SCRAPE_INTERVAL_MINUTES: int = 120
    NEWSAPI_QUERIES: str = "artificial intelligence,AI agents,deep learning,LLM"

    # === dev.to ===
    DEVTO_SCRAPE_INTERVAL_MINUTES: int = 120
    DEVTO_TAGS: str = "ai,machinelearning,deeplearning,llm,agents,python"

    # === Pipeline ===
    LLM_PROVIDER: str = "none"  # none, openai, anthropic, ollama
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    CLASSIFICATION_METHOD: str = "hybrid"  # keyword, llm, hybrid
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # === Storage ===
    CHROMA_DB_PATH: str = "./data/chroma_db"
    SQL_DB_PATH: str = "./data/content_hub.db"

    # === API ===
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8501"

    # === Digest ===
    DIGEST_INTERVAL_MINUTES: int = 360
    DIGEST_FORMAT: str = "markdown"
    DIGEST_TOPICS: str = "AI,AgenticAI,AI_Frameworks,Quantum_Computing,Robotics,RAG,MCP,LLM_Ops"
    DIGEST_SLACK_WEBHOOK: str = ""
    DIGEST_DISCORD_WEBHOOK: str = ""
    DIGEST_MAX_PER_TOPIC: int = 10

    # === Dashboard Auth ===
    DASHBOARD_USERNAME: str = "admin"
    DASHBOARD_PASSWORD: str = "admin123"

    # === AI Features ===
    SUMMARIZER_DEFAULT_LENGTH: str = "normal"  # brief, normal, detailed
    RECOMMENDER_DEFAULT_N: int = 5
    RAG_MAX_CONTEXT: int = 5
    RAG_SYSTEM_PROMPT: str = "You are an AI assistant answering questions based on scraped content. Answer concisely using only the provided context."

    # === Notifications ===
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    EMAIL_FROM: str = "ai-content-hub@localhost"
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    WEBHOOK_CONFIG_PATH: str = "./data/webhooks.json"

    # === Auth ===
    JWT_SECRET_KEY: str = "change-this-to-a-random-secret-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_TOKEN_EXPIRY_HOURS: int = 24
    AUTH_DB_PATH: str = "./data/auth.db"
    API_RATE_LIMIT_PER_MINUTE: int = 100

    # === Processing ===
    FULLTEXT_EXTRACT_TIMEOUT: int = 30
    DEDUP_SIMILARITY_THRESHOLD: float = 0.85
    RATE_LIMIT_DEFAULT_RPM: int = 10

    # === Enterprise Integrations ===
    SLACK_BOT_TOKEN: str = ""
    SLACK_SIGNING_SECRET: str = ""
    JIRA_BASE_URL: str = ""
    JIRA_EMAIL: str = ""
    JIRA_API_TOKEN: str = ""
    JIRA_PROJECT_KEY: str = ""
    TEAMS_WEBHOOK_URL: str = ""
    GOOGLE_DRIVE_CREDS_PATH: str = ""
    NOTION_API_KEY: str = ""
    NOTION_DATABASE_ID: str = ""

    # === Compliance ===
    AUDIT_DB_PATH: str = "./data/audit.db"
    RETENTION_DB_PATH: str = "./data/retention.db"
    MODERATION_TERMS_PATH: str = "./data/moderation_terms.json"
    DEFAULT_RETENTION_DAYS: int = 90
    PII_REDACTION_ENABLED: bool = True
    CONTENT_MODERATION_ENABLED: bool = True

    # === Collaboration ===
    WORKSPACES_DB_PATH: str = "./data/workspaces.db"
    COMMENTS_DB_PATH: str = "./data/comments.db"
    APPROVALS_DB_PATH: str = "./data/approvals.db"

    # === Monitoring ===
    ALERTS_DB_PATH: str = "./data/alerts.db"
    COMPETITOR_DB_PATH: str = "./data/competitors.db"
    ANOMALY_ALERT_THRESHOLD: float = 2.0

    # === Workflow ===
    WORKFLOWS_DB_PATH: str = "./data/workflows.db"
    WORKFLOW_TIMEOUT_SECONDS: int = 300

    # === Search ===
    SEARCH_ANALYTICS_DB_PATH: str = "./data/search_analytics.db"
    SAVED_SEARCHES_DB_PATH: str = "./data/saved_searches.db"
    SEARCH_PAGE_SIZE_DEFAULT: int = 20


settings = Settings()
