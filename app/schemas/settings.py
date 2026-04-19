from pydantic import BaseModel


class LLMPrefsIn(BaseModel):
    planner_model: str = "openrouter/meta-llama/llama-3.1-8b-instruct"
    researcher_model: str = "openrouter/meta-llama/llama-3.3-70b-instruct"
    synthesizer_model: str = "openrouter/meta-llama/llama-3.3-70b-instruct"
    provider_api_key: str
    provider_type: str = "openrouter"


class LLMPrefsOut(BaseModel):
    planner_model: str
    researcher_model: str
    synthesizer_model: str
    provider_type: str

    class Config:
        from_attributes = True
