import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta
from collections import defaultdict
import calendar
import numpy as np
import yaml
import time
from io import BytesIO
from openpyxl.styles import Alignment

# Default configuration
DEFAULT_DOCTORS = ["Chen", "Patel", "Johnson", "Okafor", "Valdez"]

DEFAULT_SHIFTS = {
    "Monday": {
        "7a-7p": {"start": "07:00", "end": "19:00", "hours": 12},
        "12p-12a": {"start": "12:00", "end": "00:00", "hours": 12},
        "7p-7a": {"start": "19:00", "end": "07:00", "hours": 12}
    },
    "Tuesday": {
        "7a-7p": {"start": "07:00", "end": "19:00", "hours": 12},
        "12p-12a": {"start": "12:00", "end": "00:00", "hours": 12}
    },
    "Wednesday": {
        "7a-7p": {"start": "07:00", "end": "19:00", "hours": 12},
        "12p-12a": {"start": "12:00", "end": "00:00", "hours": 12},
        "7p-7a": {"start": "19:00", "end": "07:00", "hours": 12}
    },
    "Thursday": {
        "7a-7p": {"start": "07:00", "end": "19:00", "hours": 12},
        "12p-12a": {"start": "12:00", "end": "00:00", "hours": 12},
        "7p-7a": {"start": "19:00", "end": "07:00", "hours": 12}
    },
    "Friday": {
        "7a-7p": {"start": "07:00", "end": "19:00", "hours": 12},
        "10a-10p": {"start": "10:00", "end": "22:00", "hours": 12},
        "2p-2a": {"start": "14:00", "end": "02:00", "hours": 12},
        "7p-7a": {"start": "19:00", "end": "07:00", "hours": 12}
    },
    "Saturday": {
        "7a-7p": {"start": "07:00", "end": "19:00", "hours": 12},
        "10a-10p": {"start": "10:00", "end": "22:00", "hours": 12},
        "2p-2a": {"start": "14:00", "end": "02:00", "hours": 12},
        "7p-7a": {"start": "19:00", "end": "07:00", "hours": 12}
    },
    "Sunday": {
        "7a-7p": {"start": "07:00", "end": "19:00", "hours": 12},
        "10a-10p": {"start": "10:00", "end": "22:00", "hours": 12},
        "2p-2a": {"start": "14:00", "end": "02:00", "hours": 12},
        "7p-7a": {"start": "19:00", "end": "07:00", "hours": 12}
    }
}

def init_session():
    """Initialize session state"""
    if 'doctors' not in st.session_state:
        st.session_state.doctors = []
    if 'doctor_colors' not in st.session_state:
        st.session_state.doctor_colors = {}
    if 'shift_config' not in st.session_state:
        st.session_state.shift_config = DEFAULT_SHIFTS.copy()
    if 'constraints' not in st.session_state:
        st.session_state.constraints = {}
    if 'schedule_df' not in st.session_state:
        st.session_state.schedule_df = pd.DataFrame()
    if 'schedule_generated' not in st.session_state:
        st.session_state.schedule_generated = False

def generate_colors(doctors):
    """Generate random colors for doctors"""
    colors = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FECA57",
        "#8E44AD", "#54A0FF", "#5F27CD", "#00D2D3", "#FF9F43",
        "#10AC84", "#EE5A24", "#0984E3", "#A29BFE", "#2ECC71",
        "#FDCB6E", "#6C5CE7", "#74B9FF", "#00B894", "#E17055"
    ]

    random.shuffle(colors)
    doctor_colors = {}
    for i, doctor in enumerate(doctors):
        doctor_colors[doctor] = colors[i % len(colors)]

    # Special color for Valdez
    if "Valdez" in doctor_colors:
        doctor_colors["Valdez"] = "#FD79A8"

    return doctor_colors

def get_shifts_for_day(date):
    """Get shifts for a specific day"""
    day_name = date.strftime("%A")
    return st.session_state.shift_config.get(day_name, {})

