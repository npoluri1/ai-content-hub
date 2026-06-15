"""AI Content Hub — Streamlit Dashboard

Run with:  streamlit run pipeline/dashboard/app.py
"""

import sys
import io
import os
import time
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from pipeline.core.config import settings
from pipeline.core.models import ContentItem
from pipeline.pipeline.orchestrator import ContentOrchestrator
from pipeline.storage.vector_store import VectorStore
from pipeline.storage.sql_store import SQLStore
from pipeline.ai.summarizer import summarize, batch_summarize, _summarize_with_length
from pipeline.ai.recommender import recommend_similar, recommend_for_query, recommend_by_topic, get_personalized_feed
from pipeline.ai.rag_chat import ChatEngine
from pipeline.ai.tagger import auto_tag, extract_entities, tag_items
from pipeline.analytics.trends import TrendAnalyzer
from pipeline.analytics.wordcloud import generate_wordcloud, get_frequency_table, get_topic_keywords, source_keywords
from pipeline.analytics.exporter import export_to_csv, export_to_json, export_to_markdown, export_source_report, export_topic_report
from pipeline.notifications.email_sender import NewsletterSender
from pipeline.notifications.telegram_bot import TelegramNotifier
from pipeline.notifications.webhooks import WebhookDispatcher
from pipeline.processing.fulltext import FullTextExtractor
from pipeline.processing.dedup import Deduplicator
from pipeline.auth.jwt_auth import JWTAuth
from pipeline.search.faceted_search import FacetedSearch
from pipeline.search.saved_searches import SavedSearch
from pipeline.search.search_analytics import SearchAnalytics
from pipeline.mlops.sentiment import SentimentAnalyzer
from pipeline.mlops.quality_score import QualityScorer
from pipeline.mlops.language_detect import LanguageDetector
from pipeline.mlops.enrichment import EnrichmentPipeline
from pipeline.enterprise.integrations.slack_bot import SlackBot
from pipeline.enterprise.integrations.jira_integration import JiraIntegration
from pipeline.enterprise.integrations.teams_integration import TeamsIntegration
from pipeline.enterprise.integrations.notion_enhanced import NotionEnhanced
from pipeline.enterprise.compliance.pii_detector import PIIDetector
from pipeline.enterprise.compliance.audit_log import AuditLogger
from pipeline.enterprise.compliance.data_retention import DataRetention
from pipeline.enterprise.compliance.content_moderation import ContentModerator
from pipeline.enterprise.collaboration.workspaces import WorkspaceManager
from pipeline.enterprise.collaboration.comments import CommentSystem
from pipeline.enterprise.collaboration.approval import ApprovalWorkflow
from pipeline.enterprise.monitoring.alerts import AlertEngine, ContentItem as AlertContentItem
from pipeline.enterprise.monitoring.competitor_tracker import CompetitorTracker
from pipeline.enterprise.monitoring.anomaly_detection import AnomalyDetector
from pipeline.workflow.builder import WorkflowBuilder
from pipeline.workflow.engine import WorkflowEngine
from pipeline.workflow.storage import WorkflowStorage

# ── Theme System ──────────────────────────────────────────────
THEMES = {
    "Ocean Blue": {
        "primary": "#1e88e5", "bg": "#0a1628", "card": "#0f1f3d",
        "text": "#e0e8f0", "accent": "#42a5f5", "border": "#1a3a5c",
        "success": "#4caf50", "warning": "#ff9800", "danger": "#f44336",
    },
    "Emerald Green": {
        "primary": "#2e7d32", "bg": "#0a1a0a", "card": "#0f2610",
        "text": "#e0f0e0", "accent": "#66bb6a", "border": "#1a3a1a",
        "success": "#4caf50", "warning": "#ff9800", "danger": "#f44336",
    },
    "Royal Purple": {
        "primary": "#7b1fa2", "bg": "#1a0a2e", "card": "#261040",
        "text": "#e8e0f0", "accent": "#ab47bc", "border": "#3a1a5c",
        "success": "#4caf50", "warning": "#ff9800", "danger": "#f44336",
    },
    "Sunset Orange": {
        "primary": "#e65100", "bg": "#1a0e08", "card": "#2a160a",
        "text": "#f0e8e0", "accent": "#ff7043", "border": "#4a2810",
        "success": "#4caf50", "warning": "#ff9800", "danger": "#f44336",
    },
    "Rose Pink": {
        "primary": "#c2185b", "bg": "#1a0812", "card": "#2a0e1a",
        "text": "#f0e0e8", "accent": "#ec407a", "border": "#4a1828",
        "success": "#4caf50", "warning": "#ff9800", "danger": "#f44336",
    },
    "Slate Gray": {
        "primary": "#546e7a", "bg": "#0e1117", "card": "#141820",
        "text": "#e0e4e8", "accent": "#78909c", "border": "#222a32",
        "success": "#4caf50", "warning": "#ff9800", "danger": "#f44336",
    },
    "Teal Cyan": {
        "primary": "#00897b", "bg": "#081a18", "card": "#0c2622",
        "text": "#e0f0ee", "accent": "#26a69a", "border": "#14403a",
        "success": "#4caf50", "warning": "#ff9800", "danger": "#f44336",
    },
    "Amber Glow": {
        "primary": "#ff8f00", "bg": "#1a1408", "card": "#2a2008",
        "text": "#f0ece0", "accent": "#ffa726", "border": "#4a3a10",
        "success": "#4caf50", "warning": "#ff9800", "danger": "#f44336",
    },
    "Indigo Storm": {
        "primary": "#283593", "bg": "#080e20", "card": "#0e1635",
        "text": "#e0e4f0", "accent": "#5c6bc0", "border": "#182848",
        "success": "#4caf50", "warning": "#ff9800", "danger": "#f44336",
    },
    "Crimson Red": {
        "primary": "#c62828", "bg": "#1a0808", "card": "#2a0c0c",
        "text": "#f0e0e0", "accent": "#ef5350", "border": "#4a1414",
        "success": "#4caf50", "warning": "#ff9800", "danger": "#f44336",
    },
}

THEME_LIST = list(THEMES.keys())

if "theme_name" not in st.session_state:
    st.session_state.theme_name = "Ocean Blue"

def _inject_theme():
    t = THEMES[st.session_state.theme_name]
    st.markdown(f"""
<style>
    #root > div {{ background: {t['bg']}; color: {t['text']}; }}
    .stApp {{ background: {t['bg']} !important; color: {t['text']} !important; }}
    .stApp > header {{ background: {t['card']} !important; }}
    .stSidebar {{ background: {t['card']} !important; }}
    .stSidebar .sidebar-content {{ background: {t['card']} !important; }}
    section[data-testid="stSidebar"] {{ background: {t['card']} !important; }}
    section[data-testid="stSidebar"] * {{ color: {t['text']} !important; }}
    .stMarkdown, .stText, .stCaption, p, h1, h2, h3, h4, h5, h6, label, span {{ color: {t['text']} !important; }}
    h1, h2, h3 {{ color: {t['accent']} !important; }}
    .stButton > button {{ background: {t['primary']} !important; color: white !important; border: none !important; border-radius: 8px !important; font-weight: 600 !important; padding: 8px 24px !important; transition: all 0.2s !important; }}
    .stButton > button:hover {{ filter: brightness(1.15) !important; transform: translateY(-1px) !important; box-shadow: 0 4px 12px {t['primary']}40 !important; }}
    .stButton > button[kind="secondary"] {{ background: transparent !important; border: 1.5px solid {t['primary']} !important; color: {t['accent']} !important; }}
    .stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div, .stMultiselect > div > div {{ background: {t['card']} !important; color: {t['text']} !important; border: 1px solid {t['border']} !important; border-radius: 8px !important; }}
    .stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus {{ border-color: {t['primary']} !important; box-shadow: 0 0 0 2px {t['primary']}20 !important; }}
    .stDataFrame {{ background: {t['card']} !important; }}
    .stDataFrame th {{ background: {t['primary']}22 !important; color: {t['accent']} !important; }}
    .stDataFrame td {{ background: {t['card']} !important; color: {t['text']} !important; }}
    .stTabs [data-baseweb="tab-list"] {{ background: {t['card']} !important; border-radius: 10px !important; padding: 4px !important; }}
    .stTabs [data-baseweb="tab"] {{ color: {t['text']}80 !important; }}
    .stTabs [aria-selected="true"] {{ background: {t['primary']} !important; color: white !important; border-radius: 8px !important; }}
    .stMetric {{ background: {t['card']} !important; border: 1px solid {t['border']} !important; border-radius: 12px !important; padding: 16px !important; }}
    .stMetric label {{ color: {t['text']}80 !important; }}
    .stMetric [data-testid="stMetricValue"] {{ color: {t['accent']} !important; font-size: 28px !important; }}
    .stExpander {{ background: {t['card']} !important; border: 1px solid {t['border']} !important; border-radius: 12px !important; margin: 8px 0 !important; }}
    .stExpander summary {{ color: {t['accent']} !important; font-weight: 600 !important; }}
    .stProgress > div > div > div {{ background: {t['primary']} !important; }}
    .stAlert {{ background: {t['card']} !important; border: 1px solid {t['border']} !important; color: {t['text']} !important; }}
    .stInfo {{ background: {t['primary']}15 !important; border: 1px solid {t['primary']}30 !important; color: {t['accent']} !important; }}
    .stSuccess {{ background: {t['success']}15 !important; border: 1px solid {t['success']}30 !important; }}
    .stWarning {{ background: {t['warning']}15 !important; border: 1px solid {t['warning']}30 !important; }}
    .stError {{ background: {t['danger']}15 !important; border: 1px solid {t['danger']}30 !important; }}
    .stSpinner > div {{ border-color: {t['primary']} !important; }}
    hr {{ border-color: {t['border']} !important; }}
    a {{ color: {t['accent']} !important; }}
    a:hover {{ color: {t['primary']} !important; text-decoration: underline !important; }}
    .stSelectbox [data-baseweb="select"] {{ background: {t['card']} !important; border: 1px solid {t['border']} !important; }}
    .stMultiSelect [data-baseweb="tag"] {{ background: {t['primary']}22 !important; color: {t['accent']} !important; }}
    div[data-testid="stMetric"] {{ background: linear-gradient(135deg, {t['card']}, {t['card']}dd) !important; border: 1px solid {t['border']} !important; border-radius: 12px !important; padding: 16px !important; }}
    .st-emotion-cache-16idsys p {{ font-size: 14px !important; }}
    .item-card {{ background: {t['card']} !important; border: 1px solid {t['border']} !important; border-radius: 12px !important; padding: 20px !important; margin: 8px 0 !important; transition: all 0.2s !important; }}
    .item-card:hover {{ border-color: {t['primary']} !important; transform: translateY(-2px) !important; box-shadow: 0 8px 24px {t['primary']}20 !important; }}
    .badge {{ display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; }}
    .source-badge {{ background: {t['primary']}22; color: {t['accent']}; }}
    .topic-badge {{ background: {t['success']}22; color: {t['success']}; }}
    .score-badge {{ background: {t['warning']}22; color: {t['warning']}; }}
    .stTabs [data-baseweb="tab-list"] button {{ background: transparent !important; }}
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{ background: {t['primary']} !important; }}
    .view-btn {{ background: {t['primary']} !important; color: white !important; border: none; border-radius: 6px; padding: 4px 12px; font-size: 12px; cursor: pointer; }}
    div.row-widget.stRadio > div {{ flex-direction: row !important; }}
    div.row-widget.stRadio > div label {{ background: {t['card']} !important; border: 1px solid {t['border']} !important; border-radius: 8px !important; padding: 8px 16px !important; margin: 2px !important; }}
    div.row-widget.stRadio > div label[data-baseweb="radio"] {{ background: {t['primary']} !important; border-color: {t['primary']} !important; }}
</style>
""", unsafe_allow_html=True)

st.set_page_config(
    page_title="AI Content Hub",
    page_icon=":robot_face:",
    layout="wide",
    initial_sidebar_state="expanded",
)

_inject_theme()

@st.cache_resource
def _get_orchestrator():
    return ContentOrchestrator()

@st.cache_resource
def _get_sql_store():
    return SQLStore()

@st.cache_resource
def _get_vector_store():
    return VectorStore()

@st.cache_resource
def _get_chat_engine():
    return ChatEngine()

@st.cache_resource
def _get_trend_analyzer():
    return TrendAnalyzer()

@st.cache_resource
def _get_fulltext_extractor():
    return FullTextExtractor()

@st.cache_resource
def _get_deduplicator():
    return Deduplicator()

@st.cache_resource
def _get_jwt_auth():
    return JWTAuth()

@st.cache_resource
def _get_webhook_dispatcher():
    d = WebhookDispatcher()
    d.load_from_config()
    return d

@st.cache_resource
def _get_faceted_search():
    fs = FacetedSearch()
    return fs

@st.cache_resource
def _get_saved_search():
    return SavedSearch()

@st.cache_resource
def _get_search_analytics():
    return SearchAnalytics()

@st.cache_resource
def _get_sentiment_analyzer():
    return SentimentAnalyzer()

@st.cache_resource
def _get_quality_scorer():
    return QualityScorer()

@st.cache_resource
def _get_language_detector():
    return LanguageDetector()

@st.cache_resource
def _get_enrichment_pipeline():
    return EnrichmentPipeline()

@st.cache_resource
def _get_slack_bot():
    return SlackBot()

@st.cache_resource
def _get_jira_integration():
    return JiraIntegration()

@st.cache_resource
def _get_teams_integration():
    return TeamsIntegration()

@st.cache_resource
def _get_notion_enhanced():
    return NotionEnhanced()

@st.cache_resource
def _get_pii_detector():
    return PIIDetector()

@st.cache_resource
def _get_audit_logger():
    return AuditLogger()

@st.cache_resource
def _get_data_retention():
    return DataRetention(sql_store=SQLStore())

@st.cache_resource
def _get_content_moderator():
    return ContentModerator()

@st.cache_resource
def _get_workspace_manager():
    return WorkspaceManager()

@st.cache_resource
def _get_comment_system():
    return CommentSystem()

@st.cache_resource
def _get_approval_workflow():
    return ApprovalWorkflow()

@st.cache_resource
def _get_alert_engine():
    return AlertEngine()

@st.cache_resource
def _get_competitor_tracker():
    return CompetitorTracker()

@st.cache_resource
def _get_anomaly_detector():
    return AnomalyDetector()

