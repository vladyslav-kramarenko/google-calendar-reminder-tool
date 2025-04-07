from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import time
import json

# === CONFIGURATION ===
SERVICE_ACCOUNT_FILE = 'calendar-reminder.json'
SCOPES = ['https://www.googleapis.com/auth/calendar']
USER_EMAIL = 'email@test.com'


DEFAULT_REMINDER_MINUTES = 120
MAX_MONTHS_FORWARD = 1

REMOVE_EXISTING_CUSTOM_REMINDERS = False  # Remove existing manual reminders
REPLACE_DEFAULT_REMINDERS = True  # Replace useDefault=True with custom + default reminders

# === LOG STORAGE ===
skipped_log = []
updated_log = []


def load_service():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    delegated_creds = credentials.with_subject(USER_EMAIL)
    return build('calendar', 'v3', credentials=delegated_creds)


def get_owned_calendars(service):
    calendar_list = service.calendarList().list().execute()
    return [cal for cal in calendar_list['items'] if cal.get('accessRole') == 'owner']


def update_event_reminders(service, cal_id, event, reminder_minutes, default_reminders):
    reminders = event.get('reminders', {})
    overrides = reminders.get('overrides', [])
    use_default = reminders.get('useDefault', True)

    if not use_default and not overrides:
        print(f"\n      ⚠️ Event has no reminders at all: {event.get('summary', 'Untitled')}")

    if use_default:
        if not REPLACE_DEFAULT_REMINDERS:
            print(f"\n      ⏭️ Skipping event using default reminders: {event.get('summary', 'Untitled')}")
            log_skipped_event(event, default_reminders=default_reminders)
            return False
        new_reminders = default_reminders.copy() if default_reminders else []
    else:
        if REMOVE_EXISTING_CUSTOM_REMINDERS:
            new_reminders = []
        else:
            new_reminders = overrides.copy()

    already_has = any(
        r.get('method') == 'popup' and r.get('minutes') == reminder_minutes
        for r in new_reminders
    )
    if already_has:
        print(f"\n      ✔️ Event already has such popup: {event.get('summary', 'Untitled')}")
        return False

    new_reminders.append({"method": "popup", "minutes": reminder_minutes})

    service.events().patch(
        calendarId=cal_id,
        eventId=event['id'],
        body={
            'reminders': {
                'useDefault': False,
                'overrides': new_reminders
            }
        }
    ).execute()

    print(f"\n      ✅ Updated event: {event.get('summary', 'Untitled')}")
    for r in new_reminders:
        print(f"         - {r['method']}: {r['minutes']} minutes")

    updated_log.append({
        'summary': event.get('summary', 'Untitled'),
        'start': event.get('start', {}),
        'reminders': new_reminders
    })

    return True


def log_skipped_event(event, error=None, default_reminders=[]):
    entry = {
        'summary': event.get('summary', 'Untitled'),
        'start': event.get('start', {}),
        'creator': event.get('creator', {}).get('email'),
        'organizer': event.get('organizer', {}).get('email'),
        'useDefault': event.get('reminders', {}).get('useDefault', True),
        'overrides': event.get('reminders', {}).get('overrides', []),
        'defaultReminders': default_reminders
    }
    if error:
        entry['error'] = str(error)

    skipped_log.append(entry)

    print("    ⚠️ Skipped event:")
    print(f"       Title:     {entry['summary']}")
    print(f"       Date:      {entry['start'].get('dateTime', entry['start'].get('date'))}")
    print(f"       Creator:   {entry['creator']}")
    print(f"       Organizer: {entry['organizer']}")
    print(f"       🔔 useDefault: {entry['useDefault']}")

    if entry['useDefault']:
        print(f"       🔔 defaultReminders from calendar:")
        if default_reminders:
            for r in default_reminders:
                print(f"         - {r['method']}: {r['minutes']} minutes")
        else:
            print("         (No default reminders set)")
    elif entry['overrides']:
        print("       🔔 overrides:")
        for r in entry['overrides']:
            print(f"         - {r['method']}: {r['minutes']} minutes")
    else:
        print("       🔔 overrides: None")

    if error:
        print(f"       Reason:    {entry['error']}")


def process_events(service, cal_id, events, default_reminders):
    updated_count = 0
    skipped_count = 0

    for idx, event in enumerate(events, start=1):
        try:
            start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date'))
            if not start:
                raise ValueError("Missing start time")

            success = update_event_reminders(
                service, cal_id, event, DEFAULT_REMINDER_MINUTES, default_reminders
            )
            if success:
                updated_count += 1

            if idx % 50 == 0:
                print(f"\n      🔁 Processed {idx} events...")
            elif idx % 10 == 0:
                print(".", end="", flush=True)

        except Exception as e:
            skipped_count += 1
            log_skipped_event(event, error=e)

    print(f"\n   ✅ Events updated: {updated_count}")
    print(f"   ⚠️ Events skipped: {skipped_count}")


def process_calendar(service, calendar, time_min, time_max):
    cal_id = calendar['id']
    cal_summary = calendar.get('summaryOverride') or calendar.get('summary', 'Unnamed Calendar')
    print(f"📅 Processing calendar: {cal_summary} ({cal_id})")

    try:
        events_result = service.events().list(
            calendarId=cal_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        print(f"   🔍 Events found: {len(events)}")

        calendar_defaults = service.calendarList().get(calendarId=cal_id).execute()
        default_reminders = calendar_defaults.get('defaultReminders', [])

        process_events(service, cal_id, events, default_reminders)

    except Exception as e:
        print(f"   ❌ Error while processing calendar {cal_id}: {e}")


def main():
    print(f"\n🔧 Setting reminders for all events: popup {DEFAULT_REMINDER_MINUTES} minutes before event")
    print(f"🗓️  Processing range: from today to +{MAX_MONTHS_FORWARD} months")
    print(f"⚙️  REMOVE_EXISTING_CUSTOM_REMINDERS = {REMOVE_EXISTING_CUSTOM_REMINDERS}")
    print(f"⚙️  REPLACE_DEFAULT_REMINDERS = {REPLACE_DEFAULT_REMINDERS}\n")

    if not REMOVE_EXISTING_CUSTOM_REMINDERS and not REPLACE_DEFAULT_REMINDERS:
        print("⚠️  WARNING: Nothing to update. Both custom and default reminders will be preserved.\n")

    start_time = time.time()

    service = load_service()
    calendars = get_owned_calendars(service)
    print(f"📋 Found calendars with owner access: {len(calendars)}\n")

    time_min = datetime.utcnow().isoformat() + 'Z'
    time_max = (datetime.utcnow() + timedelta(days=30 * MAX_MONTHS_FORWARD)).isoformat() + 'Z'

    for calendar in calendars:
        process_calendar(service, calendar, time_min, time_max)

    # Save logs
    with open('updated_events.json', 'w', encoding='utf-8') as f:
        json.dump(updated_log, f, indent=2, ensure_ascii=False)

    with open('skipped_events.json', 'w', encoding='utf-8') as f:
        json.dump(skipped_log, f, indent=2, ensure_ascii=False)

    elapsed = round(time.time() - start_time, 2)
    print(f"\n⏳ Script completed in {elapsed} seconds.\n")


if __name__ == '__main__':
    main()
