#!/usr/bin/env python3
"""AI Content Hub — Multi-source content aggregation pipeline with AI, analytics, notifications."""

import typer
from .core.config import settings
from .pipeline.orchestrator import ContentOrchestrator
from .pipeline.scheduler import start_scheduler, run_pipeline_job
from .storage.vector_store import VectorStore
from .storage.sql_store import SQLStore
from datetime import datetime
import json

app = typer.Typer(help="AI Content Hub — multi-source content aggregation pipeline")


# ===== PIPELINE COMMANDS =====

@app.command()
def run(
    sources: str = typer.Option(None, help="Comma-separated sources to scrape"),
):
    """Run the pipeline once for all (or specific) sources."""
    source_list = [s.strip() for s in sources.split(",")] if sources else None
    orchestrator = ContentOrchestrator()
    results = orchestrator.run_all(source_list)
    print(f"\nPipeline complete: {results}")


@app.command()
def run_source(
    source: str = typer.Argument(..., help="Source name: linkedin, reddit, techcrunch, etc."),
):
    """Run pipeline for a single source."""
    orchestrator = ContentOrchestrator()
    items = orchestrator.run_source(source)
    print(f"Collected {len(items)} items from {source}")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    source: str = typer.Option(None, help="Filter by source"),
    limit: int = typer.Option(20, help="Number of results"),
):
    """Search stored content."""
    vector_store = VectorStore()
    sql_store = SQLStore()
    results = vector_store.search(query, n_results=limit, filter_source=source)
    if results:
        for r in results:
            meta = r["metadata"]
            print(f"\n--- [{meta.get('source','?').upper()}] {meta.get('title','')[:80]} ---")
            print(f"  Topics: {meta.get('topics', 'N/A')}")
            print(f"  {r['content'][:200]}...")
    else:
        results = sql_store.search(query, limit=limit)
        for r in results:
            print(f"\n--- [{r['source'].upper()}] {r['title'][:80]} ---")
            print(f"  Topics: {r['topics']}")
            print(f"  {r['content'][:200]}...")


@app.command()
def status():
    """Show pipeline status and stats."""
    sql_store = SQLStore()
    vs_count = VectorStore().count()
    stats = sql_store.get_stats()
    print(f"\n{'='*50}")
    print(f"  AI Content Hub — Status")
    print(f"{'='*50}")
    print(f"  Vector Store: {vs_count} items")
    print(f"  SQL Store:    {stats['total']} items")
    print(f"  Sources:      {settings.SOURCES_ENABLED}")
    print(f"  Topics:       {settings.DIGEST_TOPICS}")
    print(f"  Backend:      {settings.LLM_PROVIDER or 'keyword-only'}")
    print(f"\n  Per Source:")
    for source, count in stats.get("by_source", {}).items():
        print(f"    {source}: {count}")
    print(f"\n  Per Topic:")
    for topic, count in stats.get("by_topic", {}).items():
        print(f"    {topic}: {count}")


@app.command()
def serve():
    """Run pipeline on a schedule."""
    start_scheduler()


@app.command()
def api():
    """Start the FastAPI server."""
    from .api.main import start
    start()


@app.command()
def dashboard():
    """Launch Streamlit dashboard."""
    import subprocess
    import sys
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "pipeline/dashboard/app.py", "--server.port", "8501"
    ])


@app.command()
def digest():
    """Generate and print a digest of recent relevant items."""
    from .core.models import DigestConfig
    sql_store = SQLStore()
    topics = [t.strip() for t in settings.DIGEST_TOPICS.split(",")]
    lines = [f"# AI Content Hub Digest", f"**Generated:** {datetime.now().isoformat()}", f"**Sources:** {settings.SOURCES_ENABLED}", ""]
    for topic in topics:
        items = sql_store.get_by_topic(topic, limit=10)
        if not items:
            continue
        lines.append(f"## {topic}")
        for item in items:
            snippet = item.get("content", "")[:150].replace("\n", " ")
            lines.append(f"- [{item.get('source','')}] {item.get('title','')}")
            lines.append(f"  {snippet}...")
        lines.append("")
    print("\n".join(lines))


# ===== AI COMMANDS =====

@app.command()
def summarize(
    text: str = typer.Argument(..., help="Text to summarize"),
    length: str = typer.Option("normal", help="brief, normal, or detailed"),
):
    """Summarize text using AI."""
    from .ai.summarizer import summarize as ai_summarize
    result = ai_summarize(text, length=length)
    print(f"\nSummary ({length}):\n{result}")