@st.cache_resource
def _get_workflow_storage():
    return WorkflowStorage()

ORCH = _get_orchestrator()
SQL = _get_sql_store()
VS = _get_vector_store()
CHAT = _get_chat_engine()
TRENDS = _get_trend_analyzer()
FULLTEXT = _get_fulltext_extractor()
DEDUP = _get_deduplicator()
AUTH = _get_jwt_auth()
WEBHOOKS = _get_webhook_dispatcher()
FACETED = _get_faceted_search()
SAVED = _get_saved_search()
SEARCH_ANALYTICS = _get_search_analytics()
SENTIMENT = _get_sentiment_analyzer()
QUALITY = _get_quality_scorer()
LANG = _get_language_detector()
ENRICH = _get_enrichment_pipeline()
SLACK = _get_slack_bot()
JIRA = _get_jira_integration()
TEAMS = _get_teams_integration()
NOTION = _get_notion_enhanced()
PII = _get_pii_detector()
AUDIT = _get_audit_logger()
RETENTION = _get_data_retention()
MODERATOR = _get_content_moderator()
WORKSPACE = _get_workspace_manager()
COMMENTS = _get_comment_system()
APPROVAL = _get_approval_workflow()
ALERTS = _get_alert_engine()
COMPETITOR = _get_competitor_tracker()
ANOMALY = _get_anomaly_detector()
WF_STORAGE = _get_workflow_storage()
WF_ENGINE = WorkflowEngine(store=WF_STORAGE)

SOURCES = sorted((
    "linkedin", "reddit", "techcrunch", "techgig", "arxiv",
    "youtube", "hackernews", "medium", "rss", "newsapi", "devto", "demo",
))

TOPICS = [
    "AI", "AgenticAI", "AI_Frameworks", "Quantum_Computing",
    "Robotics", "RAG", "MCP", "LLM_Ops",
]

