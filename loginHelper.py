# loginHelper.py

import requests
import pickle
import os
from datetime import datetime, timedelta

# --- Configuration ---
LOGIN_URL = "https://students.ww-p.org/genesis/sis/j_security_check?parents=Y"
HOME_URL = "https://students.ww-p.org/genesis/sis/view?gohome=true"
COOKIE_FILE = "cookies.pkl"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
# --- Credentials have been REMOVED from this file ---

def _verify_session(session):
    """
    Internal function to verify if a session is active by checking the home page.
    """
    try:
        response = session.get(HOME_URL, allow_redirects=False)
        response.raise_for_status()
        if response.status_code == 200 and 'j_username' not in response.text:
            return True
        return False
    except requests.exceptions.RequestException:
        return False

def _login_and_save_cookies(username, password):
    """Internal function to perform a new login and save cookies."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    # Use the passed-in credentials
    form_data = {"j_username": username, "j_password": password, "idTokenString": ""}
    headers = {"Referer": HOME_URL, "Content-Type": "application/x-www-form-urlencoded"}

    try:
        response = session.post(LOGIN_URL, data=form_data, headers=headers, allow_redirects=False)
        response.raise_for_status()
        
        if not _verify_session(session):
            print("  - Login failed. Please check your credentials.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"  - An error occurred during login: {e}")
        return None

    with open(COOKIE_FILE, "wb") as f:
        pickle.dump(session.cookies, f)
    return session

def get_session(username, password):
    """
    Gets a session by loading recent cookies and verifying them.
    If cookies are old, invalid, or missing, it performs a new login.
    """
    if os.path.exists(COOKIE_FILE):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(COOKIE_FILE))
        if datetime.now() - file_mod_time < timedelta(hours=1):
            session = requests.Session()
            session.headers.update({"User-Agent": USER_AGENT})
            with open(COOKIE_FILE, "rb") as f:
                session.cookies.update(pickle.load(f))
            
            if _verify_session(session):
                return session

    print("  - Cookies are missing, old, or invalid. Performing new login...")
    return _login_and_save_cookies(username, password)

def perform_login(username, password):
    """
    Forces a new login, bypassing any existing cookies, and returns a new session.
    """
    print("  - Forcing a new login...")
    return _login_and_save_cookies(username, password)

# --- Main execution (for standalone testing) ---
if __name__ == "__main__":
    print("Running login script as a standalone test...")
    # This now demonstrates how to use the function with arguments
    TEST_USERNAME = "YOUR_EMAIL_HERE"
    TEST_PASSWORD = "YOUR_PASSWORD_HERE"
    active_session = get_session(TEST_USERNAME, TEST_PASSWORD)
    
    if active_session:
        print("\nSUCCESS: A valid session was obtained.")
    else:
        print("\nFAILURE: Could not obtain a valid session.")