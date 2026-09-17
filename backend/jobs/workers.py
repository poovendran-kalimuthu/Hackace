"""
Dual Concurrency Executor Pool.

Maintains strict separation between I/O bound tasks (ThreadPoolExecutor)
and CPU-heavy ML/layout processing (ProcessPoolExecutor).
"""

from __future__ import annotations
import os
import psutil
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor
from typing import Any, Callable, Dict, Optional


class DualExecutorPool:
    """
    Manages background thread pools and multiprocessing pools with resource monitoring.
    """

    def __init__(
        self,
        io_workers: int = 4,
        cpu_workers: Optional[int] = None,
    ):
        cpu_count = os.cpu_count() or 4
        # Controlled worker count (never consume 100% of CPU cores per Section 46)
        actual_cpu_workers = cpu_workers or max(1, min(8, cpu_count - 2))

        self.thread_pool = ThreadPoolExecutor(
            max_workers=io_workers, thread_name_prefix="doc_io"
        )
        self.process_pool = ProcessPoolExecutor(
            max_workers=actual_cpu_workers
        )
        self.num_cpu_workers = actual_cpu_workers
        self.num_io_workers = io_workers

    def submit_io(self, fn: Callable, *args, **kwargs) -> Future:
        """Submit I/O, cache, preview, or disk read/write task."""
        return self.thread_pool.submit(fn, *args, **kwargs)

    def submit_cpu(self, fn: Callable, *args, **kwargs) -> Future:
        """Submit ML feature extraction, NLP, or formatting task."""
        return self.process_pool.submit(fn, *args, **kwargs)

    def get_system_metrics(self) -> Dict[str, Any]:
        """Returns live CPU, RAM, and worker pool diagnostic metrics."""
        vm = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=None)
        return {
            "cpu_percent": cpu_percent,
            "ram_used_gb": round((vm.total - vm.available) / (1024 ** 3), 2),
            "ram_total_gb": round(vm.total / (1024 ** 3), 2),
            "ram_percent": vm.percent,
            "cpu_workers": self.num_cpu_workers,
            "io_workers": self.num_io_workers,
        }

    def shutdown(self, wait: bool = False) -> None:
        self.thread_pool.shutdown(wait=wait)
        self.process_pool.shutdown(wait=wait)
