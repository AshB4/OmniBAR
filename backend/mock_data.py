import random
from datetime import UTC, datetime, timedelta
from typing import Any, Iterable
from uuid import uuid4

SUITE_LABELS = {
    "output": "Calculator Demo Suite",
    "custom": "Custom Agents Suite",
    "crisis": "Crisis Command Suite",
    "all": "Run Everything",
}

SuiteTemplate = dict[str, Any]

SUITE_TEMPLATES: dict[str, list[SuiteTemplate]] = {
    "output": [
        {
            "id": "calc-string-check",
            "name": "Addition String Check",
            "iterations": 5,
            "base_success": 0.93,
            "latency": 0.42,
            "cost": 0.00015,
            "suite": "output",
            "failure_objective": "Addition accurate",
            "failure_reason": "Mismatch between expected string and response.",
        },
        {
            "id": "calc-regex-match",
            "name": "Multiplication Regex",
            "iterations": 4,
            "base_success": 0.88,
            "latency": 0.38,
            "cost": 0.00012,
            "suite": "output",
            "failure_objective": "Regex captures product",
            "failure_reason": "Output failed to match the expected multiplication pattern.",
        },
        {
            "id": "calc-objective-run",
            "name": "Combined Objective Run",
            "iterations": 3,
            "base_success": 0.81,
            "latency": 0.55,
            "cost": 0.0002,
            "suite": "output",
            "failure_objective": "All calculator objectives pass",
            "failure_reason": "One or more scenarios returned incorrect arithmetic.",
        },
    ],
    "custom": [
        {
            "id": "custom-weather",
            "name": "Weather Agent Scenario",
            "iterations": 6,
            "base_success": 0.79,
            "latency": 0.72,
            "cost": 0.00032,
            "suite": "custom",
            "failure_objective": "Weather summary accuracy",
            "failure_reason": "Temperature range omitted or mismatched city.",
        },
        {
            "id": "custom-translate",
            "name": "Translation Agent Accuracy",
            "iterations": 5,
            "base_success": 0.84,
            "latency": 0.63,
            "cost": 0.00029,
            "suite": "custom",
            "failure_objective": "EN→ES translation fidelity",
            "failure_reason": "Idiomatic phrase translated too literally.",
        },
        {
            "id": "custom-fallbacks",
            "name": "Fallback Strategy Guardrails",
            "iterations": 4,
            "base_success": 0.75,
            "latency": 0.81,
            "cost": 0.00033,
            "suite": "custom",
            "failure_objective": "Escalation to human",
            "failure_reason": "Agent failed to surface escalation guidance after tool failure.",
        },
    ],
    "crisis": [
        {
            "id": "crisis-inventory",
            "name": "Inventory Fulfillment",
            "iterations": 7,
            "base_success": 0.77,
            "latency": 0.94,
            "cost": 0.00041,
            "suite": "crisis",
            "failure_objective": "Backorder mitigation",
            "failure_reason": "Critical SKUs not prioritized during shortage.",
        },
        {
            "id": "crisis-routing",
            "name": "Crisis Routing Plan",
            "iterations": 6,
            "base_success": 0.7,
            "latency": 1.02,
            "cost": 0.00037,
            "suite": "crisis",
            "failure_objective": "Delivery routing",
            "failure_reason": "Suboptimal route increased ETA beyond policy.",
        },
        {
            "id": "crisis-communication",
            "name": "Stakeholder Comms",
            "iterations": 5,
            "base_success": 0.83,
            "latency": 0.88,
            "cost": 0.00035,
            "suite": "crisis",
            "failure_objective": "Escalation cadence",
            "failure_reason": "Status updates missed 30-min SLA window.",
        },
    ],
}


def _iter_suite_templates(suite: str) -> Iterable[SuiteTemplate]:
    if suite == "all":
        yield from SUITE_TEMPLATES["output"]
        yield from SUITE_TEMPLATES["custom"]
        yield from SUITE_TEMPLATES["crisis"]
    else:
        yield from SUITE_TEMPLATES.get(suite, [])


