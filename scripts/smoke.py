"""Exercise upstream agent -> Docker task -> test -> patch, without SWE-bench claims."""

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from minisweagent import __version__
from minisweagent.agents.default import DefaultAgent
from minisweagent.config import get_config_from_spec
from minisweagent.environments.docker import DockerEnvironment
from minisweagent.models import get_model
from minisweagent.models.test_models import DeterministicModel, make_output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    name = "deepseek-smoke" if args.live else "deterministic-smoke"
    output = Path("/workspace/outputs") / name
    output.mkdir(parents=True, exist_ok=True)
    config = get_config_from_spec("/workspace/configs/local-swebench.yaml")
    env_config = dict(config["environment"])
    env_config["run_args"] = [arg for arg in env_config["run_args"] if not arg.startswith("--platform=")]
    env = DockerEnvironment(image="harness-rsi/mini-swe-agent:2.4.6", cwd="/testbed", **env_config)
    try:
        fixture = r"""from pathlib import Path
import subprocess
p = Path('/testbed')
(p/'calculator.py').write_text('def add(a, b):\n    return a - b\n')
(p/'test_calculator.py').write_text('import unittest\nfrom calculator import add\nclass TestAdd(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n        self.assertEqual(add(-2, 3), 1)\n')
subprocess.run(['git','init','-q'],cwd=p,check=True)
subprocess.run(['git','add','calculator.py','test_calculator.py'],cwd=p,check=True)
subprocess.run(['git','-c','user.name=Smoke','-c','user.email=smoke@example.invalid','commit','-qm','fixture'],cwd=p,check=True)
"""
        setup = env.execute({"command": "python - <<'PY'\n" + fixture + "\nPY"})
        assert setup["returncode"] == 0, setup
        before = env.execute({"command": "python -m unittest -v"})
        assert before["returncode"] != 0, "Fixture must initially fail"
        if args.live:
            model = get_model(config=config["model"])
        else:
            model = DeterministicModel(
                cost_per_call=0,
                outputs=[
                    make_output("Apply fixture repair", [{"command": "sed -i 's/return a - b/return a + b/' calculator.py"}], cost=0),
                    make_output("Test fixture", [{"command": "python -m unittest -v"}], cost=0),
                    make_output("Submit fixture", [{"command": "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT; git diff -- calculator.py"}], cost=0),
                ],
            )
        agent = DefaultAgent(
            model, env,
            system_template="You fix code using the bash tool. Use one tool per turn. After fixing and testing, submit using: echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT; git diff -- calculator.py",
            instance_template="{{task}}",
            step_limit=8,
            cost_limit=0.1,
            wall_time_limit_seconds=300,
            output_path=output / "trajectory.json",
        )
        result = agent.run("Fix add(a,b) in calculator.py. Do not modify tests. Run python -m unittest -v, then submit the patch.")
        after = env.execute({"command": "python -m unittest -v"})
        assert result["exit_status"] == "Submitted", result
        assert after["returncode"] == 0, after
        assert "calculator.py" in result["submission"], result
        assert env.execute({"command": "git diff --exit-code -- test_calculator.py"})["returncode"] == 0
        report = {
            "kind": name, "mini_version": __version__, "result": "PASS",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "model_name": model.config.model_name,
            "response_models": sorted({m.get("extra", {}).get("response", {}).get("model", "") for m in agent.messages if m.get("extra", {}).get("response", {}).get("model")}),
            "task_platform": "linux/arm64",
            "config_sha256": hashlib.sha256(Path('/workspace/configs/local-swebench.yaml').read_bytes()).hexdigest(),
            "real_llm": args.live, "swebench_result": False,
            "exit_status": result["exit_status"], "model_calls": agent.n_calls,
            "cost_usd_peak_rate_estimate": agent.cost,
            "failing_tests_before": before, "passing_tests_after": after,
        }
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        (output / "patch.diff").write_text(result["submission"])
        print(json.dumps(report, indent=2))
    finally:
        subprocess.run(["docker", "rm", "-f", env.container_id], check=True, capture_output=True)
        env.container_id = None


if __name__ == "__main__":
    main()
