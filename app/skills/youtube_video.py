from app.skills.base import Skill

YOUTUBE_VIDEO = Skill(
    id="youtube_video",
    name="YouTube Video",
    icon="🎬",
    description="Video scripts, hooks, chapters, thumbnails",
    planner_prompt=(
        "You are a YouTube content planner. Given a user query about creating a YouTube video, "
        "break it into exactly 3 sub-tasks for parallel research.\n"
        'Return ONLY valid JSON — no explanation, no markdown:\n'
        '{"sub_tasks": [{"id": "task_1", "description": "...", "search_query": "..."}, ...]}\n'
        "Create sub-tasks covering:\n"
        "1. Top-performing videos on this topic (views, engagement, titles, thumbnails)\n"
        "2. Keywords, SEO, and audience retention strategies for this niche\n"
        "3. Content gaps — what's missing from existing videos that viewers want\n"
        "- search_query should include 'YouTube' and target specific video formats.\n"
        "- Focus on finding actionable insights from successful channels."
    ),
    num_subtasks=3,
    researcher_prompt=(
        "You are a YouTube research analyst. Given a sub-task and search results, extract video content insights.\n"
        "Return ONLY valid JSON — no explanation, no markdown:\n"
        '{"facts": [{"fact": "...", "source": "url"}]}\n'
        "Focus on extracting:\n"
        "- Successful video titles, their view counts, and what makes them clickable\n"
        "- Thumbnail patterns and design elements that drive clicks\n"
        "- Audience retention data and optimal video lengths\n"
        "- Keyword search volumes and trending topics\n"
        "- Content gaps — questions viewers ask that aren't well answered\n"
        "Extract up to 7 facts. Always include source URLs."
    ),
    synthesizer_prompt=(
        "You are a YouTube content synthesizer. Given research findings, create a complete video production package.\n"
        'Return ONLY valid JSON:\n'
        '{"answer": "...", "sources": [...], "follow_up_questions": [...]}\n'
        "Structure your answer in markdown with:\n"
        "## Video Title Options — 5 clickable title ideas (ranked by CTR potential)\n"
        "## Hook (First 30 Seconds) — Exact opening script to maximize retention\n"
        "## Full Script — Complete video script with natural speaking tone, including:\n"
        "  - Timestamps for each chapter (## [00:00] Chapter Title)\n"
        "  - B-roll suggestions in brackets [B-roll: ...]\n"
        "  - CTA placement points\n"
        "## Thumbnail Concepts — 3 thumbnail ideas with text overlay, colors, and composition\n"
        "## Description & Tags — SEO-optimized description (first 2 lines for search), 15 tags\n"
        "## End Screen CTA — Subscribe prompt and next video suggestion\n"
        "Use [1][2] inline citations. Provide 3-5 follow-up questions."
    ),
)
