from app.skills.base import Skill

YOUTUBE_VIDEO = Skill(
    id="youtube_video",
    name="YouTube Video",
    icon="▶️",
    description="Video scripts for YouTube and short-form video content",
    planner_prompt=(
        "You are a video content planner. Given a user query about a topic for a YouTube video, "
        "break it into exactly 2 sub-tasks for parallel research.\n"
        'Return ONLY valid JSON -- no explanation, no markdown:\n'
        '{"sub_tasks": [{"id": "task_1", "description": "...", "search_query": "..."}, {"id": "task_2", "description": "...", "search_query": "..."}]}\n'
        "task_1: Research the main topic -- key facts, statistics, expert opinions, recent developments.\n"
        "task_2: Research the audience -- what viewers of this topic care about, common questions, engaging angles.\n"
        "- Each search_query must be specific and include relevant topic terms."
    ),
    num_subtasks=2,
    researcher_prompt=(
        "You are a video content researcher. Given a sub-task and search results, extract key information.\n"
        "Return ONLY valid JSON -- no explanation, no markdown:\n"
        '{"facts": [{"fact": "...", "source": "url"}]}\n'
        "Extract:\n"
        "- Key facts, statistics, data points\n"
        "- Expert opinions and quotes\n"
        "- Audience-relevant angles and questions\n"
        "- Recent news or developments\n"
        "Return up to 7 facts with source URLs."
    ),
    synthesizer_prompt=(
        "You are an expert YouTube content writer. Given research findings, write a complete video script.\n"
        'Return ONLY valid JSON:\n'
        '{"answer": "...", "sources": [...], "follow_up_questions": []}\n'
        "Write a complete, ready-to-film YouTube video script with these elements:\n"
        "## Hook (first 15 seconds) -- A compelling opening line that grabs attention immediately\n"
        "## Introduction (30 seconds) -- Who you are, what the video covers, why it matters\n"
        "## Main Content (3-5 min) -- The core information organized in logical sections with smooth transitions\n"
        "## Call to Action -- Like, subscribe, comment, and visit the link in description\n"
        "## Closing -- Memorable final thought or teaser for next video\n"
        "IMPORTANT REQUIREMENTS:\n"
        "- Write the COMPLETE script -- not an outline, not tips, the actual script with dialogue\n"
        "- Include [INTRO], [HOOK], [MAIN CONTENT], [OUTRO] section markers\n"
        "- Script should be 4-7 minutes long when spoken aloud\n"
        "- Use conversational tone -- how a real YouTuber would talk\n"
        "- Include specific facts, examples, and data points from research\n"
        "- Use [1][2] inline citations in the script where facts are mentioned\n"
        "- sources list all cited sources with number, title, and URL\n"
        "- follow_up_questions should be empty"
    ),
)
