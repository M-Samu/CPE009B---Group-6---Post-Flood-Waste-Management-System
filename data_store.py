# ==============================================================================
# SHARED IN-MEMORY DATA STORE
# ==============================================================================
# TODO (OOP2 Modification): Replace these in-memory lists with persistent file 
# handling (e.g., loading/saving JSON data in data_manager.py or SQLite database).
class DataStore:
    tasks = [
        "Task: Barangay 182 Flood Debris Pickup",
        "Task: Segregate Plastics at Riverbank",
        "Task: Submit Weekly Waste Report",
        "Task: Attend Community Orientation"
    ]

    announcements = [
        ("📢 Safety Advisory: Wear Protective Gear", "Ensure rubber boots and heavy-duty gloves are worn during river debris collection."),
        ("📢 Schedule Update: Barangay 182 Cleanup", "The cleanup drive start time is moved to 8:00 AM due to morning rain."),
        ("🎉 Community Milestone Reached!", "Over 1,000 kg of post-flood waste has been collected across all active districts!")
    ]

    waste_reports = [
        "📍 District 3 - High Debris Concentration (Pending Review)",
        "📍 Main Bridge Area - Blocked Water Drain (In Progress)",
        "📍 Riverside Park - Organic Waste Accumulated (Cleared)"
    ]

    cleanup_drives = [
        {"id": 1, "name": "Barangay Clean-Up Drive Alpha", "datetime": "Saturday, 8:00 AM", "location": "Central Plaza", "joined": False},
        {"id": 2, "name": "Post-Typhoon Coastal Clearing", "datetime": "Sunday, 7:00 AM", "location": "Coastal Road", "joined": False},
        {"id": 3, "name": "Riverbank Plastic Segregation", "datetime": "Next Wednesday, 1:00 PM", "location": "River Spillway", "joined": False}
    ]

    # Structured report records for volunteer profiles and galleries.
    report_records = []