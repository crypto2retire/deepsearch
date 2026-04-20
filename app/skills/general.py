from app.skills.base import Skill

GENERAL = Skill(
    id="general",
    name="General",
    icon="🔍",
    description="Broad research across multiple topics and sources",
    planner_prompt=(
        "You are a research planner. Given a user query, break it into 2 sub-tasks for parallel research.\n"
        'Return ONLY valid JSON — no explanation, no markdown:\n'
        '{"sub_tasks": [{"id": "task_1", "description": "...", "search_query": "..."}, ...]}\n'
        "Create sub-tasks that together cover the full scope of the query.\n"
        "- Each search_query should be specific and focused."
    ),
    num_subtasks=2,
    synthesizer_prompt='You are a senior research writer. Given findings from multiple researchers, produce a detailed written report.\nReturn ONLY valid JSON:\n{"answer": "...", "sources": [...], "follow_up_questions": [...]}\nWrite a comprehensive report with:\n- At least 3-4 paragraphs per major section, written as flowing analytical prose\n- Written as flowing analytical prose, not bullet-point lists\n- Explain the significance and implications of each finding\n- Connect findings together to tell a coherent story\n- Use [1][2] inline citations referencing the source numbers\n- Minimum 500 words total\n- sources list all cited sources with their numbers\n- Provide 3-5 thoughtful follow-up questions',
)
