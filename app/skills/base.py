from dataclasses import dataclass, field


@dataclass
class Skill:
    id: str
    name: str
    icon: str
    description: str
    planner_prompt: str
    num_subtasks: int = 4
    researcher_prompt: str = ""
    synthesizer_prompt: str = ""

    def get_planner_prompt(self) -> str:
        return self.planner_prompt

    def get_researcher_prompt(self) -> str:
        return self.researcher_prompt or (
            "You are a research analyst. Given a sub-task description and search results, extract the 5 most important facts.\n"
            "Return ONLY valid JSON -- no explanation, no markdown:\n"
            '{"facts": [{"fact": "...", "source": "url or \'general knowledge\'"}]}\n'
            "- Each fact should be concise and directly relevant to the sub-task.\n"
            "- Cite the source URL for each fact where available."
        )

    def get_synthesizer_prompt(self) -> str:
        return self.synthesizer_prompt or (
            "You are a senior research writer. Given findings from multiple researchers, produce a detailed written report.\n"
            'Return ONLY valid JSON:\n'
            '{"answer": "Full markdown report (500+ words, multiple paragraphs per section, written in prose not bullet points)...", "sources": [{"number": 1, "title": "...", "url": "..."}], "follow_up_questions": ["Q1", "Q2", "Q3"]}\n'
            "Write a comprehensive report with:\n"
            "- At least 3-4 paragraphs per major section\n"
            "- Written as flowing analytical prose, not bullet-point lists\n"
            "- Explain the significance and implications of each finding\n"
            "- Connect findings together to tell a coherent story\n"
            "- Use [1][2] inline citations referencing the source numbers\n"
            "- sources list all cited sources with their numbers\n"
            "- Provide EXACTLY 3 follow-up questions that dig deeper into the topic"
        )
