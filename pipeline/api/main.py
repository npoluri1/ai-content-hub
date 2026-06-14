"""FastAPI backend for AI Content Hub."""

from fastapi import FastAPI, Query, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
import asyncio
import uvicorn

from ..core.config import settings
from ..pipeline.orchestrator import ContentOrchestrator
from ..storage.vector_store import VectorStore
from ..storage.sql_store import SQLStore
from ..core.models import ContentItem, ClassifiedItem
from ..ai.summarizer import summarize, batch_summarize
from ..ai.recommender import recommend_similar, recommend_for_query, recommend_by_topic, get_personalized_feed
from ..ai.rag_chat import ChatEngine
from ..ai.tagger import auto_tag, tag_items, extract_entities
from ..analytics.trends import TrendAnalyzer
from ..analytics.wordcloud import generate_wordcloud, get_frequency_table
from ..analytics.exporter import export_to_csv, export_to_json, export_to_markdown, export_source_report, export_topic_report
from ..notifications.email_sender import NewsletterSender
from ..notifications.telegram_bot import TelegramNotifier
from ..notifications.webhooks import WebhookDispatcher
from ..processing.fulltext import FullTextExtractor
from ..processing.dedup import Deduplicator
from ..auth.jwt_auth import JWTAuth
from ..auth.middleware import AuthMiddleware
from ..search.faceted_search import FacetedSearch
from ..search.saved_searches import SavedSearch
from ..search.search_analytics import SearchAnalytics
from ..mlops.sentiment import SentimentAnalyzer
from ..mlops.quality_score import QualityScorer
from ..mlops.language_detect import LanguageDetector
from ..mlops.enrichment import EnrichmentPipeline
from ..enterprise.integrations.slack_bot import SlackBot
from ..enterprise.integrations.jira_integration import JiraIntegration
from ..enterprise.integrations.teams_integration import TeamsIntegration
from ..enterprise.integrations.notion_enhanced import NotionEnhanced
from ..enterprise.compliance.pii_detector import PIIDetector
from ..enterprise.compliance.audit_log import AuditLogger
from ..enterprise.compliance.data_retention import DataRetention
from ..enterprise.compliance.content_moderation import ContentModerator
from ..enterprise.collaboration.workspaces import WorkspaceManager
from ..enterprise.collaboration.comments import CommentSystem
from ..enterprise.collaboration.approval import ApprovalWorkflow
from ..enterprise.monitoring.alerts import AlertEngine
from ..enterprise.monitoring.competitor_tracker import CompetitorTracker
from ..enterprise.monitoring.anomaly_detection import AnomalyDetector
from ..workflow.builder import WorkflowBuilder
from ..workflow.engine import WorkflowEngine
from ..workflow.storage import WorkflowStorage

