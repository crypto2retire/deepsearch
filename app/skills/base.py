from dataclasses import dataclass, field


@dataclass
class Skill:
    id: str
    name: str
    icon: str
    description: str
    planner_prompt: str
    num_subtasks: int = 2
    researcher_prompt: str = ""
    synthesizer_prompt: str = ""

    def get_planner_prompt(self) -> str:
        return self.planner_prompt

    def get_researcher_prompt(self) -> str:
        return self.researcher_prompt or (
            "You are a research analyst. Given a sub-task description and search results, extract the 5 most important facts.\n"
            "Return ONLY valid JSON — no explanation, no markdown:\n"
            '{"facts": [{"fact": "...", "source": "url or \'general knowledge\'"}]}\n'
            "- Each fact should be concise and directly relevant to the sub-task.\n"
            "- Cite the source URL for each fact where available."
        )

    def get_synthesizer_prompt(self) -> str:
        return self.synthesizer_prompt or (
            "You are a research synthesizer. Given findings from multiple researchers, produce a comprehensive, well-cited answer.\n"
            'Return ONLY valid JSON:\n'
            '{"answer": "Full markdown answer with [1][2] inline citations...", "sources": [{"number": 1, "title": "...", "url": "..."}], "follow_up_questions": ["Q1", "Q2", "Q3"]}\n'
            "- answer should be in markdown with numbered inline citations [1][2]\n"
            "- sources should list all cited sources with their numbers\n"
            "- Provide 3-5 follow-up questions that dig deeper into the topic"
        )
