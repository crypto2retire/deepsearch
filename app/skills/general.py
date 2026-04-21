from app.skills.base import Skill

GENERAL = Skill(
    id="general",
    name="General",
    icon="🔍",
    description="Broad research across multiple topics and sources",
    planner_prompt=(
        "You are a research planner. Given a user query, break it into exactly 4 sub-tasks for parallel research.\n"
        'Return ONLY valid JSON -- no explanation, no markdown:\n'
        '{"sub_tasks": [{"id": "task_1", "description": "...", "search_query": "..."}, {"id": "task_2", "description": "...", "search_query": "..."}, {"id": "task_3", "description": "...", "search_query": "..."}, {"id": "task_4", "description": "...", "search_query": "..."}]}\n'
        "Create 4 distinct sub-tasks that together provide comprehensive coverage of the query.\n"
        "- Each sub-task should cover a different angle or aspect of the topic\n"
        "- Each search_query must be specific and focused, including key terms from the query\n"
        "- Prioritize the most current and authoritative sources"
    ),
    num_subtasks=4,
    synthesizer_prompt=(
        "You are a senior research writer. Given findings from multiple researchers, produce a detailed written report.\n"
        'Return ONLY valid JSON:\n'
        '{"answer": "...", "sources": [...], "follow_up_questions": [...]}\n'
        "Write a comprehensive report with:\n"
        "- At least 3-4 paragraphs per major section, written as flowing analytical prose\n"
        "- Written as flowing analytical prose, not bullet-point lists\n"
        "- Explain the significance and implications of each finding\n"
        "- Connect findings together to tell a coherent story\n"
        "- Use [1][2] inline citations referencing the source numbers\n"
        "- Minimum 500 words total\n"
        "- sources list all cited sources with their numbers\n"
        "- Provide 3-5 thoughtful follow-up questions"
    ),
)
