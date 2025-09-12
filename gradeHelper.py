# gradeHelper.py

import requests
import os
import re
import time
from bs4 import BeautifulSoup

# --- Configuration ---
OUTPUT_HTML_DIRECTORY = "classes"
BASE_URL = "https://students.ww-p.org/genesis/parents"

def sanitize_filename(name):
    """Removes invalid characters from a string to make it a valid filename."""
    return re.sub(r'[\\/*?:"<>|]', "", name)

def _parse_grades_from_html(html_content):
    # This function does not need changes
    soup = BeautifulSoup(html_content, 'lxml')
    assignments = []
    
    if soup.find('td', class_='cellCenter', string=re.compile(r'No graded assignments found')):
        return []

    assignments_header = soup.find('b', string='Assignments')
    if not assignments_header or not assignments_header.find_parent('table'):
        return []

    assignment_rows = assignments_header.find_parent('table').find_all('tr', class_=['listroweven', 'listrowodd'])
    
    for row in assignment_rows:
        try:
            cells = row.find_all('td', recursive=False)
            if len(cells) < 3: continue
            name_tag = cells[1].find('b')
            if not name_tag: continue
            name = name_tag.text.strip()
            description_tag = cells[1].find('input', id=re.compile(r'^assignmentDescription'))
            description = description_tag['value'].strip() if description_tag else ""
            date = cells[0].find_all('div')[1].text.strip() if len(cells[0].find_all('div')) > 1 else cells[0].text.strip()
            category_div = cells[1].find('div', style=lambda s: 'italic' in s if s else False)
            category = category_div.text.strip() if category_div else "N/A"
            points_earned, total_points = 0.0, 0.0
            grade_cell_text = cells[2].get_text(separator=' ', strip=True)
            cleaned_text = re.sub(r'\s+', ' ', grade_cell_text)
            points_match = re.search(r'([\d.]+)\s*/\s*([\d.]+)', cleaned_text)
            if points_match:
                points_earned = float(points_match.group(1))
                total_points = float(points_match.group(2))
            assignments.append({
                "name": name, "category": category, "date": date,
                "description": description, "totalPoints": total_points,
                "pointsEarned": points_earned
            })
        except (AttributeError, IndexError, ValueError):
            continue
    return assignments

def _parse_category_weights(html_content):
    # This function does not need changes
    soup = BeautifulSoup(html_content, 'lxml')
    weights = {}
    grading_header = soup.find('b', string='Grading Information')
    if not grading_header: return {}
    weight_table = grading_header.find_parent('table')
    if not weight_table: return {}
    weight_rows = weight_table.find_all('tr', class_=['listroweven', 'listrowodd'])
    for row in weight_rows:
        try:
            cells = row.find_all('td', recursive=False)
            if len(cells) < 2: continue
            category_name = cells[0].get_text(strip=True)
            weight_str = cells[1].get_text(strip=True)
            if '%' in weight_str:
                weight_value = float(weight_str.replace('%', '').strip()) / 100.0
                weights[category_name] = weight_value
        except (IndexError, ValueError):
            continue
    return weights

def _process_class_page(session, class_name, class_details, student_id, save_html):
    """
    (Internal helper) Fetches a single class page and conditionally saves the HTML.
    """
    params = {
        'tab1': 'studentdata', 'tab2': 'gradebook', 'tab3': 'coursesummary', 'studentid': student_id,
        'action': 'form', 'courseCode': class_details['courseCode'],
        'courseSection': class_details['courseSelection'], 'mp': class_details['markingPeriod']
    }
    headers = {
        "Accept": "text/html,application/xhtml+xml",
        "Referer": f"https://students.ww-p.org/genesis/parents?tab1=studentdata&tab2=gradebook&tab3=weeklysummary&action=form&studentid={student_id}"
    }
    try:
        response = session.get(BASE_URL, params=params, headers=headers)
        response.raise_for_status()

        # --- THIS IS THE NEW CONDITIONAL LOGIC ---
        if save_html:
            if not os.path.exists(OUTPUT_HTML_DIRECTORY):
                os.makedirs(OUTPUT_HTML_DIRECTORY)
            safe_filename = sanitize_filename(class_name) + ".html"
            output_filepath = os.path.join(OUTPUT_HTML_DIRECTORY, safe_filename)
            with open(output_filepath, "w", encoding="utf-8") as f:
                f.write(response.text)
        
        grades = _parse_grades_from_html(response.text)
        weights = _parse_category_weights(response.text)
        return grades, weights
        
    except requests.exceptions.RequestException as e:
        print(f"  - An error occurred while fetching data for '{class_name}': {e}")
        return [], {}

def get_all_grades(session, all_classes_data, student_id, save_html=True):
    """
    Iterates through classes, passing the save_html setting down.
    """
    if not student_id:
        print("Error in get_all_grades: student_id was not provided.")
        return all_classes_data

    for class_name, class_info in all_classes_data.items():
        print(f"  - Fetching grades for: {class_name}")
        # Pass the save_html setting to the internal function
        grades_list, weights_dict = _process_class_page(session, class_name, class_info, student_id, save_html)
        
        class_info['grades'] = grades_list
        class_info['categoryWeights'] = weights_dict
        time.sleep(0.5)
    
    return all_classes_data