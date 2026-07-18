"""Async index worker: queue consume + chunk→embed→upsert (PRD §4.8)."""

from app.services.knowledge.indexer.service import IndexerService
from app.workers.index_worker.consumer import consume_once, consumer_loop, process_job
from app.workers.index_worker.queue import IndexJob, IndexQueue, get_index_queue, reset_index_queue

__all__ = [
    "IndexerService",
    "IndexJob",
    "IndexQueue",
    "get_index_queue",
    "reset_index_queue",
    "process_job",
    "consume_once",
    "consumer_loop",
]
