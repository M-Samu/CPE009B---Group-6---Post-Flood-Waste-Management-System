import json
from pathlib import Path

DATASTORE_FILE = Path("data") / "datastore.json"

# ==============================================================================
# PERSISTENT IN-MEMORY & JSON DATA STORE
# ==============================================================================
class DataStore:
    tasks = []
    announcements = []
    waste_reports = []
    cleanup_drives = []

    report_records = []
    reward_claims = []
    cleared_announcements = {}  # Format: { "username": ["heading1|||body1", ...] }
    user_joined_tasks = []      # Format: [ { "username": "...", "task_title": "...", "completed": bool }, ... ]
    cleared_tasks = {}          # Format: { "username": ["task_title1", ...] }

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
                if "user_joined_tasks" in data:
                    cls.user_joined_tasks = data["user_joined_tasks"]
                if "cleared_tasks" in data:
                    cls.cleared_tasks = data["cleared_tasks"]
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
            "cleared_announcements": cls.cleared_announcements,
            "user_joined_tasks": getattr(cls, "user_joined_tasks", []),
            "cleared_tasks": getattr(cls, "cleared_tasks", {})
        }
        DATASTORE_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")

# Auto-load saved data on module import
DataStore.load()