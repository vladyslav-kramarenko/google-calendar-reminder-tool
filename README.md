# 📅 Google Calendar Reminder Bulk Updater
This script helps administrators of Google Workspace environments automatically set or modify reminders on calendar events for a specific user — including both default and manual reminders.

## Ideal for cases where:

* you want to ensure your teammates never miss meetings;
* you need to enforce standardized notification rules;
* you want to bulk-update reminders across multiple calendars and months.

## 🚀 Features
✅ Works with Google Workspace service accounts using domain-wide delegation.

✅ Supports all owned calendars of a target user.

✅ Applies to all upcoming events in a specified time range.

✅ Flexible config:

* Keep or replace existing manual reminders

* Keep or replace default reminders

✅ Saves update and skip logs to JSON files for review.

## ⚙️ Requirements
* Python 3.7+
* Google service account JSON key file with:
  * Domain-wide delegation enabled
  * Access to https://www.googleapis.com/auth/calendar
* Delegated user must have owned calendars

## 🔧 Configuration
Edit the top of the script (main.py) to match your environment:

```
SERVICE_ACCOUNT_FILE = 'calendar-reminder.json'  # path to service account file
USER_EMAIL = 'user@yourdomain.com'               # calendar user email

DEFAULT_REMINDER_MINUTES = 120                   # minutes before event
MAX_MONTHS_FORWARD = 1                           # how far into the future to scan

REMOVE_EXISTING_CUSTOM_REMINDERS = False         # keep or replace custom (manual) reminders
REPLACE_DEFAULT_REMINDERS = True                 # keep or replace default reminders
```

## 📄 License
MIT — free to use, modify, and share. Credits welcome if you use it in your company or publicly.
