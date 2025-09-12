# classHelper.py

import requests
import re

# --- File reading and global variables have been REMOVED ---

def get_all_classes(session, student_id):
    """
    Fetches the Gradebook Summary page to discover all available classes.

    Args:
        session (requests.Session): An authenticated requests session object.
        student_id (str): The student's ID, required for building the URLs.
    """
    # --- URLs are now built inside the function using the provided student_id ---
    target_url = f"https://students.ww-p.org/genesis/parents?tab1=studentdata&tab2=gradebook&tab3=weeklysummary&action=form&studentid={student_id}"
    referer_url = f"https://students.ww-p.org/genesis/parents?tab1=studentdata&tab2=gradebook&tab3=coursesummary&studentid={student_id}&action=form"

    if not student_id:
        print("Error in get_all_classes: student_id was not provided.")
        return None

    headers = {"Accept": "text/html,application/xhtml+xml", "Referer": referer_url}

    try:
        response = session.get(target_url, headers=headers)
        response.raise_for_status()
        if "gohome=true" in response.url:
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching the class list: {e}")
        return None

    pattern = re.compile(r"goToCourseSummary\('([^']*)','([^']*)','([^']*)'\)\">(.*?)<\/span>")
    matches = pattern.findall(response.text)

    classes_data = {}
    if not matches:
        return {}

    for match in matches:
        course_code, course_selection, marking_period, class_name = match
        class_name = class_name.strip()
        if class_name:
            classes_data[class_name] = {
                "courseCode": course_code,
                "courseSelection": course_selection,
                "markingPeriod": marking_period
            }
            
    return classes_data