def _db_conn():
    conn = sqlite3.connect(settings.SQL_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _get_source_status() -> dict:
    try:
        conn = _db_conn()
        rows = conn.execute(
            "SELECT name, last_crawl_at, items_count, status FROM sources"
        ).fetchall()
        conn.close()
        return {
            r["name"]: {
                "last_crawl_at": r["last_crawl_at"],
                "items_count": r["items_count"],
                "status": r["status"],
            }
            for r in rows
        }
    except Exception:
        return {}

def _get_all_items(limit: int = 50) -> list[dict]:
    try:
        conn = _db_conn()
        rows = conn.execute("""
            SELECT id, title, content_cleaned, url, source, topics,
                   author_name, published_at, crawled_at, engagement,
                   relevance_score
            FROM items
            ORDER BY crawled_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []

def _get_all_items_full(limit: int = 50) -> list[dict]:
    try:
        conn = _db_conn()
        rows = conn.execute("""
            SELECT id, title, content_cleaned, content, url, source, topics,
                   author_name, published_at, crawled_at, engagement,
                   relevance_score, source_type, hashtags, image_urls, video_url
            FROM items
            ORDER BY crawled_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []

def _get_item_by_id(item_id: str) -> dict:
    try:
        conn = _db_conn()
        row = conn.execute(
            "SELECT id, title, content_cleaned, content, url, source, topics, "
            "author_name, published_at, crawled_at, engagement, relevance_score "
            "FROM items WHERE id = ?", (item_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else {}
    except Exception:
        return {}

def _mask(val: str) -> str:
    s = str(val)
    if not s:
        return ""
    if len(s) <= 4:
        return "****"
    return s[:2] + "****" + s[-2:]

def _topic_distribution() -> dict[str, int]:
    topic_counts: dict[str, int] = {}
    try:
        conn = _db_conn()
        rows = conn.execute(
            "SELECT topics FROM items WHERE topics != ''"
        ).fetchall()
        conn.close()
        for r in rows:
            for t in str(r["topics"]).split(","):
                t = t.strip()
                if t:
                    topic_counts[t] = topic_counts.get(t, 0) + 1
    except Exception:
        pass
    return topic_counts

def _try_scrape_source(source: str) -> int:
    items = ORCH.run_source(source)
    count = len(items)
    try:
        conn = _db_conn()
        conn.execute(
            "INSERT OR REPLACE INTO sources "
            "(name, last_crawl_at, items_count, status) "
            "VALUES (?, ?, ?, ?)",
            (source, datetime.now().isoformat(), count, "success"),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass
    return count

PAGES = [
    "Dashboard", "Search", "Sources", "Topics",
    "Digest", "Schedule", "Analytics",
    "AI Lab", "RAG Chat",
    "Enterprise Search", "MLOps Lab", "Integrations",
    "Compliance", "Collaboration", "Monitoring & Alerts",
    "Workflow Builder",
    "Settings", "Notifications", "Processing",
]

st.sidebar.title("AI Content Hub")
st.sidebar.markdown("---")

st.sidebar.markdown("**Core**")
_pages_core = ["Dashboard", "Search", "Sources", "Topics"]
st.sidebar.markdown("**Content**")
_pages_content = ["Digest", "Schedule", "Analytics"]
st.sidebar.markdown("**AI**")
_pages_ai = ["AI Lab", "RAG Chat"]
st.sidebar.markdown("**Enterprise**")
_pages_ent = ["Enterprise Search", "MLOps Lab", "Integrations", "Compliance", "Collaboration", "Monitoring & Alerts", "Workflow Builder"]
st.sidebar.markdown("**System**")
_pages_sys = ["Settings", "Notifications", "Processing"]

page = st.sidebar.radio("Navigate", PAGES, label_visibility="collapsed")

st.sidebar.markdown("---")
try:
    total = SQL.count()
    st.sidebar.metric("Total Items", total)
except Exception:
    st.sidebar.metric("Total Items", "?")

if st.sidebar.button(":arrows_counterclockwise: Refresh"):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("**Theme**")
prev_theme = st.session_state.theme_name
selected_theme = st.sidebar.selectbox(
    "Color Theme", THEME_LIST, index=THEME_LIST.index(prev_theme),
    label_visibility="collapsed",
)
if selected_theme != prev_theme:
    st.session_state.theme_name = selected_theme
    _inject_theme()
    st.rerun()

def _render_item_card(item: dict, key_prefix: str = "item"):
    """Render a clickable item card with expander detail view."""
    title = item.get("title") or "(untitled)"
    source = item.get("source", "?")
    topics_raw = item.get("topics", "")
    topics = [t.strip() for t in str(topics_raw).split(",") if t.strip()]
    engagement = item.get("engagement", 0) or 0
    score = item.get("relevance_score", 0) or 0
    content = item.get("content_cleaned") or item.get("content") or ""
    item_id = item.get("id", "")

    badge_html = f"<span class='badge source-badge'>{source}</span>"
    if topics:
        badge_html += " " + " ".join(f"<span class='badge topic-badge'>{t}</span>" for t in topics[:3])
    badge_html += f" <span class='badge score-badge'>Score: {score:.2f}</span>"
    if engagement:
        badge_html += f" <span class='badge' style='background:#e91e6322;color:#e91e63;'>❤️ {engagement}</span>"

    st.markdown(
        f"<div class='item-card'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
        f"<div style='flex:1;'><strong style='font-size:16px;'>{title[:80]}</strong></div>"
        f"<div style='font-size:11px;color:#888;white-space:nowrap;margin-left:12px;'>{badge_html}</div>"
        f"</div>"
        f"<div style='margin-top:4px;font-size:13px;color:#999;'>{content[:150].strip().replace(chr(10), ' ')}...</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    with st.expander("View Details"):
        col_a, col_b = st.columns([3, 1])
        col_a.markdown(f"**{title}**")
        col_b.markdown(f"`{source}`")
        if topics:
            col_a.markdown(" ".join(f"`{t}`" for t in topics))
        st.markdown("---")
        st.markdown(content[:2000] if content else "*No content*")

        meta_cols = st.columns(4)
        meta_cols[0].metric("Relevance", f"{score:.2f}")
        meta_cols[1].metric("Engagement", engagement)
        if item.get("author_name"):
            meta_cols[2].markdown(f"**Author:** {item['author_name']}")
        if item.get("published_at"):
            meta_cols[3].markdown(f"**Published:** {str(item['published_at'])[:10]}")
        if item.get("url"):
            st.markdown(f":link: [Open Original]({item['url']})")

    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

def _page_dashboard():
    st.title("Dashboard")
    stats = SQL.get_stats()
    src_status = _get_source_status()

    total_items = stats.get("total", 0)
    active_srcs = len(stats.get("by_source", {}))
    topic_dist = _topic_distribution()
    topics_covered = len(topic_dist)

    last_ts = "Never"
    for info in src_status.values():
        if info.get("last_crawl_at") and (
            last_ts == "Never" or info["last_crawl_at"] > last_ts
        ):
            last_ts = info["last_crawl_at"]

    cols = st.columns(4)
    with cols[0]:
        st.metric("Total Items", total_items)
    with cols[1]:
        st.metric("Active Sources", active_srcs)
    with cols[2]:
        st.metric("Topics Covered", topics_covered)
    with cols[3]:
        label = last_ts
        if last_ts != "Never" and "T" in last_ts:
            label = last_ts[:19]
        st.metric("Last Crawl", label)

    st.subheader("Charts")
    chart_cols = st.columns(2)

    with chart_cols[0]:
        st.markdown("**Topic Distribution**")
        if topic_dist:
            df = pd.DataFrame(
                sorted(topic_dist.items(), key=lambda x: -x[1]),
                columns=["Topic", "Count"],
            ).head(8)
            st.bar_chart(df.set_index("Topic"), height=200)
        else:
            st.info("No topics yet.")

    with chart_cols[1]:
        st.markdown("**Source Distribution**")
        by_source = stats.get("by_source", {})
        if by_source:
            df_src = pd.DataFrame(
                sorted(by_source.items(), key=lambda x: -x[1]),
                columns=["Source", "Count"],
            ).head(8)
            st.bar_chart(df_src.set_index("Source"), height=200)
        else:
            st.info("No sources yet.")

    st.subheader("Recent Items")
    recent = _get_all_items(20)
    if recent:
        for i, item in enumerate(recent):
            _render_item_card(item, key_prefix=f"dash_{i}")
    else:
        st.info("No items yet. Go to **Sources** and run a scrape.")

    st.subheader("Source Health")
    rows = []
    for src in SOURCES:
        info = src_status.get(src, {})
        rows.append({
            "Source": src,
            "Status": info.get("status", "unknown"),
            "Last Crawl": (info.get("last_crawl_at", "") or "")[:19] or "Never",
            "Items": info.get("items_count", 0),
        })
    if rows:
        df_health = pd.DataFrame(rows)
        st.dataframe(df_health, width='stretch', hide_index=True, column_config={
            "Status": st.column_config.TextColumn("Status", help="Source health"),
            "Items": st.column_config.NumberColumn("Items", format="%d"),
        })

def _page_search():
    st.title("Search Content")

    c1, c2 = st.columns([3, 1])
    query = c1.text_input("Query", placeholder="e.g. RAG, agent, MCP, quantum...")
    src_filter = c2.selectbox("Source", ["All"] + SOURCES)

    if not query:
        st.info("Enter a query above to search across all content.")
        return

    with st.spinner("Searching..."):
        try:
            kwargs = {"n_results": 50}
            if src_filter != "All":
                kwargs["filter_source"] = src_filter
            results = VS.search(query, **kwargs)
        except Exception as exc:
            st.error(f"Search failed: {exc}")
            return

    if not results:
        st.warning("No results found.")
        return

    st.success(f"Found **{len(results)}** result(s)")

    for i, r in enumerate(results):
        meta = r.get("metadata") or {}
        item = {
            "id": meta.get("id", ""),
            "title": meta.get("title", "(untitled)"),
            "content": r.get("content") or meta.get("content_cleaned") or "",
            "source": meta.get("source", "?"),
            "topics": meta.get("topics", ""),
            "engagement": 0,
            "relevance_score": r.get("distance", 0),
            "url": meta.get("url", ""),
            "author_name": meta.get("author_name", ""),
            "published_at": meta.get("published_at", ""),
        }
        _render_item_card(item, key_prefix=f"search_{i}")

def _page_sources():
    st.title("Source Management")
    src_status = _get_source_status()

    if st.button("Scrape All Sources", type="primary"):
        with st.spinner("Running full pipeline across all sources..."):
            try:
                results = ORCH.run_all()
                st.success(f"Pipeline complete. {results}")
                st.rerun()
            except Exception as exc:
                st.error(f"Pipeline error: {exc}")

    st.divider()

    for src in SOURCES:
        info = src_status.get(src, {})
        max_count = max((s.get("items_count", 0) for s in src_status.values()), default=1)

        st.markdown(
            f"<div class='item-card'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<div><strong>{src}</strong> "
            f"<span class='badge source-badge'>{info.get('status', 'idle')}</span></div>"
            f"<div style='display:flex;gap:8px;align-items:center;'>"
            f"<span style='font-size:13px;color:#999;'>Items: {info.get('items_count', 0)}</span>"
            f"<span style='font-size:12px;color:#777;'>{((info.get('last_crawl_at') or '')[:19] or 'Never')}</span>"
            f"</div></div>"
            f"<div style='margin-top:8px;'>",
            unsafe_allow_html=True,
        )

        progress_val = info.get("items_count", 0) / max_count if max_count else 0
        st.progress(min(progress_val, 1.0), text=f"{info.get('items_count', 0)} items")

        scrape_col, view_col = st.columns([1, 1])
        if scrape_col.button("Scrape Now", key=f"scrape_{src}", use_container_width=True):
            with st.spinner(f"Scraping {src}..."):
                try:
                    count = _try_scrape_source(src)
                    st.success(f"{src}: {count} item(s) collected")
                    st.rerun()
                except Exception as exc:
                    st.error(f"{src}: {exc}")

        if view_col.button("View Items", key=f"view_{src}", use_container_width=True):
            try:
                src_items = SQL.get_by_source(src, limit=20)
                if src_items:
                    for i, item in enumerate(src_items):
                        _render_item_card(item, key_prefix=f"src_{src}_{i}")
                else:
                    st.info(f"No items for {src}.")
            except Exception:
                st.info(f"No items for {src}.")

        st.markdown("</div>", unsafe_allow_html=True)

def _page_topics():
    st.title("Topic Browser")

    selected = st.sidebar.selectbox("Filter by topic", ["All"] + TOPICS)

    if selected == "All":
        st.subheader("All Items Grouped by Topic")
        dist = _topic_distribution()
        if dist:
            df = pd.DataFrame(
                sorted(dist.items(), key=lambda x: -x[1]),
                columns=["Topic", "Count"],
            )
            st.dataframe(df, width='stretch', hide_index=True)
        st.divider()
        items = _get_all_items(100)
        title = "All Recent Items"
    else:
        st.subheader(f"Topic: {selected}")
        try:
            items = SQL.get_by_topic(selected, limit=50)
        except Exception:
            items = []

    if not items:
        st.info(f"No items for this topic.")
        return

    for i, item in enumerate(items):
        _render_item_card(item, key_prefix=f"topic_{i}")

def _page_digest():
    st.title("Digest Viewer")

    if "digest_content" not in st.session_state:
        st.session_state.digest_content = ""

    col_gen, col_pipe = st.columns(2)

    with col_gen:
        if st.button("Generate Digest from Stored Items", type="primary"):
            with st.spinner("Building digest..."):
                try:
                    topics = [
                        t.strip()
                        for t in settings.DIGEST_TOPICS.split(",")
                        if t.strip()
                    ]
                    max_per = settings.DIGEST_MAX_PER_TOPIC
                    lines = [
                        f"# AI Content Hub Digest",
                        f"",
                        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        f"**Sources:** {settings.SOURCES_ENABLED}",
                        f"",
                    ]

                    for topic in topics:
                        topic_items = SQL.get_by_topic(topic, limit=max_per)
                        if not topic_items:
                            continue
                        lines.append(f"## {topic}")
                        for item in topic_items:
                            snippet = (
                                (item.get("content") or "")[:150]
                                .replace("\n", " ")
                            )
                            tag = f"[{item.get('source', '?').upper()}]"
                            lines.append(
                                f"- {tag} **{item['title']}** &mdash; {snippet}..."
                            )
                            if item.get("url"):
                                lines.append(f"  {item['url']}")
                        lines.append("")

                    st.session_state.digest_content = "\n".join(lines)
                    st.success("Digest generated from stored items!")
                except Exception as exc:
                    st.error(f"Digest generation failed: {exc}")

    with col_pipe:
        if st.button("Run Pipeline then Digest"):
            with st.spinner("Running full pipeline..."):
                try:
                    results = ORCH.run_all()
                    st.success(f"Pipeline complete: {results}")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Pipeline error: {exc}")

    if st.session_state.digest_content:
        st.markdown("---")
        st.markdown(st.session_state.digest_content)

        dcol1, dcol2 = st.columns(2)
        buf = io.BytesIO(
            st.session_state.digest_content.encode("utf-8")
        )
        now_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dcol1.download_button(
            ":inbox_tray: Download .md",
            data=buf,
            file_name=f"digest_{now_ts}.md",
            mime="text/markdown",
        )
        if dcol2.button(":clipboard: Copy to Clipboard"):
            st.code(st.session_state.digest_content, language="markdown")
            st.info("Select all text above and copy (Ctrl+C / Cmd+C).")
    else:
        st.info(
            "Click **Generate Digest from Stored Items** to create a digest from "
            "existing data, or **Run Pipeline then Digest** to scrape fresh data first."
        )

def _page_schedule():
    st.title("Schedule Configuration")

    if "sched_running" not in st.session_state:
        st.session_state.sched_running = False
    if "sched_interval" not in st.session_state:
        st.session_state.sched_interval = 6
    if "sched_start" not in st.session_state:
        st.session_state.sched_start = None
    if "sched_sources" not in st.session_state:
        st.session_state.sched_sources = list(SOURCES)

    st.subheader("Run Interval")
    interval = st.number_input(
        "Run every N hours",
        min_value=1,
        max_value=72,
        value=st.session_state.sched_interval,
    )
    st.session_state.sched_interval = interval

    st.subheader("Sources to Include")
    selected = []
    for src in SOURCES:
        checked = st.checkbox(
            src,
            value=src in st.session_state.sched_sources,
            key=f"sched_{src}",
        )
        if checked:
            selected.append(src)
    st.session_state.sched_sources = selected
    st.caption(f"{len(selected)} / {len(SOURCES)} sources selected")

    c1, c2 = st.columns(2)
    if not st.session_state.sched_running:
        if c1.button("Start Scheduler", type="primary"):
            st.session_state.sched_running = True
            st.session_state.sched_start = datetime.now()
            st.success(f"Scheduler started &mdash; every {interval}h")
            st.rerun()
    else:
        if c1.button("Stop Scheduler"):
            st.session_state.sched_running = False
            st.session_state.sched_start = None
            st.warning("Scheduler stopped")
            st.rerun()

    if st.session_state.sched_running and st.session_state.sched_start:
        elapsed_h = (
            datetime.now() - st.session_state.sched_start
        ).total_seconds() / 3600
        remaining_h = max(0.0, st.session_state.sched_interval - elapsed_h)
        frac = min(elapsed_h / st.session_state.sched_interval, 1.0)

        st.metric("Next run in", f"{remaining_h:.1f}h")
        st.progress(frac)
    elif st.session_state.sched_running:
        st.info("Scheduler is running (start time not recorded).")

    st.divider()
    st.subheader("Manual Trigger")
    if st.button("Run Pipeline Now"):
        sources = (
            st.session_state.sched_sources
            if st.session_state.sched_sources
            else None
        )
        with st.spinner("Running pipeline..."):
            try:
                results = ORCH.run_all(sources=sources)
                st.success(f"Pipeline results: {results}")
            except Exception as exc:
                st.error(f"Pipeline error: {exc}")

def _page_settings():
    st.title("Settings")

    st.subheader("Environment Variables")
    env_rows = [
        ("APP_NAME", settings.APP_NAME),
        ("DATA_DIR", settings.DATA_DIR),
        ("LOG_LEVEL", settings.LOG_LEVEL),
        ("SOURCES_ENABLED", settings.SOURCES_ENABLED),
        ("LLM_PROVIDER", settings.LLM_PROVIDER),
        ("CLASSIFICATION_METHOD", settings.CLASSIFICATION_METHOD),
        ("EMBEDDING_MODEL", settings.EMBEDDING_MODEL),
        ("SQL_DB_PATH", settings.SQL_DB_PATH),
        ("CHROMA_DB_PATH", settings.CHROMA_DB_PATH),
        ("DIGEST_TOPICS", settings.DIGEST_TOPICS),
        ("DIGEST_INTERVAL_MINUTES", str(settings.DIGEST_INTERVAL_MINUTES)),
        ("DIGEST_MAX_PER_TOPIC", str(settings.DIGEST_MAX_PER_TOPIC)),
    ]
    for key, raw, secret in [
        ("OPENAI_API_KEY", settings.OPENAI_API_KEY, True),
        ("ANTHROPIC_API_KEY", settings.ANTHROPIC_API_KEY, True),
        ("NEWSAPI_API_KEY", settings.NEWSAPI_API_KEY, True),
        ("LINKEDIN_PROXYCURL_API_KEY", settings.LINKEDIN_PROXYCURL_API_KEY, True),
        ("REDDIT_CLIENT_ID", settings.REDDIT_CLIENT_ID, True),
        ("REDDIT_CLIENT_SECRET", settings.REDDIT_CLIENT_SECRET, True),
        ("YOUTUBE_API_KEY", settings.YOUTUBE_API_KEY, True),
        ("LINKEDIN_EMAIL", settings.LINKEDIN_EMAIL, False),
        ("LINKEDIN_PASSWORD", settings.LINKEDIN_PASSWORD, True),
    ]:
        val = _mask(raw) if raw and secret else (raw or "(empty)")
        env_rows.append((key, val))

    st.dataframe(
        pd.DataFrame(env_rows, columns=["Variable", "Value"]),
        width='stretch',
        hide_index=True,
    )

    st.subheader("LLM Configuration")
    providers = ["none", "openai", "anthropic", "ollama"]
    try:
        idx = providers.index(settings.LLM_PROVIDER)
    except ValueError:
        idx = 0
    st.selectbox("Provider", providers, index=idx, disabled=True)
    st.text_input(
        "OpenAI API Key",
        value=_mask(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else "",
        type="password",
        disabled=True,
    )
    st.text_input(
        "Anthropic API Key",
        value=_mask(settings.ANTHROPIC_API_KEY) if settings.ANTHROPIC_API_KEY else "",
        type="password",
        disabled=True,
    )

    st.info(
        "Edit the `.env` file in the project root to change settings, "
        "then restart the dashboard."
    )

    st.divider()
    st.subheader("System Info")
    sys_info = [
        ("Python", sys.version.split()[0]),
        ("Streamlit", st.__version__),
        ("DB Path", settings.SQL_DB_PATH),
        ("Chroma Path", settings.CHROMA_DB_PATH),
        ("Data Dir", settings.DATA_DIR),
    ]
    st.dataframe(
        pd.DataFrame(sys_info, columns=["Key", "Value"]),
        width='stretch',
        hide_index=True,
    )

def _page_ai_lab():
    st.title("AI Lab")

    tab_summarize, tab_batch, tab_recs, tab_tag = st.tabs([
        "Summarize", "Batch Summarize", "Recommendations", "Auto-Tag",
    ])

    with tab_summarize:
        st.subheader("Summarize Text")
        input_text = st.text_area(
            "Input text",
            height=200,
            placeholder="Paste content to summarize...",
        )
        length = st.select_slider(
            "Summary length",
            options=["brief", "normal", "detailed"],
            value="normal",
        )
        if st.button("Summarize", type="primary"):
            if not input_text.strip():
                st.error("Please enter text to summarize.")
            else:
                with st.spinner("Generating summary..."):
                    try:
                        result = _summarize_with_length(input_text, length)
                        st.text_area("Summary", value=result, height=150)
                        if st.button("Copy to Clipboard", key="copy_summary"):
                            st.code(result, language="text")
                            st.info("Select all and copy (Ctrl+C / Cmd+C).")
                    except Exception as exc:
                        st.error(f"Summarization failed: {exc}")

    with tab_batch:
        st.subheader("Batch Summarize Recent Items")
        recent = _get_all_items_full(30)
        if not recent:
            st.info("No items available.")
        else:
            options = {
                f"{r['id'][:8]} - {r['title'][:60]}": r
                for r in recent if r.get("content_cleaned") or r.get("content")
            }
            selected_labels = st.multiselect(
                "Select items to summarize",
                list(options.keys()),
                default=list(options.keys())[:5],
            )
            if st.button("Batch Summarize", type="primary"):
                if not selected_labels:
                    st.error("Select at least one item.")
                else:
                    with st.spinner("Summarizing..."):
                        try:
                            selected_items = [options[lab] for lab in selected_labels]
                            content_items = []
                            for r in selected_items:
                                item = ContentItem(
                                    id=r.get("id", "unknown"),
                                    title=r.get("title", ""),
                                    content=r.get("content", ""),
                                    content_cleaned=r.get("content_cleaned", ""),
                                    url=r.get("url", ""),
                                    source=r.get("source", "unknown"),
                                )
                                content_items.append(item)
                            results = batch_summarize(content_items)
                            rows = []
                            for res in results:
                                rows.append({
                                    "ID": res["id"][:12],
                                    "Title": res["title"],
                                    "Summary": res.get("summary", ""),
                                })
                            st.dataframe(
                                pd.DataFrame(rows),
                                width='stretch',
                                hide_index=True,
                            )
                            st.success(f"Summarized {len(results)} items.")
                        except Exception as exc:
                            st.error(f"Batch summarization failed: {exc}")

    with tab_recs:
        st.subheader("Recommendations")
        rec_mode = st.radio("Mode", ["By Query", "By Item ID", "By Topic"], horizontal=True)

        if rec_mode == "By Query":
            query_text = st.text_input("Search query", placeholder="e.g. RAG architecture")
            if st.button("Show Recommendations", type="primary"):
                if not query_text.strip():
                    st.error("Enter a query.")
                else:
                    with st.spinner("Finding recommendations..."):
                        try:
                            results = recommend_for_query(query_text, n=10)
                            if not results:
                                st.warning("No recommendations found.")
                            else:
                                for r in results:
                                    meta = r.get("metadata") or {}
                                    with st.container():
                                        st.markdown(f"**{meta.get('title', '(untitled)')}**")
                                        cols = st.columns(3)
                                        cols[0].markdown(f"Source: `{meta.get('source', '?')}`")
                                        cols[1].markdown(f"Topics: {meta.get('topics', 'N/A')}")
                                        cols[2].markdown(f"Score: {r.get('distance', 0):.4f}")
                                        st.caption((r.get("content") or "")[:300])
                                        st.divider()
                        except Exception as exc:
                            st.error(f"Recommendations failed: {exc}")

        elif rec_mode == "By Item ID":
            item_id = st.text_input("Item ID", placeholder="Enter content item ID")
            if st.button("Show Recommendations", type="primary"):
                if not item_id.strip():
                    st.error("Enter an item ID.")
                else:
                    with st.spinner("Finding similar items..."):
                        try:
                            row = _get_item_by_id(item_id.strip())
                            if not row:
                                st.error("Item not found.")
                            else:
                                item = ContentItem(
                                    id=row["id"],
                                    title=row["title"],
                                    content=row.get("content", ""),
                                    content_cleaned=row.get("content_cleaned", ""),
                                    url=row.get("url", ""),
                                    source=row.get("source", "unknown"),
                                )
                                results = recommend_similar(item, n=10)
                                if not results:
                                    st.warning("No similar items found.")
                                else:
                                    for r in results:
                                        meta = r.get("metadata") or {}
                                        with st.container():
                                            st.markdown(f"**{meta.get('title', '(untitled)')}**")
                                            st.caption((r.get("content") or "")[:300])
                                            st.markdown(f"Source: `{meta.get('source', '?')}` | Score: {r.get('distance', 0):.4f}")
                                            st.divider()
                        except Exception as exc:
                            st.error(f"Similar items lookup failed: {exc}")

        elif rec_mode == "By Topic":
            topic_sel = st.selectbox("Topic", TOPICS)
            if st.button("Show Recommendations", type="primary"):
                with st.spinner("Finding recommendations by topic..."):
                    try:
                        results = recommend_by_topic(topic_sel, n=10)
                        if not results:
                            st.warning("No recommendations found.")
                        else:
                            for r in results:
                                meta = r.get("metadata") or {}
                                with st.container():
                                    st.markdown(f"**{meta.get('title', '(untitled)')}**")
                                    st.caption((r.get("content") or "")[:300])
                                    st.markdown(f"Source: `{meta.get('source', '?')}`")
                                    st.divider()
                    except Exception as exc:
                        st.error(f"Topic recommendations failed: {exc}")

    with tab_tag:
        st.subheader("Auto-Tag Content")
        tag_title = st.text_input("Title", placeholder="Content title")
        tag_content = st.text_area("Content", height=150, placeholder="Content body text")
        tag_hashtags = st.text_input("Existing hashtags (comma-separated)", placeholder="ai, machine-learning")
        if st.button("Tag", type="primary"):
            if not tag_title.strip() and not tag_content.strip():
                st.error("Enter at least a title or content.")
            else:
                with st.spinner("Analyzing content..."):
                    try:
                        item = ContentItem(
                            id="preview",
                            title=tag_title,
                            content=tag_content,
                            content_cleaned=tag_content,
                            source="dashboard",
                            hashtags=[h.strip() for h in tag_hashtags.split(",") if h.strip()],
                        )
                        tags = auto_tag(item)
                        entities = extract_entities(f"{tag_title}\n{tag_content}")

                        st.subheader("Tags by Category")
                        for category, tag_list in tags.items():
                            if tag_list:
                                st.markdown(f"**{category}:** " + ", ".join(f"`{t}`" for t in tag_list))

                        st.subheader("Extracted Entities")
                        if entities:
                            df = pd.DataFrame(entities)
                            st.dataframe(df, width='stretch', hide_index=True)
                        else:
                            st.info("No entities extracted.")
                    except Exception as exc:
                        st.error(f"Tagging failed: {exc}")

def _page_rag_chat():
    st.title("RAG Chat — Ask About Your Content")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "chat_sources" not in st.session_state:
        st.session_state.chat_sources = {}

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("sources"):
                with st.expander(f"Sources ({len(msg['sources'])})"):
                    for src in msg["sources"]:
                        st.markdown(f"- **{src.get('title', '?')}** (_{src.get('source', '?')}_)")
                        if src.get("url"):
                            st.markdown(f"  :link: [{src['url']}]({src['url']})")
                        st.caption(src.get("snippet", "")[:200])

    question = st.chat_input("Ask a question about your content...")

    if st.button("Clear Chat"):
        st.session_state.chat_history = []
        st.session_state.chat_sources = {}
        st.rerun()

    if question:
        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Searching content and generating answer..."):
                try:
                    result = CHAT.query(question, n_context=5)
                    answer_text = result.get("answer", "No answer generated.")
                    sources = result.get("sources", [])

                    placeholder = st.empty()
                    displayed = ""
                    for chunk in [answer_text]:
                        displayed += chunk
                        placeholder.markdown(displayed + "▌")
                        time.sleep(0.02)
                    placeholder.markdown(displayed)

                    if sources:
                        with st.expander(f"Sources ({len(sources)})"):
                            for src in sources:
                                st.markdown(f"- **{src.get('title', '?')}** (_{src.get('source', '?')}_)")
                                if src.get("url"):
                                    st.markdown(f"  :link: [{src['url']}]({src['url']})")
                                st.caption(src.get("snippet", "")[:200])

                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": answer_text,
                        "sources": sources,
                    })
                except Exception as exc:
                    st.error(f"Query failed: {exc}")
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": f"Error: {exc}",
                        "sources": [],
                    })

def _page_analytics():
    st.title("Analytics")

    tab_trends, tab_wordcloud, tab_export = st.tabs(["Trends", "Word Cloud", "Export"])

    with tab_trends:
        st.subheader("Topic Trends Over Time")
        trend_topic = st.selectbox("Topic", ["All"] + TOPICS, key="trend_topic")
        trend_days = st.slider("Days", min_value=7, max_value=90, value=30, key="trend_days")

        with st.spinner("Computing trends..."):
            try:
                if trend_topic == "All":
                    all_trends = TRENDS.all_topics_trend(days=trend_days)
                    if all_trends:
                        combined = []
                        for t_name, t_data in all_trends.items():
                            for entry in t_data:
                                combined.append({"topic": t_name, "date": entry["date"], "count": entry["count"]})
                        if combined:
                            df = pd.DataFrame(combined)
                            df["date"] = pd.to_datetime(df["date"])
                            pivot = df.pivot_table(index="date", columns="topic", values="count", aggfunc="sum", fill_value=0)
                            st.line_chart(pivot)
                else:
                    trend_data = TRENDS.topic_trend(trend_topic, days=trend_days)
                    if trend_data:
                        df = pd.DataFrame(trend_data)
                        df["date"] = pd.to_datetime(df["date"])
                        st.line_chart(df.set_index("date")["count"])

                st.subheader("Source Comparison")
                src_data = []
                for src_name in SOURCES[:6]:
                    src_t = TRENDS.source_trend(src_name, days=trend_days)
                    for entry in src_t:
                        src_data.append({"source": src_name, "date": entry["date"], "count": entry["count"]})
                if src_data:
                    df_src = pd.DataFrame(src_data)
                    df_src["date"] = pd.to_datetime(df_src["date"])
                    pivot_src = df_src.pivot_table(index="date", columns="source", values="count", aggfunc="sum", fill_value=0)
                    st.line_chart(pivot_src)

                st.subheader("Top Movers")
                movers = TRENDS.top_movers(days=trend_days)
                if movers:
                    df_movers = pd.DataFrame(movers).head(15)
                    st.bar_chart(df_movers.set_index("topic")["change_pct"])
            except Exception as exc:
                st.error(f"Trend analysis failed: {exc}")

    with tab_wordcloud:
        st.subheader("Word Cloud Generator")
        wc_filter = st.selectbox("Filter by", ["All", "Topic", "Source"], key="wc_filter")
        wc_value = None
        if wc_filter == "Topic":
            wc_value = st.selectbox("Topic", TOPICS, key="wc_topic")
        elif wc_filter == "Source":
            wc_value = st.selectbox("Source", SOURCES, key="wc_source")

        if st.button("Generate Word Cloud", type="primary"):
            with st.spinner("Generating word cloud..."):
                try:
                    items_data = _get_all_items_full(500)
                    content_items = []
                    for r in items_data:
                        item = ContentItem(
                            id=r.get("id", "unknown"),
                            title=r.get("title", ""),
                            content=r.get("content", ""),
                            content_cleaned=r.get("content_cleaned", ""),
                            url=r.get("url", ""),
                            source=r.get("source", "unknown"),
                        )
                        if wc_filter == "Topic" and wc_value:
                            topics_str = r.get("topics", "")
                            if wc_value.lower() not in topics_str.lower():
                                continue
                        if wc_filter == "Source" and wc_value:
                            if r.get("source") != wc_value:
                                continue
                        content_items.append(item)

                    if not content_items:
                        st.warning("No items matching the filter.")
                    else:
                        output_path = os.path.join(settings.DATA_DIR, "analytics", "dashboard_wordcloud.png")
                        wc_path = generate_wordcloud(content_items, title="Content Word Cloud", output_path=output_path)
                        if wc_path and os.path.exists(wc_path):
                            st.image(wc_path, width='stretch')
                        else:
                            st.info("Word cloud library not available. Showing frequency table instead.")

                        freq = get_frequency_table(content_items, top_n=30)
                        if freq:
                            st.subheader("Frequency Table")
                            df_freq = pd.DataFrame(freq)
                            st.dataframe(df_freq, width='stretch', hide_index=True)
                except Exception as exc:
                    st.error(f"Word cloud generation failed: {exc}")

    with tab_export:
        st.subheader("Export Content")
        exp_format = st.selectbox("Format", ["CSV", "JSON", "Markdown"], key="exp_format")
        exp_filter = st.selectbox("Filter by", ["All", "Source", "Topic"], key="exp_filter")
        exp_value = None
        if exp_filter == "Source":
            exp_value = st.selectbox("Source", SOURCES, key="exp_source")
        elif exp_filter == "Topic":
            exp_value = st.selectbox("Topic", TOPICS, key="exp_topic")
        exp_days = st.number_input("Days to include", min_value=1, max_value=365, value=7, key="exp_days")
        exp_label = st.text_input("File label (optional)", placeholder="my_export")

        if st.button("Export", type="primary"):
            with st.spinner("Exporting..."):
                try:
                    fmt_map = {"CSV": "csv", "JSON": "json", "Markdown": "markdown"}
                    fmt = fmt_map[exp_format]

                    if exp_filter == "Source" and exp_value:
                        path = export_source_report(exp_value, days=exp_days, format=fmt)
                    elif exp_filter == "Topic" and exp_value:
                        path = export_topic_report(exp_value, days=exp_days, format=fmt)
                    else:
                        items_data = _get_all_items_full(500)
                        content_items = []
                        for r in items_data:
                            item = ContentItem(
                                id=r.get("id", "unknown"),
                                title=r.get("title", ""),
                                content=r.get("content", ""),
                                content_cleaned=r.get("content_cleaned", ""),
                                url=r.get("url", ""),
                                source=r.get("source", "unknown"),
                            )
                            content_items.append(item)
                        cutoff = datetime.now() - timedelta(days=exp_days)
                        content_items = [it for it in content_items if it.published_at is None or it.published_at.replace(tzinfo=None) >= cutoff]

                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        label = exp_label.replace(" ", "_") if exp_label else "export"
                        ext = {"csv": "csv", "json": "json", "markdown": "md"}[fmt]
                        out_path = os.path.join(settings.DATA_DIR, "exports", f"{label}_{ts}.{ext}")
                        os.makedirs(os.path.dirname(out_path), exist_ok=True)

                        if fmt == "csv":
                            path = export_to_csv(content_items, out_path)
                        elif fmt == "json":
                            path = export_to_json(content_items, out_path)
                        else:
                            path = export_to_markdown(content_items, out_path)

                    if path and os.path.exists(path):
                        with open(path, "rb") as f:
                            st.success(f"Exported to {path}")
                            fname = os.path.basename(path)
                            st.download_button(
                                f":inbox_tray: Download {fname}",
                                data=f.read(),
                                file_name=fname,
                            )
                    else:
                        st.error("Export failed.")
                except Exception as exc:
                    st.error(f"Export failed: {exc}")

def _page_notifications():
    st.title("Notifications")

    tab_email, tab_telegram, tab_webhooks = st.tabs(["Email", "Telegram", "Webhooks"])

    with tab_email:
        st.subheader("SMTP Configuration")

        smtp_host = st.text_input("SMTP Host", placeholder="smtp.gmail.com", key="email_host")
        smtp_port = st.number_input("SMTP Port", min_value=1, max_value=65535, value=587, key="email_port")
        smtp_user = st.text_input("SMTP Username", key="email_user")
        smtp_pass = st.text_input("SMTP Password", type="password", key="email_pass")
        to_email = st.text_input("To Email", placeholder="recipient@example.com", key="email_to")

        if st.button("Test Send", key="email_test"):
            if not smtp_host or not to_email:
                st.error("SMTP host and to-email are required.")
            else:
                with st.spinner("Sending test email..."):
                    try:
                        sender = NewsletterSender(
                            smtp_host=smtp_host,
                            smtp_port=int(smtp_port),
                            smtp_user=smtp_user or None,
                            smtp_pass=smtp_pass or None,
                        )
                        ok = sender.send_digest(
                            to_email=to_email,
                            digest_text="This is a test email from AI Content Hub Dashboard.",
                            subject="Test — AI Content Hub",
                        )
                        if ok:
                            st.success("Test email sent successfully!")
                        else:
                            st.error("Failed to send. Check SMTP settings.")
                    except Exception as exc:
                        st.error(f"Error: {exc}")

        st.divider()
        st.subheader("Weekly Digest Configuration")

        digest_topics_sel = st.multiselect("Digest Topics", TOPICS, default=TOPICS[:4], key="email_topics")
        digest_email = st.text_input("Digest Recipient", placeholder="digest@example.com", key="email_digest_to")

        if st.button("Send Weekly Digest", key="email_digest"):
            if not digest_email:
                st.error("Recipient email is required.")
            else:
                with st.spinner("Preparing weekly digest..."):
                    try:
                        items_data = _get_all_items_full(100)
                        content_items = []
                        for r in items_data:
                            item = ContentItem(
                                id=r.get("id", "unknown"),
                                title=r.get("title", ""),
                                content=r.get("content", ""),
                                content_cleaned=r.get("content_cleaned", ""),
                                url=r.get("url", ""),
                                source=r.get("source", "unknown"),
                                topics=[t.strip() for t in r.get("topics", "").split(",") if t.strip()],
                            )
                            content_items.append(item)

                        sender = NewsletterSender(
                            smtp_host=smtp_host or None,
                            smtp_port=int(smtp_port) if smtp_port else None,
                            smtp_user=smtp_user or None,
                            smtp_pass=smtp_pass or None,
                        )
                        ok = sender.send_weekly_newsletter(
                            to_email=digest_email,
                            items=content_items,
                            topics=digest_topics_sel,
                        )
                        if ok:
                            st.success("Weekly digest sent!")
                        else:
                            st.error("Failed to send digest.")
                    except Exception as exc:
                        st.error(f"Error: {exc}")

    with tab_telegram:
        st.subheader("Telegram Bot Configuration")

        bot_token = st.text_input("Bot Token", type="password", placeholder="123456:ABC-DEF...", key="tg_token")
        chat_id = st.text_input("Chat ID", placeholder="-1001234567890", key="tg_chat")

        if st.button("Test Message", key="tg_test"):
            if not bot_token or not chat_id:
                st.error("Bot token and chat ID are required.")
            else:
                with st.spinner("Sending test message..."):
                    try:
                        notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)
                        ok = notifier.send_message("Test message from AI Content Hub Dashboard.")
                        if ok:
                            st.success("Test message sent!")
                        else:
                            st.error("Failed to send. Check token and chat ID.")
                    except Exception as exc:
                        st.error(f"Error: {exc}")

        if st.button("Send Digest via Telegram", key="tg_digest"):
            if not bot_token or not chat_id:
                st.error("Bot token and chat ID are required.")
            else:
                with st.spinner("Sending digest..."):
                    try:
                        topics = [t.strip() for t in settings.DIGEST_TOPICS.split(",") if t.strip()]
                        lines = [f"*AI Content Hub Digest*", f"", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", f""]
                        for topic in topics:
                            topic_items = SQL.get_by_topic(topic, limit=5)
                            if topic_items:
                                lines.append(f"*{topic}*")
                                for item in topic_items:
                                    title = item.get("title", "Untitled")
                                    src = item.get("source", "?")
                                    lines.append(f"- [{src}] {title}")
                                lines.append("")

                        digest_text = "\n".join(lines)
                        notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)
                        ok = notifier.send_digest(digest_text)
                        if ok:
                            st.success("Digest sent via Telegram!")
                        else:
                            st.error("Failed to send digest.")
                    except Exception as exc:
                        st.error(f"Error: {exc}")

    with tab_webhooks:
        st.subheader("Add Webhook")

        wh_name = st.text_input("Webhook Name", placeholder="my-slack-hook", key="wh_name")
        wh_url = st.text_input("Webhook URL", placeholder="https://hooks.slack.com/...", key="wh_url")
        wh_events = st.multiselect(
            "Events",
            ["new_item", "digest", "alert", "source_complete"],
            default=["new_item"],
            key="wh_events",
        )
        wh_secret = st.text_input("Secret (optional)", type="password", key="wh_secret")

        if st.button("Add Webhook", key="wh_add"):
            if not wh_name or not wh_url:
                st.error("Name and URL are required.")
            else:
                with st.spinner("Registering webhook..."):
                    try:
                        WEBHOOKS.register(
                            name=wh_name,
                            url=wh_url,
                            events=wh_events,
                            secret=wh_secret or None,
                        )
                        WEBHOOKS.save_to_config()
                        st.success(f"Webhook '{wh_name}' registered!")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Failed to register webhook: {exc}")

        st.divider()
        st.subheader("Registered Webhooks")

        try:
            wh_path = os.path.join(settings.DATA_DIR, "webhooks.json")
            if os.path.exists(wh_path):
                with open(wh_path, "r") as f:
                    wh_data = json.load(f)
                if wh_data:
                    rows = []
                    for entry in wh_data:
                        rows.append({
                            "Name": entry.get("name", ""),
                            "URL": entry.get("url", ""),
                            "Events": ", ".join(entry.get("events", [])),
                            "Has Secret": "Yes" if entry.get("secret") else "No",
                        })
                    st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)

                    if st.button("Test Dispatch (new_item)", key="wh_test"):
                        with st.spinner("Dispatching test event..."):
                            try:
                                results = WEBHOOKS.dispatch("new_item", {"event": "new_item", "test": True, "timestamp": datetime.now().isoformat()})
                                for r in results:
                                    name = r.get("name", "?")
                                    status = "Success" if r.get("success") else "Failed"
                                    code = r.get("status_code", "N/A")
                                    err = r.get("error", "")
                                    st.write(f"**{name}**: {status} (HTTP {code}) {err}")
                            except Exception as exc:
                                st.error(f"Dispatch failed: {exc}")
                else:
                    st.info("No webhooks registered.")
            else:
                st.info("No webhooks registered.")
        except Exception as exc:
            st.error(f"Error loading webhooks: {exc}")

def _page_processing():
    st.title("Content Processing")

    tab_ft, tab_dedup, tab_auth = st.tabs(["Full-Text Extract", "Deduplication", "Auth"])

    with tab_ft:
        st.subheader("Full-Text Extraction")
        ft_url = st.text_input("URL to extract", placeholder="https://example.com/article")
        if st.button("Extract", type="primary"):
            if not ft_url.strip():
                st.error("Enter a URL.")
            else:
                with st.spinner("Extracting content..."):
                    try:
                        result = FULLTEXT.extract(ft_url.strip())
                        if result.get("title"):
                            st.subheader(f"Title: {result['title']}")
                        if result.get("author"):
                            st.markdown(f"**Author:** {result['author']}")
                        if result.get("date"):
                            st.markdown(f"**Date:** {result['date']}")
                        if result.get("content"):
                            st.text_area("Content", value=result["content"], height=300)
                        elif result.get("text"):
                            st.text_area("Text", value=result["text"], height=300)
                        else:
                            st.warning("No content could be extracted from this URL.")
                        if result.get("description"):
                            st.caption(f"Description: {result['description']}")
                    except Exception as exc:
                        st.error(f"Extraction failed: {exc}")

    with tab_dedup:
        st.subheader("Deduplication")
        dedup_limit = st.number_input("Items to load", min_value=10, max_value=500, value=100, key="dedup_limit")

        if st.button("Load & Run Dedup", type="primary"):
            with st.spinner("Loading items and detecting duplicates..."):
                try:
                    items_data = _get_all_items_full(dedup_limit)
                    if not items_data:
                        st.warning("No items loaded.")
                    else:
                        content_items = []
                        items_dict = {}
                        for r in items_data:
                            item = ContentItem(
                                id=r.get("id", "unknown"),
                                title=r.get("title", ""),
                                content=r.get("content", ""),
                                content_cleaned=r.get("content_cleaned", ""),
                                url=r.get("url", ""),
                                source=r.get("source", "unknown"),
                                engagement=r.get("engagement", 0),
                            )
                            content_items.append(item)
                            items_dict[item.id] = item

                        url_groups = DEDUP.find_url_duplicates(content_items)
                        title_groups = DEDUP.find_title_duplicates(content_items)
                        content_groups = DEDUP.find_duplicates(content_items)

                        all_groups = url_groups + title_groups + content_groups

                        if not all_groups:
                            st.success("No duplicate groups found.")
                        else:
                            st.warning(f"Found {len(all_groups)} duplicate groups")

                            for i, group in enumerate(all_groups):
                                with st.expander(f"Group {i+1}: {len(group)} items"):
                                    for gid in group:
                                        item = items_dict.get(gid)
                                        if item:
                                            st.markdown(f"- `{item.id[:12]}` **{item.title}** ({item.source})")
                                            if item.url:
                                                st.markdown(f"  :link: {item.url}")

                            if st.button("Merge Duplicates (keep best)"):
                                with st.spinner("Merging duplicates..."):
                                    try:
                                        merged = DEDUP.merge_duplicates(all_groups, items_dict)
                                        st.success(f"Merged into {len(merged)} items (from {len(content_items)})")
                                    except Exception as exc:
                                        st.error(f"Merge failed: {exc}")
                except Exception as exc:
                    st.error(f"Deduplication failed: {exc}")

    with tab_auth:
        st.subheader("Authentication")

        tab_register, tab_login, tab_verify = st.tabs(["Register", "Login", "Verify"])

        with tab_register:
            reg_user = st.text_input("Username", key="reg_user")
            reg_pass = st.text_input("Password", type="password", key="reg_pass")
            reg_role = st.selectbox("Role", ["user", "admin"], key="reg_role")
            if st.button("Register", key="auth_register"):
                if not reg_user or not reg_pass:
                    st.error("Username and password required.")
                else:
                    try:
                        user = AUTH.create_user(reg_user, reg_pass, reg_role)
                        st.success(f"User '{user['username']}' created (role: {user['role']})")
                    except ValueError as exc:
                        st.error(str(exc))
                    except Exception as exc:
                        st.error(f"Registration failed: {exc}")

        with tab_login:
            login_user = st.text_input("Username", key="login_user")
            login_pass = st.text_input("Password", type="password", key="login_pass")
            if st.button("Login", key="auth_login"):
                if not login_user or not login_pass:
                    st.error("Username and password required.")
                else:
                    try:
                        token = AUTH.authenticate(login_user, login_pass)
                        st.success("Authenticated!")
                        st.code(token, language="text")
                        st.info("Copy this token for API access.")
                        st.session_state["auth_token"] = token
                        st.session_state["auth_user"] = login_user
                    except ValueError as exc:
                        st.error(str(exc))
                    except Exception as exc:
                        st.error(f"Login failed: {exc}")

        with tab_verify:
            verify_token_input = st.text_area("JWT Token", height=100, key="verify_token")
            if st.button("Verify Token", key="auth_verify"):
                if not verify_token_input.strip():
                    st.error("Enter a token to verify.")
                else:
                    try:
                        payload = AUTH.verify_token(verify_token_input.strip())
                        st.success("Token is valid!")
                        st.json(payload)
                    except ValueError as exc:
                        st.error(str(exc))
                    except Exception as exc:
                        st.error(f"Verification failed: {exc}")

            st.divider()
            st.subheader("Current User")

            token = st.session_state.get("auth_token", "")
            if token:
                try:
                    user_info = AUTH.get_current_user(token)
                    st.json(user_info)
                except Exception as exc:
                    st.warning(f"Could not retrieve user info: {exc}")
            else:
                st.info("No user logged in. Use the Login tab to authenticate.")

def _page_enterprise_search():
    st.title("Enterprise Search")

    tab_faceted, tab_saved, tab_analytics = st.tabs(["Faceted Search", "Saved Searches", "Search Analytics"])

    with tab_faceted:
        c1, c2 = st.columns([3, 1])
        query = c1.text_input("Search query", placeholder="Search all content...", key="es_query")
        sort = c2.selectbox("Sort", ["relevance", "date_desc", "date_asc", "engagement"], key="es_sort")

        with st.sidebar:
            st.markdown("### Facets")
            facet_opts = FACETED.get_facet_options()
            sources = list(facet_opts.get("sources", {}).keys())
            selected_sources = st.multiselect("Source", sources if sources else SOURCES, key="es_facet_src")
            topics_list = list(facet_opts.get("topics", {}).keys())
            selected_topics = st.multiselect("Topics", topics_list if topics_list else TOPICS, key="es_facet_topic")
            date_range = st.selectbox("Date Range", ["Any", "Today", "This Week", "This Month"], key="es_facet_date")
            source_types = list(facet_opts.get("source_types", {}).keys())
            selected_stype = st.multiselect("Source Type", source_types, key="es_facet_stype")

        page_num = st.number_input("Page", min_value=1, value=1, key="es_page")

        if st.button("Search", type="primary", key="es_search"):
            facets = {}
            if selected_sources:
                facets["source"] = selected_sources
            if selected_topics:
                facets["topics"] = selected_topics
            if date_range == "Today":
                facets["date_from"] = datetime.now().strftime("%Y-%m-%d")
            elif date_range == "This Week":
                facets["date_from"] = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            elif date_range == "This Month":
                facets["date_from"] = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            if selected_stype:
                facets["source_type"] = selected_stype

            with st.spinner("Searching..."):
                try:
                    result = FACETED.search(query=query, facets=facets, page=int(page_num), page_size=20, sort=sort)
                    total = result.get("total", 0)
                    st.success(f"Found **{total}** result(s)")
                    for i, item in enumerate(result.get("results", [])):
                        _render_item_card(item, key_prefix=f"es_{i}")
                except Exception as exc:
                    st.error(f"Search failed: {exc}")

    with tab_saved:
        st.subheader("Create Saved Search")
        with st.form("saved_search_form"):
            ss_name = st.text_input("Name", placeholder="My Search")
            ss_query = st.text_input("Query", placeholder="Search terms")
            ss_facets = st.text_area("Facets (JSON)", value="{}", height=80)
            ss_freq = st.selectbox("Frequency", ["daily", "weekly", "hourly"])
            ss_notify = st.checkbox("Notify on new results", value=True)
            if st.form_submit_button("Save Search", type="primary"):
                try:
                    facets_dict = json.loads(ss_facets) if ss_facets.strip() else {}
                    saved = SAVED.create(name=ss_name, query=ss_query, facets=facets_dict, notify_on_new=ss_notify, frequency=ss_freq)
                    st.success(f"Saved search '{ss_name}' created (ID: {saved['id'][:8]})")
                except Exception as exc:
                    st.error(f"Failed: {exc}")

        st.divider()
        st.subheader("Saved Searches")
        saved_list = SAVED.list()
        if not saved_list:
            st.info("No saved searches yet.")
        else:
            for ss in saved_list:
                with st.container():
                    a, b, c, d, e = st.columns([2, 1, 1, 1, 1])
                    a.markdown(f"**{ss.get('name', 'Unnamed')}**")
                    b.markdown(f"Query: `{ss.get('query', '')}`")
                    c.markdown(f"Freq: {ss.get('frequency', 'daily')}")
                    if e.button("Execute", key=f"exec_{ss['id']}"):
                        with st.spinner("Executing..."):
                            res = SAVED.execute(ss["id"])
                            st.success(f"Found {res.get('total', 0)} results")
                    if d.button("Delete", key=f"del_{ss['id']}"):
                        SAVED.delete(ss["id"])
                        st.rerun()
                st.divider()

    with tab_analytics:
        st.subheader("Search Analytics")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Refresh Analytics", key="sa_refresh"):
                st.rerun()
        with col2:
            sa_days = st.number_input("Days", min_value=1, max_value=90, value=30, key="sa_days")

        popular = SEARCH_ANALYTICS.get_popular_searches(days=sa_days)
        if popular:
            st.subheader("Popular Searches")
            df_pop = pd.DataFrame(popular)
            st.dataframe(df_pop, width='stretch', hide_index=True)

        zero = SEARCH_ANALYTICS.get_zero_result_searches()
        if zero:
            st.subheader("Zero-Result Searches (Content Gaps)")
            df_zero = pd.DataFrame(zero)
            st.dataframe(df_zero, width='stretch', hide_index=True)

        trends = SEARCH_ANALYTICS.get_search_trends(days=sa_days)
        if trends:
            st.subheader("Search Volume")
            df_trends = pd.DataFrame(trends)
            df_trends["date"] = pd.to_datetime(df_trends["date"])
            st.line_chart(df_trends.set_index("date")["search_count"])

        ctr = SEARCH_ANALYTICS.get_click_through_rate(days=sa_days)
        st.metric("Click-Through Rate", f"{ctr * 100:.2f}%" if ctr else "0%")

def _page_mlops_lab():
    st.title("MLOps Lab")

    tab_sent, tab_quality, tab_lang, tab_enrich = st.tabs(["Sentiment", "Quality Score", "Language", "Enrichment"])

    with tab_sent:
        st.subheader("Sentiment Analysis")
        sent_text = st.text_area("Input text", height=150, placeholder="Enter text to analyze sentiment...", key="sent_text")
        if st.button("Analyze", type="primary", key="sent_btn"):
            if not sent_text.strip():
                st.error("Please enter text.")
            else:
                with st.spinner("Analyzing sentiment..."):
                    try:
                        result = SENTIMENT.analyze(sent_text)
                        score = result.get("score", 0)
                        sentiment = result.get("sentiment", "neutral")
                        confidence = result.get("confidence", 0)
                        details = result.get("details", {})

                        cols = st.columns(3)
                        cols[0].metric("Sentiment", sentiment)
                        cols[1].metric("Score", f"{score:.4f}")
                        cols[2].metric("Confidence", f"{confidence:.2%}")

                        st.progress(abs(score), text="Sentiment Polarity")

                        tone = details.get("emotional_tone", "neutral")
                        st.info(f"**Emotional Tone:** {tone}")

                        pos_words = details.get("positive_words", [])
                        neg_words = details.get("negative_words", [])
                        if pos_words:
                            st.markdown(f"**Positive words found:** {', '.join(f'`{w}`' for w in pos_words)}")
                        if neg_words:
                            st.markdown(f"**Negative words found:** {', '.join(f'`{w}`' for w in neg_words)}")
                    except Exception as exc:
                        st.error(f"Sentiment analysis failed: {exc}")

    with tab_quality:
        st.subheader("Quality Score")
        qual_text = st.text_area("Input text", height=150, placeholder="Enter text to score...", key="qual_text")
        if st.button("Score", type="primary", key="qual_btn"):
            if not qual_text.strip():
                st.error("Please enter text.")
            else:
                with st.spinner("Scoring quality..."):
                    try:
                        result = QUALITY.score(qual_text)
                        score = result.get("score", 0)
                        factors = result.get("factors", {})
                        details = result.get("details", {})

                        if score >= 80:
                            tier = "Excellent"
                            tier_color = "green"
                        elif score >= 60:
                            tier = "Good"
                            tier_color = "blue"
                        elif score >= 40:
                            tier = "Average"
                            tier_color = "orange"
                        else:
                            tier = "Poor"
                            tier_color = "red"

                        cols = st.columns(4)
                        cols[0].metric("Total Score", score)
                        cols[1].markdown(f"**Tier:** :{tier_color}[{tier}]")
                        cols[2].metric("Word Count", details.get("word_count", 0))
                        cols[3].metric("Readability", f"{details.get('flesch_score', 0):.1f}")

                        st.subheader("Factor Breakdown")
                        radar_df = pd.DataFrame({
                            "Factor": list(factors.keys()),
                            "Score": list(factors.values()),
                        })
                        st.bar_chart(radar_df.set_index("Factor"))

                        st.subheader("Trending Content")
                        trending = QUALITY.get_trending_content(limit=10)
                        if trending:
                            trend_rows = []
                            for t in trending:
                                trend_rows.append({
                                    "Title": t.title[:60],
                                    "Score": t.metadata.get("quality_score", 0),
                                    "Tier": t.metadata.get("quality_tier", ""),
                                })
                            st.dataframe(pd.DataFrame(trend_rows), width='stretch', hide_index=True)
                    except Exception as exc:
                        st.error(f"Quality scoring failed: {exc}")

    with tab_lang:
        st.subheader("Language Detection")
        lang_text = st.text_area("Input text", height=150, placeholder="Enter text to detect language...", key="lang_text")
        if st.button("Detect", type="primary", key="lang_btn"):
            if not lang_text.strip():
                st.error("Please enter text.")
            else:
                with st.spinner("Detecting language..."):
                    try:
                        result = LANG.detect(lang_text)
                        lang_name = result.get("language", "Unknown")
                        lang_code = result.get("code", "?")
                        confidence = result.get("confidence", 0)

                        cols = st.columns(3)
                        cols[0].metric("Language", lang_name)
                        cols[1].metric("Code", lang_code)
                        cols[2].metric("Confidence", f"{confidence:.2%}")
                    except Exception as exc:
                        st.error(f"Language detection failed: {exc}")

        st.divider()
        st.subheader("Translation")
        trans_text = st.text_area("Text to translate", height=100, placeholder="Enter text to translate...", key="trans_text")
        trans_target = st.selectbox("Target language", ["en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko"], key="trans_target")
        if st.button("Translate", key="trans_btn"):
            if not trans_text.strip():
                st.error("Please enter text.")
            else:
                with st.spinner("Translating..."):
                    try:
                        translated = LANG.translate(trans_text, target_language=trans_target)
                        st.text_area("Translated text", value=translated, height=100)
                    except Exception as exc:
                        st.error(f"Translation failed: {exc}")

    with tab_enrich:
        st.subheader("Content Enrichment")
        enrich_title = st.text_input("Title", placeholder="Content title", key="enrich_title")
        enrich_content = st.text_area("Content", height=150, placeholder="Content body", key="enrich_content")
        enrich_source = st.text_input("Source", placeholder="Source name (e.g. linkedin)", key="enrich_source")
        if st.button("Enrich", type="primary", key="enrich_btn"):
            if not enrich_content.strip():
                st.error("Please enter content.")
            else:
                with st.spinner("Enriching content..."):
                    try:
                        item = ContentItem(
                            id="enrich_preview",
                            title=enrich_title,
                            content=enrich_content,
                            source=enrich_source or "manual",
                            content_cleaned=enrich_content,
                        )
                        enriched = ENRICH.enrich_item(item)
                        meta = enriched.metadata

                        st.subheader("Extracted Fields")
                        st.markdown(f"**Keywords:** {', '.join(meta.get('keywords', []))}")
                        st.markdown(f"**Read Time:** {meta.get('read_time', 0)} min")
                        st.markdown(f"**Category:** {meta.get('category', 'N/A')}")
                        st.markdown(f"**Meta Description:** {meta.get('meta_description', '')[:200]}")

                        links = meta.get("links", [])
                        if links:
                            st.markdown(f"**Links ({len(links)}):**")
                            for link in links[:5]:
                                st.markdown(f"- {link.get('domain', '?')}: [{link.get('url', '')[:60]}]({link.get('url', '')})")

                        mentions = meta.get("mentions", [])
                        if mentions:
                            st.markdown(f"**Mentions:** {', '.join(f'@{m}' for m in mentions)}")

                        hashtags = meta.get("hashtags", [])
                        if hashtags:
                            st.markdown(f"**Hashtags:** {' '.join(f'#{h}' for h in hashtags)}")
                    except Exception as exc:
                        st.error(f"Enrichment failed: {exc}")

def _page_integrations():
    st.title("Integrations")

    tab_slack, tab_jira, tab_teams, tab_notion = st.tabs(["Slack", "Jira", "Teams", "Notion"])

    with tab_slack:
        st.subheader("Slack Integration")
        slack_channel = st.text_input("Channel", value="#general", key="slack_channel")
        slack_message = st.text_area("Message text", height=100, placeholder="Type a message...", key="slack_msg")

        if slack_message:
            preview_blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": slack_message}}]
            st.code(json.dumps(preview_blocks, indent=2), language="json")

        if st.button("Send Message", type="primary", key="slack_send"):
            with st.spinner("Sending to Slack..."):
                try:
                    resp = SLACK.send_message(slack_channel, slack_message)
                    if resp and resp.get("ok"):
                        st.success("Message sent to Slack!")
                    else:
                        st.error(f"Failed: {resp.get('error', 'unknown') if resp else 'Not configured'}")
                except Exception as exc:
                    st.error(f"Slack error: {exc}")

        st.divider()
        items = _get_all_items(10)
        if items:
            item_options = {f"{i['id'][:8]} - {i['title'][:50]}": i for i in items}
            selected_item_label = st.selectbox("Send Content Card", list(item_options.keys()), key="slack_item")
            if st.button("Send Content Card", key="slack_card"):
                with st.spinner("Sending content card..."):
                    try:
                        sel = item_options[selected_item_label]
                        citem = ContentItem(id=sel["id"], title=sel["title"], content=sel.get("content_cleaned", ""), content_cleaned=sel.get("content_cleaned", ""), url=sel.get("url", ""), source=sel.get("source", ""), topics=[t.strip() for t in sel.get("topics", "").split(",") if t.strip()], relevance_score=sel.get("relevance_score", 0), engagement=sel.get("engagement", 0))
                        resp = SLACK.send_content_item(slack_channel, citem)
                        if resp and resp.get("ok"):
                            st.success("Content card sent!")
                        else:
                            st.error("Failed to send content card.")
                    except Exception as exc:
                        st.error(f"Error: {exc}")

    with tab_jira:
        st.subheader("Create Jira Issue")
        jira_summary = st.text_input("Summary", placeholder="Issue summary", key="jira_summary")
        jira_desc = st.text_area("Description", height=150, placeholder="Issue description", key="jira_desc")
        jira_priority = st.selectbox("Priority", ["Low", "Medium", "High", "Highest"], key="jira_priority")
        jira_type = st.selectbox("Issue Type", ["Task", "Story", "Bug", "Epic"], key="jira_type")

        if st.button("Create Issue", type="primary", key="jira_create"):
            with st.spinner("Creating Jira issue..."):
                try:
                    result = JIRA.create_issue(jira_summary, jira_desc, jira_type, jira_priority)
                    if result and "error" not in result:
                        st.success(f"Issue created: {result.get('key', '?')}")
                        st.json(result)
                    else:
                        st.error(f"Failed: {result.get('error', 'Not configured') if result else 'Not configured'}")
                except Exception as exc:
                    st.error(f"Jira error: {exc}")

        st.divider()
        st.subheader("Jira Issues")
        if st.button("Fetch Issues", key="jira_fetch"):
            with st.spinner("Fetching issues..."):
                try:
                    issues = JIRA.search_issues("assignee=currentuser() ORDER BY created DESC")
                    if issues:
                        rows = []
                        for iss in issues:
                            fields = iss.get("fields", {})
                            rows.append({"Key": iss.get("key", ""), "Summary": fields.get("summary", ""), "Status": fields.get("status", {}).get("name", ""), "Priority": fields.get("priority", {}).get("name", "")})
                        st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)
                    else:
                        st.info("No issues found or Jira not configured.")
                except Exception as exc:
                    st.error(f"Failed: {exc}")

    with tab_teams:
        st.subheader("Teams Integration")
        teams_text = st.text_area("Message text", height=100, placeholder="Type a message...", key="teams_text")
        teams_title = st.text_input("Title", value="Notification", key="teams_title")

        if teams_text:
            preview_card = TEAMS._build_adaptive_card(body=[{"type": "TextBlock", "text": teams_title, "weight": "bolder", "size": "medium"}, {"type": "TextBlock", "text": teams_text, "wrap": True}])
            st.code(json.dumps(preview_card, indent=2), language="json")

        if st.button("Send to Teams", type="primary", key="teams_send"):
            with st.spinner("Sending to Teams..."):
                try:
                    ok = TEAMS.send_message(teams_text, title=teams_title)
                    if ok:
                        st.success("Message sent to Teams!")
                    else:
                        st.error("Failed. Check Teams webhook URL configuration.")
                except Exception as exc:
                    st.error(f"Teams error: {exc}")

    with tab_notion:
        st.subheader("Notion Integration")
        items_full = _get_all_items(20)
        if items_full:
            notion_opts = {f"{i['id'][:8]} - {i['title'][:50]}": i for i in items_full}
            notion_sel = st.selectbox("Select content item", list(notion_opts.keys()), key="notion_item")
            if st.button("Create Page in Notion", type="primary", key="notion_create"):
                with st.spinner("Creating Notion page..."):
                    try:
                        sel = notion_opts[notion_sel]
                        citem = ContentItem(id=sel["id"], title=sel["title"], content=sel.get("content_cleaned", ""), content_cleaned=sel.get("content_cleaned", ""), url=sel.get("url", ""), source=sel.get("source", ""), topics=[t.strip() for t in sel.get("topics", "").split(",") if t.strip()], relevance_score=sel.get("relevance_score", 0))
                        page_id = NOTION.create_content_page(citem)
                        if page_id:
                            st.success(f"Page created in Notion! ID: {page_id}")
                        else:
                            st.error("Failed to create page. Check Notion API key configuration.")
                    except Exception as exc:
                        st.error(f"Notion error: {exc}")

        st.divider()
        st.subheader("Create Database")
        with st.form("notion_db_form"):
            db_title = st.text_input("Database title", placeholder="Content Digest 2024-01-01")
            if st.form_submit_button("Create Database", type="primary"):
                with st.spinner("Creating database..."):
                    try:
                        db_id = NOTION.create_digest_database([], title=db_title)
                        if db_id:
                            st.success(f"Database created! ID: {db_id}")
                        else:
                            st.error("Failed to create database.")
                    except Exception as exc:
                        st.error(f"Error: {exc}")