def _bounded(value: float, *, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _generate_history_slice(success_rate: float) -> list[dict[str, Any]]:
    now = datetime.now(UTC)
    entries: list[dict[str, Any]] = []
    for step in range(3):
        entries.append(
            {
                "timestamp": (now - timedelta(minutes=step * 5))
                .replace(microsecond=0)
                .isoformat(),
                "objective": f"Check {step + 1}",
                "result": success_rate > 0.5 or step < 1,
                "message": "Objective evaluated via OmniBAR mock snapshot.",
            }
        )
    return entries


def _generate_suite_payload(
    suite: str, threshold: float | None = None
) -> dict[str, Any]:
    now = datetime.now(UTC)
    benchmarks: list[dict[str, Any]] = []
    failure_insights: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []

    total_success = 0
    total_failed = 0

    for template in _iter_suite_templates(suite):
        success_rate = _bounded(template["base_success"] + random.uniform(-0.08, 0.08))
        status = "success" if success_rate >= 0.8 else "failed"
        if status == "success":
            total_success += 1
        else:
            total_failed += 1

        latency = max(template["latency"] + random.uniform(-0.2, 0.25), 0.08)
        cost = max(template["cost"] + random.uniform(-0.0002, 0.0002), 0.0)
        tokens = int(600 + random.uniform(-80, 120))

        history = _generate_history_slice(success_rate)
        benchmark = {
            "id": template["id"],
            "name": template["name"],
            "iterations": template["iterations"],
            "successRate": round(success_rate, 3),
            "status": status,
            "updatedAt": now.isoformat(),
            "suite": template.get("suite", suite),
            "latencySeconds": round(latency, 3),
            "tokensUsed": tokens,
            "costUsd": round(cost, 5),
            "confidenceReported": round(_bounded(success_rate * 0.96), 3),
            "confidenceCalibrated": round(_bounded(success_rate * 0.92), 3),
            "history": history,
        }

        if status == "failed":
            benchmark["latestFailure"] = {
                "objective": template.get("failure_objective"),
                "reason": template.get("failure_reason"),
                "category": "quality",
            }
            failure_insights.append(
                {
                    "id": f"insight-{template['id']}",
                    "benchmarkId": template["id"],
                    "benchmarkName": template["name"],
                    "failureRate": round(1 - success_rate, 3),
                    "lastFailureAt": now.isoformat(),
                    "topIssues": [
                        template.get(
                            "failure_reason", "Observed deviation in latest run."
                        ),
                        "Requires operator follow-up.",
                    ],
                    "recommendedFix": "Review prompt strategy and re-run targeted objectives.",
                    "failureCategory": "quality",
                    "history": history,
                }
            )

        benchmarks.append(benchmark)

    total = len(benchmarks)
    summary = {"total": total, "success": total_success, "failed": total_failed}

    recommendations = [
        {
            "id": f"rec-{suite}-playbook",
            "title": "Refresh evaluation playbook",
            "impact": "High",
            "summary": "Review the latest OmniBAR telemetry and confirm coverage of risky objectives.",
            "action": "Draft a remediation checklist for the agent team.",
        },
        {
            "id": f"rec-{suite}-guardrails",
            "title": "Tighten guardrails",
            "impact": "Medium",
            "summary": "Implement guardrail prompts for known failure modes captured in the insights panel.",
            "action": "Experiment with a low-temperature retry policy and compare scores.",
        },
    ]

    live_runs = [
        {
            "id": str(uuid4()),
            "benchmarkName": benchmarks[0]["name"] if benchmarks else "Calculator Demo",
            "status": "completed",
            "currentIteration": benchmarks[0]["iterations"] if benchmarks else 3,
            "totalIterations": benchmarks[0]["iterations"] if benchmarks else 3,
            "startedAt": now.isoformat(),
        },
        {
            "id": str(uuid4()),
            "benchmarkName": "OmniBAR Snapshot Builder",
            "status": "queued",
            "currentIteration": 0,
            "totalIterations": 5,
            "startedAt": None,
        },
    ]

    payload = {
        "benchmarks": benchmarks,
        "summary": summary,
        "liveRuns": live_runs,
        "failureInsights": failure_insights,
        "recommendations": recommendations,
        "generatedAt": now.isoformat(),
        "threshold": threshold,
    }
    return payload


