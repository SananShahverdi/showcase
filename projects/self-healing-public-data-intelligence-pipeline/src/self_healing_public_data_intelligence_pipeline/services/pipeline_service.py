from typing import Any, Dict, List, Optional
from uuid import UUID

from bs4 import BeautifulSoup

from self_healing_public_data_intelligence_pipeline.adapters.repositories import InMemoryRepository
from self_healing_public_data_intelligence_pipeline.algorithms.dom_fingerprinting import compute_dom_fingerprint
from self_healing_public_data_intelligence_pipeline.algorithms.recipe_scoring import score_recipe
from self_healing_public_data_intelligence_pipeline.algorithms.schema_validation import validate_and_quarantine
from self_healing_public_data_intelligence_pipeline.domain.models import CrawlRun, ExtractionRecipe, Record, Source


TYPE_MAP = {"str": str, "float": float, "int": int, "bool": bool}


def extract_records(html_content: str, selectors: Dict[str, str]) -> List[Dict[str, Any]]:
    """Extract records from HTML with real CSS selectors.

    An optional ``_record`` selector defines repeating containers. Without it the
    document is one record. Attribute values can be requested as ``selector@attr``.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    record_selector = selectors.get("_record")
    roots = soup.select(record_selector) if record_selector else [soup]
    records: List[Dict[str, Any]] = []
    for root in roots:
        record: Dict[str, Any] = {}
        for field, selector_spec in selectors.items():
            if field.startswith("_"):
                continue
            selector, separator, attribute = selector_spec.rpartition("@")
            if not separator:
                selector, attribute = selector_spec, ""
            element = root.select_one(selector)
            if element is None:
                continue
            if attribute:
                value = element.get(attribute)
            else:
                value = element.get("content") or element.get("value") or element.get_text(" ", strip=True)
            if value is not None:
                record[field] = value.strip() if isinstance(value, str) else value
        if record:
            records.append(record)
    return records


class PipelineService:
    def __init__(self, repo: InMemoryRepository):
        self.repo = repo

    def register_source(
        self,
        url: str,
        name: str,
        selectors: Dict[str, str],
        expected_schema: Optional[Dict[str, str]] = None,
        rate_limit_ms: int = 1000,
    ) -> Source:
        if not url.startswith(("https://", "fixture://")):
            raise ValueError("Source URL must use https:// or fixture://")
        if not selectors or any(not key or not value for key, value in selectors.items()):
            raise ValueError("At least one non-empty selector is required")
        schema = expected_schema or {"title": "str", "price": "float"}
        unknown = sorted(set(schema.values()) - set(TYPE_MAP))
        if unknown:
            raise ValueError(f"Unsupported schema types: {', '.join(unknown)}")
        source = Source(url=url, name=name.strip(), rate_limit_ms=rate_limit_ms, expected_schema=schema)
        recipe = ExtractionRecipe(source_id=source.id, selectors=selectors)
        self.repo.save_source(source)
        self.repo.save_recipe(recipe)
        return source

    def process_crawl(
        self,
        source_id: str,
        html_content: str,
        raw_extracted_data: Optional[List[Dict[str, Any]]] = None,
        expected_schema: Optional[Dict[str, type]] = None,
    ) -> CrawlRun:
        source_uuid = UUID(source_id)
        source = self.repo.get_source(source_uuid)
        recipe = self.repo.get_active_recipe_for_source(source_uuid)
        if not source or not recipe:
            raise ValueError("Source or active recipe not found")
        if not html_content.strip():
            raise ValueError("HTML snapshot cannot be empty")

        fingerprint = compute_dom_fingerprint(html_content)
        previous_runs = self.repo.get_runs_for_source(source_uuid)
        run = CrawlRun(
            source_id=source_uuid,
            recipe_id=recipe.id,
            html_snapshot_path=f"memory://snapshots/{source_uuid}",
            html_snapshot=html_content,
            dom_fingerprint=fingerprint,
            schema_drift=bool(previous_runs and previous_runs[-1].dom_fingerprint != fingerprint),
        )
        self.repo.save_run(run)

        records_data = raw_extracted_data if raw_extracted_data is not None else extract_records(html_content, recipe.selectors)
        schema = expected_schema or {field: TYPE_MAP[type_name] for field, type_name in source.expected_schema.items()}
        if not records_data:
            records_data = [{}]
        failures_count = 0
        for data in records_data:
            record = Record(crawl_run_id=run.id, extracted_data=dict(data))
            failures = validate_and_quarantine(record, schema)
            self.repo.save_record(record)
            for failure in failures:
                self.repo.save_failure(failure)
            run.extracted_count += 1
            if failures:
                failures_count += 1
                run.quarantined_count += 1
            else:
                run.valid_count += 1

        run.success = failures_count == 0
        recipe.success_rate = score_recipe(run.valid_count, run.quarantined_count)
        self.repo.save_recipe(recipe)
        self.repo.save_run(run)
        return run

    def seed_demo(self) -> dict:
        self.repo.reset()
        source = self.register_source(
            "fixture://city-market",
            "City market prices",
            {"_record": "article.product", "title": "h2", "price": "[data-field='price']"},
        )
        html = """<main><article class='product'><h2>Apples</h2><span data-field='price'>2.40</span></article><article class='product'><h2>Pears</h2><span data-field='price'>bad</span></article></main>"""
        run = self.process_crawl(str(source.id), html)
        return {"source": source, "run": run}
