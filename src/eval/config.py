from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

@dataclass
class EvalConfig:
    subset: str = "full"
    split: str = "test"
    predictions_path: Path = Path("preds.json")
    run_id: Optional[str] = None
    instance_ids: list[str] = field(default_factory=list)
    output_dir: Path = Path("sb-cli-reports")
    overwrite: bool = False
    gen_report: bool = True
    workers: int = 1
    timeout: int = 900

DATASET_MAPPING = {
    "full": "princeton-nlp/SWE-Bench",
    "verified": "princeton-nlp/SWE-Bench_Verified",
    "lite": "princeton-nlp/SWE-Bench_Lite",
    "multimodal": "princeton-nlp/SWE-Bench_Multimodal",
    "multilingual": "swe-bench/SWE-Bench_Multilingual",
    "smith": "SWE-bench/SWE-smith",
    "_test": "klieret/swe-bench-dummy-test-dataset",
    "swe-bench-m": "princeton-nlp/SWE-Bench_Multimodal",
    "swe-bench_verified": "princeton-nlp/SWE-Bench_Verified",
    "swe-bench_lite": "princeton-nlp/SWE-Bench_Lite",
}