@app.command()
def recommend(
    query: str = typer.Argument(..., help="Query or item ID"),
    n: int = typer.Option(5, help="Number of recommendations"),
):
    """Get content recommendations."""
    from .ai.recommender import recommend_for_query
    results = recommend_for_query(query, n=n)
    for r in results:
        meta = r.get("metadata", {})
        print(f"\n- {meta.get('title', '')[:80]}")
        print(f"  Source: {meta.get('source', '')} | Topics: {meta.get('topics', '')}")


@app.command()
def chat(
    question: str = typer.Argument(..., help="Your question"),
):
    """Ask a question about your stored content (RAG)."""
    from .ai.rag_chat import ChatEngine
    engine = ChatEngine()
    result = engine.query(question)
    print(f"\nAnswer: {result['answer']}\n")
    print("Sources:")
    for s in result.get("sources", []):
        print(f"  - {s.get('title', '')} ({s.get('source', '')})")
        if s.get("url"):
            print(f"    {s['url']}")


@app.command()
def tag(
    text: str = typer.Argument(..., help="Content to tag"),
):
    """Auto-tag content with taxonomy categories."""
    from .ai.tagger import auto_tag, extract_entities
    from ..core.models import ContentItem
    item = ContentItem(id="cli", title=text[:100], content=text, source="cli")
    tags = auto_tag(item)
    entities = extract_entities(text)
    print("\nTags:")
    for category, cat_tags in tags.items():
        print(f"  {category}: {', '.join(cat_tags)}")
    print(f"\nEntities:")
    for e in entities:
        print(f"  {e['text']} ({e['type']})")


# ===== ANALYTICS COMMANDS =====

@app.command()
def trends(
    topic: str = typer.Argument(..., help="Topic name"),
    days: int = typer.Option(30, help="Number of days"),
):
    """Show topic trends over time."""
    from .analytics.trends import TrendAnalyzer
    ta = TrendAnalyzer()
    data = ta.topic_trend(topic, days=days)
    print(f"\nTrend for '{topic}' (last {days} days):")
    for d in data[-14:]:
        bar = "█" * min(d["count"], 40)
        print(f"  {d['date']}: {bar} {d['count']}")


@app.command()
def top_movers(
    days: int = typer.Option(7, help="Lookback days"),
):
    """Show topics with biggest increase/decrease."""
    from .analytics.trends import TrendAnalyzer
    ta = TrendAnalyzer()
    movers = ta.top_movers(days=days)
    print(f"\nTop Movers (last {days} days vs previous {days}):")
    for m in sorted(movers, key=lambda x: abs(x["change_pct"]), reverse=True)[:10]:
        arrow = "▲" if m["change_pct"] > 0 else "▼"
        print(f"  {m['topic']}: {arrow} {abs(m['change_pct']):.1f}% ({m['current']} vs {m['previous']})")


@app.command()
def export(
    format: str = typer.Option("markdown", help="csv, json, or markdown"),
    topic: str = typer.Option(None, help="Filter by topic"),
    source: str = typer.Option(None, help="Filter by source"),
    output: str = typer.Option("./export", help="Output directory"),
):
    """Export stored content."""
    from .analytics.exporter import export_to_csv, export_to_json, export_to_markdown
    from .storage.sql_store import SQLStore
    sql = SQLStore()
    if topic:
        items = sql.get_by_topic(topic, limit=500)
    elif source:
        items = sql.get_by_source(source, limit=500)
    else:
        items = sql.search("", limit=500)
    if format == "csv":
        path = export_to_csv(items, f"{output}/export.csv")
    elif format == "json":
        path = export_to_json(items, f"{output}/export.json")
    else:
        path = export_to_markdown(items, f"{output}/export.md")
    print(f"Exported {len(items)} items to {path}")


# ===== NOTIFICATION COMMANDS =====

@app.command()
def send_email(
    to: str = typer.Argument(..., help="Recipient email"),
    topic: str = typer.Option(None, help="Topic for digest"),
):
    """Send email digest."""
    from .notifications.email_sender import NewsletterSender
    from .storage.sql_store import SQLStore
    sql = SQLStore()
    topics = [topic] if topic else settings.DIGEST_TOPICS.split(",")
    all_items = []
    for t in topics:
        all_items.extend(sql.get_by_topic(t.strip(), limit=10))
    sender = NewsletterSender()
    success = sender.send_weekly_newsletter(to, all_items, topics)
    print(f"Email sent: {success}")


