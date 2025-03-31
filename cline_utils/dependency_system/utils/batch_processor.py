"""
Utility module for parallel batch processing.
Provides efficient parallel execution of tasks with adaptive batch sizing.
"""

import os
import time
from typing import List, Callable, TypeVar, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from cline_utils.dependency_system.utils.cache_manager import cached

import logging
logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')

class BatchProcessor:
    """Generic batch processor for parallel execution of tasks."""

    def __init__(self, max_workers: Optional[int] = None, batch_size: Optional[int] = None, show_progress: bool = True):
        """
        Initialize the batch processor.

        Args:
            max_workers: Maximum number of worker threads (defaults to CPU count * 2, capped at 32)
            batch_size: Size of batches to process (defaults to adaptive sizing)
            show_progress: Whether to show progress information
        """
        cpu_count = os.cpu_count() or 1
        self.max_workers = max_workers or min(32, cpu_count * 2)
        self.batch_size = batch_size
        self.show_progress = show_progress
        self.total_items = 0
        self.processed_items = 0
        self.start_time = 0

    def process_items(self, items: List[T], processor_func: Callable[[T], R]) -> List[R]:
        """
        Process a list of items in parallel batches.

        Args:
            items: List of items to process
            processor_func: Function to process each item
        Returns:
            List of results from processing each item
        """
        if not callable(processor_func):
            logger.error("processor_func must be callable")
            raise ValueError("processor_func must be a callable")

        self.total_items = len(items)
        if not self.total_items:
            logger.info("No items to process")
            return []

        self.processed_items = 0
        self.start_time = time.time()

        actual_batch_size = self._determine_batch_size()
        logger.debug(f"Using batch size: {actual_batch_size} with {self.max_workers} workers")

        results = []
        for i in range(0, self.total_items, actual_batch_size):
            batch = items[i:i + actual_batch_size]
            batch_results = self._process_batch(batch, processor_func)
            results.extend(batch_results)
            self.processed_items += len(batch)
            if self.show_progress:
                self._show_progress()

        logger.info(f"Processed {self.total_items} items in {time.time() - self.start_time:.2f} seconds")
        return results

    def process_with_collector(self, items: List[T], processor_func: Callable[[T], R], collector_func: Callable[[List[R]], Any]) -> Any:
        """
        Process items in batches and collect results with a collector function.

        Args:
            items: List of items to process
            processor_func: Function to process each item
            collector_func: Function to collect and process batch results
        Returns:
            Result from the collector function
        """
        if not (callable(processor_func) and callable(collector_func)):
            logger.error("processor_func and collector_func must be callable")
            raise ValueError("processor_func and collector_func must be callable")

        self.total_items = len(items)
        if not self.total_items:
            logger.info("No items to process")
            return collector_func([])

        self.processed_items = 0
        self.start_time = time.time()

        actual_batch_size = self._determine_batch_size()
        logger.debug(f"Using batch size: {actual_batch_size} with {self.max_workers} workers")

        all_results = []
        for i in range(0, self.total_items, actual_batch_size):
            batch = items[i:i + actual_batch_size]
            batch_results = self._process_batch(batch, processor_func)
            all_results.extend(batch_results)
            self.processed_items += len(batch)
            if self.show_progress:
                self._show_progress()

        logger.info(f"Processed {self.total_items} items in {time.time() - self.start_time:.2f} seconds")
        return collector_func(all_results)

    def _determine_batch_size(self) -> int:
        """Determine adaptive batch size based on total items."""
        if self.batch_size is not None:
            return max(1, self.batch_size)
        if self.total_items < 100:
            return max(1, self.total_items // 4)
        elif self.total_items < 1000:
            return max(10, self.total_items // 10)
        else:
            return max(50, self.total_items // 20)

    def _process_batch(self, batch: List[T], processor_func: Callable[[T], R]) -> List[R]:
        """
        Process a single batch of items in parallel.

        Args:
            batch: Batch of items to process
            processor_func: Function to process each item
        Returns:
            List of results from processing the batch
        """
        if not batch:
            return []

        batch_results = [None] * len(batch)  # Preserve order
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(batch))) as executor:
            future_to_idx = {executor.submit(processor_func, item): i for i, item in enumerate(batch)}
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    batch_results[idx] = future.result()
                except Exception as e:
                    logger.exception(f"Error processing item at index {idx}: {e}")
                    batch_results[idx] = None  # Or raise, depending on desired behavior
        return [r for r in batch_results if r is not None]

    def _show_progress(self) -> None:
        """Show progress information."""
        elapsed_time = time.time() - self.start_time
        items_per_second = self.processed_items / max(0.1, elapsed_time)
        percent_complete = (self.processed_items / max(1, self.total_items)) * 100
        remaining_items = self.total_items - self.processed_items
        eta = remaining_items / items_per_second if items_per_second > 0 else 0

        print(
            f"Progress: {self.processed_items}/{self.total_items} ({percent_complete:.1f}%), "
            f"{items_per_second:.1f} items/s, ETA: {eta:.1f}s",
            end="\r"
        )
        if self.processed_items >= self.total_items:
            print()

# @cached("batch_processing",
#        key_func=lambda items, processor_func, max_workers=None, batch_size=None, show_progress=True:
#        f"process_items:{hash(str(items))}:{processor_func.__name__}:{max_workers}:{batch_size}:{show_progress}")
def process_items(items: List[T], processor_func: Callable[[T], R], max_workers: Optional[int] = None, batch_size: Optional[int] = None, show_progress: bool = True) -> List[R]:
    """Convenience function to process items in parallel."""
    processor = BatchProcessor(max_workers, batch_size, show_progress)
    return processor.process_items(items, processor_func)

#@cached("batch_collecting",
 #       key_func=lambda items, processor_func, collector_func, max_workers=None, batch_size=None, show_progress=True:
  #      f"process_with_collector:{hash(str(items))}:{processor_func.__name__}:{collector_func.__name__}:{max_workers}:{batch_size}:{show_progress}")
def process_with_collector(items: List[T], processor_func: Callable[[T], R], collector_func: Callable[[List[R]], Any], max_workers: Optional[int] = None, batch_size: Optional[int] = None, show_progress: bool = True) -> Any:
    """Convenience function to process items and collect results."""
    processor = BatchProcessor(max_workers, batch_size, show_progress)
    return processor.process_with_collector(items, processor_func, collector_func)

# EoF