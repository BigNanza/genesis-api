# main.py

import json
import os
import threading
import time
from loginHelper import get_session, perform_login
from classHelper import get_all_classes
from dotenv import load_dotenv
from gradeHelper import get_all_grades, update_active_mp_grades
from userHelper import get_user_summary_data
from dashboardHelper import generate_dashboard
from app import start_dashboard


# --- Configuration ---
OUTPUT_JSON_FILE = "output.json"
SAVE_HTML_FILES = False
# --- Auto-update interval in minutes (set to 0 to disable automatic updates) ---
AUTO_UPDATE_INTERVAL_MINUTES = 0

def get_credentials():
    """Get credentials from .env file or prompt user for input."""
    load_dotenv()
    username = os.getenv("GENESIS_USERNAME")
    password = os.getenv("GENESIS_PASSWORD")
    
    # If credentials are missing, prompt user
    if not username or not password:
        print("Credentials not found in .env file or incomplete.")
        username = input("Enter your Genesis username/email: ").strip()
        password = input("Enter your Genesis password: ").strip()
        
        # Save credentials to .env file
        env_content = f"GENESIS_USERNAME={username}\nGENESIS_PASSWORD={password}\n"
        
        try:
            with open(".env", "w") as f:
                f.write(env_content)
            print("Credentials saved to .env file.")
        except IOError as e:
            print(f"Warning: Could not save credentials to .env file: {e}")
    
    return username, password

def scrape_grades():
    """Scrape grades and generate dashboard. Returns True on success, False on failure."""
    try:
        # --- Step 1: Get Credentials ---
        username, password = get_credentials()
        
        # --- Step 2: Authentication ---
        print("--- Authenticating ---")
        session = get_session(username, password)
        if not session:
            print("Initial authentication failed. Aborting.")
            return False
        print("  - Session obtained.")

        # --- Step 3: Get User Data and Student ID ---
        print("\n--- Fetching User Summary Data ---")
        user_data = get_user_summary_data(session)
        if not user_data or "studentID" not in user_data or not user_data["studentID"]:
            print("  - Failed to fetch or parse user data, or studentID is missing. Aborting.")
            return False
        
        student_id = user_data["studentID"]
        print(f"  - Successfully parsed user data. Student ID: {student_id}")

        # --- Step 4: Discover All Classes using the Student ID ---
        print("\n--- Discovering Classes ---")
        classes_data = get_all_classes(session, student_id)

        # Validate session and re-login if necessary
        if classes_data is None:
            print("  - Session appears to be invalid. Attempting to re-authenticate...")
            session = perform_login(username, password)
            if not session:
                print("Re-authentication failed. Aborting script.")
                return False
            
            print("  - Re-authentication successful. Retrying class discovery...")
            classes_data = get_all_classes(session, student_id)

        if classes_data is None or not classes_data:
            print("Failed to discover any classes. Aborting.")
            return False

        print(f"Successfully discovered {len(classes_data)} classes.")
        
        # --- Step 5: Fetch Detailed Grades for Each Class ---
        print("\n--- Fetching Grades for Each Class ---")
        # Pass the SAVE_HTML_FILES setting to the grade helper
        final_class_data = get_all_grades(session, classes_data, student_id, save_html=SAVE_HTML_FILES)
        
        # --- Step 6: Combine and Save All Retrieved Data ---
        print("\n--- Combining and Saving Data ---")

        # Create the final, combined dictionary structure
        combined_data = {
            "user": user_data,
            "classes": final_class_data
        }

        # Save the single combined file
        try:
            with open(OUTPUT_JSON_FILE, "w", encoding="utf-8") as f:
                json.dump(combined_data, f, indent=2)
            print(f"Successfully saved all combined data to '{OUTPUT_JSON_FILE}'.")
        except IOError as e:
            print(f"Error: Could not write to file '{OUTPUT_JSON_FILE}'. Reason: {e}")
            return False

        # Generate the dashboard
        generate_dashboard(OUTPUT_JSON_FILE)
        print("\nProcess complete.")
        return True
        
    except Exception as e:
        print(f"Error during grade scraping: {e}")
        return False