def _page_compliance():
    st.title("Compliance")

    tab_pii, tab_mod, tab_audit, tab_retention = st.tabs(["PII Detection", "Content Moderation", "Audit Log", "Data Retention"])

    with tab_pii:
        st.subheader("PII Detection")
        pii_text = st.text_area("Input text", height=150, placeholder="Paste text to scan for PII...", key="pii_text")
        if st.button("Detect PII", type="primary", key="pii_detect"):
            if not pii_text.strip():
                st.error("Please enter text.")
            else:
                with st.spinner("Scanning for PII..."):
                    try:
                        findings = PII.detect(pii_text)
                        if not findings:
                            st.success("No PII detected.")
                        else:
                            st.warning(f"Found **{len(findings)}** PII instance(s)")
                            for f in findings:
                                color = {"email": "blue", "phone": "green", "credit_card": "red", "ssn": "red", "ip_address": "orange", "api_key": "red"}.get(f["type"], "grey")
                                st.markdown(f":{color}[**{f['type']}**] `{f['value']}` (confidence: {f['confidence']:.0%})")

                            st.divider()
                            if st.button("Redact PII", key="pii_redact"):
                                redacted = PII.redact(pii_text)
                                col_a, col_b = st.columns(2)
                                col_a.text_area("Before", value=pii_text, height=150, disabled=True)
                                col_b.text_area("After (Redacted)", value=redacted, height=150)
                                st.success("PII redacted!")
                    except Exception as exc:
                        st.error(f"PII detection failed: {exc}")

    with tab_mod:
        st.subheader("Content Moderation")
        mod_text = st.text_area("Input text", height=150, placeholder="Paste text to moderate...", key="mod_text")
        if st.button("Moderate", type="primary", key="mod_btn"):
            if not mod_text.strip():
                st.error("Please enter text.")
            else:
                with st.spinner("Running moderation checks..."):
                    try:
                        result = MODERATOR.moderate(mod_text)
                        approved = result.get("approved", True)
                        flags = result.get("flags", [])
                        score = result.get("score", 0)

                        if approved:
                            st.success("Content Approved")
                        else:
                            st.error("Content Flagged")

                        if flags:
                            st.subheader("Flags")
                            for flag in flags:
                                conf = flag.get("confidence", 0)
                                st.markdown(f"- **{flag.get('type')}** (confidence: {conf:.0%}) — `{flag.get('word', '')}`")
                                st.progress(conf, text=flag["type"])
                        else:
                            st.info("No flags raised.")
                    except Exception as exc:
                        st.error(f"Moderation failed: {exc}")

        st.divider()
        st.subheader("Blocklist Management")
        blocked = MODERATOR.get_blocked_terms()
        if blocked:
            st.markdown(f"**{len(blocked)}** terms in blocklist")
        new_term = st.text_input("Add term to blocklist", placeholder="new-blocked-term", key="mod_term")
        if st.button("Add Term", key="mod_add"):
            if MODERATOR.add_blocked_term(new_term):
                st.success(f"Term '{new_term}' added.")
                st.rerun()
            else:
                st.error("Failed to add term.")

    with tab_audit:
        st.subheader("Audit Log Query")
        with st.form("audit_form"):
            col_a, col_b, col_c = st.columns(3)
            a_actor = col_a.text_input("Actor")
            a_event = col_b.text_input("Event")
            a_resource = col_c.text_input("Resource Type")
            a_start = st.date_input("Start Date", value=datetime.now() - timedelta(days=7), key="audit_start")
            a_end = st.date_input("End Date", value=datetime.now(), key="audit_end")
            if st.form_submit_button("Query", type="primary"):
                with st.spinner("Querying audit log..."):
                    try:
                        results = AUDIT.query(
                            actor=a_actor or None,
                            event=a_event or None,
                            resource_type=a_resource or None,
                            start_time=a_start.isoformat() if a_start else None,
                            end_time=a_end.isoformat() if a_end else None,
                            limit=100,
                        )
                        if results:
                            st.success(f"Found **{len(results)}** event(s)")
                            df = pd.DataFrame(results)
                            st.dataframe(df, width='stretch', hide_index=True)
                        else:
                            st.info("No matching events.")
                    except Exception as exc:
                        st.error(f"Query failed: {exc}")

        st.divider()
        st.subheader("Audit Summary")
        summary = AUDIT.get_summary(days=7)
        if summary:
            cols = st.columns(3)
            cols[0].metric("Total Events (7d)", summary.get("total_events", 0))
            cols[1].metric("Unique Actors", summary.get("unique_actors", 0))
            cols[2].metric("DB Size", f"{AUDIT.get_stats().get('db_size_bytes', 0) / 1024:.1f} KB")

    with tab_retention:
        st.subheader("Retention Policies")
        policies = RETENTION.list_policies()
        pol_data = []
        for src, days in policies.items():
            pol_data.append({"Source": src, "Retention (Days)": days})
        if pol_data:
            st.dataframe(pd.DataFrame(pol_data), width='stretch', hide_index=True)
        else:
            st.info("No custom policies. Default is 90 days.")

        st.subheader("Set Policy")
        with st.form("retention_form"):
            pol_src = st.selectbox("Source", SOURCES, key="pol_src")
            pol_days = st.number_input("Retention Days", min_value=1, max_value=365, value=90, key="pol_days")
            if st.form_submit_button("Set Policy"):
                RETENTION.set_policy(pol_src, pol_days)
                st.success(f"Policy set: {pol_src} = {pol_days} days")
                st.rerun()

        st.divider()
        st.subheader("Enforce Policies")
        dry_run = st.checkbox("Dry run (simulate only)", value=True, key="retention_dry")
        if st.button("Enforce Now", type="primary"):
            with st.spinner("Enforcing retention policies..."):
                try:
                    result = RETENTION.enforce_policies(dry_run=dry_run)
                    if dry_run:
                        st.info(f"Dry run: {result.get('deleted', 0)} items would be deleted")
                    else:
                        st.success(f"Deleted {result.get('deleted', 0)} items")
                    st.json(result.get("per_source", {}))
                except Exception as exc:
                    st.error(f"Enforcement failed: {exc}")

        st.subheader("Archive")
        archive_days = st.number_input("Archive items older than (days)", min_value=1, max_value=365, value=90, key="archive_days")
        if st.button("Archive Now"):
            with st.spinner("Archiving..."):
                try:
                    result = RETENTION.archive_before(days=archive_days)
                    st.success(f"Archived {result.get('archived_count', 0)} items")
                    for f in result.get("archive_files", []):
                        st.markdown(f"- `{f}`")
                except Exception as exc:
                    st.error(f"Archive failed: {exc}")

