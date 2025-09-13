import webview
import os
from pathlib import Path

class Api:
    def __init__(self, update_callback=None):
        self.update_callback = update_callback
    
    def update_grades(self):
        """Update grades by calling the provided callback function."""
        print("Updating grades...")
        try:
            if self.update_callback:
                # Call the update function (this will be main.py's scraping logic)
                result = self.update_callback()
                print("Grades updated successfully!")
                return {"success": True, "message": "Grades updated successfully"}
            else:
                print("No update callback provided")
                return {"success": False, "message": "No update function available"}
        except Exception as e:
            print(f"Error updating grades: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}

def start_dashboard(update_callback=None, dashboard_file="dashboard.html", fullscreen=True):
    """
    Start the pywebview dashboard application.
    
    Args:
        update_callback: Function to call when update_grades is triggered
        dashboard_file: Path to the dashboard HTML file
        fullscreen: Whether to start in fullscreen mode
    """
    # Check if dashboard file exists
    if not os.path.exists(dashboard_file):
        print(f"Error: Dashboard file '{dashboard_file}' not found.")
        print("Please run the grade scraping first to generate the dashboard.")
        return False
    
    # Create API instance with the update callback
    api = Api(update_callback)
    
    # Create and start the webview window
    try:
        window = webview.create_window(
            "Grades Dashboard", 
            dashboard_file, 
            js_api=api, 
            fullscreen=fullscreen,
            width=1200,
            height=800,
            min_size=(800, 600)
        )
        
        print(f"Starting dashboard from: {Path(dashboard_file).resolve()}")
        webview.start(debug=False)
        return True
        
    except Exception as e:
        print(f"Error starting dashboard: {e}")
        return False

# Allow running app.py directly for testing
if __name__ == "__main__":
    start_dashboard()
