from __future__ import annotations

import ast
import csv
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
import os
from pathlib import Path
from statistics import fmean, pstdev
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from autonomous_data_quality_observatory.domain.models import (
    ColumnProfile,
    DataSource,
    DatasetProfile,
    DriftResult,
    DriftSignal,
    Rule,
    RuleResult,
    SourceType,
)


class ConnectorError(ValueError):
    pass


class ConnectorUnavailable(ConnectorError):
    pass


class Connectors:
    MAX_ROWS = 10_000
    MAX_BYTES = 5 * 1024 * 1024

    @classmethod
    def fetch_data(cls, source: DataSource) -> List[Dict[str, Any]]:
        if not source.enabled:
            raise ConnectorError("Source is disabled")
        if source.type == SourceType.INLINE:
            return cls._validate_records(source.config.get("records"))
        if source.type == SourceType.CSV:
            content = cls._text_content(source, "csv")
            return cls._validate_records(list(csv.DictReader(io.StringIO(content))))
        if source.type == SourceType.JSON:
            if "records" in source.config:
                return cls._validate_records(source.config["records"])
            content = cls._text_content(source, "json")
            try:
                payload = json.loads(content)
            except json.JSONDecodeError as exc:
                raise ConnectorError(f"Invalid JSON: {exc.msg}") from exc
            records = payload if isinstance(payload, list) else payload.get("records") if isinstance(payload, dict) else None
            return cls._validate_records(records)
        if source.type == SourceType.API:
            return cls._fetch_api(source)
        if source.type == SourceType.POSTGRES:
            raise ConnectorUnavailable(
                "PostgreSQL adapter requires a deployment-specific secret provider and read-only query adapter; no data was fabricated."
            )
        if source.type == SourceType.S3:
            raise ConnectorUnavailable(
                "S3/MinIO adapter requires deployment credentials and an object client; no data was fabricated."
            )
        raise ConnectorError(f"Unsupported source type: {source.type}")

    @classmethod
    def _validate_records(cls, records: Any) -> List[Dict[str, Any]]:
        if not isinstance(records, list):
            raise ConnectorError("Source must provide a list of record objects")
        if len(records) > cls.MAX_ROWS:
            records = records[: cls.MAX_ROWS]
        if any(not isinstance(row, dict) for row in records):
            raise ConnectorError("Every record must be an object")
        return [dict(row) for row in records]

    @classmethod
    def _text_content(cls, source: DataSource, format_name: str) -> str:
        if "content" in source.config:
            content = str(source.config["content"])
            if len(content.encode("utf-8")) > cls.MAX_BYTES:
                raise ConnectorError(f"{format_name.upper()} content exceeds {cls.MAX_BYTES} bytes")
            return content
        configured_path = source.config.get("path")
        if not configured_path:
            raise ConnectorError(f"{format_name.upper()} source requires config.content or config.path")
        allowed_root = Path(os.getenv("DATA_QUALITY_ALLOWED_DATA_DIR", "./data")).resolve()
        path = Path(str(configured_path)).resolve()
        if allowed_root != path and allowed_root not in path.parents:
            raise ConnectorError(f"Path is outside the allowed data directory: {allowed_root}")
        if not path.is_file():
            raise ConnectorError("Configured source file does not exist")
        if path.stat().st_size > cls.MAX_BYTES:
            raise ConnectorError(f"Source file exceeds {cls.MAX_BYTES} bytes")
        return path.read_text(encoding="utf-8")

    @classmethod
    def _fetch_api(cls, source: DataSource) -> List[Dict[str, Any]]:
        url = str(source.config.get("url", ""))
        parsed = urlparse(url)
        allowed_hosts = {host.strip() for host in os.getenv("DATA_QUALITY_API_ALLOW_HOSTS", "").split(",") if host.strip()}
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ConnectorError("API URL must use http or https")
        if parsed.hostname not in allowed_hosts:
            raise ConnectorError("API host is not in DATA_QUALITY_API_ALLOW_HOSTS")
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "data-quality-observatory/1.0"})
        try:
            with urlopen(request, timeout=5) as response:
                content_length = int(response.headers.get("Content-Length", "0") or 0)
                if content_length > cls.MAX_BYTES:
                    raise ConnectorError("API response is too large")
                raw = response.read(cls.MAX_BYTES + 1)
        except ConnectorError:
            raise
        except Exception as exc:
            raise ConnectorUnavailable(f"API read failed: {type(exc).__name__}") from exc
        if len(raw) > cls.MAX_BYTES:
            raise ConnectorError("API response is too large")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ConnectorError("API response is not valid JSON") from exc
        records = payload if isinstance(payload, list) else payload.get("records") if isinstance(payload, dict) else None
        return cls._validate_records(records)