app = FastAPI(title="AI Content Hub API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.API_CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = ContentOrchestrator()
vector_store = VectorStore()
sql_store = SQLStore()


# === Pydantic Models ===

class RunResponse(BaseModel):
    status: str
    results: dict
    timestamp: str

class SearchResult(BaseModel):
    id: str
    content: str
    metadata: dict
    distance: float = 0

class StatsResponse(BaseModel):
    total_items: int
    by_source: dict
    by_topic: dict

class ScheduleRequest(BaseModel):
    interval_minutes: int = 360
    sources: list[str] = []

class SummarizeRequest(BaseModel):
    text: str
    length: str = "normal"

class SummarizeBatchRequest(BaseModel):
    items: list[dict]

class RAGQueryRequest(BaseModel):
    question: str
    n_context: int = 5

class TagRequest(BaseModel):
    title: str
    content: str
    hashtags: list[str] = []

class TagBatchRequest(BaseModel):
    items: list[dict]

class ExportRequest(BaseModel):
    items: list[dict]
    filename: str = "export"

class EmailDigestRequest(BaseModel):
    to_email: str
    topics: list[str]
    subject: Optional[str] = None

class TelegramSendRequest(BaseModel):
    message: str

class TelegramDigestRequest(BaseModel):
    topics: list[str]

class WebhookRegisterRequest(BaseModel):
    name: str
    url: str
    events: list[str]
    secret: Optional[str] = None

class WebhookDispatchRequest(BaseModel):
    event: str
    payload: dict

class ExtractRequest(BaseModel):
    url: str

class ExtractBatchRequest(BaseModel):
    urls: list[str]

class DedupRequest(BaseModel):
    items: list[dict]
    threshold: float = 0.85

class AuthRegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "user"

class AuthLoginRequest(BaseModel):
    username: str
    password: str

class AuthVerifyRequest(BaseModel):
    token: str

class FacetedSearchRequest(BaseModel):
    query: str
    facets: dict
    page: int = 1
    page_size: int = 20
    sort: str = "relevance"

class SaveSearchRequest(BaseModel):
    name: str
    query: str
    facets: dict = {}
    user: str
    notify_on_new: bool = False
    frequency: str = "daily"

class SentimentRequest(BaseModel):
    text: str

class SentimentBatchRequest(BaseModel):
    texts: list[str]

class QualityRequest(BaseModel):
    text: str

class LanguageRequest(BaseModel):
    text: str

class TranslateRequest(BaseModel):
    text: str
    target_language: str
    source_language: Optional[str] = None

class EnrichRequest(BaseModel):
    title: str
    content: str
    source: str
    hashtags: list[str] = []

class SlackSendRequest(BaseModel):
    channel: str
    text: str
    blocks: Optional[list[dict]] = None

class SlackContentRequest(BaseModel):
    channel: str
    item: dict

class JiraIssueRequest(BaseModel):
    item: dict
    issue_type: str = "Task"
    priority: str = "Medium"

class TeamsSendRequest(BaseModel):
    text: str
    title: str = ""

class TeamsCardRequest(BaseModel):
    item: dict

class NotionPageRequest(BaseModel):
    item: dict

class NotionDigestRequest(BaseModel):
    items: list[dict]
    title: str

class PIIDetectRequest(BaseModel):
    text: str

class PIIRedactRequest(BaseModel):
    text: str

class ModerateRequest(BaseModel):
    text: str

class RetentionEnforceRequest(BaseModel):
    dry_run: bool = True

class RetentionPolicyRequest(BaseModel):
    source: str
    retention_days: int

class CreateWorkspaceRequest(BaseModel):
    name: str
    description: str = ""
    owner: str

class AddMemberRequest(BaseModel):
    user: str
    role: str = "viewer"

class AddContentRequest(BaseModel):
    item: dict
    added_by: str

class AddCommentRequest(BaseModel):
    content_id: str
    user: str
    text: str
    parent_id: Optional[str] = None

class AddReactionRequest(BaseModel):
    user: str
    reaction: str

class CreateWorkflowRequest(BaseModel):
    name: str
    steps: list[dict]
    created_by: str

class SubmitApprovalRequest(BaseModel):
    content_id: str
    workflow_id: str
    submitted_by: str

class ApproveRequest(BaseModel):
    step_name: str
    user: str
    comment: str = ""

class RejectRequest(BaseModel):
    step_name: str
    user: str
    reason: str = ""

class CreateAlertRequest(BaseModel):
    name: str
    keywords: list[str]
    sources: list[str] = []
    topics: list[str] = []
    channels: list[str] = ["slack"]
    user: str

class SuppressAlertRequest(BaseModel):
    hours: int = 24

class AddCompetitorRequest(BaseModel):
    name: str
    domains: list[str] = []
    linkedin_urls: list[str] = []
    keywords: list[str] = []
    notes: str = ""

class CreateWorkflowDefRequest(BaseModel):
    name: str
    description: str = ""

class UpdateWorkflowRequest(BaseModel):
    workflow: dict


# === Existing Routes ===

@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME, "timestamp": datetime.now().isoformat()}


@app.post("/run", response_model=RunResponse)
def run_pipeline(sources: Optional[str] = Query(None, description="Comma-separated source names")):
    source_list = [s.strip() for s in sources.split(",")] if sources else None
    results = orchestrator.run_all(source_list)
    return RunResponse(status="success", results=results, timestamp=datetime.now().isoformat())


@app.get("/search", response_model=list[SearchResult])
def search_items(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    source: Optional[str] = Query(None),
):
    results = vector_store.search(q, n_results=limit, filter_source=source)
    if not results:
        results = sql_store.search(q, limit=limit)
    return results


