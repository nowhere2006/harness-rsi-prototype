"""Verify one official task image and dataset metadata; no LLM or grading."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from datasets import load_dataset

from minisweagent.config import get_config_from_spec
from minisweagent.run.benchmarks.swebench import DATASET_MAPPING, get_sb_environment, get_swebench_docker_image_name
from minisweagent.utils.serialize import recursive_merge

instance_id = "sympy__sympy-20590"
dataset = load_dataset(DATASET_MAPPING["verified"], split="test")
instance = next(item for item in dataset if item["instance_id"] == instance_id)
config = recursive_merge(get_config_from_spec("swebench.yaml"), get_config_from_spec("/workspace/configs/local-swebench.yaml"))
env = get_sb_environment(config, instance)
try:
    checks = {}
    for name, command in {
        "architecture": "uname -m",
        "base_commit": "git rev-parse HEAD",
        "working_tree": "git status --porcelain",
        "python": "python --version",
        "package_execution": "python -c 'import sympy; assert sympy.simplify(sympy.sympify(\"(x+1)**2-x**2-2*x\")) == 1; print(sympy.__version__)'",
    }.items():
        checks[name] = env.execute({"command": command}, timeout=120)
        assert checks[name]["returncode"] == 0, checks[name]
    baseline_probe = """import json, subprocess
base = %r
raw = subprocess.check_output(['git','diff','--raw','--abbrev=40',base,'HEAD'],text=True)
rows = [line.split('\t',1)[0].split() for line in raw.splitlines()]
assert all(row[2] == row[3] for row in rows), 'Task image has source content differences from dataset baseline'
print(json.dumps({'source_content_matches_base_commit': True, 'mode_only_changes': len(rows), 'mode_changes': sorted({row[0][1:] + ' -> ' + row[1] for row in rows})}))
""" % instance["base_commit"]
    checks["baseline_source"] = env.execute({"command": "python - <<'PY'\n" + baseline_probe + "\nPY"})
    assert checks["baseline_source"]["returncode"] == 0, checks["baseline_source"]
    assert checks["working_tree"]["output"].strip() == "", checks["working_tree"]
    assert checks["architecture"]["output"].strip() == "x86_64", checks
    image = get_swebench_docker_image_name(instance)
    image_info = json.loads(subprocess.check_output(["docker", "image", "inspect", image, "--format", "{{json .RepoDigests}}"], text=True))
    report = {
        "result": "PASS", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "kind": "official-swebench-task-environment-only", "real_llm": False,
        "dataset": DATASET_MAPPING["verified"], "split": "test", "dataset_fingerprint": dataset._fingerprint,
        "instance_id": instance_id, "base_commit": instance["base_commit"],
        "image": image, "image_repo_digests": image_info, "host_architecture": "arm64",
        "task_platform": "linux/amd64", "checks": checks,
        "prediction_generated": False, "swebench_evaluated": False, "resolved": None,
    }
    Path("/workspace/artifacts/swebench-task-environment.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
finally:
    subprocess.run(["docker", "rm", "-f", env.container_id], check=True, capture_output=True)
    env.container_id = None
