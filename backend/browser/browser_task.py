# backend/browser/browser_task.py

import sys
import time
import base64
import logging
import os
import random
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def wait_and_click(page, selector, timeout=15000, description=""):
    """Helper function to wait for element and click with better error handling"""
    try:
        logger.info(f"Waiting for {description}: {selector}")
        page.wait_for_selector(selector, timeout=timeout)
        page.click(selector)
        logger.info(f"Successfully clicked {description}")
        return True
    except PlaywrightTimeoutError:
        logger.error(f"Timeout waiting for {description}: {selector}")
        return False
    except Exception as e:
        logger.error(f"Error clicking {description}: {e}")
        return False

def wait_and_fill(page, selector, value, timeout=15000, description=""):
    """Helper function to wait for element and fill with better error handling"""
    try:
        logger.info(f"Waiting for {description}: {selector}")
        page.wait_for_selector(selector, timeout=timeout)
        page.fill(selector, value)
        logger.info(f"Successfully filled {description} with: {value[:20]}...")
        return True
    except PlaywrightTimeoutError:
        logger.error(f"Timeout waiting for {description}: {selector}")
        return False
    except Exception as e:
        logger.error(f"Error filling {description}: {e}")
        return False

def handle_security_challenge(page):
    """Handle Google security challenges if they appear"""
    try:
        # Check if security challenge page appears
        if page.query_selector("text=Verify it's you"):
            logger.warning("Security challenge detected. Manual intervention required.")
            page.pause()  # Pauses script execution for manual intervention
            return True
    except Exception as e:
        logger.error(f"Security challenge handling failed: {e}")
    return False

def main():
    
    if len(sys.argv) != 4:
        print("Usage: python browser_task.py <recipient> <subject> <body>", file=sys.stderr)
        sys.exit(1)
    
    recipient, subject, body = sys.argv[1:]
    logger.info(f"Starting Gmail automation to send email to {recipient}")

    try:
        with sync_playwright() as p:
            # Launch browser with user profile to maintain login session
            browser = p.chromium.launch(
                headless=False,
                slow_mo=500,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized"
                ]
            )
            
            # Use persistent context to maintain login
            context = browser.new_context(
                viewport={"width": 1200, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # Navigate directly to Gmail 
            logger.info("Navigating to Gmail inbox (assuming already logged in)")
            page.goto("https://mail.google.com/mail/u/0/#inbox", timeout=60000)
            
            # Wait for Gmail to load
            try:
                page.wait_for_selector("div[gh='cm']", timeout=30000)
                logger.info("Gmail inbox loaded successfully")
            except PlaywrightTimeoutError:
                logger.warning("Compose button not found, checking for login requirement")
                if "accounts.google.com" in page.url or "signin" in page.url:
                    logger.info("Pausing for manual Gmail login. Please complete login in the opened browser window, then resume.")
                    page.pause()  # This opens Playwright Inspector and lets user interact
                    # After resume, try again for Compose button
                    page.wait_for_selector("div[gh='cm']", timeout=60000)
                    logger.info("Gmail inbox loaded after manual login.")
                else:
                    raise Exception("Gmail inbox not detected")
            
            
            
            # 2️⃣ Clicking Compose
            logger.info("Step 2: Opening compose window")
            compose_selectors = [
                "[data-tooltip='Compose']",
                "text=Compose",
                "div[role='button']:has-text('Compose')",
                "[aria-label='Compose']"
            ]
            
            compose_clicked = False
            for selector in compose_selectors:
                if wait_and_click(page, selector, description="Compose button"):
                    compose_clicked = True
                    break
            
            if not compose_clicked:
                raise Exception("Could not find or click Compose button")

            # 3️⃣ Fill in the email fields
            logger.info("Step 3: Filling email fields")
            time.sleep(2)  # Wait for compose window to fully load
            
            # Fill recipient
            to_selectors = [
                "textarea[name='to']",
                "input[name='to']",
                "[aria-label='To']",
                "div[aria-label='To'] input"
            ]
            
            to_filled = False
            for selector in to_selectors:
                if wait_and_fill(page, selector, recipient, description="To field"):
                    to_filled = True
                    break
            
            if not to_filled:
                raise Exception("Could not find To field")
            
            # Fill subject
            subject_selectors = [
                "input[name='subjectbox']",
                "input[aria-label='Subject']",
                "[name='subjectbox']"
            ]
            
            subject_filled = False
            for selector in subject_selectors:
                if wait_and_fill(page, selector, subject, description="Subject field"):
                    subject_filled = True
                    break
            
            if not subject_filled:
                raise Exception("Could not find Subject field")
            
            # Fill body
            body_selectors = [
                "div[aria-label='Message Body']",
                "div[role='textbox']",
                "[contenteditable='true'][aria-label*='Message']"
            ]
            
            body_filled = False
            for selector in body_selectors:
                try:
                    logger.info(f"Trying to fill body with selector: {selector}")
                    page.wait_for_selector(selector, timeout=10000)
                    page.click(selector)
                    page.keyboard.type(body)
                    logger.info("Successfully filled message body")
                    body_filled = True
                    break
                except Exception as e:
                    logger.warning(f"Failed to fill body with selector {selector}: {e}")
                    continue
            
            if not body_filled:
                raise Exception("Could not find or fill message body")

            # 4️⃣ Send the email
            logger.info("Step 4: Sending email")
            time.sleep(1)  # Brief pause before sending
            
            send_selectors = [
                "div[role='button']:has-text('Send')",
                "button:has-text('Send')",
                "[aria-label='Send']",
                "div[data-tooltip='Send']"
            ]
            
            send_clicked = False
            for selector in send_selectors:
                if wait_and_click(page, selector, description="Send button"):
                    send_clicked = True
                    break
            
            if not send_clicked:
                raise Exception("Could not find or click Send button")
            
            # Wait for confirmation
            logger.info("Waiting for send confirmation...")
            confirmation_selectors = [
                "text=Message sent",
                "span:has-text('sent')",
                "[aria-label*='sent']"
            ]
            
            confirmation_found = False
            for selector in confirmation_selectors:
                try:
                    page.wait_for_selector(selector, timeout=10000)
                    logger.info("Email sent successfully!")
                    confirmation_found = True
                    break
                except:
                    continue
            
            if not confirmation_found:
                logger.warning("Could not find send confirmation, but proceeding...")

            # 5️⃣ Capture screenshot
            logger.info("Step 5: Capturing screenshot")
            screenshot_path = os.path.join(os.getcwd(), "sent_confirmation.png")
            page.screenshot(path=screenshot_path, full_page=False)
            logger.info(f"Screenshot saved to: {screenshot_path}")

            # Print base64 screenshot for downstream consumption
            with open(screenshot_path, "rb") as img:
                encoded = base64.b64encode(img.read()).decode()
                print(encoded)

    except Exception as e:
        logger.exception("Critical error during automation")
        raise e
    finally:
        try:
            browser.close()
        except Exception as close_err:
            logger.warning(f"Could not close browser cleanly: {close_err}")

if __name__ == "__main__":
    main()