@app.get("/topics/{topic}")
def get_by_topic(topic: str, limit: int = 20):
    results = vector_store.search_by_topic(topic, n_results=limit)
    if not results:
        results = sql_store.get_by_topic(topic, limit=limit)
    return results


@app.get("/sources/{source}")
def get_by_source(source: str, limit: int = 50):
    return sql_store.get_by_source(source, limit=limit)


@app.get("/stats", response_model=StatsResponse)
def get_stats():
    vs_count = vector_store.count()
    sql_stats = sql_store.get_stats()
    return StatsResponse(
        total_items=max(vs_count, sql_stats["total"]),
        by_source=sql_stats.get("by_source", {}),
        by_topic=sql_stats.get("by_topic", {}),
    )


@app.get("/recent")
def get_recent(limit: int = 50):
    return vector_store.get_recent(limit=limit)


@app.post("/schedule")
def set_schedule(req: ScheduleRequest):
    from ..pipeline.scheduler import run_pipeline_job
    import threading
    t = threading.Thread(target=run_pipeline_job, daemon=True)
    t.start()
    return {"status": "scheduled", "interval_minutes": req.interval_minutes, "sources": req.sources}


@app.get("/digest")
def get_digest():
    items = sql_store.get_by_topic("", limit=100)
    topics = [t.strip() for t in settings.DIGEST_TOPICS.split(",")]
    lines = [f"# AI Content Hub Digest", f"**Generated:** {datetime.now().isoformat()}", ""]
    for topic in topics:
        topic_items = [i for i in items if topic in i.get("topics", "")][:10]
        if not topic_items:
            continue
        lines.append(f"## {topic}")
        for item in topic_items:
            snippet = item.get("content", "")[:150].replace("\n", " ")
            lines.append(f"- [{item.get('source', '').upper()}] **{item.get('title', '')}** \u2014 {snippet}...")
            if item.get("url"):
                lines.append(f"  {item['url']}")
        lines.append("")
    return {"digest": "\n".join(lines)}


# === AI Routes ===

