import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

import typer
from tqdm import tqdm
from swebench.harness.run_evaluation import get_dataset_from_preds
from swebench.harness.test_spec.test_spec import make_test_spec
from swebench.harness.utils import KEY_INSTANCE_ID, get_predictions_from_file

from eval.run import run_eval
from minisweagent.environments.extra.vefaas.config import VefaasDeploymentConfig
from minisweagent.environments.extra.vefaas.utils import check_env
from minisweagent.run.extra.swebench import get_swebench_docker_image_name
from minisweagent.environments.extra import VEFAAS_ACCESS_KEY, VEFAAS_SECRET_KEY, VEFAAS_REGION, VEFAAS_FUNCTION_ID, VEFAAS_APIG_ENDPOINT
from minisweagent.environments.extra.vefaas.apig import get_function_endpoint

app = typer.Typer()


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

async def run_eval_all(test_specs, predictions, run_id, workers, timeout, rewrite_reports):
    sem = asyncio.Semaphore(workers)
    stats = {"✓": 0, "✖": 0, "error": 0}
    pbar = tqdm(total=len(test_specs), desc="Evaluation", postfix=stats)
    # env_config = check_env()
    # apig_endpoint = get_function_endpoint(env_config["access_key"], env_config["secret_key"], env_config["region"], env_config["function_id"])


    async def worker(test_spec):
        async with sem:
            try:
                vefaas_config = VefaasDeploymentConfig(
                    function_id = VEFAAS_FUNCTION_ID,
                    access_key = VEFAAS_ACCESS_KEY,
                    secret_key = VEFAAS_SECRET_KEY,
                    region = VEFAAS_REGION,
                    apig_endpoint = VEFAAS_APIG_ENDPOINT,
                    type="vefaas",
                    image=get_swebench_docker_image_name({KEY_INSTANCE_ID: test_spec.instance_id}),
                    command="curl -fsSL https://vefaas-swe.tos-cn-beijing.ivolces.com/swe-rex/install_1.4.0-optimize.sh | bash -s -- {token}",
                )
                deployment = vefaas_config.get_deployment()
                pred = predictions[test_spec.instance_id]
                result = await run_eval(
                    test_spec=test_spec,
                    pred=pred,
                    container=deployment,
                    run_id=run_id,
                    timeout=timeout,
                    rewrite_reports=rewrite_reports
                )
                result["instance_id"] = test_spec.instance_id
                
                if result.get("completed"):
                    if result.get("resolved"):
                        stats["✓"] += 1
                    else:
                        stats["✖"] += 1
                else:
                    stats["error"] += 1
            except Exception as e:
                logging.error(f"Error evaluating instance {test_spec.instance_id}: {e}")
                stats["error"] += 1
                result = {"completed": False, "resolved": False}
            finally:
                pbar.set_postfix(stats)
                pbar.update(1)
            return result


    tasks = [worker(spec) for spec in test_specs]
    results = await asyncio.gather(*tasks)
    pbar.close()
    return results

@app.command()
def submit(
    subset: str,
    split: str,
    predictions_path: str = typer.Option("preds.json", "--predictions_path"),
    run_id: Optional[str] = typer.Option(None, "--run_id"),
    instance_ids: Optional[str] = typer.Option(None, "--instance_ids"),
    output_dir: str = typer.Option("", "--output_dir"),
    overwrite: bool = typer.Option(False, "--overwrite"),
    gen_report: bool = typer.Option(True, "--gen_report"),
    workers: int = typer.Option(1, "--workers"),
):
    if subset == "":
        subset = "full"
    if split == "":
        split = "test"
    if run_id is None:
        run_id = uuid.uuid4().hex[:8]
    if output_dir != "":
        os.environ["EVALUATION_DIR"] = output_dir
    dataset_name = DATASET_MAPPING.get(subset, subset)
    
    print(f"Loading predictions from {predictions_path}...")
    predictions_list = get_predictions_from_file(predictions_path, subset, split)
    predictions = {pred[KEY_INSTANCE_ID]: pred for pred in predictions_list}

    instance_ids_list = instance_ids.split(",") if instance_ids else []

    print(f"Loading dataset {dataset_name} for split {split}...")
    dataset = get_dataset_from_preds(
        dataset_name, split, instance_ids_list, predictions, run_id, False,
    )

    test_specs = [make_test_spec(instance) for instance in dataset]

    print(f"Starting evaluation of {len(test_specs)} instances with {workers} workers...")

    results = asyncio.run(run_eval_all(test_specs, predictions, run_id, workers, 1800, overwrite))
    
    resolved = [res["instance_id"] for res in results if res.get("completed") and res.get("resolved")]
    unresolved = [res["instance_id"] for res in results if res.get("completed") and not res.get("resolved")]
    errored = [res["instance_id"] for res in results if not res.get("completed")]

    print("\nEvaluation Summary:")
    print(f"Total instances: {len(test_specs)}")
    print(f"Resolved   (✓): {len(resolved)}")
    print(f"Unresolved (✖): {len(unresolved)}")
    print(f"Errored       : {len(errored)}")

    if resolved:
        print(f"\nResolved IDs:\n{', '.join(resolved)}")
    if unresolved:
        print(f"\nUnresolved IDs:\n{', '.join(unresolved)}")
    if errored:
        print(f"\nErrored IDs:\n{', '.join(errored)}")
    
    if gen_report:
        print(f"\nReports saved to {output_dir}/{run_id}")

if __name__ == "__main__":
    app()
