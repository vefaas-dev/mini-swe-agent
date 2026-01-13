.PHONY: swebench_single swebench eval

swebench_single:
	@echo "Running SWE-Bench on single instance"
	@mini-extra swebench-single -c swebench_vefaas.yaml

swebench:
	@echo "Running SWE-Bench"
	@mini-extra swebench -c swebench_vefaas.yaml  --split=test --shuffle --output=preds --workers=20

eval:
	@echo "Evaluating SWE-Bench"
	@sb-cli verified test --predictions_path preds/preds.json --workers=20 --output_dir eval
