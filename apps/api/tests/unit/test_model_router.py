from app.core.config import Settings
from app.models.enums import LLMPurpose
from app.services.agent.model_router.router import ModelRouter


def test_different_purposes_can_use_different_models():
    s = Settings(
        ASKFLOW_ENV="test",
        SECRET_KEY="test-secret-key-not-for-prod",
        LLM_MODEL_CLASSIFY="model-classify-a",
        LLM_MODEL_GENERATE="model-generate-b",
    )
    r = ModelRouter(s)
    c = r.pick(LLMPurpose.INTENT_CLASSIFY)
    g = r.pick(LLMPurpose.RAG_GENERATE)
    assert c.model == "model-classify-a"
    assert g.model == "model-generate-b"
    assert c.purpose != g.purpose
