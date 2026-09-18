#!/usr/bin/env python3
"""
Remove all calendar events that start with "TIMER:" from an ICS file.
This script reads an ICS file and creates a filtered version without TIMER events.
"""

import sys
from ics import Calendar

# Configuration
INPUT_ICS = "apple_calendar_full_export.ics"
OUTPUT_ICS = "apple_calendar_filtered.ics"

def main():
    print(f"Reading calendar from {INPUT_ICS}...")

    try:
        with open(INPUT_ICS, "r", encoding="utf-8") as f:
            cal = Calendar(f.read())
    except FileNotFoundError:
        print(f"Error: File '{INPUT_ICS}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading ICS file: {e}")
        sys.exit(1)

    original_count = len(cal.events)
    print(f"Found {original_count} events in total")

    # Filter out events that start with "TIMER:"
    filtered_events = []
    timer_count = 0

    for event in cal.events:
        event_name = event.name or ""
        if event_name.startswith("TIMER:"):
            timer_count += 1
            print(f"  Removing: {event_name}")
        else:
            filtered_events.append(event)

    # Create a new calendar with filtered events
    filtered_cal = Calendar()
    for event in filtered_events:
        filtered_cal.events.add(event)

    # Write the filtered calendar
    print(f"\nWriting filtered calendar to {OUTPUT_ICS}...")
    with open(OUTPUT_ICS, "w", encoding="utf-8") as f:
        f.writelines(filtered_cal)

    print(f"\n✅ Done!")
    print(f"   Original events: {original_count}")
    print(f"   TIMER events removed: {timer_count}")
    print(f"   Remaining events: {len(filtered_events)}")
    print(f"   Output file: {OUTPUT_ICS}")

if __name__ == "__main__":
    main()