def main():
    """Main function - scrape grades and start dashboard."""
    # First, scrape grades and generate dashboard
    success = scrape_grades()
    
    if success:
        # Start auto-update thread if enabled
        if AUTO_UPDATE_INTERVAL_MINUTES > 0:
            auto_update_thread = threading.Thread(target=auto_update_worker, daemon=True)
            auto_update_thread.start()
        
        # Start the dashboard with update callback
        print("\n--- Starting Dashboard ---")
        start_dashboard(update_callback=update_active_mp_only)
    else:
        print("Failed to generate dashboard. Please check the errors above.")

def update_active_mp_only():
    """Update only the active marking period grades. Returns True on success, False on failure."""
    try:
        # Load existing data to get active MP and class info
        if not os.path.exists(OUTPUT_JSON_FILE):
            print("No existing data found. Running full scrape instead.")
            return scrape_grades()
        
        with open(OUTPUT_JSON_FILE, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
        
        # Get credentials and authenticate
        username, password = get_credentials()
        
        print("--- Authenticating ---")
        session = get_session(username, password)
        if not session:
            print("Initial authentication failed. Aborting.")
            return False
        print("  - Session obtained.")
        
        # Get student ID from existing data
        student_id = existing_data.get("user", {}).get("studentID")
        if not student_id:
            print("No student ID found in existing data. Running full scrape instead.")
            return scrape_grades()
        
        # Determine active marking period from existing data
        active_mp = None
        classes = existing_data.get("classes", {})
        for class_name, class_info in classes.items():
            if class_info.get("markingPeriod"):
                active_mp = class_info.get("markingPeriod")
                break
        
        if not active_mp:
            print("No active marking period found. Running full scrape instead.")
            return scrape_grades()
        
        print(f"\n--- Updating {active_mp} Grades Only ---")
        
        # Update grades for active MP only
        updated_classes = update_active_mp_grades(session, classes, student_id, active_mp, save_html=SAVE_HTML_FILES)
        
        if updated_classes is None:
            print("Failed to update grades.")
            return False
        
        # Update the existing data with new grades
        existing_data["classes"] = updated_classes
        
        # Save updated data
        try:
            with open(OUTPUT_JSON_FILE, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=2)
            print(f"Successfully updated {active_mp} grades in '{OUTPUT_JSON_FILE}'.")
        except IOError as e:
            print(f"Error: Could not write to file '{OUTPUT_JSON_FILE}'. Reason: {e}")
            return False
        
        # Regenerate dashboard with updated data
        generate_dashboard(OUTPUT_JSON_FILE)
        print(f"\n{active_mp} grades update complete.")
        return True
        
    except Exception as e:
        print(f"Error during active MP update: {e}")
        return False

def auto_update_worker():
    """Background worker that automatically updates grades at specified intervals."""
    if AUTO_UPDATE_INTERVAL_MINUTES <= 0:
        return  # Auto-update disabled
    
    print(f"Auto-update enabled: will update grades every {AUTO_UPDATE_INTERVAL_MINUTES} minutes")
    
    while True:
        try:
            # Wait for the specified interval
            time.sleep(AUTO_UPDATE_INTERVAL_MINUTES * 60)
            
            # Perform the update
            print(f"\n--- Automatic Grade Update ({time.strftime('%Y-%m-%d %H:%M:%S')}) ---")
            success = update_active_mp_only()
            
            if success:
                print("Automatic grade update completed successfully.")
            else:
                print("Automatic grade update failed.")
                
        except Exception as e:
            print(f"Error in auto-update worker: {e}")
            # Continue running even if there's an error

def run_dashboard_only():
    """Start dashboard without scraping (assumes dashboard.html exists)."""
    print("--- Starting Dashboard (existing data) ---")
    
    # Start auto-update thread if enabled
    if AUTO_UPDATE_INTERVAL_MINUTES > 0:
        auto_update_thread = threading.Thread(target=auto_update_worker, daemon=True)
        auto_update_thread.start()
    
    start_dashboard(update_callback=update_active_mp_only)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--dashboard-only":
        # Just start dashboard with existing data
        run_dashboard_only()
    else:
        # Full process: scrape grades then start dashboard
        main()
