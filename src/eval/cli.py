import asyncio
import logging
import uuid
from pathlib import Path
from typing import Optional

import typer,os
from tqdm import tqdm
from swebench.harness.run_evaluation import get_dataset_from_preds
from swebench.harness.test_spec.test_spec import make_test_spec
from swebench.harness.utils import KEY_INSTANCE_ID, get_predictions_from_file

from eval.config import EvalConfig, DATASET_MAPPING
from eval.evaluator import run_eval
from minisweagent.environments.extra.vefaas.config import VefaasDeploymentConfig
from minisweagent.run.extra.swebench import get_swebench_docker_image_name
from minisweagent.environments.extra import (
    VEFAAS_ACCESS_KEY, 
    VEFAAS_SECRET_KEY, 
    VEFAAS_REGION, 
    VEFAAS_FUNCTION_ID, 
    VEFAAS_APIG_ENDPOINT
)

app = typer.Typer(help="SWE-bench Evaluation CLI")

async def run_eval_batch(test_specs, predictions, config: EvalConfig):
    sem = asyncio.Semaphore(config.workers)
    stats = {"✓": 0, "✖": 0, "error": 0}
    pbar = tqdm(total=len(test_specs), desc="Evaluation", postfix=stats)

    async def worker(test_spec):
        async with sem:
            try:
                vefaas_config = VefaasDeploymentConfig(
                    function_id=VEFAAS_FUNCTION_ID,
                    access_key=VEFAAS_ACCESS_KEY,
                    secret_key=VEFAAS_SECRET_KEY,
                    region=VEFAAS_REGION,
                    apig_endpoint=VEFAAS_APIG_ENDPOINT,
                    type="vefaas",
                    image=get_swebench_docker_image_name({KEY_INSTANCE_ID: test_spec.instance_id}),
                    command="curl -fsSL -o /tmp/install.sh https://vefaas-swe.tos-cn-beijing.ivolces.com/swe-rex/install_1.4.0-mini.sh && exec /bin/bash /tmp/install.sh {token}",
                )
                
                result = await run_eval(
                    test_spec=test_spec,
                    pred=predictions[test_spec.instance_id],
                    container=vefaas_config.get_deployment(),
                    run_id=config.run_id,
                    timeout=config.timeout,
                    rewrite_reports=config.overwrite
                )
                result["instance_id"] = test_spec.instance_id
                
                if result.get("completed"):
                    stats["✓" if result.get("resolved") else "✖"] += 1
                else:
                    stats["error"] += 1
                return result
            except Exception as e:
                logging.error(f"Error evaluating {test_spec.instance_id}: {e}")
                stats["error"] += 1
                return {"instance_id": test_spec.instance_id, "completed": False, "resolved": False}
            finally:
                pbar.set_postfix(stats)
                pbar.update(1)

    results = await asyncio.gather(*[worker(spec) for spec in test_specs])
    pbar.close()
    return results

@app.command()
def submit(
    subset: str = typer.Argument("full", help="Dataset subset"),
    split: str = typer.Argument("test", help="Dataset split"),
    predictions_path: Path = typer.Option("preds.json", "--predictions_path", help="Path to predictions file"),
    run_id: Optional[str] = typer.Option(None, "--run_id", help="Run ID"),
    instance_ids: Optional[str] = typer.Option(None, "--instance_ids", help="Comma-separated instance IDs"),
    output_dir: Path = typer.Option("sb-cli-reports", "--output_dir", help="Output directory"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing reports"),
    gen_report: bool = typer.Option(True, "--gen_report", help="Generate final report"),
    workers: int = typer.Option(1, "--workers", help="Number of parallel workers"),
    timeout: int = typer.Option(900, "--timeout", help="Timeout for seconds"),
):
    config = EvalConfig(
        subset=subset,
        split=split,
        predictions_path=predictions_path,
        run_id=run_id or uuid.uuid4().hex[:8],
        instance_ids=instance_ids.split(",") if instance_ids else [],
        output_dir=output_dir,
        overwrite=overwrite,
        gen_report=gen_report,
        workers=workers,
        timeout=timeout,
    )
    if output_dir != "":
        os.environ["EVALUATION_DIR"] = str(output_dir)

    print(f"Loading predictions from {config.predictions_path}...")
    preds_list = get_predictions_from_file(str(config.predictions_path), config.subset, config.split)
    predictions = {p[KEY_INSTANCE_ID]: p for p in preds_list}

    dataset_name = DATASET_MAPPING.get(config.subset, config.subset)
    print(f"Loading dataset {dataset_name} ({config.split})...")
    dataset = get_dataset_from_preds(dataset_name, config.split, config.instance_ids, predictions, config.run_id, False)
    test_specs = [make_test_spec(instance) for instance in dataset]

    print(f"Starting evaluation of {len(test_specs)} instances with {config.workers} workers...")
    results = asyncio.run(run_eval_batch(test_specs, predictions, config))
    
    _print_summary(results)
    if config.gen_report:
        print(f"\nReports saved to {config.output_dir}/{config.run_id}")

def _print_summary(results):
    resolved = [r["instance_id"] for r in results if r.get("completed") and r.get("resolved")]
    unresolved = [r["instance_id"] for r in results if r.get("completed") and not r.get("resolved")]
    errored = [r["instance_id"] for r in results if not r.get("completed")]

    print("\nEvaluation Summary:")
    print(f"Total: {len(results)}")
    print(f"Resolved   (✓): {len(resolved)}")
    print(f"Unresolved (✖): {len(unresolved)}")
    print(f"Errored       : {len(errored)}")

    for label, ids in [("Resolved", resolved), ("Unresolved", unresolved), ("Errored", errored)]:
        if ids:
            print(f"\n{label} IDs:\n{', '.join(ids)}")

if __name__ == "__main__":
    app()