@app.command()
def send_telegram(
    message: str = typer.Argument(..., help="Message to send"),
):
    """Send Telegram message."""
    from .notifications.telegram_bot import TelegramNotifier
    bot = TelegramNotifier()
    success = bot.send_message(message)
    print(f"Telegram message sent: {success}")


@app.command()
def extract(
    url: str = typer.Argument(..., help="URL to extract"),
):
    """Extract full article content from URL."""
    from .processing.fulltext import FullTextExtractor
    xt = FullTextExtractor()
    result = xt.extract(url)
    print(f"\nTitle: {result.get('title', '')}")
    print(f"Author: {result.get('author', '')}")
    print(f"Content:\n{result.get('text', '')[:1000]}...")


# ===== AUTH COMMANDS =====

@app.command()
def register(
    username: str = typer.Argument(..., help="Username"),
    password: str = typer.Argument(..., help="Password"),
):
    """Register a new user."""
    from .auth.jwt_auth import JWTAuth
    auth = JWTAuth()
    user = auth.create_user(username, password)
    print(f"User '{user['username']}' created (role: {user['role']})")


@app.command()
def login(
    username: str = typer.Argument(..., help="Username"),
    password: str = typer.Argument(..., help="Password"),
):
    """Get auth token."""
    from .auth.jwt_auth import JWTAuth
    auth = JWTAuth()
    token = auth.authenticate(username, password)
    print(f"Token: {token}")


# ===== ENTERPRISE COMMANDS =====

@app.command()
def sentiment(text: str = typer.Argument(..., help="Text to analyze")):
    """Analyze sentiment of text."""
    from .mlops.sentiment import SentimentAnalyzer
    sa = SentimentAnalyzer()
    result = sa.analyze(text)
    print(f"\nSentiment: {result['sentiment']}")
    print(f"Score: {result['score']:.2f}")
    print(f"Tone: {result.get('details', {}).get('emotional_tone', 'N/A')}")
    print(f"Confidence: {result['confidence']:.2f}")


@app.command()
def discover(text: str = typer.Argument(..., help="Text to discover")):
    """Enrich content with ML (keywords, links, category, read time)."""
    from .mlops.enrichment import EnrichmentPipeline
    from ..core.models import ContentItem
    ep = EnrichmentPipeline()
    item = ContentItem(id="cli", title=text[:100], content=text, source="cli")
    enriched = ep.enrich_item(item)
    print(f"\nKeywords: {', '.join(enriched.metadata.get('keywords', [])[:10])}")
    print(f"Category: {enriched.metadata.get('category', 'N/A')}")
    print(f"Read Time: {enriched.metadata.get('read_time', 'N/A')} min")
    print(f"Mentions: {', '.join(enriched.metadata.get('mentions', [])[:5])}")


@app.command()
def search_faceted(
    query: str = typer.Argument(..., help="Search query"),
    source: str = typer.Option(None, help="Filter by source"),
    topic: str = typer.Option(None, help="Filter by topic"),
):
    """Enterprise faceted search."""
    from .search.faceted_search import FacetedSearch
    fs = FacetedSearch()
    facets = {}
    if source: facets["source"] = [source]
    if topic: facets["topics"] = [topic]
    results = fs.search(query, facets=facets, page=1, page_size=10)
    print(f"\nTotal results: {results['total']}")
    print(f"Facets: {json.dumps({k: dict(list(v.items())[:5]) for k, v in results.get('facets', {}).items()}, indent=2)}")
    for r in results.get("results", [])[:5]:
        print(f"\n- [{r.get('source','?').upper()}] {r.get('title','')[:80]}")


@app.command()
def moderates(
    text: str = typer.Argument(..., help="Text to moderate"),
):
    """Check content for moderation flags."""
    from .enterprise.compliance.content_moderation import ContentModerator
    cm = ContentModerator()
    result = cm.moderate(text)
    print(f"\nApproved: {result['approved']}")
    print(f"Score: {result['score']:.2f}")
    for flag in result.get("flags", []):
        print(f"  ⚠ {flag['type']}: {flag.get('word', '')} (conf: {flag['confidence']:.2f})")


@app.command()
def pii_detect(text: str = typer.Argument(..., help="Text to check for PII")):
    """Detect and redact PII in text."""
    from .enterprise.compliance.pii_detector import PIIDetector
    pii = PIIDetector()
    detected = pii.detect(text)
    redacted = pii.redact(text)
    print(f"\nPII Found: {len(detected)}")
    for d in detected:
        print(f"  {d['type']}: '{d['value']}' (conf: {d['confidence']:.2f})")
    print(f"\nRedacted:\n{redacted[:500]}")


