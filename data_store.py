import json
from pathlib import Path

DATASTORE_FILE = Path("data") / "datastore.json"

# ==============================================================================
# PERSISTENT IN-MEMORY & JSON DATA STORE
# ==============================================================================
class DataStore:
    tasks = [
        "Task: Barangay 182 Flood Debris Pickup",
        "Task: Segregate Plastics at Riverbank",
        "Task: Submit Weekly Waste Report",
        "Task: Attend Community Orientation"
    ]

    announcements = [
        ("Safety Advisory: Wear Protective Gear", "Ensure rubber boots and heavy-duty gloves are worn during river debris collection."),
        ("Schedule Update: Barangay 182 Cleanup", "The cleanup drive start time is moved to 8:00 AM due to morning rain."),
        ("Community Milestone Reached!", "Over 1,000 kg of post-flood waste has been collected across all active districts!")
    ]

    waste_reports = [
        "District 3 - High Debris Concentration (Pending Review)",
        "Main Bridge Area - Blocked Water Drain (In Progress)",
        "Riverside Park - Organic Waste Accumulated (Cleared)"
    ]

    cleanup_drives = [
        {"id": 1, "name": "Barangay Clean-Up Drive Alpha", "datetime": "Saturday, 8:00 AM", "location": "Central Plaza", "joined": False},
        {"id": 2, "name": "Post-Typhoon Coastal Clearing", "datetime": "Sunday, 7:00 AM", "location": "Coastal Road", "joined": False},
        {"id": 3, "name": "Riverbank Plastic Segregation", "datetime": "Next Wednesday, 1:00 PM", "location": "River Spillway", "joined": False}
    ]

    report_records = []
    reward_claims = []
    cleared_announcements = {}  # Format: { "username": ["heading1|||body1", ...] }

    @classmethod
    def load(cls):
        """Loads saved items from data/datastore.json if present."""
        if DATASTORE_FILE.exists():
            try:
                data = json.loads(DATASTORE_FILE.read_text(encoding="utf-8"))
                if "tasks" in data:
                    cls.tasks = data["tasks"]
                if "announcements" in data:
                    cls.announcements = [tuple(a) if isinstance(a, list) else a for a in data["announcements"]]
                if "waste_reports" in data:
                    cls.waste_reports = data["waste_reports"]
                if "cleanup_drives" in data:
                    cls.cleanup_drives = data["cleanup_drives"]
                if "report_records" in data:
                    cls.report_records = data["report_records"]
                if "reward_claims" in data:
                    cls.reward_claims = data["reward_claims"]
                if "cleared_announcements" in data:
                    cls.cleared_announcements = data["cleared_announcements"]
            except Exception as error:
                print(f"Error loading persistent data store: {error}")

    @classmethod
    def save(cls):
        """Saves current state to data/datastore.json."""
        DATASTORE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "tasks": cls.tasks,
            "announcements": [list(a) if isinstance(a, tuple) else a for a in cls.announcements],
            "waste_reports": cls.waste_reports,
            "cleanup_drives": cls.cleanup_drives,
            "report_records": cls.report_records,
            "reward_claims": cls.reward_claims,
            "cleared_announcements": cls.cleared_announcements
        }
        DATASTORE_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")

# Auto-load saved data on module import
DataStore.load()