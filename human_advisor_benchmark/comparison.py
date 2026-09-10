"""Explicit model experiments in an isolated benchmark process, never production."""
from dataclasses import dataclass
PROFILES={
    "baseline": {"model":None,"reasoning_effort":None,"adapter":"canonical /advisor"},
    "sol_medium": {"model":"gpt-5.6-sol","reasoning_effort":"medium","adapter":"same advisor with injected model configuration"},
    "astra_light": {"model":"gpt-6-astra","reasoning_effort":"low","adapter":"same advisor with injected model configuration"},
}
class ConfiguredResponses:
    def __init__(self, responses, model, effort):
        self.original=responses; self.model=model; self.effort=effort
    def create(self, **kwargs):
        # Applied on every round, not just the first request.
        return self.original.create(**{**kwargs,"model":self.model,"reasoning":{"effort":self.effort}})

class ConfiguredClient:
    def __init__(self, original, model, effort):
        self.responses=ConfiguredResponses(original.responses,model,effort)

def make_app(profile):
    from fastapi import FastAPI, HTTPException
    from main import AdvisorRequest
    from ai_advisor import answer_student_question
    from openai import OpenAI
    config=PROFILES[profile]
    client=ConfiguredClient(OpenAI(),config["model"],config["reasoning_effort"])
    app=FastAPI(title="Isolated benchmark model experiment")
    @app.post("/advisor")
    def advisor(request: AdvisorRequest):
        try:
            return answer_student_question(question=request.question,completed_courses=[],
                conversation=[m.model_dump() for m in request.conversation],
                conversation_state=request.conversation_state,client=client)
        except ValueError as e:
            raise HTTPException(status_code=400,detail=str(e)) from e
    return app
