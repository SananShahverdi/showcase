"""Environment diagnostics for the OCW Smart Scraper."""

from __future__ import annotations

import importlib
import logging
import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import requests

from .config import RuntimeConfig
from .logging_config import configure_logging
from .pdf import write_text_pdf

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """Result of an individual diagnostic check."""

    name: str
    passed: bool
    detail: str
    optional: bool = False


class SelfTestRunner:
    """Run a battery of checks to validate the local environment."""

    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config

    # ------------------------------------------------------------------
    def run(self, *, verbose: bool = False) -> bool:
        """Execute all diagnostic checks and emit a summary."""

        configure_logging(self.config.output_dir, verbose=verbose)
        logger.info("Starting self-test on %s", platform.platform())

        results = self._collect_checks()

        passed = sum(1 for result in results if result.passed and not result.optional)
        optional_passed = sum(1 for result in results if result.passed and result.optional)
        warnings = sum(1 for result in results if not result.passed and result.optional)
        failures = sum(1 for result in results if not result.passed and not result.optional)

        for result in results:
            if result.passed:
                level = logging.INFO if not result.optional else logging.INFO
                prefix = "[PASS]" if not result.optional else "[OK]"
            else:
                level = logging.WARNING if result.optional else logging.ERROR
                prefix = "[WARN]" if result.optional else "[FAIL]"
            logger.log(level, "%s %s - %s", prefix, result.name, result.detail)

        logger.info(
            "Self-test complete: %d required passed, %d optional available, %d warnings, %d failures",
            passed,
            optional_passed,
            warnings,
            failures,
        )
        return failures == 0

    # ------------------------------------------------------------------
    def _collect_checks(self) -> List[CheckResult]:
        checks: List[CheckResult] = []
        checks.append(self._check_python_version())
        checks.append(self._check_output_directory())
        checks.extend(self._check_required_imports())
        checks.append(self._check_pdf_generation())
        checks.append(self._check_ffmpeg())
        checks.append(self._check_network_connectivity())
        checks.extend(self._check_optional_packages())
        return checks

    # ------------------------------------------------------------------
    def _check_python_version(self) -> CheckResult:
        required = (3, 9)
        current = sys.version_info[:3]
        version_str = ".".join(str(part) for part in current)
        if current >= required:
            detail = f"Python {version_str} (>= {required[0]}.{required[1]} required)"
            return CheckResult("Python runtime", True, detail)
        detail = f"Detected Python {version_str}; upgrade to >= {required[0]}.{required[1]}"
        return CheckResult("Python runtime", False, detail)

    # ------------------------------------------------------------------
    def _check_output_directory(self) -> CheckResult:
        try:
            output_dir = self.config.output_dir
        except Exception as exc:  # pragma: no cover - configuration edge case
            return CheckResult("Output directory", False, f"Failed to prepare output directory: {exc}")
        return CheckResult("Output directory", True, f"Using {output_dir}")

    # ------------------------------------------------------------------
    def _check_required_imports(self) -> Iterable[CheckResult]:
        modules = [
            ("requests", "HTTP client"),
            ("bs4", "BeautifulSoup"),
            ("pypdf", "PDF utilities"),
            ("yaml", "YAML loader"),
            ("reportlab", "ReportLab"),
        ]
        for module_name, friendly in modules:
            yield self._import_check(module_name, friendly)

    # ------------------------------------------------------------------
    def _check_pdf_generation(self) -> CheckResult:
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                output_path = Path(tmp_dir) / "self_test.pdf"
                write_text_pdf(output_path, ["Self-test PDF generation", "", "This file confirms ReportLab and pypdf dependencies."])
                if output_path.exists() and output_path.stat().st_size > 0:
                    return CheckResult("PDF generation", True, f"Created sample PDF at {output_path}")
                return CheckResult("PDF generation", False, "Sample PDF was not created")
        except Exception as exc:
            return CheckResult("PDF generation", False, f"Failed to create sample PDF: {exc}")

    # ------------------------------------------------------------------
    def _check_ffmpeg(self) -> CheckResult:
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            return CheckResult("FFmpeg", False, "ffmpeg executable not found in PATH")
        try:
            process = subprocess.run(
                [ffmpeg_path, "-version"],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            first_line = process.stdout.splitlines()[0] if process.stdout else "ffmpeg detected"
            return CheckResult("FFmpeg", True, first_line.strip())
        except Exception as exc:  # pragma: no cover - unexpected failure
            return CheckResult("FFmpeg", False, f"ffmpeg is present but invocation failed: {exc}")

    # ------------------------------------------------------------------
    def _check_network_connectivity(self) -> CheckResult:
        test_url = "https://ocw.mit.edu/"
        try:
            response = requests.get(test_url, timeout=5)
            response.raise_for_status()
        except Exception as exc:
            return CheckResult("Network connectivity", False, f"Unable to reach {test_url}: {exc}")
        return CheckResult("Network connectivity", True, f"Received HTTP {response.status_code} from ocw.mit.edu")

    # ------------------------------------------------------------------
    def _check_optional_packages(self) -> Iterable[CheckResult]:
        optional_modules = [
            ("selenium", "Selenium"),
            ("webdriver_manager", "webdriver-manager"),
            ("torch", "Torch"),
            ("torchaudio", "Torchaudio"),
        ]
        for module_name, friendly in optional_modules:
            yield self._import_check(module_name, friendly, optional=True)
        yield self._check_whisper()

    # ------------------------------------------------------------------
    def _import_check(self, module_name: str, friendly: str, optional: bool = False) -> CheckResult:
        try:
            importlib.import_module(module_name)
        except ModuleNotFoundError:
            detail = f"Install '{module_name}' to enable {friendly.lower()}"
            return CheckResult(friendly, False, detail, optional=optional)
        except Exception as exc:  # pragma: no cover - unexpected import error
            detail = f"Importing '{module_name}' failed: {exc}"
            return CheckResult(friendly, False, detail, optional=optional)
        return CheckResult(friendly, True, f"Module '{module_name}' available", optional=optional)

    # ------------------------------------------------------------------
    def _check_whisper(self) -> CheckResult:
        candidates = ("openai_whisper", "whisper")
        found = None
        for module_name in candidates:
            try:
                importlib.import_module(module_name)
            except ModuleNotFoundError:
                continue
            except Exception as exc:  # pragma: no cover - unexpected import error
                return CheckResult("Whisper", False, f"Importing '{module_name}' failed: {exc}", optional=True)
            found = module_name
            break
        if found:
            return CheckResult("Whisper", True, f"Module '{found}' available", optional=True)
        return CheckResult("Whisper", False, "Install 'openai-whisper' for transcription support", optional=True)