@app.command()
def audit_log(
    actor: str = typer.Option(None, help="Filter by actor"),
    event: str = typer.Option(None, help="Filter by event type"),
    limit: int = typer.Option(20, help="Number of entries"),
):
    """Query the audit log."""
    from .enterprise.compliance.audit_log import AuditLogger
    al = AuditLogger()
    results = al.query(actor=actor, event=event, limit=limit)
    print(f"\nAudit Log ({len(results)} entries):")
    for r in results[:10]:
        print(f"  [{r['timestamp'][:19]}] {r['actor']} -> {r['action']} on {r['resource_type']}:{r['resource_id']}")


@app.command()
def workflow_run(
    name: str = typer.Argument(..., help="Workflow name"),
    trigger: str = typer.Option("manual", help="Trigger type: manual, scheduled"),
    source: str = typer.Option(None, help="Source to collect from"),
):
    """Create and run a workflow on the fly."""
    from .workflow.builder import WorkflowBuilder
    from .workflow.engine import WorkflowEngine
    wb = WorkflowBuilder(name=name)
    trigger_id = wb.add_trigger(trigger, source=source)
    collect_id = wb.add_collector(source or "demo", max_items=10)
    classify_id = wb.add_classifier()
    notify_id = wb.add_notifier(channel="console")
    wb.connect(trigger_id, collect_id)
    wb.connect(collect_id, classify_id)
    wb.connect(classify_id, notify_id)
    workflow = wb.build()
    engine = WorkflowEngine()
    result = engine.execute(workflow)
    print(f"\nWorkflow '{name}' executed: {result['status']}")
    print(f"Time: {result.get('execution_time', 0):.2f}s")
    for node_id, output in result.get("results", {}).items():
        print(f"  Node {node_id}: {str(output)[:100]}")


@app.command()
def workspace(
    action: str = typer.Argument(..., help="create, list, info"),
    name: str = typer.Option(None, help="Workspace name"),
):
    """Manage workspaces."""
    from .enterprise.collaboration.workspaces import WorkspaceManager
    wm = WorkspaceManager()
    if action == "list":
        for ws in wm.list_workspaces():
            print(f"  {ws['id']}: {ws['name']} ({ws.get('member_count', 0)} members)")
    elif action == "create" and name:
        ws = wm.create_workspace(name, "", "admin")
        print(f"Created: {ws['id']}")


@app.command()
def alert(
    name: str = typer.Argument(..., help="Alert name"),
    keywords: str = typer.Argument(..., help="Comma-separated keywords"),
):
    """Create a keyword alert."""
    from .enterprise.monitoring.alerts import AlertEngine
    ae = AlertEngine()
    kw_list = [k.strip() for k in keywords.split(",")]
    alert = ae.create_alert(name, kw_list)
    print(f"Alert '{name}' created with {len(kw_list)} keywords")


@app.command()
def competitor_add(
    name: str = typer.Argument(..., help="Competitor name"),
    domains: str = typer.Argument(..., help="Comma-separated domains"),
):
    """Add a competitor to track."""
    from .enterprise.monitoring.competitor_tracker import CompetitorTracker
    ct = CompetitorTracker()
    comp = ct.add_competitor(name, [d.strip() for d in domains.split(",")])
    print(f"Competitor '{name}' added (id: {comp.get('id', 'N/A')})")


@app.command()
def competitor_summary(
    name: str = typer.Argument(..., help="Competitor name"),
    days: int = typer.Option(30, help="Lookback days"),
):
    """Get competitor intelligence summary."""
    from .enterprise.monitoring.competitor_tracker import CompetitorTracker
    ct = CompetitorTracker()
    competitors = ct.list_competitors()
    comp = next((c for c in competitors if c["name"].lower() == name.lower()), None)
    if not comp:
        print(f"Competitor '{name}' not found")
        return
    summary = ct.get_competitor_summary(comp["id"], days=days)
    print(f"\n=== {summary['name']} ===")
    print(f"Mentions: {summary.get('mention_count', 0)}")
    print(f"Sentiment: {summary.get('sentiment_avg', 0):.2f}")
    print(f"Top Sources: {', '.join(list(summary.get('top_sources', {}).keys())[:5])}")


if __name__ == "__main__":
    app()
