import json
import webbrowser
from pathlib import Path
from html import escape
from string import Template

def generate_dashboard(json_file="output.json", html_file="dashboard.html"):
    """
    Generate a clean, table-based dashboard matching the provided design mockups.
    """
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: '{json_file}' not found.")
        return
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return

    user = data.get("user", {})
    classes = data.get("classes", {})

    def get_letter_grade(pct):
        if pct is None:
            return "N/A"
        if pct >= 89.5: return "A"
        if pct >= 79.5: return "B"
        if pct >= 69.5: return "C"
        if pct >= 59.5: return "D"
        return "F"

    def get_grade_color(pct):
        if pct is None:
            return "#64748b"
        if pct >= 90: return "#10b981"
        if pct >= 80: return "#06b6d4"
        if pct >= 70: return "#f59e0b"
        if pct >= 60: return "#f97316"
        return "#ef4444"

    def calculate_grade_for_mp(grades, cat_weights):
        """Calculate overall grade for a specific marking period."""
        # Calculate overall grade
        cat_sums = {}
        for g in grades:
            cat = g.get("category", "") or ""
            cat_entry = cat_sums.setdefault(cat, {"earned": 0.0, "total": 0.0})
            try:
                earned = float(g.get("pointsEarned", 0) or 0)
                total = float(g.get("totalPoints", 0) or 0)
            except Exception:
                earned = total = 0.0
            cat_entry["earned"] += earned
            cat_entry["total"] += total

        cat_scores = {}
        for cat, weight in cat_weights.items():
            sums = cat_sums.get(cat, {"earned": 0.0, "total": 0.0})
            if sums["total"] > 0:
                cat_scores[cat] = sums["earned"] / sums["total"]
            else:
                cat_scores[cat] = None

        effective_weight = 0.0
        weighted_sum = 0.0
        for cat, weight in cat_weights.items():
            frac = cat_scores.get(cat)
            if frac is not None:
                effective_weight += float(weight)
                weighted_sum += frac * float(weight)

        overall_pct = None
        if effective_weight > 0:
            overall_pct = round((weighted_sum / effective_weight) * 100, 1)

        return overall_pct, cat_scores

    # Process classes data
    classes_data = []
    active_mp = None
    
    for class_name, class_info in classes.items():
        course_code = class_info.get("courseCode", "")
        marking_period = class_info.get("markingPeriod", "")
        if active_mp is None:
            active_mp = marking_period  # Set active MP from first class
        
        all_grades = class_info.get("grades", {})
        all_cat_weights = class_info.get("categoryWeights", {})
        
        # Calculate grades for all marking periods
        mp_data = {}
        for mp in ['MP1', 'MP2', 'MP3', 'MP4']:
            mp_grades = all_grades.get(mp, [])
            mp_weights = all_cat_weights.get(mp, {})
            overall_pct, cat_scores = calculate_grade_for_mp(mp_grades, mp_weights)
            
            mp_data[mp] = {
                "overall_pct": overall_pct,
                "letter_grade": get_letter_grade(overall_pct),
                "grade_color": get_grade_color(overall_pct),
                "grades": mp_grades,
                "cat_weights": mp_weights,
                "cat_scores": cat_scores
            }

        classes_data.append({
            "name": class_name,
            "course_code": course_code,
            "active_marking_period": marking_period,
            "mp_data": mp_data
        })

    # Generate summary table rows (will be populated by JavaScript)
    summary_rows = []
    for i, cls in enumerate(classes_data):
        summary_rows.append(f"""
        <tr class="course-row" onclick="openModal({i})" data-class-index="{i}">
            <td class="course-name">{escape(cls['name'])}</td>
            <td class="course-average" data-mp-grade></td>
            <td class="course-grade" data-mp-letter></td>
        </tr>
        """)

    # Generate modal content for each class
    modal_content = []
    for i, cls in enumerate(classes_data):
        modal_content.append(f"""
        <div id="modal-{i}" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <div class="modal-title-section">
                        <h2 class="modal-title">View Assignments for {escape(cls['name'])}</h2>
                        <button class="close-btn" onclick="closeModal({i})">&times;</button>
                    </div>
                    <div class="modal-controls">
                        <select id="modal-mp-select-{i}" class="mp-select" onchange="updateModalMP({i})">
                            <option value="MP1">MP1</option>
                            <option value="MP2">MP2</option>
                            <option value="MP3">MP3</option>
                            <option value="MP4">MP4</option>
                        </select>
                        <div class="modal-grade">
                            <span id="modal-grade-percent-{i}" class="modal-grade-percent"></span>
                            <button id="toggle-categories-{i}" class="toggle-btn" onclick="toggleCategories({i})">
                                Show Category Averages
                            </button>
                        </div>
                    </div>
                </div>
                
                <div class="modal-body">
                    <div id="categories-view-{i}" class="categories-view" style="display: none;">
                        <div id="categories-container-{i}" class="categories-container">
                            <!-- Categories will be populated by JavaScript -->
                        </div>
                    </div>
                    
                    <div id="assignments-view-{i}" class="assignments-view">
                        <table class="assignments-table">
                            <thead>
                                <tr>
                                    <th class="due-header">DUE</th>
                                    <th class="category-header">CATEGORY</th>
                                    <th class="assignment-header">ASSIGNMENT</th>
                                    <th class="grade-header">GRADE</th>
                                </tr>
                            </thead>
                            <tbody id="assignments-tbody-{i}">
                                <!-- Assignments will be populated by JavaScript -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        """)

    # HTML template
    page_template = Template("""
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Grades Dashboard — $schoolName</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f0f9ff;
            color: #0f172a;
            min-height: 100vh;
        }

        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
        }

        .header {
            text-align: center;
            margin-bottom: 2rem;
        }

        .header h1 {
            font-size: 2rem;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 0.5rem;
        }

        .header .subtitle {
            color: #64748b;
            font-size: 1rem;
        }

        .controls {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .mp-select {
            padding: 0.5rem 1rem;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            background: white;
            color: #1e293b;
            font-size: 0.9rem;
            cursor: pointer;
        }

        .mp-select:focus {
            outline: none;
            border-color: #0ea5e9;
            box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.1);
        }

        .update-btn {
            background: #0ea5e9;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 500;
            transition: all 0.2s;
        }

        .update-btn:hover {
            background: #0284c7;
        }

        .update-btn:disabled {
            background: #94a3b8;
            cursor: not-allowed;
        }

        .summary-table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            border: 1px solid #e0f2fe;
        }

        .summary-table thead {
            background: #0ea5e9;
        }

        .summary-table th {
            padding: 1rem 1.5rem;
            text-align: left;
            font-weight: 600;
            font-size: 0.875rem;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            color: white;
            border-bottom: none;
        }

        .summary-table th:first-child {
            width: 50%;
        }

        .summary-table th:nth-child(2) {
            width: 25%;
            text-align: center;
        }

        .summary-table th:last-child {
            width: 25%;
            text-align: center;
        }

        .course-row {
            cursor: pointer;
            transition: all 0.2s ease;
            border-bottom: 1px solid #f1f5f9;
        }

        .course-row:hover {
            background: #f0f9ff;
        }

        .course-row:last-child {
            border-bottom: none;
        }

        .course-name {
            padding: 1.25rem 1.5rem;
            font-weight: 500;
            color: #0f172a;
        }

        .course-average {
            padding: 1.25rem 1.5rem;
            text-align: center;
            font-weight: 600;
            font-size: 1rem;
        }

        .course-grade {
            padding: 1.25rem 1.5rem;
            text-align: center;
            font-weight: 700;
            font-size: 1.1rem;
        }

        /* Modal Styles */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(4px);
        }

        .modal-content {
            background: #f8fafc;
            margin: 2% auto;
            padding: 0;
            border-radius: 16px;
            width: 90%;
            max-width: 1000px;
            max-height: 90vh;
            overflow: hidden;
            box-shadow: 0 20px 25px rgba(0, 0, 0, 0.15);
        }

        .modal-header {
            background: #1e293b;
            padding: 1.5rem 2rem;
            border-bottom: 1px solid #cbd5e1;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }

        .modal-title-section {
            display: flex;
            align-items: center;
            gap: 1rem;
            flex: 1;
        }

        .modal-title {
            color: white;
            font-size: 1.2rem;
            font-weight: 600;
        }

        .close-btn {
            background: rgba(255, 255, 255, 0.2);
            border: none;
            color: white;
            font-size: 1.5rem;
            cursor: pointer;
            padding: 0.5rem;
            border-radius: 6px;
            transition: all 0.2s;
        }

        .close-btn:hover {
            background: rgba(255, 255, 255, 0.3);
        }

        .modal-controls {
            display: flex;
            align-items: center;
            gap: 1rem;
            flex-wrap: wrap;
        }

        .modal-grade {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .modal-grade-percent {
            font-size: 1.8rem;
            font-weight: 700;
            background: white;
            padding: 0.5rem 0.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .toggle-btn {
            background: #0ea5e9;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.85rem;
            font-weight: 500;
            transition: all 0.2s;
        }

        .toggle-btn:hover {
            background: #0284c7;
        }

        .modal-body {
            max-height: 80vh;
            overflow-y: auto;
        }

        .assignments-view {
            padding: 2rem;
        }

        .categories-view {
            padding: 2rem;
            border-bottom: 1px solid #e2e8f0;
        }

        .assignments-table {
            width: 100%;
            border-collapse: collapse;
        }

        .assignments-table th {
            background: #374151;
            color: white;
            padding: 1rem;
            text-align: left;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            border-bottom: none;
        }

        .assignments-table td {
            padding: 1rem;
            border-bottom: 1px solid #e2e8f0;
            color: #1e293b;
        }

        .assignments-table tr:hover {
            background: #f1f5f9;
        }

        .due-header { width: 15%; }
        .category-header { width: 25%; }
        .assignment-header { width: 45%; }
        .grade-header { width: 15%; }

        .date-col { color: #64748b; font-size: 0.9rem; }
        .category-col { color: #0ea5e9; font-weight: 500; }
        .assignment-col { color: #1e293b; }
        .grade-col { font-weight: 600; }

        .no-data {
            text-align: center;
            color: #64748b;
            font-style: italic;
            padding: 2rem !important;
        }

        /* Category Averages Styles */
        .categories-container {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .category-bar {
            background: white;
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            border: 1px solid #e2e8f0;
        }

        .category-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }

        .category-name {
            color: #1e293b;
            font-weight: 500;
            font-size: 0.9rem;
        }

        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e2e8f0;
            border-radius: 4px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.6s ease;
        }

        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }

            .summary-table th,
            .course-name,
            .course-average,
            .course-grade {
                padding: 1rem;
            }

            .modal-content {
                width: 95%;
                margin: 5% auto;
            }

            .modal-header {
                padding: 1rem;
                flex-direction: column;
                align-items: stretch;
            }

            .modal-title-section {
                justify-content: space-between;
            }

            .assignments-view, .categories-view {
                padding: 1rem;
            }

            .assignments-table {
                font-size: 0.85rem;
            }

            .assignments-table th,
            .assignments-table td {
                padding: 0.75rem 0.5rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>Grades Dashboard</h1>
            <div class="subtitle">$schoolName • Grade $grade • Student ID: $studentID</div>
        </header>

        <div class="controls">
            <button id="update-btn" class="update-btn" onclick="updateGrades()">Update Grades</button>
            <select id="main-mp-select" class="mp-select" onchange="updateMainMP()">
                <option value="MP1">MP1</option>
                <option value="MP2">MP2</option>
                <option value="MP3">MP3</option>
                <option value="MP4">MP4</option>
            </select>
        </div>

        <main>
            <table class="summary-table">
                <thead>
                    <tr>
                        <th>COURSE</th>
                        <th>AVERAGE</th>
                        <th>GRADE</th>
                    </tr>
                </thead>
                <tbody id="summary-tbody">
                    $summary_rows
                </tbody>
            </table>
        </main>
    </div>

    $modal_content

    <script>
        const classesData = $classes_data_json;
        const activeMP = '$active_mp';
        let currentMainMP = activeMP;
        let currentModalMP = {};

        // Initialize the dashboard
        document.addEventListener('DOMContentLoaded', function() {
            // Set active MP in main dropdown
            document.getElementById('main-mp-select').value = activeMP;
            updateMainMP();
        });

        function updateGrades() {
            const updateBtn = document.getElementById('update-btn');
            
            // Disable button and show loading state
            updateBtn.disabled = true;
            updateBtn.textContent = 'Updating...';
            
            // Call the Python function via pywebview
            if (window.pywebview && window.pywebview.api) {
                window.pywebview.api.update_grades().then(function(result) {
                    // Re-enable button
                    updateBtn.disabled = false;
                    updateBtn.textContent = 'Update Grades';
                    
                    // Reload the page to show updated data
                    window.location.reload();
                }).catch(function(error) {
                    console.error('Error updating grades:', error);
                    
                    // Re-enable button on error
                    updateBtn.disabled = false;
                    updateBtn.textContent = 'Update Grades';
                    
                    alert('Error updating grades. Please try again.');
                });
            } else {
                // Fallback for development/testing
                console.log('pywebview not available, update_grades() would be called');
                updateBtn.disabled = false;
                updateBtn.textContent = 'Update Grades';
            }
        }

        function updateMainMP() {
            currentMainMP = document.getElementById('main-mp-select').value;
            updateSummaryTable();
        }

        function updateSummaryTable() {
            const rows = document.querySelectorAll('[data-class-index]');
            rows.forEach((row, index) => {
                const classData = classesData[index];
                const mpData = classData.mp_data[currentMainMP];
                
                const gradeCell = row.querySelector('[data-mp-grade]');
                const letterCell = row.querySelector('[data-mp-letter]');
                
                const gradeDisplay = mpData.overall_pct !== null ? mpData.overall_pct + '%' : 'No Grades';
                
                gradeCell.textContent = gradeDisplay;
                gradeCell.style.color = mpData.grade_color;
                
                letterCell.textContent = mpData.letter_grade;
                letterCell.style.color = mpData.grade_color;
            });
        }

        function openModal(index) {
            document.getElementById('modal-' + index).style.display = 'block';
            document.body.style.overflow = 'hidden';
            
            // Set modal MP to current main MP
            currentModalMP[index] = currentMainMP;
            document.getElementById('modal-mp-select-' + index).value = currentMainMP;
            updateModalContent(index);
        }

        function closeModal(index) {
            document.getElementById('modal-' + index).style.display = 'none';
            document.body.style.overflow = 'auto';
        }

        function updateModalMP(index) {
            currentModalMP[index] = document.getElementById('modal-mp-select-' + index).value;
            updateModalContent(index);
        }

        function updateModalContent(index) {
            const classData = classesData[index];
            const mp = currentModalMP[index] || currentMainMP;
            const mpData = classData.mp_data[mp];
            
            // Update grade display
            const gradeElement = document.getElementById('modal-grade-percent-' + index);
            const gradeDisplay = mpData.overall_pct !== null ? mpData.overall_pct + '%' : 'N/A';
            gradeElement.textContent = gradeDisplay;
            gradeElement.style.color = mpData.grade_color;
            gradeElement.style.borderColor = mpData.grade_color;
            
            // Update assignments table
            updateAssignmentsTable(index, mpData.grades);
            
            // Update categories
            updateCategoriesView(index, mpData.cat_weights, mpData.cat_scores);
        }

        function updateAssignmentsTable(index, grades) {
            const tbody = document.getElementById('assignments-tbody-' + index);
            
            if (grades.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="no-data">No assignments yet</td></tr>';
                return;
            }
            
            let rows = '';
            grades.forEach(g => {
                const name = escapeHtml(g.name || '');
                const category = escapeHtml(g.category || '');
                const date = escapeHtml(g.date || '');
                
                let gradeDisplay = 'N/A';
                try {
                    if (g.totalPoints && g.totalPoints > 0) {
                        const pct = (g.pointsEarned / g.totalPoints) * 100;
                        gradeDisplay = pct.toFixed(1) + '%';
                    }
                } catch (e) {
                    gradeDisplay = 'N/A';
                }
                
                rows += `
                    <tr>
                        <td class="date-col">${date}</td>
                        <td class="category-col">${category}</td>
                        <td class="assignment-col">${name}</td>
                        <td class="grade-col">${gradeDisplay}</td>
                    </tr>
                `;
            });
            
            tbody.innerHTML = rows;
        }

        function updateCategoriesView(index, catWeights, catScores) {
            const container = document.getElementById('categories-container-' + index);
            
            let html = '';
            Object.entries(catWeights).forEach(([cat, weight]) => {
                const score = catScores[cat];
                let catDisplay = 'No Grades';
                let color = '#64748b';
                let barWidth = 0;
                
                if (score !== null && score !== undefined) {
                    catDisplay = (score * 100).toFixed(1) + '%';
                    color = getGradeColor(score * 100);
                    barWidth = score * 100;
                }
                
                const weightDisplay = `(${(weight * 100).toFixed(0)}%)`;
                
                html += `
                    <div class="category-bar">
                        <div class="category-info">
                            <span class="category-name">${escapeHtml(cat)} ${weightDisplay}</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${barWidth}%; background-color: ${color};"></div>
                        </div>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        }

        function toggleCategories(index) {
            const categoriesView = document.getElementById('categories-view-' + index);
            const toggleBtn = document.getElementById('toggle-categories-' + index);

            if (categoriesView.style.display === 'none') {
                categoriesView.style.display = 'block';
                toggleBtn.textContent = 'Hide Category Averages';
                
                // Animate progress bars when showing categories
                setTimeout(() => {
                    const progressBars = categoriesView.querySelectorAll('.progress-fill');
                    progressBars.forEach(bar => {
                        const width = bar.style.width;
                        bar.style.width = '0%';
                        setTimeout(() => bar.style.width = width, 100);
                    });
                }, 50);
            } else {
                categoriesView.style.display = 'none';
                toggleBtn.textContent = 'Show Category Averages';
            }
        }

        function getGradeColor(pct) {
            if (pct === null || pct === undefined) return "#64748b";
            if (pct >= 90) return "#10b981";
            if (pct >= 80) return "#06b6d4";
            if (pct >= 70) return "#f59e0b";
            if (pct >= 60) return "#f97316";
            return "#ef4444";
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Close modal when clicking outside
        window.onclick = function(event) {
            if (event.target.classList.contains('modal')) {
                event.target.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        }

        // Close modal with Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                const modals = document.querySelectorAll('.modal');
                modals.forEach(modal => {
                    if (modal.style.display === 'block') {
                        modal.style.display = 'none';
                        document.body.style.overflow = 'auto';
                    }
                });
            }
        });
    </script>
</body>
</html>
    """)

    html_filled = page_template.safe_substitute(
        schoolName=escape(user.get("schoolName", "")),
        grade=escape(str(user.get("grade", ""))),
        studentID=escape(str(user.get("studentID", ""))),
        summary_rows="\n".join(summary_rows),
        modal_content="\n".join(modal_content),
        classes_data_json=json.dumps(classes_data),
        active_mp=active_mp or "MP1"
    )

    path = Path(html_file).resolve()
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_filled)

    # webbrowser.open(f"file://{path}")
    print(f"Dashboard generated: {path}")

if __name__ == "__main__":
    generate_dashboard("output.json")
