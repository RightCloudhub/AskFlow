"""out_of_scope refusal + offline eval runner."""

import pytest

from app.services.agent.intent.classifier import IntentClassifier
from app.services.agent.pipeline.runner import MessagePipeline
from app.services.eval_runner.runner import EvalRunner


@pytest.mark.asyncio
async def test_out_of_scope_pipeline_refuses():
    ir = await IntentClassifier().classify("请给我癌症治疗方案和处方建议")
    assert ir.intent.value == "out_of_scope"
    pr = await MessagePipeline().handle("请给我癌症治疗方案和处方建议")
    assert pr.refused is True
    assert pr.route == "refuse"
    assert pr.intent == "out_of_scope"
    assert "根据知识库资料" not in pr.answer
    assert "业务范围" in pr.answer or "超出" in pr.answer


@pytest.mark.asyncio
async def test_eval_runner_passes_corpora():
    report = await EvalRunner().run()
    assert report.ok, [(r.path, r.detail) for r in report.results if not r.ok]
    assert report.passed >= 5