def _page_collaboration():
    st.title("Collaboration")

    tab_ws, tab_comments, tab_approvals = st.tabs(["Workspaces", "Comments", "Approvals"])

    with tab_ws:
        st.subheader("Create Workspace")
        with st.form("ws_form"):
            ws_name = st.text_input("Workspace Name", placeholder="My Workspace")
            ws_desc = st.text_area("Description", placeholder="Workspace description")
            ws_owner = st.text_input("Owner", placeholder="username")
            if st.form_submit_button("Create", type="primary"):
                try:
                    ws = WORKSPACE.create_workspace(name=ws_name, description=ws_desc, owner=ws_owner)
                    st.success(f"Workspace '{ws_name}' created (ID: {ws['id'][:8]})")
                except Exception as exc:
                    st.error(f"Failed: {exc}")

        st.divider()
        st.subheader("Workspaces")
        workspaces = WORKSPACE.list_workspaces()
        if not workspaces:
            st.info("No workspaces yet.")
        else:
            ws_names = {f"{w['name']} (by {w['owner']})": w for w in workspaces}
            selected_ws_name = st.selectbox("Select workspace", list(ws_names.keys()), key="ws_select")
            selected_ws = ws_names[selected_ws_name]

            a, b = st.columns(2)
            if a.button("View Members", key="ws_members"):
                members = WORKSPACE.get_members(selected_ws["id"])
                if members:
                    st.dataframe(pd.DataFrame(members), width='stretch', hide_index=True)
                else:
                    st.info("No members.")

            if b.button("View Content", key="ws_content"):
                content = WORKSPACE.get_content(selected_ws["id"])
                if content:
                    for c in content[:10]:
                        st.markdown(f"- **{c.get('title', 'Untitled')}** ({c.get('source', '?')})")
                else:
                    st.info("No content in this workspace.")

            st.subheader("Add Content to Workspace")
            items = _get_all_items(20)
            if items:
                item_opts = {f"{i['id'][:8]} - {i['title'][:50]}": i for i in items}
                sel_item_label = st.selectbox("Select item", list(item_opts.keys()), key="ws_add_item")
                if st.button("Add to Workspace", key="ws_add"):
                    sel = item_opts[sel_item_label]
                    citem = ContentItem(id=sel["id"], title=sel["title"], content=sel.get("content_cleaned", ""), source=sel.get("source", ""), url=sel.get("url", ""))
                    ok = WORKSPACE.add_content(selected_ws["id"], citem, added_by=ws_owner or "dashboard")
                    if ok:
                        st.success("Content added to workspace!")
                    else:
                        st.error("Failed to add content.")

    with tab_comments:
        st.subheader("Comments")
        comment_content_id = st.text_input("Content ID", placeholder="Enter content item ID", key="comment_cid")
        if comment_content_id:
            with st.spinner("Loading comments..."):
                try:
                    threads = COMMENTS.get_comments(comment_content_id)
                    if not threads:
                        st.info("No comments yet.")
                    else:
                        for thread in threads:
                            st.markdown(f"**{thread.get('user', 'Anonymous')}** — {thread.get('created_at', '')[:19]}")
                            st.markdown(thread.get("text", ""))
                            reactions = thread.get("reactions", {})
                            if reactions:
                                st.markdown(f"Reactions: {' '.join(f'{r} {c}' for r, c in reactions.items())}")
                            for reply in thread.get("replies", []):
                                st.markdown(f"> **{reply.get('user', '?')}**: {reply.get('text', '')}")
                            st.divider()
                except Exception as exc:
                    st.error(f"Failed to load comments: {exc}")

        st.subheader("Add Comment")
        with st.form("comment_form"):
            c_user = st.text_input("Your username", placeholder="user", key="c_user")
            c_text = st.text_area("Comment text", placeholder="Write a comment...", key="c_text")
            c_parent = st.text_input("Parent Comment ID (for reply, optional)", key="c_parent")
            if st.form_submit_button("Post Comment", type="primary"):
                if not comment_content_id or not c_user or not c_text:
                    st.error("Content ID, username, and text are required.")
                else:
                    try:
                        created = COMMENTS.add_comment(content_id=comment_content_id, user=c_user, text=c_text, parent_id=c_parent or None)
                        if created:
                            st.success("Comment posted!")
                        else:
                            st.error("Failed to post comment.")
                    except Exception as exc:
                        st.error(f"Error: {exc}")

        st.subheader("Add Reaction")
        with st.form("reaction_form"):
            r_comment_id = st.text_input("Comment ID", key="r_comment_id")
            r_user = st.text_input("Username", key="r_user")
            r_reaction = st.selectbox("Reaction", ["👍", "❤️", "🎯", "💡", "🤔", "🔥"], key="r_reaction")
            if st.form_submit_button("Add Reaction"):
                if COMMENTS.add_reaction(r_comment_id, r_user, r_reaction):
                    st.success("Reaction added!")
                else:
                    st.error("Failed to add reaction.")

    with tab_approvals:
        st.subheader("Create Approval Workflow")
        with st.form("approval_wf_form"):
            aw_name = st.text_input("Workflow Name", placeholder="Content Review")
            aw_steps = st.text_area("Steps (JSON array)", value='[{"name": "Review", "assignees": ["admin"], "required_approvals": 1}]', height=100)
            aw_creator = st.text_input("Created By", placeholder="admin")
            if st.form_submit_button("Create Workflow", type="primary"):
                try:
                    steps = json.loads(aw_steps)
                    wf = APPROVAL.create_workflow(name=aw_name, steps=steps, created_by=aw_creator)
                    st.success(f"Workflow '{aw_name}' created (ID: {wf['id'][:8]})")
                except Exception as exc:
                    st.error(f"Failed: {exc}")

        st.divider()
        st.subheader("Submissions")
        if st.button("Refresh Submissions", key="approval_refresh"):
            st.rerun()

        user_for_approval = st.text_input("Check pending approvals for user", placeholder="username", key="aw_user")
        if user_for_approval:
            pending = APPROVAL.get_pending_approvals(user_for_approval)
            if pending:
                for p in pending:
                    with st.container():
                        st.markdown(f"**{p.get('workflow_name', '?')}** — Step: {p.get('step_name', '?')}")
                        st.markdown(f"Content: {p.get('content_id', '?')} | Status: {p.get('status', '?')}")
                        ca, cb = st.columns(2)
                        step_name = p.get("step_name", "")
                        sub_id = p.get("submission_id", "")
                        if ca.button("Approve", key=f"app_{sub_id}"):
                            APPROVAL.approve(submission_id=sub_id, step_name=step_name, user=user_for_approval)
                            st.success("Approved!")
                            st.rerun()
                        if cb.button("Reject", key=f"rej_{sub_id}"):
                            APPROVAL.reject(submission_id=sub_id, step_name=step_name, user=user_for_approval, reason="Rejected via dashboard")
                            st.success("Rejected!")
                            st.rerun()
                        st.divider()
            else:
                st.info("No pending approvals.")

