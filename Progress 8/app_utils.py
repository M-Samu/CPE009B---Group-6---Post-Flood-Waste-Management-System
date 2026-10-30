# Import datetime to access the current date and time
from datetime import datetime

# Get the current date and time as a formatted string
def current_datetime() -> str:
    # Return the date and time in year-month-day hour:minute:second format
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")