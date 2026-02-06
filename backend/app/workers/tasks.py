"""Celery tasks: run scan async, send alerts."""

from app.workers.celery_app import celery_app
from app.scanner.schemas import ScanRequest
from app.scanner.engine import ScannerEngine
from app.indicators.engine import IndicatorEngine


@celery_app.task(bind=True)
def run_scan_async(self, request_dict: dict) -> dict:
    """
    Run scan in worker. request_dict is ScanRequest.model_dump().
    Returns ScanResponse as dict for storage/alerting.
    """
    request = ScanRequest.model_validate(request_dict)
    engine = ScannerEngine(indicator_engine=IndicatorEngine())
    response = engine.run_scan(request, symbol_series=None)
    return response.model_dump()