def _page_monitoring():
    st.title("Monitoring & Alerts")

    tab_alerts, tab_competitors, tab_anomaly = st.tabs(["Alerts", "Competitors", "Anomaly Detection"])

    with tab_alerts:
        st.subheader("Create Alert")
        with st.form("alert_form"):
            al_name = st.text_input("Alert Name", placeholder="My Alert")
            al_keywords = st.text_input("Keywords (comma-separated)", placeholder="AI, machine learning, RAG")
            al_sources = st.multiselect("Sources", SOURCES, key="al_sources")
            al_channels = st.multiselect("Channels", ["slack", "teams", "email", "webhook"], key="al_channels")
            if st.form_submit_button("Create Alert", type="primary"):
                try:
                    keywords = [k.strip() for k in al_keywords.split(",") if k.strip()]
                    alert = ALERTS.create_alert(name=al_name, keywords=keywords, sources=al_sources, channels=al_channels)
                    st.success(f"Alert '{al_name}' created (ID: {alert.get('id', '?')[:8]})")
                except Exception as exc:
                    st.error(f"Failed: {exc}")

        st.divider()
        st.subheader("Active Alerts")
        alerts_list = ALERTS.list_alerts()
        if not alerts_list:
            st.info("No alerts configured.")
        else:
            for al in alerts_list:
                with st.container():
                    a, b, c, d = st.columns([2, 1, 1, 1])
                    a.markdown(f"**{al.get('name', 'Unnamed')}**")
                    b.markdown(f"Keywords: {', '.join(al.get('keywords', []))}")
                    c.markdown(f"Enabled: {'Yes' if al.get('enabled') else 'No'}")
                    if d.button("Toggle", key=f"al_toggle_{al['id']}"):
                        ALERTS.update_alert(al["id"], enabled=not al.get("enabled", True))
                        st.rerun()
                    if a.button("Suppress 24h", key=f"al_supp_{al['id']}"):
                        ALERTS.suppress(al["id"], hours=24)
                        st.success(f"Alert '{al['name']}' suppressed for 24h")
                    if b.button("Delete", key=f"al_del_{al['id']}"):
                        ALERTS.delete_alert(al["id"])
                        st.rerun()
                st.divider()

        st.subheader("Triggered Alerts")
        al_stats = ALERTS.get_alert_stats(days=7)
        cols = st.columns(3)
        cols[0].metric("Total Alerts", al_stats.get("total_alerts", 0))
        cols[1].metric("Triggered (7d)", al_stats.get("triggered_count", 0))
        if al_stats.get("top_alerts"):
            st.dataframe(pd.DataFrame(al_stats["top_alerts"]), width='stretch', hide_index=True)

    with tab_competitors:
        st.subheader("Add Competitor")
        with st.form("comp_form"):
            comp_name = st.text_input("Competitor Name", placeholder="Competitor Inc.")
            comp_domains = st.text_input("Domains (comma-separated)", placeholder="competitor.com, competitor.io")
            comp_keywords = st.text_input("Keywords (comma-separated)", placeholder="competitor product, competitor ai")
            if st.form_submit_button("Add Competitor", type="primary"):
                try:
                    domains = [d.strip() for d in comp_domains.split(",") if d.strip()]
                    keywords = [k.strip() for k in comp_keywords.split(",") if k.strip()]
                    COMPETITOR.add_competitor(name=comp_name, domains=domains, keywords=keywords)
                    st.success(f"Competitor '{comp_name}' added!")
                except Exception as exc:
                    st.error(f"Failed: {exc}")

        st.divider()
        st.subheader("Competitors")
        competitors = COMPETITOR.list_competitors()
        if not competitors:
            st.info("No competitors tracked.")
        else:
            comp_opts = {c["name"]: c for c in competitors}
            selected_comp_name = st.selectbox("Select competitor", list(comp_opts.keys()), key="comp_select")
            selected_comp = comp_opts[selected_comp_name]

            summary = COMPETITOR.get_competitor_summary(selected_comp["id"], days=30)
            if summary:
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Mentions (30d)", summary.get("mention_count", 0))
                col_b.metric("Avg Sentiment", summary.get("sentiment_avg", 0))
                col_c.metric("Total Engagement", summary.get("engagement_total", 0))

                if summary.get("top_sources"):
                    st.subheader("Top Sources")
                    st.dataframe(pd.DataFrame(summary["top_sources"]), width='stretch', hide_index=True)

                mentions = summary.get("recent_mentions", [])
                if mentions:
                    st.subheader("Mention Timeline")
                    mention_df = pd.DataFrame(mentions)
                    if "published_at" in mention_df.columns:
                        mention_df["date"] = pd.to_datetime(mention_df["published_at"]).dt.date
                        timeline = mention_df.groupby("date").size().reset_index(name="count")
                        st.line_chart(timeline.set_index("date"))

            if st.button("Generate Report", key="comp_report"):
                report = COMPETITOR.generate_report(selected_comp["id"], format="markdown")
                st.markdown(report)

            if st.button("Find Mentions Now", key="comp_find"):
                with st.spinner("Scanning content for mentions..."):
                    try:
                        items_data = _get_all_items_full(100)
                        alert_items = []
                        for r in items_data:
                            alert_items.append(AlertContentItem(id=r.get("id", ""), title=r.get("title", ""), content=r.get("content_cleaned", "") or r.get("content", ""), source=r.get("source", ""), url=r.get("url", ""), published_at=r.get("published_at", "")))
                        mentions_found = COMPETITOR.find_mentions(alert_items)
                        total = sum(len(v) for v in mentions_found.values())
                        st.success(f"Found {total} mention(s)")
                    except Exception as exc:
                        st.error(f"Failed: {exc}")

    with tab_anomaly:
        st.subheader("Anomaly Detection")
        if st.button("Run All Checks", type="primary"):
            with st.spinner("Running anomaly detection checks..."):
                try:
                    items_data = _get_all_items_full(200)
                    for r in items_data:
                        pub = r.get("published_at", datetime.now().isoformat())[:10]
                        ANOMALY.record_daily(pub, source=r.get("source", ""), count=1)

                    findings = ANOMALY.run_all_checks(days=7)
                    if findings:
                        st.warning(f"Found **{len(findings)}** anomaly(ies)")
                        for finding in findings:
                            details = finding.get("details", {})
                            check_type = finding.get("check", "unknown")
                            with st.container():
                                st.markdown(f"**{check_type}**")
                                st.json(details)
                                st.divider()
                    else:
                        st.success("No anomalies detected.")
                except Exception as exc:
                    st.error(f"Anomaly check failed: {exc}")

        st.subheader("Volume Check")
        an_src = st.selectbox("Source for volume check", ["All"] + SOURCES, key="an_src")
        if st.button("Check Volume", key="an_vol"):
            with st.spinner("Checking volume..."):
                try:
                    result = ANOMALY.check_volume_anomaly(source=an_src if an_src != "All" else None)
                    cols = st.columns(4)
                    cols[0].metric("Current", result.get("current_count", 0))
                    cols[1].metric("Expected", result.get("expected_count", 0))
                    cols[2].metric("Z-Score", result.get("z_score", 0))
                    cols[3].markdown(f"**Direction:** {result.get('direction', 'normal')}")
                    if result.get("is_anomaly"):
                        st.error("Anomaly detected!")
                    else:
                        st.success("Volume normal.")
                except Exception as exc:
                    st.error(f"Check failed: {exc}")

        st.subheader("Topic Shift Analysis")
        for topic in TOPICS:
            shift = ANOMALY.check_topic_shift(topic, window_days=14)
            if shift.get("is_shift"):
                st.warning(f"**{topic}**: {shift.get('change_pct', 0)*100:.1f}% change (prev: {shift.get('prev_avg', 0):.1f}, current: {shift.get('current_avg', 0):.1f})")

