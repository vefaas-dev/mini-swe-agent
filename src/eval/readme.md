# SWE-bench CLI

A command-line interface for interacting with the SWE-bench API. Use this tool to submit predictions, manage runs, and retrieve evaluation reports.

Read the full documentation [here](https://www.swebench.com/sb-cli/). For submission guidelines, see [here](https://swebench.com/sb-cli/submit-to-leaderboard).

## Subsets and Splits

SWE-bench has different subsets and splits available:

### Subsets
- `swe-bench-m`: The SWE-bench Multimodal dataset
- `swe-bench_verified`: 500 verified problems from SWE-bench [Learn more](https://openai.com/index/introducing-swe-bench-verified/)
- `swe-bench_lite`: A subset of the original SWE-bench for testing


### Splits
- `dev`: Development/validation split
- `test`: Test split (currently only available for `swe-bench_lite` and `swe-bench_verified`)

You'll need to specify both a subset and split for most commands.

## Usage

### Submit Predictions

Submit your model's predictions to SWE-bench:

```bash
sb-cli submit swe-bench-m test \
    --predictions_path predictions.json \
    --run_id my_run_id
```

Options:
- `--run_id`: ID of the run to submit predictions for (optional, defaults to the name of the parent directory of the predictions file)
- `--instance_ids`: Comma-separated list of specific instance IDs to submit (optional)
- `--output_dir`: Directory to save report files (default: sb-cli-reports)
- `--overwrite`: Overwrite existing report (default: 0)
- `--gen_report`: Generate a report after evaluation is complete (default: 1)
- `--workers`: Number of parallel workers to use for evaluation (default: 1)


## Predictions File Format

Your predictions file should be a JSON file in one of these formats:

```json
{
    "instance_id_1": {
        "model_patch": "...",
        "model_name_or_path": "..."
    },
    "instance_id_2": {
        "model_patch": "...",
        "model_name_or_path": "..."
    }
}
```