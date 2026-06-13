"""
Celery task definitions. The FastAPI endpoint kicks off run_research_task
asynchronously, allowing long-running pipelines to run in background workers.
"""
from celery import Celery
import asyncio
import structlog
from app.config import settings

log = structlog.get_logger()

celery_app = Celery(
    "intel_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(bind=True, name="tasks.run_research", max_retries=2)
def run_research_task(self, session_id: str, company: str):
    """
    Celery task that runs the full intelligence pipeline.
    Creates its own event loop for async orchestrator.
    """
    log.info("celery_task_start", session_id=session_id, company=company)

    async def _run():
        from app.database import AsyncSessionLocal
        from app.agents.orchestrator import AgentOrchestrator

        async with AsyncSessionLocal() as db:
            orchestrator = AgentOrchestrator(db)
            return await orchestrator.run_pipeline(session_id, company)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_run())
        loop.close()
        log.info("celery_task_done", session_id=session_id)
        return result
    except Exception as exc:
        log.error("celery_task_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=30)