class Profiler:
    @staticmethod
    def _dtype(values: List[Any]) -> str:
        concrete = [value for value in values if value is not None and value != ""]
        if not concrete:
            return "null"
        if all(isinstance(value, bool) for value in concrete):
            return "boolean"
        if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in concrete):
            return "number"
        return "string"

    @staticmethod
    def profile(
        source_id: str,
        data: List[Dict[str, Any]],
        source_freshness_at: Optional[datetime] = None,
        sampled: bool = False,
    ) -> DatasetProfile:
        normalized_rows = [json.dumps(row, sort_keys=True, default=str) for row in data]
        row_count = len(data)
        keys = sorted({key for row in data for key in row})
        columns: List[ColumnProfile] = []
        for key in keys:
            values = [row.get(key) for row in data]
            non_null = [value for value in values if value is not None and value != ""]
            dtype = Profiler._dtype(values)
            serialized = [json.dumps(value, sort_keys=True, default=str) for value in non_null]
            unique_count = len(set(serialized))
            numeric = [float(value) for value in non_null if isinstance(value, (int, float)) and not isinstance(value, bool)]
            counts = Counter(str(value) for value in non_null)
            columns.append(
                ColumnProfile(
                    name=key,
                    dtype=dtype,
                    null_count=row_count - len(non_null),
                    total_count=row_count,
                    null_ratio=(row_count - len(non_null)) / row_count if row_count else 0,
                    unique_count=unique_count,
                    uniqueness_ratio=unique_count / len(non_null) if non_null else 0,
                    minimum=min(numeric) if numeric else None,
                    maximum=max(numeric) if numeric else None,
                    mean=fmean(numeric) if numeric else None,
                    standard_deviation=pstdev(numeric) if len(numeric) > 1 else 0 if numeric else None,
                    top_values=dict(counts.most_common(5)),
                )
            )
        digest = sha256("\n".join(normalized_rows).encode("utf-8")).hexdigest()
        return DatasetProfile(
            source_id=source_id,
            row_count=row_count,
            sampled=sampled,
            sample_size=row_count,
            duplicate_row_count=row_count - len(set(normalized_rows)),
            columns=columns,
            data_hash=digest,
            source_freshness_at=source_freshness_at,
        )


class SafeExpression:
    ALLOWED_NODES = (
        ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not,
        ast.Compare, ast.Name, ast.Load, ast.Constant, ast.Eq, ast.NotEq,
        ast.Gt, ast.GtE, ast.Lt, ast.LtE, ast.In, ast.NotIn,
    )

    @classmethod
    def evaluate(cls, expression: str, row: Dict[str, Any]) -> bool:
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as exc:
            raise ValueError("Business expression is invalid") from exc
        if any(not isinstance(node, cls.ALLOWED_NODES) for node in ast.walk(tree)):
            raise ValueError("Business expression contains an unsafe operation")
        try:
            return bool(eval(compile(tree, "<business-rule>", "eval"), {"__builtins__": {}}, dict(row)))
        except (NameError, TypeError, ValueError) as exc:
            raise ValueError(f"Business expression could not be evaluated: {type(exc).__name__}") from exc


