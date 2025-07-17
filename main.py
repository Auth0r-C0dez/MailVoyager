# main.py

import sys
import subprocess
import logging
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Windows asyncio subprocess fix (needed if you ever mix async, but here we run sync subprocess)
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from backend.conversation.chat_manager import ChatManager

app = FastAPI()

# Allow calls from your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single global chat manager
chat = ChatManager()

class Message(BaseModel):
    message: str

@app.get("/health")
def health_check():
    return {"status": "ok", "detail": "Agent running"}

@app.post("/chat")
def chat_endpoint(msg: Message):
    text = msg.message.strip()
    step = chat.memory["step"]

    # Step 0: start flow if user mentions "leave"
    if step == 0:
        if "leave" in text.lower():
            chat.update_memory(text)
            return {"reply": chat.next_prompt()}
        else:
            return {"reply": "🤖 Hello! What would you like me to do?"}

    # Steps 1–5: collect inputs
    chat.update_memory(text)

    # If we have all inputs, trigger browser automation
    if chat.is_ready():
        # Generate subject & body via LLM
        subject, body = chat.generate_email()
        recipient = chat.memory["recipient"]

        # Call the standalone browser_task.py via subprocess
        browser_script_path = os.path.join(os.getcwd(), "backend", "browser", "browser_task.py")
        logger.info(f"Starting browser automation with script: {browser_script_path}")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Script exists: {os.path.exists(browser_script_path)}")
        
        try:
            proc = subprocess.run(
                [
                    sys.executable,
                    "backend/browser/browser_task.py",
                    recipient,
                    subject,
                    body
                ],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=os.getcwd()
            )
            
            logger.info(f"Browser task return code: {proc.returncode}")
            logger.info(f"Browser task stdout: {proc.stdout[:200]}...")  # First 200 chars
            if proc.stderr:
                logger.error(f"Browser task stderr: {proc.stderr}")
            
            if proc.returncode != 0:
                error_msg = proc.stderr or "Unknown error in browser task"
                logger.error(f"Browser automation failed with return code {proc.returncode}: {error_msg}")
                raise Exception(error_msg)

            screenshot_b64 = proc.stdout.strip()
            if not screenshot_b64:
                raise Exception("No screenshot data received from browser task")
                
        except subprocess.TimeoutExpired:
            logger.error("Browser automation timed out after 120 seconds")
            chat.reset()
            raise HTTPException(status_code=500, detail="Browser automation timed out")
        except Exception as e:
            logger.error(f"Browser automation error: {str(e)}")
            # Reset state so user can retry
            chat.reset()
            raise HTTPException(status_code=500, detail=f"Browser automation failed: {e}")

        # Reset for next conversation
        chat.reset()

        # Final reply with screenshot
        return {
            "reply": f"✅ Email sent successfully to {recipient}.\n\nSubject: {subject}\n\n{body}",
            "screenshot": screenshot_b64
        }

    # Otherwise, ask the next question
    return {"reply": chat.next_prompt()}
