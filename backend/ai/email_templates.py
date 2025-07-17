# backend/ai/email_templates.py

import requests

# Replace with your actual OpenRouter API key
OPENROUTER_API_KEY = "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"

def format_leave_email(name: str, dates: str, reason: str = "personal leave") -> tuple[str, str]:
    """
    Calls OpenRouter to generate a formal leave application email.
    Falls back to a simple template on any error or unexpected response.
    """
    prompt = (
        f"You are a professional email writer. Please draft a formal leave application email for {name}, "
        f"who needs leave from {dates} due to {reason}. Return the subject line prefixed with 'Subject:' "
        f"and then the full email body."
    )

    try:
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistralai/mistral-7b-instruct",
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=15
        )
        data = res.json()

        # Safely extract the generated content
        if isinstance(data, dict) and data.get("choices"):
            choice = data["choices"][0]
            content = choice.get("message", {}).get("content", "")
        else:
            raise ValueError(f"Unexpected response structure: {data}")

        # Split into subject and body
        parts = content.strip().split("\n", 1)
        subject_line = parts[0].removeprefix("Subject:").strip()
        body = parts[1].strip() if len(parts) > 1 else ""

        # Ensure both are non-empty
        subject = subject_line or f"Leave Application for {dates}"
        body = body or f"Dear Sir/Madam,\n\nI am requesting leave from {dates} due to {reason}.\n\nRegards,\n{name}"

        return subject, body

    except Exception as e:
        # Log the error for debugging
        print(f"❌ LLM Error in format_leave_email: {e}")
        # Fallback template
        subject = f"Leave Application for {dates}"
        body = (
            f"Dear Sir/Madam,\n\n"
            f"I need leave from {dates} due to {reason}.\n\n"
            f"Regards,\n{name}"
        )
        return subject, body