class RulesEngine:
    @staticmethod
    def evaluate(profile: DatasetProfile, rules: List[Rule], data: Optional[List[Dict[str, Any]]] = None) -> List[RuleResult]:
        results: List[RuleResult] = []
        columns = {column.name: column for column in profile.columns}
        for rule in (item for item in rules if item.enabled):
            params = rule.parameters
            passed = False
            observed: Any = None
            expected: Any = params
            details = ""
            if rule.rule_type == "schema":
                expected_columns = set(params.get("columns", []))
                actual_columns = set(columns)
                missing = sorted(expected_columns - actual_columns)
                expected_types = params.get("types", {})
                wrong_types = {
                    name: {"expected": expected_type, "actual": columns[name].dtype}
                    for name, expected_type in expected_types.items()
                    if name in columns and columns[name].dtype != expected_type
                }
                passed = not missing and not wrong_types
                observed = {"columns": sorted(actual_columns), "wrong_types": wrong_types}
                details = "Schema matches" if passed else f"Missing columns: {missing}; type mismatches: {wrong_types}"
            elif rule.rule_type in {"null_check", "null_ratio"}:
                column = columns.get(str(params.get("column", "")))
                if column is None:
                    details = f"Column {params.get('column')} is missing"
                else:
                    observed = column.null_count if rule.rule_type == "null_check" else column.null_ratio
                    limit = params.get("max_nulls", 0) if rule.rule_type == "null_check" else params.get("max_ratio", 0)
                    passed = observed <= limit
                    details = f"Observed {observed}; maximum allowed is {limit}"
            elif rule.rule_type == "volume":
                minimum = int(params.get("min_rows", 0))
                maximum = int(params.get("max_rows", 2**63 - 1))
                observed = profile.row_count
                passed = minimum <= observed <= maximum
                details = f"Observed {observed} rows; expected between {minimum} and {maximum}"
            elif rule.rule_type == "uniqueness":
                column = columns.get(str(params.get("column", "")))
                minimum = float(params.get("min_ratio", 1))
                observed = column.uniqueness_ratio if column else None
                passed = column is not None and observed >= minimum
                details = f"Observed uniqueness {observed}; minimum is {minimum}"
            elif rule.rule_type == "range":
                column = columns.get(str(params.get("column", "")))
                lower = params.get("min")
                upper = params.get("max")
                observed = {"min": column.minimum if column else None, "max": column.maximum if column else None}
                passed = column is not None and column.minimum is not None
                if passed and lower is not None:
                    passed = column.minimum >= float(lower)
                if passed and upper is not None:
                    passed = column.maximum <= float(upper)
                details = f"Observed range {observed}; expected min={lower}, max={upper}"
            elif rule.rule_type == "freshness":
                max_age = float(params.get("max_age_hours", 24))
                if profile.source_freshness_at is None:
                    details = "Source has no parseable freshness timestamp"
                else:
                    current = datetime.now(timezone.utc)
                    timestamp = profile.source_freshness_at
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone.utc)
                    observed = max(0, (current - timestamp).total_seconds() / 3600)
                    passed = observed <= max_age
                    details = f"Source age is {observed:.2f} hours; maximum is {max_age}"
            elif rule.rule_type == "business_expression":
                expression = str(params.get("expression", ""))
                rows = data or []
                failures = sum(1 for row in rows if not SafeExpression.evaluate(expression, row))
                allowed_failures = int(params.get("max_failures", 0))
                observed = failures
                passed = failures <= allowed_failures
                details = f"{failures} row(s) failed expression; maximum is {allowed_failures}"
            else:
                details = f"Unsupported rule type: {rule.rule_type}"
            results.append(
                RuleResult(
                    rule_id=rule.id,
                    passed=passed,
                    severity=rule.severity,
                    details=details,
                    observed=observed,
                    expected=expected,
                )
            )
        return results


class DriftDetector:
    @staticmethod
    def detect(
        current: DatasetProfile,
        baseline: Optional[DatasetProfile],
        volume_threshold_pct: float = 25,
        numeric_mean_threshold: float = 2.0,
    ) -> DriftResult:
        if baseline is None:
            return DriftResult(has_drift=False, details="No baseline to compare", signals=[])
        signals: List[DriftSignal] = []
        current_columns = {item.name: item for item in current.columns}
        baseline_columns = {item.name: item for item in baseline.columns}
        if set(current_columns) != set(baseline_columns):
            signals.append(
                DriftSignal(
                    drift_type="schema",
                    score=float(len(set(current_columns) ^ set(baseline_columns))),
                    threshold=0,
                    details=f"Baseline columns {sorted(baseline_columns)}; current columns {sorted(current_columns)}",
                )
            )
        for name in sorted(set(current_columns) & set(baseline_columns)):
            left, right = baseline_columns[name], current_columns[name]
            if left.dtype != right.dtype:
                signals.append(
                    DriftSignal(drift_type="type", column=name, score=1, threshold=0, details=f"Type changed from {left.dtype} to {right.dtype}")
                )
            if left.mean is not None and right.mean is not None:
                scale = left.standard_deviation or max(abs(left.mean) * 0.05, 1)
                score = abs(right.mean - left.mean) / scale
                if score > numeric_mean_threshold:
                    signals.append(
                        DriftSignal(
                            drift_type="numeric_distribution",
                            column=name,
                            score=round(score, 4),
                            threshold=numeric_mean_threshold,
                            details=f"Mean shifted from {left.mean:.3f} to {right.mean:.3f} ({score:.2f} baseline deviations)",
                        )
                    )
        baseline_rows = max(baseline.row_count, 1)
        volume_change = abs(current.row_count - baseline.row_count) / baseline_rows * 100
        if volume_change > volume_threshold_pct:
            signals.append(
                DriftSignal(
                    drift_type="volume",
                    score=round(volume_change, 3),
                    threshold=volume_threshold_pct,
                    details=f"Row count changed from {baseline.row_count} to {current.row_count}",
                )
            )
        return DriftResult(
            has_drift=bool(signals),
            details=f"{len(signals)} drift signal(s) detected" if signals else "No drift detected",
            signals=signals,
            baseline_profile_id=baseline.id,
        )
