from app.skills.base import Skill

CODING = Skill(
    id="coding",
    name="Coding Mode",
    icon="💻",
    description="Build applications with AI agents that architect, code, and push to GitHub.",
    planner_prompt="You are a coding project planner. Analyze the user's request and create a detailed specification.",
    num_subtasks=1,
)