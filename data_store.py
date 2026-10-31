import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATASTORE_FILE = BASE_DIR / "data" / "datastore.json"

# ==============================================================================
# PERSISTENT IN-MEMORY & JSON DATA STORE
# ==============================================================================
class DataStore:

    # Existing application data
    tasks = []
    announcements = []
    waste_reports = []

    cleanup_drives = [
        {
            "id": 1,
            "name": "Barangay Clean-Up Drive Alpha",
            "datetime": "Saturday, 8:00 AM",
            "location": "Central Plaza",
            "joined": False
        },
        {
            "id": 2,
            "name": "Post-Typhoon Coastal Clearing",
            "datetime": "Sunday, 7:00 AM",
            "location": "Coastal Road",
            "joined": False
        },
        {
            "id": 3,
            "name": "Riverbank Plastic Segregation",
            "datetime": "Next Wednesday, 1:00 PM",
            "location": "River Spillway",
            "joined": False
        }
    ]

    report_records = []
    reward_claims = []
    cleared_announcements = {}
    # Progress 6 task participation/completion tracking.
    user_joined_tasks = []
    cleared_tasks = {}

    # New: moderation information for submitted reports.
    # Entries correspond to the same indexes in waste_reports.
    report_moderation = []

    # New: volunteer tickets and administrative responses.
    report_tickets = []

    @classmethod
    def load(cls):
        """Load saved application data from the JSON data store."""

        if not DATASTORE_FILE.exists():
            return

        try:
            data = json.loads(
                DATASTORE_FILE.read_text(encoding="utf-8")
            )

            if not isinstance(data, dict):
                raise ValueError(
                    "The data store must contain a JSON object."
                )

            if "tasks" in data:
                cls.tasks = data["tasks"]

            if "announcements" in data:
                cls.announcements = [
                    tuple(item)
                    if isinstance(item, list)
                    else item
                    for item in data["announcements"]
                ]

            if "waste_reports" in data:
                cls.waste_reports = data["waste_reports"]

            if "cleanup_drives" in data:
                cls.cleanup_drives = data["cleanup_drives"]

            if "report_records" in data:
                cls.report_records = data["report_records"]

            if "reward_claims" in data:
                cls.reward_claims = data["reward_claims"]

            if "cleared_announcements" in data:
                cls.cleared_announcements = (
                    data["cleared_announcements"]
                )

            # Progress 6 task state; defaults keep older data files compatible.
            if "user_joined_tasks" in data:
                cls.user_joined_tasks = data["user_joined_tasks"]
            if "cleared_tasks" in data:
                cls.cleared_tasks = data["cleared_tasks"]

            # New fields. Existing JSON files may not contain them.
            if "report_moderation" in data:
                cls.report_moderation = data["report_moderation"]

            if "report_tickets" in data:
                cls.report_tickets = data["report_tickets"]

            # Give old reports a default moderation status.
            cls._synchronize_report_moderation()

        except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
            print(f"Error loading persistent data store: {error}")

    @classmethod
    def save(cls):
        """Save application data to the JSON data store."""

        DATASTORE_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        cls._synchronize_report_moderation()
        cls._synchronize_report_social_data()

        data = {
            "tasks": cls.tasks,

            "announcements": [
                list(item)
                if isinstance(item, tuple)
                else item
                for item in cls.announcements
            ],

            "waste_reports": cls.waste_reports,
            "cleanup_drives": cls.cleanup_drives,
            "report_records": cls.report_records,
            "reward_claims": cls.reward_claims,
            "cleared_announcements": cls.cleared_announcements,
            "user_joined_tasks": cls.user_joined_tasks,
            "cleared_tasks": cls.cleared_tasks,

            # New persistent fields
            "report_moderation": cls.report_moderation,
            "report_tickets": cls.report_tickets
        }

        # Write to a temporary file first to reduce the risk of
        # leaving a partially written JSON file.
        temp_file = DATASTORE_FILE.with_suffix(".tmp")

        try:
            temp_file.write_text(
                json.dumps(data, indent=4),
                encoding="utf-8"
            )
            temp_file.replace(DATASTORE_FILE)

        except (OSError, TypeError, ValueError) as error:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass

            raise RuntimeError(
                f"Could not save application data: {error}"
            ) from error

    
    # ==========================================================================
    # PUBLIC REPORTS, LIKES, AND COMMENTS
    # ==========================================================================

    @classmethod
    def _synchronize_report_social_data(cls):
        """
        Prepare report records for the public feed.

        Existing records receive empty likes and comments lists.
        """
        if not isinstance(cls.report_records, list):
            cls.report_records = []

        for record in cls.report_records:
            if not isinstance(record, dict):
                continue

            if not isinstance(record.get("likes"), list):
                record["likes"] = []

            if not isinstance(record.get("comments"), list):
                record["comments"] = []

    @classmethod
    def get_approved_report_records(cls):
        """
        Return approved reports with their matching detail records.

        Each result contains the original report index, report text,
        and corresponding report record.
        """
        cls._synchronize_report_moderation()
        cls._synchronize_report_social_data()

        approved = []

        for index, report in enumerate(cls.waste_reports):
            moderation = cls.get_report_moderation(index)

            if not moderation or moderation.get("status") != "Approved":
                continue

            # Do not display a report if its matching details are missing.
            if index >= len(cls.report_records):
                continue

            record = cls.report_records[index]

            if not isinstance(record, dict):
                continue

            approved.append((index, report, record))

        return approved

    @classmethod
    def toggle_report_like(cls, report_index, username):
        """
        Add a like or remove the user's existing like.
        Returns True if liked, or False if unliked.
        """
        if not username or not str(username).strip():
            raise ValueError("A valid username is required.")

        if not 0 <= report_index < len(cls.waste_reports):
            raise IndexError("Waste report was not found.")

        moderation = cls.get_report_moderation(report_index)

        if not moderation or moderation.get("status") != "Approved":
            raise ValueError("Only approved reports can be liked.")

        if report_index >= len(cls.report_records):
            raise IndexError("Report details were not found.")

        cls._synchronize_report_social_data()
        record = cls.report_records[report_index]
        likes = record["likes"]
        username = str(username).strip()

        # Compare usernames without case sensitivity.
        existing = next(
            (
                name for name in likes
                if isinstance(name, str)
                and name.casefold() == username.casefold()
            ),
            None
        )

        if existing is not None:
            old_likes = list(likes)
            record["likes"] = [
                name for name in likes
                if not (
                    isinstance(name, str)
                    and name.casefold() == username.casefold()
                )
            ]
            liked = False
        else:
            old_likes = list(likes)
            likes.append(username)
            liked = True

        try:
            cls.save()
        except Exception:
            record["likes"] = old_likes
            raise

        return liked

    @classmethod
    def add_report_comment(
        cls,
        report_index,
        username,
        full_name,
        comment_text
    ):
        """Save a comment on an approved report."""
        from datetime import datetime

        username = str(username or "").strip()
        full_name = str(full_name or username).strip()
        comment_text = str(comment_text or "").strip()

        if not username:
            raise ValueError("A valid username is required.")

        if not comment_text:
            raise ValueError("Comment cannot be empty.")

        if not 0 <= report_index < len(cls.waste_reports):
            raise IndexError("Waste report was not found.")

        moderation = cls.get_report_moderation(report_index)

        if not moderation or moderation.get("status") != "Approved":
            raise ValueError("Only approved reports can be commented on.")

        if report_index >= len(cls.report_records):
            raise IndexError("Report details were not found.")

        cls._synchronize_report_social_data()
        record = cls.report_records[report_index]

        comment = {
            "username": username,
            "full_name": full_name,
            "text": comment_text,
            "submitted_at": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        }

        record["comments"].append(comment)

        try:
            cls.save()
        except Exception:
            record["comments"].pop()
            raise

        return comment

    # ==========================================================================
    # REPORT MODERATION
    # ==========================================================================

    @classmethod
    def _synchronize_report_moderation(cls):
        """
        Keep one moderation entry for each waste report.

        Existing reports without moderation data default to Pending.
        """

        if not isinstance(cls.report_moderation, list):
            cls.report_moderation = []

        while len(cls.report_moderation) < len(cls.waste_reports):
            cls.report_moderation.append({
                "status": "Pending",
                "admin_note": ""
            })

        # Remove moderation entries for reports that no longer exist.
        cls.report_moderation = cls.report_moderation[
            :len(cls.waste_reports)
        ]

        for index, entry in enumerate(cls.report_moderation):
            if not isinstance(entry, dict):
                cls.report_moderation[index] = {
                    "status": "Pending",
                    "admin_note": ""
                }
                continue

            status = entry.get("status", "Pending")

            if status not in ("Pending", "Approved", "Rejected"):
                status = "Pending"

            entry["status"] = status
            entry.setdefault("admin_note", "")

    @classmethod
    def get_report_moderation(cls, report_index):
        """Return moderation details for a report."""

        cls._synchronize_report_moderation()
        cls._synchronize_report_social_data()

        if not 0 <= report_index < len(cls.waste_reports):
            return None

        return cls.report_moderation[report_index]

    @classmethod
    def update_report_moderation(
        cls,
        report_index,
        status,
        admin_note=""
    ):
        """Update the approval status and administrator's note."""

        if status not in ("Pending", "Approved", "Rejected"):
            raise ValueError("Invalid report moderation status.")

        if not 0 <= report_index < len(cls.waste_reports):
            raise IndexError("Waste report was not found.")

        cls._synchronize_report_moderation()

        old_entry = dict(cls.report_moderation[report_index])

        cls.report_moderation[report_index] = {
            "status": status,
            "admin_note": admin_note.strip()
        }

        try:
            cls.save()
        except Exception:
            cls.report_moderation[report_index] = old_entry
            raise

    @classmethod
    def get_approved_reports(cls):
        """Return reports approved for public display."""

        cls._synchronize_report_moderation()

        return [
            report
            for index, report in enumerate(cls.waste_reports)
            if cls.report_moderation[index]["status"] == "Approved"
        ]

    
    @classmethod
    
    @classmethod
    def delete_report(cls, report_index):
        """
        Delete a report and its matching record and moderation entry
        while keeping ticket references consistent.
        """
        if not 0 <= report_index < len(cls.waste_reports):
            raise IndexError("Waste report was not found.")

        # Keep backups in case saving fails.
        old_reports = list(cls.waste_reports)
        old_records = list(cls.report_records)
        old_moderation = [
            dict(entry) if isinstance(entry, dict) else entry
            for entry in cls.report_moderation
        ]
        old_tickets = [
            dict(ticket) for ticket in cls.report_tickets
        ]

        try:
            # Remove matching report data at the same index.
            cls.waste_reports.pop(report_index)

            if report_index < len(cls.report_records):
                cls.report_records.pop(report_index)

            # Remove the matching moderation entry directly.
            if report_index < len(cls.report_moderation):
                cls.report_moderation.pop(report_index)

            # Update tickets that refer to report indexes.
            for ticket in cls.report_tickets:
                ticket_index = ticket.get("report_index")

                if ticket_index == report_index:
                    ticket["report_index"] = None
                    ticket["status"] = "Report Deleted"

                elif (
                    isinstance(ticket_index, int)
                    and not isinstance(ticket_index, bool)
                    and ticket_index > report_index
                ):
                    ticket["report_index"] = ticket_index - 1

            # Synchronize only after all related data is updated.
            cls._synchronize_report_moderation()
            cls.save()

        except Exception:
            cls.waste_reports = old_reports
            cls.report_records = old_records
            cls.report_moderation = old_moderation
            cls.report_tickets = old_tickets
            raise

    # ==========================================================================
    # REPORT TICKETS AND ADMIN RESPONSES
    # ==========================================================================

    @classmethod
    def create_report_ticket(cls, username, message, report_index=None, reported_username=None):
        """Create a ticket submitted by a volunteer."""

        ticket_id = max(
            (
                ticket.get("id", 0)
                for ticket in cls.report_tickets
                if isinstance(ticket, dict)
                and isinstance(ticket.get("id"), int)
            ),
            default=0
        ) + 1

        ticket = {
            "id": ticket_id,
            "username": username,
            "message": message,
            "report_index": report_index,
            "reported_username": reported_username,
            "admin_response": "",
            "status": "Open"
        }

        cls.report_tickets.append(ticket)
        cls.save()
        return ticket

    @classmethod
    def respond_to_ticket(
        cls,
        ticket_id,
        response,
        status="Responded"
    ):
        """Save an administrator's response to a volunteer ticket."""

        response = response.strip()

        if not response:
            raise ValueError("The response cannot be empty.")

        allowed_statuses = (
            "Open",
            "Responded",
            "Resolved"
        )

        if status not in allowed_statuses:
            raise ValueError("Invalid ticket status.")

        for ticket in cls.report_tickets:
            if ticket.get("id") == ticket_id:
                old_response = ticket.get("admin_response", "")
                old_status = ticket.get("status", "Open")

                ticket["admin_response"] = response
                ticket["status"] = status

                try:
                    cls.save()
                except Exception:
                    ticket["admin_response"] = old_response
                    ticket["status"] = old_status
                    raise

                return True

        return False

    @classmethod
    def get_tickets_for_user(cls, username):
        """Return tickets submitted by a particular volunteer."""

        username = username.casefold()

        return [
            ticket
            for ticket in cls.report_tickets
            if ticket.get("username", "").casefold() == username
        ]

# Load saved data when the module is imported.
DataStore.load()