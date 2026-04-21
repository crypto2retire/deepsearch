from app.skills.base import Skill

SOCIAL_CONTENT = Skill(
    id="social_content",
    name="Social Media Post",
    icon="📱",
    description="Generate posts for Facebook, Twitter, LinkedIn, Instagram, TikTok",
    planner_prompt=(
        "You are a social media copywriter planner. Given a user request to create a post for a specific business, "
        "create exactly 2 sub-tasks:\n"
        'Return ONLY valid JSON -- no explanation, no markdown:\n'
        '{"sub_tasks": [{"id": "task_1", "description": "...", "search_query": "..."}, {"id": "task_2", "description": "...", "search_query": "..."}]}\n'
        "IMPORTANT SEARCH QUERY RULES:\n"
        "- task_1: Research the business -- search for the business name + location + 'reviews' or 'website' to find their actual information\n"
        "- task_2: Research the target social platform + business niche -- find examples of high-performing posts, effective hashtags, and CTAs for this type of business\n"
        "- ALWAYS include location if the business is local (city, state)\n"
        "- Search queries must be specific -- e.g. 'Clear The Clutter Junk Removal Oshkosh reviews' not 'junk removal'\n"
        "- Platform detection: if the query mentions 'Facebook' or 'fb', target Facebook. 'Twitter' or 'X', target Twitter/X. "
        "'LinkedIn', target LinkedIn. 'Instagram' or 'TikTok', target that platform. If unspecified, default to Facebook.\n"
    ),
    num_subtasks=2,
    researcher_prompt=(
        "You are a social media researcher. Given a sub-task and search results, extract all useful information.\n"
        "Return ONLY valid JSON -- no explanation, no markdown:\n"
        '{"facts": [{"fact": "...", "source": "url"}]}\n'
        "Extract:\n"
        "- Business name, location, services offered, unique selling points from their website\n"
        "- Customer pain points or emotional triggers from reviews\n"
        "- Effective hooks, CTAs, hashtags used in similar local business posts\n"
        "- Platform-specific formatting tips (character limits, media preferences)\n"
        "IMPORTANT: Only extract information that appears in the search results. Do NOT make up business details.\n"
        "Return up to 7 facts with source URLs."
    ),
    synthesizer_prompt=(
        "You are an expert social media copywriter. Given research findings about a business and platform best practices, "
        "write the actual social media post that was requested.\n"
        'Return ONLY valid JSON:\n'
        '{"answer": "the complete, polished social media post (no markdown code fences, no explanations, just the post text)", "sources": [{"number": 1, "title": "...", "url": "..."}], "follow_up_questions": []}\n'
        "Requirements for the post:\n"
        "- Write the COMPLETE post -- not a strategy, not an outline, not tips -- the actual post ready to publish\n"
        "- Start with a HOOK that grabs attention in the first line\n"
        "- Include the business name, what they do, and a clear CTA (call-to-action)\n"
        "- Add 1-2 relevant hashtags at the end (or more if platform allows)\n"
        "- Match the tone and format of the target platform (Facebook = conversational, LinkedIn = professional, etc.)\n"
        "- If location is relevant, include it for local SEO\n"
        "- Keep it authentic -- like a real person wrote it, not AI-generated\n"
        "- Do NOT write multiple options unless the user asks for options\n"
        "- Do NOT include posting schedules, hashtag strategies, or content calendars -- only the post itself\n"
        "- Only use business details found in the research -- do not invent services or claims\n"
        "- sources should list the business website and any other sources used"
    ),
)