def get_doctor_constraints(doctor, year, month):
    """Get constraints for a doctor in a specific month"""
    month_key = f"{year}-{month:02d}"
    doctor_constraints = st.session_state.constraints.get(doctor, {})

    constraints = {
        'fixed_shifts': doctor_constraints.get('fixed_shifts', {}),  # Day of week based
        'days_off': doctor_constraints.get(month_key, {}).get('days_off', []),  # Month specific
    }

    return constraints

def is_available(doctor, date_str, shift_name, year, month):
    """Check if doctor is available"""
    constraints = get_doctor_constraints(doctor, year, month)

    # Check days off
    days_off = constraints.get('days_off', [])
    if days_off and date_str in days_off:
        return False

    # Check fixed shifts by day of week
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    day_of_week = date_obj.strftime('%A')
    fixed_shifts = constraints.get('fixed_shifts', {})

    if day_of_week in fixed_shifts and fixed_shifts[day_of_week] != shift_name:
        return False

    return True

def get_fixed_shift(doctor, date_str, year, month):
    """Get fixed shift for doctor on date"""
    constraints = get_doctor_constraints(doctor, year, month)

    # Check fixed shifts by day of week
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    day_of_week = date_obj.strftime('%A')
    fixed_shifts = constraints.get('fixed_shifts', {})

    return fixed_shifts.get(day_of_week)

def generate_schedule(year, month, doctors):
    """Generate monthly schedule"""
    days_in_month = calendar.monthrange(year, month)[1]
    doctor_shifts = {doctor: 0 for doctor in doctors}
    daily_assignments = defaultdict(set)

    # Create shift slots
    shifts = []
    for day in range(1, days_in_month + 1):
        date = datetime(year, month, day)
        date_str = date.strftime("%Y-%m-%d")
        day_shifts = get_shifts_for_day(date)

        for shift_name, shift_data in day_shifts.items():
            shifts.append({
                'Date': date_str,
                'Day': date.strftime("%A"),
                'Shift': shift_name,
                'Start_Time': shift_data['start'],
                'End_Time': shift_data['end'],
                'Doctor': None
            })

    # Sort by date
    shifts.sort(key=lambda x: x['Date'])

    # Assign shifts
    for shift in shifts:
        date_str = shift['Date']
        shift_name = shift['Shift']

        # Check for fixed assignments first
        fixed_doctor = None
        for doctor in doctors:
            if get_fixed_shift(doctor, date_str, year, month) == shift_name:
                fixed_doctor = doctor
                break

        if fixed_doctor:
            assigned_doctor = fixed_doctor
        else:
            # Find available doctors
            available = [d for d in doctors if is_available(d, date_str, shift_name, year, month)]
            if not available:
                available = doctors

            # Prefer doctors not working today
            not_working = [d for d in available if d not in daily_assignments[date_str]]
            if not_working:
                available = not_working

            # Choose doctor with fewest shifts
            min_shifts = min(doctor_shifts[d] for d in available)
            candidates = [d for d in available if doctor_shifts[d] == min_shifts]
            assigned_doctor = random.choice(candidates)

        # Assign shift
        shift['Doctor'] = assigned_doctor
        doctor_shifts[assigned_doctor] += 1
        daily_assignments[date_str].add(assigned_doctor)

    return pd.DataFrame(shifts)

