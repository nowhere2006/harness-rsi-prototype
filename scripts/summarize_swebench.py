"""Summarize one completed attempt without running models or changing scores."""

import argparse
import hashlib
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    run = root / "outputs" / args.run_id
    manifest = json.loads((run / "run-manifest.json").read_text())
    iid = manifest["instance_id"]
    trajectory_path = run / iid / f"{iid}.traj.json"
    trajectory = json.loads(trajectory_path.read_text())
    prediction = json.loads((run / "preds.json").read_text())[iid]
    reports = list((run / "evaluation" / "logs" / "run_evaluation").glob(f"*/**/{iid}/report.json"))
    assert len(reports) == 1, "Expected exactly one evaluation result"
    official = json.loads(reports[0].read_text())[iid]
    usage = {}
    responses = []
    steps = []
    for message in trajectory["messages"]:
        extra = message.get("extra", {})
        if response := extra.get("response"):
            responses.append(response)
            for key, value in (response.get("usage") or {}).items():
                if isinstance(value, (int, float)):
                    usage[key] = usage.get(key, 0) + value
        if actions := extra.get("actions"):
            steps.append([action.get("command", "") for action in actions])
    counts = {group: {state: len(tests) for state, tests in values.items()} for group, values in official["tests_status"].items()}
    patch = prediction["model_patch"]
    (run / "model.patch").write_text(patch)
    input_tokens = usage["prompt_tokens"]
    cached_tokens = usage.get("prompt_cache_hit_tokens", 0)
    missed_tokens = usage.get("prompt_cache_miss_tokens", input_tokens - cached_tokens)
    peak_cost = missed_tokens * 0.3e-6 + cached_tokens * 0.006e-6 + usage["completion_tokens"] * 1.2e-6
    summary = {
        "run_id": args.run_id, "instance_id": iid,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "attempts": 1, "seed": manifest["seed"],
        "model_name": prediction["model_name_or_path"],
        "response_models": sorted({r.get("model", "") for r in responses}),
        "agent_version": trajectory["info"]["mini_version"],
        "agent_commit": manifest["upstream_commit"],
        "agent_exit_status": trajectory["info"]["exit_status"],
        "model_calls": trajectory["info"]["model_stats"]["api_calls"],
        "tool_commands": sum(len(s) for s in steps),
        "usage": usage,
        "cost_usd_litellm_reported_estimate": trajectory["info"]["model_stats"]["instance_cost"],
        "cost_usd_recomputed_peak_rate_estimate": peak_cost,
        "cost_usd_recomputed_off_peak_rate_estimate": peak_cost / 2,
        "cost_note": "Client estimate agrees with off-peak rates; no provider billing statement was read. Peak-rate recomputation is separate.",
        "price_source": "https://api-docs.deepseek.com/quick_start/pricing/",
        "official_evaluation": {"resolved": official["resolved"], "patch_applied": official["patch_successfully_applied"], "infra_failure": official.get("infra_failure"), "test_counts": counts},
        "grading_dataset": json.loads((run / "evaluation" / "dataset-provenance.json").read_text()),
        "patch_files": re.findall(r"^diff --git a/(.*?) b/", patch, flags=re.M),
        "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
        "source_modified_in_controller": False,
        "rsi_method_implemented": False,
        "claim_boundary": "One selected task passed in one attempt; not a full benchmark score, model success probability, or RSI improvement.",
        "artifacts": {"trajectory": str(trajectory_path.relative_to(run)), "patch": "model.patch", "official_report": str(reports[0].relative_to(run)), "test_output": str((reports[0].parent / "test_output.txt").relative_to(run))},
    }
    assert summary["agent_exit_status"] == "Submitted"
    assert summary["model_calls"] == len(responses)
    (run / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    status = "通过" if official["resolved"] else "未通过"
    links = " · ".join(f'<a href="{html.escape(path, quote=True)}">{html.escape(label)}</a>' for label, path in summary["artifacts"].items())
    step_html = "".join(f'<details><summary>模型第 {i} 轮 · {len(commands)} 个命令</summary><pre>{html.escape(chr(10).join(commands))}</pre></details>' for i, commands in enumerate(steps, 1))
    rows = [
        ("任务", iid), ("模型 / Agent", f"{summary['model_name']} / mini-swe-agent {summary['agent_version']}"),
        ("官方评分", f"resolved = {str(official['resolved']).lower()}"),
        ("故障修复测试", f"{counts['FAIL_TO_PASS']['success']} 通过，{counts['FAIL_TO_PASS']['failure']} 失败"),
        ("回归测试", f"{counts['PASS_TO_PASS']['success']} 通过，{counts['PASS_TO_PASS']['failure']} 失败"),
        ("模型调用 / 工具命令", f"{summary['model_calls']} 次 / {summary['tool_commands']} 条"),
        ("输入 / 输出 token", f"{input_tokens:,} / {usage['completion_tokens']:,}"),
        ("客户端费用估算", f"US${summary['cost_usd_litellm_reported_estimate']:.8f}"),
        ("峰值价保守重算", f"US${peak_cost:.8f}"),
    ]
    table = "".join(f"<tr><th>{html.escape(k)}</th><td>{html.escape(str(v))}</td></tr>" for k, v in rows)
    page = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SWE-bench 单题结果</title>
<style>body{{font:16px/1.65 system-ui,sans-serif;max-width:1000px;margin:40px auto;padding:0 24px;color:#20303c;background:#fafbfc}}h1{{font-size:30px}}.badge{{display:inline-block;padding:4px 12px;border-radius:20px;background:#dff3e7;color:#175433}}table{{border-collapse:collapse;width:100%;background:white}}td,th{{border-bottom:1px solid #dde3e8;text-align:left;padding:11px}}th{{width:28%}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#eef1f4;padding:16px;border-radius:8px;font-size:13px}}details{{margin:10px 0;background:white;padding:12px;border:1px solid #dde3e8;border-radius:8px}}a{{color:#1b5b97}}.note{{padding:16px;background:#fff3d5;border-radius:8px}}</style>
<h1>SWE-bench 单题结果 <span class="badge">{status}</span></h1>
<p>原版 mini-swe-agent + DeepSeek Flash 的一次正式尝试。任务补丁由模型生成，主 Agent 未修改候选补丁；官方评分与测试结果见下表。</p>
<table>{table}</table>
<p class="note">一次手选任务、一次尝试。此结果支持本题通过和运行链路可用；不能据此推断完整 benchmark 成功率或 RSI 改进。模型服务返回别名 deepseek-flash，服务端精确权重版本未独立核实。费用是估算，未读取服务商账单。</p>
<p>{links}</p><h2>模型提交的补丁</h2><pre>{html.escape(patch)}</pre>
<h2>执行轨迹中的命令</h2><p>每项对应一轮模型响应，可展开查看命令。原始轨迹另存于上方链接。</p>{step_html}
<h2>来源与复现边界</h2><p>Agent commit：<code>{html.escape(summary['agent_commit'])}</code>。测试定义来自官方 SWE-bench/SWE-bench_Verified，revision：<code>{html.escape(summary['grading_dataset']['revision'])}</code>。推理使用 princeton-nlp 版本的同一实例，基线 commit 已核对相同。ARM64 Mac 上执行 linux/amd64 任务容器。</p>
<p>完整命令、配置快照、种子说明和预算在同目录 run-manifest.json 与 summary.json。原版 Agent 源码保持干净；生成的任务补丁作为结果文件保存。</p></html>'''
    (run / "report.html").write_text(page)
    print(json.dumps({"resolved": official["resolved"], "model_calls": summary["model_calls"], "cost_reported_estimate": summary["cost_usd_litellm_reported_estimate"], "peak_rate_estimate": peak_cost, "report": str(run / "report.html")}, indent=2))


if __name__ == "__main__":
    main()
