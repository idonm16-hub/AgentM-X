class SkillRegistry:
    def __init__(self, max_new: int = 1):
        self.max_new = max_new
        self.new_count = 0

    def can_add(self) -> bool:
        return self.new_count < self.max_new

    def add(self, skill_name: str):
        if not self.can_add():
            raise RuntimeError("max new skills per run exceeded")
        self.new_count += 1

    def notepad(self):
        from agentmx.skills.gui.notepad import NotepadSkill
        return NotepadSkill