def export_config():
    """Export configuration as YAML"""
    # Create example constraints if none exist
    example_constraints = {}
    if not st.session_state.constraints and st.session_state.doctors:
        current_date = datetime.now()
        month_key = f"{current_date.year}-{current_date.month:02d}"

        # Example for first doctor - has set weekly schedule
        if len(st.session_state.doctors) > 0:
            doctor1 = st.session_state.doctors[0]
            example_constraints[doctor1] = {
                "fixed_shifts": {
                    "Monday": "7a-7p",
                    "Wednesday": "7a-7p",
                    "Friday": "7a-7p"
                },
                month_key: {
                    "days_off": [
                        f"{current_date.year}-{current_date.month:02d}-05",
                        f"{current_date.year}-{current_date.month:02d}-12"
                    ]
                },
                "notes": "Works Monday/Wednesday/Friday day shifts, prefers day shifts"
            }

        # Example for second doctor - has days off requests
        if len(st.session_state.doctors) > 1:
            doctor2 = st.session_state.doctors[1]
            example_constraints[doctor2] = {
                "fixed_shifts": {},
                month_key: {
                    "days_off": [
                        f"{current_date.year}-{current_date.month:02d}-10",
                        f"{current_date.year}-{current_date.month:02d}-11",
                        f"{current_date.year}-{current_date.month:02d}-25"
                    ]
                },
                "notes": "Prefers weekend shifts, vacation mid-month"
            }

        # Example for third doctor - night shift specialist
        if len(st.session_state.doctors) > 2:
            doctor3 = st.session_state.doctors[2]
            example_constraints[doctor3] = {
                "fixed_shifts": {
                    "Tuesday": "7p-7a",
                    "Thursday": "7p-7a",
                    "Saturday": "7p-7a"
                },
                month_key: {
                    "days_off": []
                },
                "notes": "Night shift specialist, works Tuesday/Thursday/Saturday nights"
            }

    config = {
        'team_members': st.session_state.doctors,
        'shift_configuration': st.session_state.shift_config,
        'constraints': st.session_state.constraints or example_constraints,
        'export_date': datetime.now().isoformat(),
        'examples': {
            'description': 'Simplified configuration with day-of-week fixed shifts',
            'constraint_types': {
                'fixed_shifts': 'Day of week assignments (e.g., Monday: "7a-7p") - portable across months',
                'days_off': 'Specific dates when unavailable (month-specific under YYYY-MM key)',
                'notes': 'Additional information about the team member'
            }
        }
    }
    return yaml.dump(config, default_flow_style=False, sort_keys=False)

