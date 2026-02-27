"""Runtime telemetry helpers for tokenizer training."""

from __future__ import annotations

from dataclasses import dataclass
import os
import platform
import sys
from typing import Any

import psutil
import regex


BYTES_PER_MB = 1024.0 * 1024.0


def bytes_to_mb(num_bytes: int | float) -> float:
    return round(float(num_bytes) / BYTES_PER_MB, 3)


def _safe_proc_memory_rss(proc: psutil.Process) -> int:
    try:
        return int(proc.memory_info().rss)
    except (psutil.Error, ProcessLookupError):
        return 0


def sample_process_tree_rss_bytes() -> int:
    """Return current RSS for the process tree rooted at the current process."""
    proc = psutil.Process(os.getpid())
    total = _safe_proc_memory_rss(proc)
    try:
        children = proc.children(recursive=True)
    except (psutil.Error, ProcessLookupError):
        children = []
    for child in children:
        total += _safe_proc_memory_rss(child)
    return int(total)


@dataclass
class RssSampler:
    """Track current and peak process-tree RSS."""

    peak_bytes: int = 0
    last_bytes: int = 0

    def sample(self) -> int:
        current = sample_process_tree_rss_bytes()
        self.last_bytes = current
        if current > self.peak_bytes:
            self.peak_bytes = current
        return current

    @property
    def peak_mb(self) -> float:
        return bytes_to_mb(self.peak_bytes)

    @property
    def last_mb(self) -> float:
        return bytes_to_mb(self.last_bytes)


def _detect_platform_mode() -> str:
    system = platform.system()
    if system == "Linux":
        try:
            proc_version = ""
            if os.path.exists("/proc/version"):
                with open("/proc/version", "r", encoding="utf-8", errors="replace") as f:
                    proc_version = f.read().lower()
            release = platform.release().lower()
            if "microsoft" in proc_version or "microsoft" in release or "wsl" in release:
                return "WSL"
        except OSError:
            pass
        return "Linux native"
    return f"{system} native"


def _read_linux_cpu_model() -> str | None:
    if platform.system() != "Linux":
        return None
    if not os.path.exists("/proc/cpuinfo"):
        return None
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.lower().startswith("model name"):
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        return parts[1].strip()
    except OSError:
        return None
    return None


def collect_environment_snapshot() -> dict[str, Any]:
    virtual_mem = psutil.virtual_memory()
    cpu_model = _read_linux_cpu_model() or platform.processor() or platform.machine()
    return {
        "os": platform.platform(),
        "platform_mode": _detect_platform_mode(),
        "cpu_model": cpu_model,
        "cpu_count_logical": psutil.cpu_count(logical=True),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "ram_total_bytes": int(virtual_mem.total),
        "ram_total_gb": round(float(virtual_mem.total) / (1024.0**3), 3),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "regex_version": getattr(regex, "__version__", "unknown"),
        "executable": sys.executable,
    }

