# calendar_helper.py
import os, json, pymysql
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request  # <-- ΜΟΝΟ εδώ, μία φορά
from datetime import datetime, timedelta, timezone

class GoogleCalendarHelper:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self.SCOPES = [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.events",
        ]
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.credentials_file = os.path.join(BASE_DIR, "credentials.json")
        self.redirect_uri = "http://localhost:8000/oauth2callback"

    # ---------- OAuth ----------
    def get_auth_url(self) -> str:
        flow = Flow.from_client_secrets_file(
            self.credentials_file,
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri,
        )
        auth_url, _ = flow.authorization_url(
            prompt="consent",
            access_type="offline",
            include_granted_scopes="true",
            state=self.api_key,
        )
        return auth_url

    def get_credentials_from_code(self, code: str):
        try:
            flow = Flow.from_client_secrets_file(
                self.credentials_file,
                scopes=self.SCOPES,
                redirect_uri=self.redirect_uri,
            )
            flow.fetch_token(code=code)
            return flow.credentials
        except Exception as e:
            print("Error getting credentials:", e)
            return None

    def save_credentials_to_db(self, credentials) -> bool:
        if not self.api_key:
            return False
        from server5 import get_database_connection
        conn = get_database_connection()
        try:
            cursor = conn.cursor()
            creds_data = {
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": list(credentials.scopes or []),
            }
            cursor.execute(
                "UPDATE companies SET google_credentials = %s WHERE api_key = %s",
                (json.dumps(creds_data), self.api_key),
            )
            conn.commit()
            return cursor.rowcount == 1
        except Exception as e:
            print("Error saving credentials:", e)
            return False
        finally:
            conn.close()

    def load_credentials(self):
        if not self.api_key:
            return None
        from server5 import get_database_connection
        conn = get_database_connection()
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)  # <-- DictCursor για result['google_credentials']
            cursor.execute(
                "SELECT google_credentials FROM companies WHERE api_key = %s",
                (self.api_key,),
            )
            row = cursor.fetchone()
        finally:
            conn.close()

        if not row or not row.get("google_credentials"):
            return None

        try:
            data = json.loads(row["google_credentials"])
            return Credentials(
                token=data.get("token"),
                refresh_token=data.get("refresh_token"),
                token_uri=data.get("token_uri"),
                client_id=data.get("client_id"),
                client_secret=data.get("client_secret"),
                scopes=data.get("scopes") or self.SCOPES,
            )
        except Exception as e:
            print("Error loading credentials:", e)
            return None

    def get_calendar_service(self):  # <-- ΜΕΣΑ στην κλάση
        try:
            creds = self.load_credentials()
            if not creds:
                return None
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    self.save_credentials_to_db(creds)  # <-- ξανασώσε τα φρέσκα tokens
                else:
                    return None
            return build("calendar", "v3", credentials=creds)
        except Exception as e:
            print(f"Error creating calendar service: {e}")
            return None
    
    

    def get_available_slots(self, date: str, appointment_settings: dict = None):
        try:
            service = self.get_calendar_service()
            if not service:
                return []

        # Default settings
            settings = {
                'workStart': '09:00',
                'workEnd': '17:00',
                'slotDuration': 30,
                'workDays': ['Δευ','Τρι','Τετ','Πεμ','Παρ']
          }
        
        # Override με settings από τη βάση
            if appointment_settings:
                settings.update(appointment_settings)
 
        # Έλεγχος εργάσιμης ημέρας
            day = datetime.strptime(date, "%Y-%m-%d")
            weekday_names = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
            weekday_name = weekday_names[day.weekday()]
        
            if weekday_name not in settings['workDays']:
                return []  # Μη εργάσιμη μέρα
        
        # Parse work hours
            work_start_time = datetime.strptime(settings['workStart'], '%H:%M').time()
            work_end_time = datetime.strptime(settings['workEnd'], '%H:%M').time()
            slot_duration = settings['slotDuration']
        
        # Timezone setup (υπάρχον κώδικας)
            gr_tz = timezone(timedelta(hours=3))
            start_local = day.replace(
                hour=work_start_time.hour, 
                minute=work_start_time.minute, 
                second=0, microsecond=0, tzinfo=gr_tz
            )
            end_local = day.replace(
                hour=work_end_time.hour, 
                minute=work_end_time.minute, 
                second=0, microsecond=0, tzinfo=gr_tz
           )

        # Fetch existing events (υπάρχον κώδικας)
            events_result = service.events().list(
                calendarId='primary',
                timeMin=start_local.isoformat(),
                timeMax=end_local.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])

            print(f"📅 DEBUG: Date={date}, Found {len(events)} events")
            print(f"📅 DEBUG: Time range {start_local} to {end_local}")
            for i, event in enumerate(events):
                print(f"📅 DEBUG: Event {i}: {event.get('summary', 'No title')}")

        # Generate slots με τη σωστή διάρκεια
            available = []
            current = start_local
            while current + timedelta(minutes=slot_duration) <= end_local:
                slot_end = current + timedelta(minutes=slot_duration)

            # Έλεγχος overlap με events (υπάρχον κώδικας)
                is_free = True
                for e in events:
                    evs = e['start'].get('dateTime') or e['start'].get('date')
                    eve = e['end'].get('dateTime') or e['end'].get('date')

                    ev_start = datetime.fromisoformat(evs.replace('Z', '+00:00')) if 'T' in evs else \
                              datetime.fromisoformat(evs + 'T00:00:00+03:00')
                    ev_end = datetime.fromisoformat(eve.replace('Z', '+00:00')) if 'T' in eve else \
                            datetime.fromisoformat(eve + 'T00:00:00+03:00')

                    if current < ev_end and slot_end > ev_start:
                        is_free = False
                        break

                if is_free:
                    available.append({
                        "start_time": current.strftime("%H:%M"),
                        "end_time": slot_end.strftime("%H:%M"),
                        "datetime": current.isoformat(),
                    })

                current += timedelta(minutes=slot_duration)

            return available
        except Exception as e:
            print("Error getting available slots:", e)
            return []

    def create_event(self, title: str, description: str, start_datetime: str,
                 duration_minutes: int = 60, attendee_email: str | None = None) -> str | None:
        try:
            service = self.get_calendar_service()
            if not service:
                return None

            start_dt = datetime.fromisoformat(start_datetime)
            end_dt = start_dt + timedelta(minutes=duration_minutes)

            event = {
                "summary": title,
                "description": description or "",
                "start": {"dateTime": start_dt.isoformat(), "timeZone": "Europe/Athens"},
                "end":   {"dateTime": end_dt.isoformat(),   "timeZone": "Europe/Athens"},
          }
            if attendee_email:
                event["attendees"] = [{"email": attendee_email}]

            created = service.events().insert(calendarId='primary', body=event).execute()
            return created.get("id")
        except Exception as e:
            print("Error creating event:", e)
            return None