@app.post("/ai/summarize")
def ai_summarize(req: SummarizeRequest):
    try:
        result = summarize(req.text, length=req.length)
        return {"summary": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/summarize-batch")
def ai_summarize_batch(req: SummarizeBatchRequest):
    try:
        results = batch_summarize(req.items)
        return {"summaries": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ai/recommend/{item_id}")
def ai_recommend_similar(item_id: str, n: int = Query(5, ge=1, le=50)):
    try:
        results = recommend_similar(item_id, n=n)
        return {"recommendations": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ai/recommend/query")
def ai_recommend_query(q: str = Query(...), n: int = Query(5, ge=1, le=50)):
    try:
        results = recommend_for_query(q, n=n)
        return {"recommendations": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ai/recommend/topic/{topic}")
def ai_recommend_topic(topic: str, n: int = Query(5, ge=1, le=50)):
    try:
        results = recommend_by_topic(topic, n=n)
        return {"recommendations": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ai/recommend/feed")
def ai_personalized_feed(user_id: str = Query(...), n: int = Query(10, ge=1, le=50)):
    try:
        results = get_personalized_feed(user_id, n=n)
        return {"feed": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/rag/query")
def ai_rag_query(req: RAGQueryRequest):
    try:
        engine = ChatEngine()
        answer, sources = engine.query(req.question, n_context=req.n_context)
        return {"answer": answer, "sources": sources}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/tag")
def ai_tag(req: TagRequest):
    try:
        tags = auto_tag(req.title, req.content, hashtags=req.hashtags)
        entities = extract_entities(req.content)
        return {"tags": tags, "entities": entities}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/tag-batch")
def ai_tag_batch(req: TagBatchRequest):
    try:
        tagged = tag_items(req.items)
        return {"tagged": tagged}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Analytics Routes ===

@app.get("/analytics/trends/topic/{topic}")
def analytics_trends_topic(topic: str, days: int = Query(30, ge=1, le=365)):
    try:
        analyzer = TrendAnalyzer()
        results = analyzer.trends_by_topic(topic, days=days)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/trends/all")
def analytics_trends_all(days: int = Query(30, ge=1, le=365)):
    try:
        analyzer = TrendAnalyzer()
        results = analyzer.trends_all(days=days)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/trends/movers")
def analytics_trends_movers(days: int = Query(7, ge=1, le=90)):
    try:
        analyzer = TrendAnalyzer()
        results = analyzer.top_movers(days=days)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/trends/hours")
def analytics_trends_hours(source: Optional[str] = Query(None), days: int = Query(30, ge=1, le=365)):
    try:
        analyzer = TrendAnalyzer()
        results = analyzer.hourly_trends(source=source, days=days)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/wordcloud")
def analytics_wordcloud(topic: Optional[str] = Query(None), source: Optional[str] = Query(None)):
    try:
        image_b64 = generate_wordcloud(topic=topic, source=source)
        return {"image_base64": image_b64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/frequencies")
def analytics_frequencies(topic: Optional[str] = Query(None), top_n: int = Query(50, ge=1, le=500)):
    try:
        table = get_frequency_table(topic=topic, top_n=top_n)
        return {"frequencies": table}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/bigrams")
def analytics_bigrams(topic: Optional[str] = Query(None), top_n: int = Query(20, ge=1, le=100)):
    try:
        analyzer = TrendAnalyzer()
        results = analyzer.top_bigrams(topic=topic, top_n=top_n)
        return {"bigrams": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Export Routes ===

@app.post("/export/csv")
def export_csv(req: ExportRequest):
    try:
        output = export_to_csv(req.items)
        return {"csv": output, "filename": f"{req.filename}.csv"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/export/json")
def export_json(req: ExportRequest):
    try:
        output = export_to_json(req.items)
        return {"json": output, "filename": f"{req.filename}.json"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/export/source-report/{source}")
def export_source_report(source: str, days: int = Query(7, ge=1, le=365), format: str = Query("json")):
    try:
        if format == "csv":
            output = export_source_report(source, days=days, fmt="csv")
        elif format == "markdown":
            output = export_source_report(source, days=days, fmt="markdown")
        else:
            output = export_source_report(source, days=days, fmt="json")
        return {"report": output, "source": source, "format": format}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/export/topic-report/{topic}")
def export_topic_report(topic: str, days: int = Query(30, ge=1, le=365), format: str = Query("json")):
    try:
        if format == "csv":
            output = export_topic_report(topic, days=days, fmt="csv")
        elif format == "markdown":
            output = export_topic_report(topic, days=days, fmt="markdown")
        else:
            output = export_topic_report(topic, days=days, fmt="json")
        return {"report": output, "topic": topic, "format": format}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Notification Routes ===

@app.post("/notifications/email/digest")
def notify_email_digest(req: EmailDigestRequest):
    try:
        sender = NewsletterSender()
        result = sender.send_digest(to_email=req.to_email, topics=req.topics, subject=req.subject)
        return {"status": "sent", "to": req.to_email, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/notifications/telegram/send")
def notify_telegram_send(req: TelegramSendRequest):
    try:
        notifier = TelegramNotifier()
        result = notifier.send_message(req.message)
        return {"status": "sent", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/notifications/telegram/digest")
def notify_telegram_digest(req: TelegramDigestRequest):
    try:
        notifier = TelegramNotifier()
        result = notifier.send_digest(topics=req.topics)
        return {"status": "sent", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/notifications/webhooks/register")
def notify_webhook_register(req: WebhookRegisterRequest):
    try:
        dispatcher = WebhookDispatcher()
        webhook = dispatcher.register(name=req.name, url=req.url, events=req.events, secret=req.secret)
        return {"status": "registered", "webhook": webhook}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/notifications/webhooks/dispatch")
def notify_webhook_dispatch(req: WebhookDispatchRequest):
    try:
        dispatcher = WebhookDispatcher()
        result = dispatcher.dispatch(event=req.event, payload=req.payload)
        return {"status": "dispatched", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Processing Routes ===

@app.post("/process/extract")
def process_extract(req: ExtractRequest):
    try:
        extractor = FullTextExtractor()
        article = extractor.extract(req.url)
        return {"article": article}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process/extract-batch")
def process_extract_batch(req: ExtractBatchRequest):
    try:
        extractor = FullTextExtractor()
        articles = extractor.extract_batch(req.urls)
        return {"articles": articles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process/dedup")
def process_dedup(req: DedupRequest):
    try:
        deduper = Deduplicator()
        result = deduper.deduplicate(req.items, threshold=req.threshold)
        return {"deduplicated": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Auth Routes ===

@app.post("/auth/register")
def auth_register(req: AuthRegisterRequest):
    try:
        auth = JWTAuth()
        user = auth.register(username=req.username, password=req.password, role=req.role)
        return {"user": user}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login")
def auth_login(req: AuthLoginRequest):
    try:
        auth = JWTAuth()
        token, user = auth.login(username=req.username, password=req.password)
        if not token:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {"token": token, "user": user}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/auth/me")
def auth_me(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    try:
        auth = JWTAuth()
        token = authorization.replace("Bearer ", "")
        payload = auth.verify_token(token)
        user = auth.get_user(payload.get("sub"))
        return {"user": user}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/auth/verify")
def auth_verify(req: AuthVerifyRequest):
    try:
        auth = JWTAuth()
        payload = auth.verify_token(req.token)
        return {"valid": payload is not None, "payload": payload}
    except Exception as e:
        return {"valid": False, "payload": None, "error": str(e)}


# === Enterprise Search Routes ===

@app.post("/search/faceted")
def search_faceted(req: FacetedSearchRequest):
    try:
        fs = FacetedSearch()
        results = fs.search(query=req.query, facets=req.facets, page=req.page, page_size=req.page_size, sort=req.sort)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search/autocomplete")
def search_autocomplete(q: str = Query(...), field: str = Query("title"), limit: int = Query(10, ge=1, le=50)):
    try:
        fs = FacetedSearch()
        suggestions = fs.autocomplete(q, field=field, limit=limit)
        return {"suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search/facets")
def search_get_facets():
    try:
        fs = FacetedSearch()
        facets = fs.get_facets()
        return {"facets": facets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/save")
def search_save(req: SaveSearchRequest):
    try:
        ss = SavedSearch()
        saved = ss.save(name=req.name, query=req.query, facets=req.facets, user=req.user, notify_on_new=req.notify_on_new, frequency=req.frequency)
        return {"saved_search": saved}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search/saved")
def search_list_saved(user: str = Query(...)):
    try:
        ss = SavedSearch()
        saved_list = ss.list_by_user(user)
        return {"saved_searches": saved_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/search/saved/{search_id}")
def search_delete_saved(search_id: str):
    try:
        ss = SavedSearch()
        ss.delete(search_id)
        return {"status": "deleted", "id": search_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/saved/{search_id}/execute")
def search_execute_saved(search_id: str):
    try:
        ss = SavedSearch()
        results = ss.execute(search_id)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search/analytics/popular")
def search_analytics_popular(limit: int = Query(20, ge=1, le=100)):
    try:
        sa = SearchAnalytics()
        popular = sa.popular_searches(limit=limit)
        return {"popular_searches": popular}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search/analytics/zeros")
def search_analytics_zeros(limit: int = Query(20, ge=1, le=100)):
    try:
        sa = SearchAnalytics()
        zeros = sa.zero_result_searches(limit=limit)
        return {"zero_result_searches": zeros}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search/analytics/trends")
def search_analytics_trends(days: int = Query(30, ge=1, le=365)):
    try:
        sa = SearchAnalytics()
        trends = sa.search_volume_trends(days=days)
        return {"trends": trends}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Enterprise MLOps Routes ===

@app.post("/mlops/sentiment")
def mlops_sentiment(req: SentimentRequest):
    try:
        sa = SentimentAnalyzer()
        result = sa.analyze(req.text)
        return {"sentiment": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mlops/sentiment/batch")
def mlops_sentiment_batch(req: SentimentBatchRequest):
    try:
        sa = SentimentAnalyzer()
        results = sa.analyze_batch(req.texts)
        return {"sentiments": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mlops/sentiment/topic/{topic}")
def mlops_sentiment_topic(topic: str, days: int = Query(30, ge=1, le=365)):
    try:
        sa = SentimentAnalyzer()
        result = sa.topic_sentiment(topic, days=days)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mlops/quality")
def mlops_quality(req: QualityRequest):
    try:
        qs = QualityScorer()
        score = qs.score(req.text)
        return {"quality_score": score}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mlops/language")
def mlops_language(req: LanguageRequest):
    try:
        ld = LanguageDetector()
        result = ld.detect(req.text)
        return {"language": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mlops/language/translate")
def mlops_translate(req: TranslateRequest):
    try:
        ld = LanguageDetector()
        result = ld.translate(req.text, target_language=req.target_language, source_language=req.source_language)
        return {"translated": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mlops/enrich")
def mlops_enrich(req: EnrichRequest):
    try:
        ep = EnrichmentPipeline()
        enriched = ep.enrich(title=req.title, content=req.content, source=req.source, hashtags=req.hashtags)
        return {"enriched": enriched}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mlops/quality/trending")
def mlops_quality_trending(topic: Optional[str] = Query(None), limit: int = Query(20, ge=1, le=100)):
    try:
        qs = QualityScorer()
        trending = qs.trending_content(topic=topic, limit=limit)
        return {"trending": trending}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Enterprise Integration Routes ===

@app.post("/integrations/slack/send")
def integrations_slack_send(req: SlackSendRequest):
    try:
        sb = SlackBot()
        result = sb.send_message(channel=req.channel, text=req.text, blocks=req.blocks)
        return {"status": "sent", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/integrations/slack/content")
def integrations_slack_content(req: SlackContentRequest):
    try:
        sb = SlackBot()
        result = sb.send_content_card(channel=req.channel, item=req.item)
        return {"status": "sent", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/integrations/jira/issue")
def integrations_jira_issue(req: JiraIssueRequest):
    try:
        ji = JiraIntegration()
        issue = ji.create_issue(item=req.item, issue_type=req.issue_type, priority=req.priority)
        return {"issue": issue}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/integrations/teams/send")
def integrations_teams_send(req: TeamsSendRequest):
    try:
        ti = TeamsIntegration()
        result = ti.send_message(text=req.text, title=req.title)
        return {"status": "sent", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/integrations/teams/card")
def integrations_teams_card(req: TeamsCardRequest):
    try:
        ti = TeamsIntegration()
        result = ti.send_content_card(item=req.item)
        return {"status": "sent", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/integrations/notion/page")
def integrations_notion_page(req: NotionPageRequest):
    try:
        ne = NotionEnhanced()
        page = ne.create_page(item=req.item)
        return {"page": page}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/integrations/notion/digest")
def integrations_notion_digest(req: NotionDigestRequest):
    try:
        ne = NotionEnhanced()
        result = ne.create_digest_database(items=req.items, title=req.title)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Compliance Routes ===

@app.post("/compliance/pii/detect")
def compliance_pii_detect(req: PIIDetectRequest):
    try:
        pd = PIIDetector()
        result = pd.detect(req.text)
        return {"pii_detected": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/compliance/pii/redact")
def compliance_pii_redact(req: PIIRedactRequest):
    try:
        pd = PIIDetector()
        redacted = pd.redact(req.text)
        return {"redacted": redacted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/compliance/moderate")
def compliance_moderate(req: ModerateRequest):
    try:
        cm = ContentModerator()
        result = cm.moderate(req.text)
        return {"moderation": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/compliance/audit")
def compliance_audit_query(actor: Optional[str] = Query(None), event: Optional[str] = Query(None), resource_type: Optional[str] = Query(None), limit: int = Query(100, ge=1, le=1000)):
    try:
        al = AuditLogger()
        entries = al.query(actor=actor, event=event, resource_type=resource_type, limit=limit)
        return {"audit_entries": entries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/compliance/audit/summary")
def compliance_audit_summary(days: int = Query(30, ge=1, le=365)):
    try:
        al = AuditLogger()
        summary = al.summary(days=days)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/compliance/retention/enforce")
def compliance_retention_enforce(req: RetentionEnforceRequest):
    try:
        dr = DataRetention()
        result = dr.enforce_policies(dry_run=req.dry_run)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/compliance/retention/policies")
def compliance_retention_policies():
    try:
        dr = DataRetention()
        policies = dr.list_policies()
        return {"policies": policies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/compliance/retention/policy")
def compliance_retention_add_policy(req: RetentionPolicyRequest):
    try:
        dr = DataRetention()
        policy = dr.add_policy(source=req.source, retention_days=req.retention_days)
        return {"policy": policy}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Collaboration Routes ===

@app.post("/collab/workspaces")
def collab_create_workspace(req: CreateWorkspaceRequest):
    try:
        wm = WorkspaceManager()
        ws = wm.create(name=req.name, description=req.description, owner=req.owner)
        return {"workspace": ws}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collab/workspaces")
def collab_list_workspaces(user: str = Query(...)):
    try:
        wm = WorkspaceManager()
        workspaces = wm.list_by_user(user)
        return {"workspaces": workspaces}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collab/workspaces/{ws_id}")
def collab_get_workspace(ws_id: str):
    try:
        wm = WorkspaceManager()
        ws = wm.get(ws_id)
        return {"workspace": ws}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collab/workspaces/{ws_id}/members")
def collab_add_member(ws_id: str, req: AddMemberRequest):
    try:
        wm = WorkspaceManager()
        member = wm.add_member(ws_id, user=req.user, role=req.role)
        return {"member": member}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/collab/workspaces/{ws_id}/members/{user}")
def collab_remove_member(ws_id: str, user: str):
    try:
        wm = WorkspaceManager()
        wm.remove_member(ws_id, user)
        return {"status": "removed", "user": user}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collab/workspaces/{ws_id}/content")
def collab_add_content(ws_id: str, req: AddContentRequest):
    try:
        wm = WorkspaceManager()
        content = wm.add_content(ws_id, item=req.item, added_by=req.added_by)
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collab/workspaces/{ws_id}/content")
def collab_get_content(ws_id: str, topic: Optional[str] = Query(None), source: Optional[str] = Query(None), limit: int = Query(50, ge=1, le=200)):
    try:
        wm = WorkspaceManager()
        content = wm.get_content(ws_id, topic=topic, source=source, limit=limit)
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collab/comments")
def collab_add_comment(req: AddCommentRequest):
    try:
        cs = CommentSystem()
        comment = cs.add_comment(content_id=req.content_id, user=req.user, text=req.text, parent_id=req.parent_id)
        return {"comment": comment}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collab/comments/{content_id}")
def collab_get_comments(content_id: str):
    try:
        cs = CommentSystem()
        comments = cs.get_comments(content_id)
        return {"comments": comments}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collab/comments/{comment_id}/reaction")
def collab_add_reaction(comment_id: str, req: AddReactionRequest):
    try:
        cs = CommentSystem()
        result = cs.add_reaction(comment_id, user=req.user, reaction=req.reaction)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collab/approval/workflow")
def collab_create_approval_workflow(req: CreateWorkflowRequest):
    try:
        aw = ApprovalWorkflow()
        wf = aw.create_workflow(name=req.name, steps=req.steps, created_by=req.created_by)
        return {"workflow": wf}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collab/approval/submit")
def collab_submit_approval(req: SubmitApprovalRequest):
    try:
        aw = ApprovalWorkflow()
        submission = aw.submit(content_id=req.content_id, workflow_id=req.workflow_id, submitted_by=req.submitted_by)
        return {"submission": submission}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collab/approval/{submission_id}/approve")
def collab_approve_step(submission_id: str, req: ApproveRequest):
    try:
        aw = ApprovalWorkflow()
        result = aw.approve(submission_id, step_name=req.step_name, user=req.user, comment=req.comment)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collab/approval/{submission_id}/reject")
def collab_reject_step(submission_id: str, req: RejectRequest):
    try:
        aw = ApprovalWorkflow()
        result = aw.reject(submission_id, step_name=req.step_name, user=req.user, reason=req.reason)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/collab/approval/pending/{user}")
def collab_pending_approvals(user: str):
    try:
        aw = ApprovalWorkflow()
        pending = aw.get_pending(user)
        return {"pending_approvals": pending}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Monitoring Routes ===

@app.post("/monitoring/alerts")
def monitoring_create_alert(req: CreateAlertRequest):
    try:
        ae = AlertEngine()
        alert = ae.create_alert(name=req.name, keywords=req.keywords, sources=req.sources, topics=req.topics, channels=req.channels, user=req.user)
        return {"alert": alert}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/monitoring/alerts")
def monitoring_list_alerts(user: str = Query(...)):
    try:
        ae = AlertEngine()
        alerts = ae.list_alerts(user)
        return {"alerts": alerts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/monitoring/alerts/{alert_id}")
def monitoring_delete_alert(alert_id: str):
    try:
        ae = AlertEngine()
        ae.delete_alert(alert_id)
        return {"status": "deleted", "id": alert_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/monitoring/alerts/{alert_id}/suppress")
def monitoring_suppress_alert(alert_id: str, req: SuppressAlertRequest):
    try:
        ae = AlertEngine()
        result = ae.suppress_alert(alert_id, hours=req.hours)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/monitoring/competitors")
def monitoring_add_competitor(req: AddCompetitorRequest):
    try:
        ct = CompetitorTracker()
        competitor = ct.add_competitor(name=req.name, domains=req.domains, linkedin_urls=req.linkedin_urls, keywords=req.keywords, notes=req.notes)
        return {"competitor": competitor}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/monitoring/competitors")
def monitoring_list_competitors():
    try:
        ct = CompetitorTracker()
        competitors = ct.list_competitors()
        return {"competitors": competitors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/monitoring/competitors/{comp_id}/summary")
def monitoring_competitor_summary(comp_id: str, days: int = Query(30, ge=1, le=365)):
    try:
        ct = CompetitorTracker()
        summary = ct.get_summary(comp_id, days=days)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/monitoring/competitors/{comp_id}/mentions")
def monitoring_competitor_mentions(comp_id: str, days: int = Query(30, ge=1, le=365), limit: int = Query(50, ge=1, le=200)):
    try:
        ct = CompetitorTracker()
        mentions = ct.get_mentions(comp_id, days=days, limit=limit)
        return {"mentions": mentions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/monitoring/anomaly/check")
def monitoring_anomaly_check(days: int = Query(7, ge=1, le=90)):
    try:
        ad = AnomalyDetector()
        checks = ad.run_all_checks(days=days)
        return {"anomaly_checks": checks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/monitoring/anomaly/volume")
def monitoring_anomaly_volume(source: Optional[str] = Query(None), topic: Optional[str] = Query(None), days: int = Query(30, ge=1, le=365)):
    try:
        ad = AnomalyDetector()
        result = ad.check_volume(source=source, topic=topic, days=days)
        return {"volume_anomaly": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Workflow Routes ===

@app.post("/workflows")
def workflows_create(req: CreateWorkflowDefRequest):
    try:
        wb = WorkflowBuilder()
        wf = wb.create(name=req.name, description=req.description)
        return {"workflow": wf}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/workflows")
def workflows_list():
    try:
        ws = WorkflowStorage()
        workflows = ws.list_all()
        return {"workflows": workflows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/workflows/{wf_id}")
def workflows_get(wf_id: str):
    try:
        ws = WorkflowStorage()
        wf = ws.get(wf_id)
        return {"workflow": wf}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/workflows/{wf_id}")
def workflows_update(wf_id: str, req: UpdateWorkflowRequest):
    try:
        ws = WorkflowStorage()
        wf = ws.update(wf_id, req.workflow)
        return {"workflow": wf}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/workflows/{wf_id}")
def workflows_delete(wf_id: str):
    try:
        ws = WorkflowStorage()
        ws.delete(wf_id)
        return {"status": "deleted", "id": wf_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/workflows/{wf_id}/execute")
def workflows_execute(wf_id: str):
    try:
        we = WorkflowEngine()
        result = we.execute(wf_id)
        return {"execution": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/workflows/{wf_id}/executions")
def workflows_executions(wf_id: str, limit: int = Query(10, ge=1, le=100)):
    try:
        we = WorkflowEngine()
        executions = we.get_executions(wf_id, limit=limit)
        return {"executions": executions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/workflows/{wf_id}/toggle")
def workflows_toggle(wf_id: str):
    try:
        ws = WorkflowStorage()
        wf = ws.toggle(wf_id)
        return {"workflow": wf}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/workflows/stats")
def workflows_stats():
    try:
        ws = WorkflowStorage()
        stats = ws.get_stats()
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def start():
    uvicorn.run(
        "pipeline.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False,
    )
