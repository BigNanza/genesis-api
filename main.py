# main.py

import json
import os
from loginHelper import get_session, perform_login
from classHelper import get_all_classes
from dotenv import load_dotenv
from gradeHelper import get_all_grades
from userHelper import get_user_summary_data

# --- Configuration ---
CLASS_DATA_FILE = "classes.json"
USER_DATA_FILE = "user.json"

# --- Credentials ---
load_dotenv()
USERNAME = os.getenv("GENESIS_USERNAME")
PASSWORD = os.getenv("GENESIS_PASSWORD")

def main():
    """Main function to orchestrate the entire scraping process."""
    
    # --- Step 1: Authentication ---
    print("--- Authenticating ---")
    session = get_session(USERNAME, PASSWORD)
    if not session:
        print("Initial authentication failed. Aborting.")
        return
    print("  - Session obtained.")

    # --- Step 2: Get User Data and Student ID ---
    print("\n--- Fetching User Summary Data ---")
    user_data = get_user_summary_data(session)
    if not user_data or "studentID" not in user_data or not user_data["studentID"]:
        print("  - Failed to fetch or parse user data, or studentID is missing. Aborting.")
        return
    
    student_id = user_data["studentID"]
    print(f"  - Successfully parsed user data. Student ID: {student_id}")

    # --- Step 3: Discover All Classes using the Student ID ---
    print("\n--- Discovering Classes ---")
    classes_data = get_all_classes(session, student_id)

    # Validate session and re-login if necessary
    if classes_data is None:
        print("  - Session appears to be invalid. Attempting to re-authenticate...")
        session = perform_login(USERNAME, PASSWORD)
        if not session:
            print("Re-authentication failed. Aborting script.")
            return
        
        print("  - Re-authentication successful. Retrying class discovery...")
        classes_data = get_all_classes(session, student_id)

    if classes_data is None or not classes_data:
        print("Failed to discover any classes. Aborting.")
        return

    print(f"Successfully discovered {len(classes_data)} classes.")
    
    # --- Step 4: Fetch Detailed Grades for Each Class ---
    print("\n--- Fetching Grades for Each Class ---")
    final_class_data = get_all_grades(session, classes_data, student_id)
    
    # --- Step 5: Save All Retrieved Data ---
    print("\n--- Saving Data to Files ---")
    try:
        with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(user_data, f, indent=4)
        print(f"Successfully saved user summary to '{USER_DATA_FILE}'.")
    except IOError as e:
        print(f"Error: Could not write to file '{USER_DATA_FILE}'. Reason: {e}")

    try:
        with open(CLASS_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(final_class_data, f, indent=4)
        print(f"Successfully saved all class data to '{CLASS_DATA_FILE}'.")
    except IOError as e:
        print(f"Error: Could not write to file '{CLASS_DATA_FILE}'. Reason: {e}")

    print("\nProcess complete.")

if __name__ == "__main__":
    main()