def import_config(content):
    """Import configuration from YAML"""
    try:
        config = yaml.safe_load(content)

        # Debug: Show what was parsed
        imported_items = []

        if 'team_members' in config and config['team_members']:
            st.session_state.doctors = config['team_members']
            st.session_state.doctor_colors = generate_colors(st.session_state.doctors)
            imported_items.append(f"Team members: {len(config['team_members'])} members")

        if 'shift_configuration' in config and config['shift_configuration']:
            st.session_state.shift_config = config['shift_configuration']
            imported_items.append("Shift configuration")

        if 'constraints' in config and config['constraints']:
            st.session_state.constraints = config['constraints']

            # Count constraints
            fixed_shifts_count = sum(1 for doctor_constraints in config['constraints'].values()
                                   if isinstance(doctor_constraints, dict) and doctor_constraints.get('fixed_shifts'))

            days_off_count = 0
            for doctor_constraints in config['constraints'].values():
                if isinstance(doctor_constraints, dict):
                    for month_key, month_data in doctor_constraints.items():
                        if month_key.count('-') == 1 and isinstance(month_data, dict):  # YYYY-MM format
                            days_off = month_data.get('days_off', [])
                            if days_off:
                                days_off_count += len(days_off)

            constraint_details = []
            if fixed_shifts_count > 0:
                constraint_details.append(f"{fixed_shifts_count} weekly schedules")
            if days_off_count > 0:
                constraint_details.append(f"{days_off_count} days off")

            if constraint_details:
                imported_items.append(f"Constraints: {', '.join(constraint_details)}")

        if imported_items:
            return True, f"Successfully imported: {', '.join(imported_items)}"
        else:
            return False, "No valid configuration data found in file"

    except yaml.YAMLError as e:
        return False, f"YAML parsing error: {str(e)}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def create_excel_export(df, year, month):
    """Create Excel export with individual cells for each shift"""
    buffer = BytesIO()

    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # Schedule sheet
        df.to_excel(writer, sheet_name='Schedule', index=False)

        # Summary sheet
        summary_data = []
        shifts_per_doctor = df['Doctor'].value_counts()
        for doctor, count in shifts_per_doctor.items():
            summary_data.append({'Doctor': doctor, 'Total_Shifts': count})
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)

        # Calendar sheet with dates in one row and shifts stacked below
        cal = calendar.monthcalendar(year, month)

        # Find maximum number of shifts per day to determine how many rows we need
        max_shifts_per_day = 0
        for week in cal:
            for day in week:
                if day != 0:
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    day_shifts = df[df['Date'] == date_str]
                    max_shifts_per_day = max(max_shifts_per_day, len(day_shifts))

        # Create headers
        headers = ['Week', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        calendar_data = [headers]

        for week_num, week in enumerate(cal):
            # First row: Week label and dates
            date_row = [f'Week {week_num + 1}']
            for day in week:
                if day == 0:
                    date_row.append('')
                else:
                    date_row.append(day)
            calendar_data.append(date_row)

            # Additional rows: shifts for each day (stacked vertically)
            for shift_level in range(max_shifts_per_day):
                shift_row = ['']  # Empty week column for shift rows

                for day in week:
                    if day == 0:
                        shift_row.append('')
                    else:
                        date_str = f"{year}-{month:02d}-{day:02d}"
                        day_shifts = df[df['Date'] == date_str].sort_values('Start_Time')

                        if shift_level < len(day_shifts):
                            shift = day_shifts.iloc[shift_level]
                            shift_text = f"{shift['Shift']}: {shift['Doctor'].replace('Dr. ', '')}"
                            shift_row.append(shift_text)
                        else:
                            shift_row.append('')

                calendar_data.append(shift_row)

        # Create DataFrame and export
        cal_df = pd.DataFrame(calendar_data[1:], columns=calendar_data[0])
        cal_df.to_excel(writer, sheet_name='Calendar', index=False)

        # Format the calendar sheet
        workbook = writer.book
        cal_sheet = writer.sheets['Calendar']

        # Set column widths
        cal_sheet.column_dimensions['A'].width = 12  # Week column
        for col in range(2, 9):  # Columns B through H (Mon-Sun)
            col_letter = chr(64 + col)  # A=65, so B=66, etc.
            cal_sheet.column_dimensions[col_letter].width = 18

        # Set row heights and alignment
        for row_num in range(2, len(calendar_data) + 1):
            # First row of each week (dates) - shorter height
            if (row_num - 2) % (max_shifts_per_day + 1) == 0:
                cal_sheet.row_dimensions[row_num].height = 20
            else:
                # Shift rows - taller height
                cal_sheet.row_dimensions[row_num].height = 18

            for col_num in range(1, 9):  # A through H
                cell = cal_sheet.cell(row=row_num, column=col_num)
                if col_num == 1:  # Week column
                    cell.alignment = Alignment(horizontal='left', vertical='center')
                else:
                    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    buffer.seek(0)
    return buffer

def create_ics_export(df):
    """Create ICS calendar export"""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Tool Sched//EN"
    ]

    for _, row in df.iterrows():
        date = datetime.strptime(row['Date'], '%Y-%m-%d')
        start_time = row['Start_Time']
        end_time = row['End_Time']

        start_hour, start_min = map(int, start_time.split(':'))
        end_hour, end_min = map(int, end_time.split(':'))

        start_dt = date.replace(hour=start_hour, minute=start_min)
        end_dt = date.replace(hour=end_hour, minute=end_min)

        if end_dt <= start_dt:
            end_dt += timedelta(days=1)

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{row['Date']}-{row['Shift']}-{row['Doctor'].replace(' ', '')}",
            f"DTSTART:{start_dt.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{row['Doctor']} - {row['Shift']}",
            f"DESCRIPTION:Shift assignment for {row['Doctor']}",
            "LOCATION:Workplace",
            "END:VEVENT"
        ])

    lines.append("END:VCALENDAR")
    return '\n'.join(lines)
