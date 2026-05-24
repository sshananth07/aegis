from enum import Enum 

class EvaluationStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    partially_completed = "partially_completed"
    cancelled = "cancelled"
    review_required = "review_required"

class BenchmarkRunStatus(str, Enum): 
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    partially_completed = "partially_completed"