def _page_workflow_builder():
    st.title("Workflow Builder")

    if "wf_nodes" not in st.session_state:
        st.session_state.wf_nodes = {}
    if "wf_edges" not in st.session_state:
        st.session_state.wf_edges = []
    if "wf_selected_node" not in st.session_state:
        st.session_state.wf_selected_node = None
    if "wf_name" not in st.session_state:
        st.session_state.wf_name = "Untitled Workflow"

    builder = WorkflowBuilder(name=st.session_state.wf_name)

    with st.sidebar:
        st.markdown("### Node Palette")
        node_types = [
            ("Trigger", "schedule, source, topic"),
            ("Collect", "source, max_items, query"),
            ("Filter", "min_relevance, topics, condition"),
            ("Classify", "method"),
            ("Notify", "channel, template, recipients"),
            ("Export", "format, path"),
            ("Condition", "if_expression"),
            ("Transform", "script"),
            ("Delay", "seconds"),
        ]
        for ntype, params in node_types:
            if st.button(f"+ {ntype}", key=f"palette_{ntype}", width='stretch'):
                if ntype == "Trigger":
                    builder.add_trigger(schedule="hourly")
                elif ntype == "Collect":
                    builder.add_collector(source="linkedin")
                elif ntype == "Filter":
                    builder.add_filter()
                elif ntype == "Classify":
                    builder.add_classifier()
                elif ntype == "Notify":
                    builder.add_notifier(channel="slack")
                elif ntype == "Export":
                    builder.add_exporter()
                elif ntype == "Condition":
                    builder.add_condition("True")
                elif ntype == "Transform":
                    builder.add_transform("result = ctx")
                elif ntype == "Delay":
                    builder.add_delay(5)

                for nid, node in builder.nodes.items():
                    if nid not in st.session_state.wf_nodes:
                        st.session_state.wf_nodes[nid] = node.to_dict()
                st.rerun()

    col_canvas, col_config = st.columns([3, 1])

    with col_canvas:
        st.subheader(f"Canvas: {st.session_state.wf_name}")

        nodes = list(st.session_state.wf_nodes.values())
        if not nodes:
            st.info("Add nodes from the palette in the sidebar.")
        else:
            ncols = st.columns(max(len(nodes), 1))
            for i, node in enumerate(nodes):
                col_idx = i % len(ncols) if ncols else 0
                with ncols[col_idx]:
                    ntype = node.get("type", "unknown")
                    color_map = {"trigger": "blue", "collect": "green", "filter": "orange", "classify": "violet", "notify": "red", "export": "grey", "condition": "yellow", "transform": "teal", "delay": "brown"}
                    color = color_map.get(ntype, "grey")
                    st.markdown(f":{color}[**{node.get('name', 'Node')}**] ({ntype})")
                    st.caption(f"ID: {node['id'][:8]}")
                    config = node.get("config", {})
                    for k, v in list(config.items())[:3]:
                        st.caption(f"{k}: {str(v)[:20]}")
                    if st.button("Select", key=f"sel_{node['id']}"):
                        st.session_state.wf_selected_node = node["id"]
                        st.rerun()
                    st.divider()

        st.subheader("Connections")
        if len(nodes) > 1:
            src_ids = {n["id"]: f"{n.get('name', '?')} ({n['id'][:8]})" for n in nodes}
            conn_src = st.selectbox("Source Node", list(src_ids.keys()), format_func=lambda x: src_ids.get(x, x), key="conn_src")
            conn_tgt = st.selectbox("Target Node", list(src_ids.keys()), format_func=lambda x: src_ids.get(x, x), key="conn_tgt")
            if st.button("Add Edge", key="conn_add"):
                st.session_state.wf_edges.append({"from": conn_src, "to": conn_tgt, "label": ""})
                st.success("Edge added!")
                st.rerun()

        if st.session_state.wf_edges:
            st.subheader("Edges")
            for edge in st.session_state.wf_edges:
                st.markdown(f"`{edge['from'][:8]}` → `{edge['to'][:8]}`")

    with col_config:
        st.subheader("Node Config")
        selected_nid = st.session_state.wf_selected_node
        if selected_nid and selected_nid in st.session_state.wf_nodes:
            node = st.session_state.wf_nodes[selected_nid]
            st.markdown(f"### {node.get('name', 'Node')}")
            st.markdown(f"**Type:** {node.get('type', '?')}")
            st.markdown(f"**ID:** `{selected_nid}`")
            config = node.get("config", {})
            new_config = {}
            for k, v in config.items():
                if isinstance(v, str):
                    new_config[k] = st.text_input(k, value=v, key=f"cfg_{selected_nid}_{k}")
                elif isinstance(v, (int, float)):
                    new_config[k] = st.number_input(k, value=v, key=f"cfg_{selected_nid}_{k}")
                elif isinstance(v, list):
                    new_config[k] = st.text_input(k, value=", ".join(v), key=f"cfg_{selected_nid}_{k}").split(", ")
                else:
                    new_config[k] = v
            if st.button("Update Config", key="cfg_update"):
                st.session_state.wf_nodes[selected_nid]["config"] = new_config
                st.success("Config updated!")
        else:
            st.info("Click 'Select' on a node to edit its config.")

    st.divider()

    wf_actions_cols = st.columns(5)
    with wf_actions_cols[0]:
        if st.button("Save Workflow", type="primary"):
            try:
                wf_nodes_list = list(st.session_state.wf_nodes.values())
                wf_data = {"id": str(Path(settings.DATA_DIR) / "workflows" / "custom.json"), "name": st.session_state.wf_name, "description": "", "nodes": wf_nodes_list, "edges": st.session_state.wf_edges, "created_at": datetime.utcnow().isoformat()}
                wf_id = WF_STORAGE.save_workflow(wf_data)
                st.success(f"Workflow saved! (ID: {wf_id[:12] if wf_id else '?'})")
            except Exception as exc:
                st.error(f"Save failed: {exc}")

    with wf_actions_cols[1]:
        saved_wfs = WF_STORAGE.list_workflows(include_disabled=True)
        if saved_wfs:
            wf_opts = {w["name"]: w["id"] for w in saved_wfs}
            selected_wf_name = st.selectbox("Load", list(wf_opts.keys()), key="wf_load")
            if st.button("Load"):
                wf_id = wf_opts[selected_wf_name]
                loaded = WF_STORAGE.get_workflow(wf_id)
                if loaded and loaded.get("workflow"):
                    wf = loaded["workflow"]
                    st.session_state.wf_nodes = {n["id"]: n for n in wf.get("nodes", [])}
                    st.session_state.wf_edges = wf.get("edges", [])
                    st.session_state.wf_name = loaded.get("name", "Loaded Workflow")
                    st.success(f"Loaded '{selected_wf_name}'")
                    st.rerun()

    with wf_actions_cols[2]:
        if st.button("Validate"):
            wf_nodes_list = list(st.session_state.wf_nodes.values())
            wf_data = {"nodes": wf_nodes_list, "edges": st.session_state.wf_edges}
            wf_obj = WorkflowBuilder()
            wf_obj.load = lambda p: None
            wf_obj.nodes = {n["id"]: type("obj", (), {"to_dict": lambda self=n: self, "name": n.get("name", "?"), "type": type("t", (), {"value": n.get("type", "")})()})() for n in wf_nodes_list}
            wf_obj.edges = st.session_state.wf_edges
            errors = wf_obj.validate()
            if errors:
                for err in errors:
                    st.error(err)
            else:
                st.success("Workflow is valid!")

    with wf_actions_cols[3]:
        if st.button("Execute"):
            wf_nodes_list = list(st.session_state.wf_nodes.values())
            wf_data = {"id": "custom", "name": st.session_state.wf_name, "nodes": wf_nodes_list, "edges": st.session_state.wf_edges}
            with st.spinner("Executing workflow..."):
                try:
                    result = WF_ENGINE.execute(wf_data)
                    st.json(result)
                except Exception as exc:
                    st.error(f"Execution failed: {exc}")

    with wf_actions_cols[4]:
        if st.button("Mermaid Preview"):
            wf_nodes_list = list(st.session_state.wf_nodes.values())
            wf_obj = WorkflowBuilder()
            wf_obj.nodes = {n["id"]: type("obj", (), {"to_dict": lambda self=n: self, "name": n.get("name", "?"), "type": type("t", (), {"value": n.get("type", "")})()})() for n in wf_nodes_list}
            wf_obj.edges = st.session_state.wf_edges
            mermaid = wf_obj.to_mermaid()
            st.code(mermaid, language="mermaid")

    st.divider()
    st.subheader("Execution History")
    if st.button("Refresh History"):
        st.rerun()
    all_execs = WF_ENGINE.list_executions(limit=20)
    if all_execs:
        df_exec = pd.DataFrame(all_execs)
        st.dataframe(df_exec, width='stretch', hide_index=True)
    else:
        st.info("No execution history yet.")

    st.subheader("Workflow Stats")
    stats = WF_STORAGE.get_stats()
    if stats:
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Total Workflows", stats.get("total_workflows", 0))
        col_b.metric("Active", stats.get("active_workflows", 0))
        col_c.metric("Total Executions", stats.get("total_executions", 0))
        col_d.metric("Success Rate", f"{stats.get('success_rate', 0)}%")

_PAGE_FUNCS = {
    "Dashboard": _page_dashboard,
    "Search": _page_search,
    "Sources": _page_sources,
    "Topics": _page_topics,
    "Digest": _page_digest,
    "Schedule": _page_schedule,
    "Settings": _page_settings,
    "AI Lab": _page_ai_lab,
    "RAG Chat": _page_rag_chat,
    "Analytics": _page_analytics,
    "Notifications": _page_notifications,
    "Processing": _page_processing,
    "Enterprise Search": _page_enterprise_search,
    "MLOps Lab": _page_mlops_lab,
    "Integrations": _page_integrations,
    "Compliance": _page_compliance,
    "Collaboration": _page_collaboration,
    "Monitoring & Alerts": _page_monitoring,
    "Workflow Builder": _page_workflow_builder,
}

if page in _PAGE_FUNCS:
    _PAGE_FUNCS[page]()
