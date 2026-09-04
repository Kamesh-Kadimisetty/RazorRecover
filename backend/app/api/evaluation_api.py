from fastapi import APIRouter
from backend.app.ml.evaluator import run_batch_evaluation

router = APIRouter(prefix="/api/evaluation", tags=["Evaluation Benchmark"])

# Cache benchmark result so it responds instantly
_CACHED_BENCHMARK = None

@router.get("/benchmark")
def get_benchmark_results():
    """Returns benchmark comparison results across all 4 strategies."""
    global _CACHED_BENCHMARK
    if _CACHED_BENCHMARK is None:
        _CACHED_BENCHMARK = run_batch_evaluation(num_cases=1000, seed=42)
    return _CACHED_BENCHMARK

@router.post("/run-benchmark")
def rerun_benchmark():
    """Forces re-execution of the 1,000-case evaluation benchmark."""
    global _CACHED_BENCHMARK
    _CACHED_BENCHMARK = run_batch_evaluation(num_cases=1000, seed=42)
    return _CACHED_BENCHMARK
