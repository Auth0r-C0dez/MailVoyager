# backend/conversation/chat_manager.py

from backend.ai.email_templates import format_leave_email

class ChatManager:
    def __init__(self):
        self.reset()

    def reset(self):
        """Clear memory for a fresh conversation."""
        self.memory = {
            "step": 0,
            "recipient": "",
            "leave_date": "",
            "leave_reason": ""
        }

    def update_memory(self, user_input: str):
        """Advance state and store the user’s reply."""
        text = user_input.strip()
        step = self.memory["step"]

        if step == 0:
            # User invoked the flow by saying “leave”
            self.memory["step"] = 1
            return

        # Steps 1–3: capture each piece of info
        if step == 1:
            self.memory["recipient"] = text
        elif step == 2:
            self.memory["leave_date"] = text
        elif step == 3:
            self.memory["leave_reason"] = text

        # Move to next question
        self.memory["step"] += 1

    def next_prompt(self) -> str:
        """Return the next question based on the current step."""
        prompts = {
            0: "🤖 What's in your mind?",
            1: "📨 Who should the leave email be sent to?",
            2: "📅 What date(s) are you requesting leave for?",
            3: "📝 What's the reason for your leave?"
        }
        # After step 3, we are ready to send
        return prompts.get(self.memory["step"], "✅ Gathering details... Please wait.")

    def is_ready(self) -> bool:
        """Return True when all required info has been collected."""
        return self.memory["step"] > 3

    def generate_email(self):
        """Use the LLM-based template to produce subject and body."""
        name = "User"  
        dates = self.memory["leave_date"]
        reason = self.memory["leave_reason"]
        return format_leave_email(name=name, dates=dates, reason=reason)
