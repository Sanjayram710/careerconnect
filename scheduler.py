from app import app

from services.job_api import (
    fetch_jobs,
    fetch_internships
)
from services.calendar_service import check_and_send_event_reminders

with app.app_context():

    try:

        fetch_jobs()

        fetch_internships()

        print("API refresh completed")
        
        check_and_send_event_reminders()
        print("Calendar reminders checking completed")

    except Exception as e:

        print(
            "CRITICAL: Failed to refresh API or reminders:",
            str(e)
        )