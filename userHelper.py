# userHelper.py

import requests
import re
from bs4 import BeautifulSoup

# --- Configuration ---
TARGET_URL = "https://students.ww-p.org/genesis/parents?tab1=studentdata&tab2=studentsummary&action=form"
REFERER_URL = "https://students.ww-p.org/genesis/parents?tab1=studentdata&tab2=gradebook&tab3=weeklysummary&action=form"

def _parse_user_data(html_content):
    """
    Parses the student summary page with the final, precise strategy.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    # # print("\n  --- DEBUG: Starting to parse user data with FINAL strategy ---")
    
    anchor_text = soup.find(string=re.compile(r'Student ID:'))
    if not anchor_text:
        # # print("  DEBUG: FAILED to find the text 'Student ID:'.")
        return None
    # # print("  DEBUG: Successfully found the 'Student ID:' text node.")
    main_info_table = anchor_text.find_parent('table')
    if not main_info_table:
        # # print("  DEBUG: FAILED to find the parent table of the anchor text.")
        return None
    # # print("  DEBUG: Successfully located the main student info table.")

    student_id_text = main_info_table.find(string=re.compile(r'Student ID:'))
    student_id = student_id_text.find_next('span').get_text(strip=True) if student_id_text else None
    # # print(f"  DEBUG: Student ID found: '{student_id}'")
    
    grade_label_span = main_info_table.find('span', string=re.compile(r'Grade:'))
    grade = grade_label_span.find_next_sibling('span').get_text(strip=True) if grade_label_span else None
    # # print(f"  DEBUG: Grade found: '{grade}'")
    
    school_name = None
    rows = main_info_table.find_all('tr', recursive=False)
    if len(rows) > 1 and rows[1].find('td'):
        school_name = rows[1].find('td').get_text(strip=True)
    # # print(f"  DEBUG: School Name found: '{school_name}'")
    # # print("  --- DEBUG: Parsing complete ---")

    if all(v is None for v in [student_id, grade, school_name]):
        return None

    return {
        "studentID": student_id,
        "grade": grade,
        "schoolName": school_name
    }

def get_user_summary_data(session):
    """
    Fetches the student summary page, parses it, and returns the extracted data.
    """
    headers = {"Accept": "text/html,application/xhtml+xml", "Referer": REFERER_URL}
    try:
        response = session.get(TARGET_URL, headers=headers)
        response.raise_for_status()
        return _parse_user_data(response.text)
    except requests.exceptions.RequestException as e:
        print(f"  - An error occurred while fetching the user summary page: {e}")
        return None