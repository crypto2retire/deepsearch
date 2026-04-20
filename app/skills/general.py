from app.skills.base import Skill

GENERAL = Skill(
    id="general",
    name="General Research",
    icon="🔍",
    description="Broad research on any topic",
    planner_prompt=(
        "You are a research planner. Given a user query, break it into exactly 2 sub-tasks for parallel research.\n"
        'Return ONLY valid JSON — no explanation, no markdown — in this exact format:\n'
        '{"sub_tasks": [{"id": "task_1", "description": "...", "search_query": "..."}, {"id": "task_2", "description": "...", "search_query": "..."}]}\n'
        "- search_query should be a Google-friendly web search query.\n"
        "- Keep descriptions concise (1-2 sentences).\n"
        "- Each sub-task should cover a distinct aspect of the user's query."
    ),
    num_subtasks=2,
)
