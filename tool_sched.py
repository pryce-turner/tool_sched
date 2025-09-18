import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta
from collections import defaultdict
import calendar
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import io
from io import BytesIO

# Configuration
DEFAULT_DOCTORS = ["Dr. Smith", "Dr. Johnson", "Dr. Williams", "Dr. Brown", "Dr. Valdez"]

# Default shift configurations by day of week
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

def initialize_session_state():
    """Initialize session state variables"""
    if 'schedule_generated' not in st.session_state:
        st.session_state.schedule_generated = False
    if 'schedule_df' not in st.session_state:
        st.session_state.schedule_df = pd.DataFrame()
    if 'swap_requests' not in st.session_state:
        st.session_state.swap_requests = []
    if 'doctors' not in st.session_state:
        st.session_state.doctors = []
    if 'doctor_colors' not in st.session_state:
        st.session_state.doctor_colors = {}
    if 'shift_config' not in st.session_state:
        st.session_state.shift_config = DEFAULT_SHIFTS.copy()

def generate_random_colors(doctors):
    """Generate random colors for doctors"""
    colors = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FECA57",
        "#8E44AD", "#54A0FF", "#5F27CD", "#00D2D3", "#FF9F43",
        "#10AC84", "#EE5A24", "#0984E3", "#A29BFE", "#2ECC71",
        "#FDCB6E", "#6C5CE7", "#74B9FF", "#00B894", "#E17055"
    ]

    # Shuffle colors for randomness
    random.shuffle(colors)

    doctor_colors = {}
    for i, doctor in enumerate(doctors):
        doctor_colors[doctor] = colors[i % len(colors)]

    # Special color assignment for Dr. Valdez
    if doctor_colors.get("Dr. Valdez"):
        doctor_colors["Dr. Valdez"] = "#FD79A8"

    return doctor_colors

def get_shifts_for_day(date):
    """Get available shifts for a given date based on configured shifts"""
    day_name = date.strftime("%A")
    return st.session_state.shift_config.get(day_name, {})

def generate_monthly_schedule(year, month, doctors):
    """Generate a schedule for the specified month with balanced shift distribution"""
    # Get number of days in the month
    days_in_month = calendar.monthrange(year, month)[1]

    # Calculate total shifts for the month
    total_shifts = 0
    for day in range(1, days_in_month + 1):
        date = datetime(year, month, day)
        shifts_for_day = get_shifts_for_day(date)
        total_shifts += len(shifts_for_day)

    # Initialize shift counters for each doctor
    doctor_shifts = {doctor: 0 for doctor in doctors}
    # Track which doctors are assigned on which days to prevent double-booking
    doctor_daily_assignments = defaultdict(set)  # {date: {doctors assigned that day}}

    # Create all shift slots
    shift_slots = []
    for day in range(1, days_in_month + 1):
        date = datetime(year, month, day)
        date_str = date.strftime("%Y-%m-%d")
        shifts_for_day = get_shifts_for_day(date)

        for shift_type, shift_details in shifts_for_day.items():
            shift_slots.append({
                'Date': date_str,
                'Day': date.strftime("%A"),
                'Shift': shift_type,
                'Start_Time': shift_details['start'],
                'End_Time': shift_details['end']
            })

    # Sort shift slots by date for better assignment distribution
    shift_slots.sort(key=lambda x: x['Date'])

    schedule_data = []

    # Assign shifts one by one, ensuring balanced distribution and no double shifts per day
    for shift_slot in shift_slots:
        shift_date = shift_slot['Date']

        # Get doctors who are NOT already assigned on this day
        available_doctors = [doc for doc in doctors if doc not in doctor_daily_assignments[shift_date]]

        # If all doctors are already assigned this day, fall back to all doctors
        # but prioritize those with fewer total shifts
        if not available_doctors:
            available_doctors = doctors

        # Among available doctors, find those with the minimum number of shifts
        min_shifts = min(doctor_shifts[doc] for doc in available_doctors)
        best_candidates = [doc for doc in available_doctors if doctor_shifts[doc] == min_shifts]

        # If multiple doctors have the same minimum shifts, prefer those not working today
        doctors_not_working_today = [doc for doc in best_candidates if doc not in doctor_daily_assignments[shift_date]]
        if doctors_not_working_today:
            best_candidates = doctors_not_working_today

        # Randomly select from the best candidates
        assigned_doctor = random.choice(best_candidates)

        # Assign the shift
        doctor_shifts[assigned_doctor] += 1
        doctor_daily_assignments[shift_date].add(assigned_doctor)

        shift_slot['Doctor'] = assigned_doctor
        schedule_data.append(shift_slot)

    return pd.DataFrame(schedule_data)

def display_schedule_summary(df):
    """Display summary statistics of the schedule"""
    st.subheader("Schedule Summary")

    # Calculate shifts per doctor
    shifts_per_doctor = df['Doctor'].value_counts()

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Shifts per Team Member:**")
        for doctor, count in shifts_per_doctor.items():
            st.write(f"{doctor}: {count} shifts")

    with col2:
        st.write("**Shift Distribution:**")
        shift_counts = df['Shift'].value_counts()
        for shift, count in shift_counts.items():
            st.write(f"{shift}: {count} shifts")

        # Add balance check
        st.write("**Balance Status:**")
        if len(shifts_per_doctor) > 0:
            min_shifts = shifts_per_doctor.min()
            max_shifts = shifts_per_doctor.max()
            difference = max_shifts - min_shifts

            if difference <= 1:
                st.success(f"✅ Well balanced (difference: {difference})")
            elif difference <= 2:
                st.info(f"📊 Reasonably balanced (difference: {difference})")
            else:
                st.warning(f"⚠️ Imbalanced workload (difference: {difference})")

def display_calendar_view(df, year, month, doctor_colors):
    """Display schedule in calendar format"""
    st.subheader("Calendar View")

    # Create calendar grid
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]

    st.write(f"### {month_name} {year}")

    # Create a table-like visualization for the calendar
    calendar_html = f"<div style='font-family: Arial, sans-serif;'>"
    calendar_html += "<table style='width: 100%; border-collapse: collapse; margin: 20px 0;'>"

    # Header row
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    calendar_html += "<tr>"
    for day_name in days:
        calendar_html += f"<th style='border: 1px solid #ddd; padding: 8px; background-color: #f2f2f2; color: black; text-align: center;'>{day_name[:3]}</th>"
    calendar_html += "</tr>"

    # Calendar rows
    for week in cal:
        calendar_html += "<tr style='height: 120px;'>"
        for day in week:
            if day == 0:
                calendar_html += "<td style='border: 1px solid #ddd; padding: 4px; background-color: #f9f9f9;'></td>"
            else:
                day_date = datetime(year, month, day).strftime("%Y-%m-%d")
                day_shifts = df[df['Date'] == day_date]

                cell_content = f"<div style='font-weight: bold; margin-bottom: 5px;'>{day}</div>"

                for _, shift in day_shifts.iterrows():
                    color = doctor_colors.get(shift['Doctor'], '#CCCCCC')
                    cell_content += f"<div style='background-color: {color}; color: white; padding: 2px; margin: 1px; border-radius: 3px; font-size: 10px; text-align: center;'>"
                    cell_content += f"<b>{shift['Shift']}</b><br>{shift['Doctor'].replace('Dr. ', '')}"
                    cell_content += "</div>"

                calendar_html += f"<td style='border: 1px solid #ddd; padding: 4px; vertical-align: top;'>{cell_content}</td>"
        calendar_html += "</tr>"

    calendar_html += "</table></div>"

    # Display the calendar
    st.markdown(calendar_html, unsafe_allow_html=True)

    # Legend
    st.write("**Doctor Color Legend:**")
    legend_cols = st.columns(len(doctor_colors))
    for i, (doctor, color) in enumerate(doctor_colors.items()):
        with legend_cols[i]:
            st.markdown(f'<div style="background-color: {color}; color: white; padding: 5px; text-align: center; border-radius: 5px; margin: 2px;">{doctor}</div>', unsafe_allow_html=True)

def display_schedule_table(df):
    """Display the schedule in a table format"""
    st.subheader("Table View")

    # Add filters
    col1, col2, col3 = st.columns(3)

    with col1:
        selected_doctors = st.multiselect(
            "Filter by Doctor:",
            options=st.session_state.doctors if st.session_state.doctors else [],
            default=st.session_state.doctors if st.session_state.doctors else []
        )

    with col2:
        selected_shifts = st.multiselect(
            "Filter by Shift:",
            options=df['Shift'].unique(),
            default=df['Shift'].unique()
        )

    with col3:
        selected_days = st.multiselect(
            "Filter by Day:",
            options=df['Day'].unique(),
            default=df['Day'].unique()
        )

    # Filter the dataframe
    filtered_df = df[
        (df['Doctor'].isin(selected_doctors)) &
        (df['Shift'].isin(selected_shifts)) &
        (df['Day'].isin(selected_days))
    ]

    # Display the filtered table
    st.dataframe(
        filtered_df,
        width='stretch',
        hide_index=True
    )

    return filtered_df

def create_excel_export(df, year, month):
    """Create an Excel file with the schedule data"""
    # Create a BytesIO buffer
    buffer = BytesIO()

    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # Main schedule sheet
        df.to_excel(writer, sheet_name='Schedule', index=False)

        # Summary sheet
        summary_data = []
        shifts_per_doctor = df['Doctor'].value_counts()
        for doctor, count in shifts_per_doctor.items():
            summary_data.append({
                'Doctor': doctor,
                'Total Shifts': count,
                'Status': 'Balanced'
            })

        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)

        # Daily view sheet
        daily_pivot = df.pivot_table(
            index='Date',
            columns='Shift',
            values='Doctor',
            aggfunc='first',
            fill_value=''
        )
        daily_pivot.to_excel(writer, sheet_name='Daily View')

        # Calendar view sheet
        cal = calendar.monthcalendar(year, month)
        month_name = calendar.month_name[month]

        # Create calendar data structure
        calendar_data = []
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        # Add header row
        calendar_data.append([''] + day_names)

        # Process each week
        for week_num, week in enumerate(cal):
            week_data = [f'Week {week_num + 1}']

            for day in week:
                if day == 0:
                    week_data.append('')
                else:
                    # Get shifts for this day
                    day_date = datetime(year, month, day).strftime("%Y-%m-%d")
                    day_shifts = df[df['Date'] == day_date]

                    # Create cell content with day number and shifts
                    cell_content = f"{day}\n"

                    if not day_shifts.empty:
                        for _, shift in day_shifts.iterrows():
                            cell_content += f"{shift['Shift']}: {shift['Doctor']}\n"

                    week_data.append(cell_content.strip())

            calendar_data.append(week_data)

        # Create DataFrame and export
        calendar_df = pd.DataFrame(calendar_data[1:], columns=calendar_data[0])
        calendar_df.to_excel(writer, sheet_name='Calendar View', index=False)

        # Format the calendar sheet
        workbook = writer.book
        calendar_sheet = writer.sheets['Calendar View']

        # Set column widths
        for col in range(1, 8):  # Columns B through H (days of week)
            calendar_sheet.column_dimensions[chr(65 + col)].width = 20

        # Set row heights and enable text wrapping
        for row in range(2, len(calendar_data) + 1):
            calendar_sheet.row_dimensions[row].height = 80
            for col in range(1, 8):
                cell = calendar_sheet.cell(row=row, column=col + 1)
                from openpyxl.styles import Alignment
                cell.alignment = Alignment(wrap_text=True, vertical='top')

    buffer.seek(0)
    return buffer

def create_ics_export(df, year, month):
    """Create an ICS calendar file with the schedule data"""
    ics_content = []
    ics_content.append("BEGIN:VCALENDAR")
    ics_content.append("VERSION:2.0")
    ics_content.append("PRODID:-//Tool Sched//EN")
    ics_content.append("CALSCALE:GREGORIAN")
    ics_content.append("METHOD:PUBLISH")

    for _, row in df.iterrows():
        # Parse the date and times
        event_date = datetime.strptime(row['Date'], '%Y-%m-%d')

        # Parse start time
        start_time_str = row['Start_Time']
        start_hour, start_minute = map(int, start_time_str.split(':'))
        start_dt = event_date.replace(hour=start_hour, minute=start_minute)

        # Parse end time (handle overnight shifts)
        end_time_str = row['End_Time']
        end_hour, end_minute = map(int, end_time_str.split(':'))
        end_dt = event_date.replace(hour=end_hour, minute=end_minute)

        # If end time is earlier than start time, it's next day
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)

        # Format for ICS (UTC format)
        start_utc = start_dt.strftime('%Y%m%dT%H%M%S')
        end_utc = end_dt.strftime('%Y%m%dT%H%M%S')

        # Create unique ID for the event
        uid = f"{row['Date']}-{row['Shift']}-{row['Doctor'].replace(' ', '')}-{hash(row['Doctor'] + row['Date'] + row['Shift'])}"

        # Add event
        ics_content.append("BEGIN:VEVENT")
        ics_content.append(f"UID:{uid}")
        ics_content.append(f"DTSTART:{start_utc}")
        ics_content.append(f"DTEND:{end_utc}")
        ics_content.append(f"SUMMARY:{row['Doctor']} - {row['Shift']} Shift")
        ics_content.append(f"DESCRIPTION:Shift assignment for {row['Doctor']} on {row['Day']}")
        ics_content.append(f"LOCATION:Workplace")
        ics_content.append("END:VEVENT")

    ics_content.append("END:VCALENDAR")

    return '\n'.join(ics_content)

def handle_shift_swaps():
    """Handle shift swap requests between doctors"""
    st.subheader("Shift Exchange System")

    if st.session_state.schedule_df.empty:
        st.warning("Please generate a schedule first.")
        return

    with st.form("swap_form"):
        st.write("**Request Shift Exchange**")

        col1, col2 = st.columns(2)

        with col1:
            # Doctor requesting swap
            requesting_doctor = st.selectbox(
                "Your Name:",
                options=st.session_state.doctors if st.session_state.doctors else []
            )

            # Get shifts for requesting doctor
            doctor_shifts = st.session_state.schedule_df[
                st.session_state.schedule_df['Doctor'] == requesting_doctor
            ].copy()

            if not doctor_shifts.empty:
                doctor_shifts['Display'] = (
                    doctor_shifts['Date'] + " - " +
                    doctor_shifts['Shift'] + " (" +
                    doctor_shifts['Start_Time'] + " - " +
                    doctor_shifts['End_Time'] + ")"
                )

                shift_to_give = st.selectbox(
                    "Shift you want to give away:",
                    options=doctor_shifts['Display'].tolist(),
                    key="give_shift"
                )
            else:
                st.write("No shifts assigned to selected doctor")
                shift_to_give = None

        with col2:
            # Target doctor for swap
            target_doctor = st.selectbox(
                "Doctor to swap with:",
                options=[d for d in st.session_state.doctors if d != requesting_doctor] if st.session_state.doctors else []
            )

            # Get shifts for target doctor
            target_shifts = st.session_state.schedule_df[
                st.session_state.schedule_df['Doctor'] == target_doctor
            ].copy()

            if not target_shifts.empty:
                target_shifts['Display'] = (
                    target_shifts['Date'] + " - " +
                    target_shifts['Shift'] + " (" +
                    target_shifts['Start_Time'] + " - " +
                    target_shifts['End_Time'] + ")"
                )

                shift_to_get = st.selectbox(
                    "Shift you want to take:",
                    options=target_shifts['Display'].tolist(),
                    key="get_shift"
                )
            else:
                st.write("No shifts assigned to target doctor")
                shift_to_get = None

        submit_swap = st.form_submit_button("Request Swap")

        if submit_swap and shift_to_give and shift_to_get:
            # Process the swap
            swap_request = {
                'requesting_doctor': requesting_doctor,
                'target_doctor': target_doctor,
                'give_shift': shift_to_give,
                'get_shift': shift_to_get,
                'status': 'pending'
            }

            st.session_state.swap_requests.append(swap_request)
            st.success("Swap request submitted!")

    # Display pending swap requests
    if st.session_state.swap_requests:
        st.write("**Pending Swap Requests:**")

        for i, swap in enumerate(st.session_state.swap_requests):
            if swap['status'] == 'pending':
                with st.expander(f"Swap Request #{i+1}"):
                    st.write(f"**From:** {swap['requesting_doctor']}")
                    st.write(f"**To:** {swap['target_doctor']}")
                    st.write(f"**Giving:** {swap['give_shift']}")
                    st.write(f"**Wanting:** {swap['get_shift']}")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"Approve Swap #{i+1}", key=f"approve_{i}"):
                            execute_swap(i)
                            st.rerun()

                    with col2:
                        if st.button(f"Reject Swap #{i+1}", key=f"reject_{i}"):
                            st.session_state.swap_requests[i]['status'] = 'rejected'
                            st.rerun()

def execute_swap(swap_index):
    """Execute an approved shift swap"""
    swap = st.session_state.swap_requests[swap_index]

    # Parse shift information from display strings
    give_date = swap['give_shift'].split(' - ')[0]
    give_shift_type = swap['give_shift'].split(' - ')[1].split(' (')[0]

    get_date = swap['get_shift'].split(' - ')[0]
    get_shift_type = swap['get_shift'].split(' - ')[1].split(' (')[0]

    # Update the schedule dataframe
    df = st.session_state.schedule_df

    # Find and swap the assignments
    give_mask = (df['Date'] == give_date) & (df['Shift'] == give_shift_type)
    get_mask = (df['Date'] == get_date) & (df['Shift'] == get_shift_type)

    df.loc[give_mask, 'Doctor'] = swap['target_doctor']
    df.loc[get_mask, 'Doctor'] = swap['requesting_doctor']

    # Mark swap as completed
    st.session_state.swap_requests[swap_index]['status'] = 'completed'

    st.success("Swap completed successfully!")

def main():
    st.set_page_config(
        page_title="Tool Sched",
        page_icon="🛠️",
        layout="wide"
    )

    st.title("🛠️ Tool Sched")
    st.write("Collaborative scheduling system for any team")

    initialize_session_state()

    # Sidebar for schedule generation
    with st.sidebar:
        st.header("Team Configuration")

        # Doctor input section
        st.subheader("Add Team Members")

        # Option to use defaults or start fresh
        if st.button("Load Default Team"):
            st.session_state.doctors = DEFAULT_DOCTORS.copy()
            st.session_state.doctor_colors = generate_random_colors(st.session_state.doctors)
            st.rerun()

        # Manual doctor entry
        new_doctor = st.text_input("Add Team Member Name:", placeholder="e.g., Dr. Johnson")
        if st.button("Add Team Member") and new_doctor.strip():
            if new_doctor.strip() not in st.session_state.doctors:
                st.session_state.doctors.append(new_doctor.strip())
                st.session_state.doctor_colors = generate_random_colors(st.session_state.doctors)
                st.success(f"Added {new_doctor.strip()}")
                st.rerun()
            else:
                st.warning("Team member already exists!")

        # Display current doctors with remove option
        if st.session_state.doctors:
            st.subheader("Current Team Members")
            for i, doctor in enumerate(st.session_state.doctors):
                col1, col2 = st.columns([3, 1])
                with col1:
                    color = st.session_state.doctor_colors.get(doctor, "#CCCCCC")
                    st.markdown(f'<div style="background-color: {color}; color: white; padding: 3px; border-radius: 3px; text-align: center; margin: 2px;">{doctor}</div>', unsafe_allow_html=True)
                with col2:
                    if st.button("❌", key=f"remove_{i}"):
                        st.session_state.doctors.remove(doctor)
                        st.session_state.doctor_colors = generate_random_colors(st.session_state.doctors)
                        st.rerun()

            if st.button("🎨 Regenerate Colors"):
                st.session_state.doctor_colors = generate_random_colors(st.session_state.doctors)
                st.rerun()

        st.divider()

        # Shift Configuration Section
        st.header("Shift Configuration")

        if st.button("Reset to Default Shifts"):
            st.session_state.shift_config = DEFAULT_SHIFTS.copy()
            st.success("Shifts reset to defaults!")
            st.rerun()

        # Configurable shift editor
        st.subheader("Edit Shifts by Day")

        for day_name in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
            with st.expander(f"📅 {day_name} Shifts"):
                day_shifts = st.session_state.shift_config.get(day_name, {}).copy()

                # Track changes
                changes_made = False

                # Display existing shifts with edit/delete options
                for i, (shift_name, shift_details) in enumerate(list(day_shifts.items())):
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

                    with col1:
                        new_shift_name = st.text_input(f"Shift Name", value=shift_name, key=f"{day_name}_name_{i}")
                    with col2:
                        new_start = st.text_input(f"Start", value=shift_details['start'], key=f"{day_name}_start_{i}", help="HH:MM format")
                    with col3:
                        new_end = st.text_input(f"End", value=shift_details['end'], key=f"{day_name}_end_{i}", help="HH:MM format")
                    with col4:
                        if st.button("🗑️", key=f"{day_name}_delete_{i}", help="Delete shift"):
                            del day_shifts[shift_name]
                            changes_made = True

                    # Update shift if name or times changed
                    if new_shift_name != shift_name or new_start != shift_details['start'] or new_end != shift_details['end']:
                        try:
                            datetime.strptime(new_start, '%H:%M')
                            datetime.strptime(new_end, '%H:%M')

                            # Calculate hours (handle overnight shifts)
                            start_dt = datetime.strptime(new_start, '%H:%M')
                            end_dt = datetime.strptime(new_end, '%H:%M')
                            if end_dt <= start_dt:
                                # Overnight shift
                                hours = 24 - (start_dt.hour - end_dt.hour) - (start_dt.minute - end_dt.minute) / 60
                            else:
                                hours = (end_dt.hour - start_dt.hour) + (end_dt.minute - start_dt.minute) / 60

                            # Remove old shift if name changed
                            if new_shift_name != shift_name and shift_name in day_shifts:
                                del day_shifts[shift_name]

                            # Add/update shift
                            day_shifts[new_shift_name] = {
                                "start": new_start,
                                "end": new_end,
                                "hours": round(hours, 1)
                            }
                            changes_made = True
                        except ValueError:
                            st.error(f"Invalid time format for {shift_name}. Use HH:MM format (e.g., 07:00)")

                # Add new shift section
                st.write("**Add New Shift:**")
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

                with col1:
                    new_shift_name = st.text_input("New Shift Name", key=f"{day_name}_new_name", placeholder="e.g., 6a-6p")
                with col2:
                    new_shift_start = st.text_input("Start Time", key=f"{day_name}_new_start", placeholder="06:00")
                with col3:
                    new_shift_end = st.text_input("End Time", key=f"{day_name}_new_end", placeholder="18:00")
                with col4:
                    if st.button("➕ Add", key=f"{day_name}_add"):
                        if new_shift_name and new_shift_start and new_shift_end:
                            try:
                                datetime.strptime(new_shift_start, '%H:%M')
                                datetime.strptime(new_shift_end, '%H:%M')

                                # Calculate hours
                                start_dt = datetime.strptime(new_shift_start, '%H:%M')
                                end_dt = datetime.strptime(new_shift_end, '%H:%M')
                                if end_dt <= start_dt:
                                    hours = 24 - (start_dt.hour - end_dt.hour) - (start_dt.minute - end_dt.minute) / 60
                                else:
                                    hours = (end_dt.hour - start_dt.hour) + (end_dt.minute - start_dt.minute) / 60

                                day_shifts[new_shift_name] = {
                                    "start": new_shift_start,
                                    "end": new_shift_end,
                                    "hours": round(hours, 1)
                                }
                                changes_made = True
                                st.success(f"Added {new_shift_name} shift!")
                            except ValueError:
                                st.error("Invalid time format. Use HH:MM format (e.g., 07:00)")
                        else:
                            st.error("Please fill in all fields")

                # Apply changes to session state
                if changes_made:
                    st.session_state.shift_config[day_name] = day_shifts
                    st.rerun()

                # Show summary for this day
                if day_shifts:
                    st.write("**Current shifts:**")
                    for shift_name, shift_details in day_shifts.items():
                        st.write(f"• {shift_name}: {shift_details['start']} - {shift_details['end']} ({shift_details['hours']}h)")
                else:
                    st.write("No shifts configured for this day")

        # Validation summary
        st.subheader("📊 Configuration Summary")
        total_shifts_week = 0
        for day_name, day_shifts in st.session_state.shift_config.items():
            shift_count = len(day_shifts)
            total_shifts_week += shift_count
            if shift_count == 0:
                st.warning(f"⚠️ {day_name}: No shifts configured")
            else:
                st.info(f"✅ {day_name}: {shift_count} shifts")

        st.write(f"**Total shifts per week:** {total_shifts_week}")

        if total_shifts_week == 0:
            st.error("❌ No shifts configured. Please add shifts before generating schedule.")

        st.divider()
        st.header("Schedule Generation")

        # Check if we have enough doctors and shifts
        total_shifts_configured = sum(len(day_shifts) for day_shifts in st.session_state.shift_config.values())

        if len(st.session_state.doctors) < 2:
            st.warning("⚠️ Add at least 2 team members before generating schedule")
            schedule_generation_disabled = True
        elif total_shifts_configured == 0:
            st.warning("⚠️ Configure at least one shift before generating schedule")
            schedule_generation_disabled = True
        else:
            schedule_generation_disabled = False

        # Month and year selection
        current_date = datetime.now()

        col1, col2 = st.columns(2)
        with col1:
            selected_month = st.selectbox(
                "Month:",
                options=range(1, 13),
                index=current_date.month - 1,
                format_func=lambda x: calendar.month_name[x]
            )

        with col2:
            selected_year = st.number_input(
                "Year:",
                min_value=2024,
                max_value=2030,
                value=current_date.year
            )

        if st.button("Generate Schedule", type="primary", disabled=schedule_generation_disabled):
            st.session_state.schedule_df = generate_monthly_schedule(
                selected_year, selected_month, st.session_state.doctors
            )
            st.session_state.schedule_generated = True
            st.session_state.swap_requests = []  # Reset swap requests
            st.success("Schedule generated!")
            st.rerun()

        # Display configuration
        st.header("Configuration")
        st.write(f"**Total Team Members:** {len(st.session_state.doctors)}")

        st.write("**Shift Types:**")
        st.write("• Fully configurable by day of week")
        st.write("• Default: Mon/Wed/Thu (3 shifts), Tue (2 shifts), Fri-Sun (4 shifts)")
        st.write("• Edit in Shift Configuration section above")

        st.write("**Requirements:**")
        st.write("• Balanced shift distribution across team")
        st.write("• No multiple shifts per person per day")
        st.write("• 24/7 coverage")
        st.write("• 12-hour shifts")
        st.write("• Automatic balancing algorithm")

    # Main content
    if st.session_state.schedule_generated and not st.session_state.schedule_df.empty:
        # Create tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📅 Calendar View", "📋 Table View", "🔄 Shift Exchanges", "📊 Analytics"])

        with tab1:
            display_schedule_summary(st.session_state.schedule_df)
            st.divider()
            display_calendar_view(st.session_state.schedule_df, selected_year, selected_month, st.session_state.doctor_colors)

        with tab2:
            filtered_df = display_schedule_table(st.session_state.schedule_df)

            # Export options
            st.subheader("Export Options")
            col1, col2, col3 = st.columns(3)

            with col1:
                # CSV export
                csv = filtered_df.to_csv(index=False)
                st.download_button(
                    label="📄 Download as CSV",
                    data=csv,
                    file_name=f"schedule_{selected_year}_{selected_month:02d}.csv",
                    mime="text/csv"
                )

            with col2:
                # Excel export
                excel_buffer = create_excel_export(st.session_state.schedule_df, selected_year, selected_month)
                st.download_button(
                    label="📊 Download as Excel",
                    data=excel_buffer,
                    file_name=f"schedule_{selected_year}_{selected_month:02d}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            with col3:
                # ICS calendar export
                ics_content = create_ics_export(st.session_state.schedule_df, selected_year, selected_month)
                st.download_button(
                    label="📅 Download as Calendar",
                    data=ics_content,
                    file_name=f"schedule_{selected_year}_{selected_month:02d}.ics",
                    mime="text/calendar"
                )

        with tab3:
            handle_shift_swaps()

        with tab4:
            st.subheader("Schedule Analytics")

            # Doctor workload chart
            shifts_per_doctor = st.session_state.schedule_df['Doctor'].value_counts()
            st.bar_chart(shifts_per_doctor)

            # Shift type distribution
            st.subheader("Shift Type Distribution")
            shift_distribution = st.session_state.schedule_df['Shift'].value_counts()
            st.bar_chart(shift_distribution)

            # Daily coverage view
            st.subheader("Daily Coverage")
            daily_coverage = st.session_state.schedule_df.groupby('Date').size()
            st.line_chart(daily_coverage)

    else:
        st.info("👈 Configure doctors and generate a schedule using the sidebar to get started!")

        # Show example of what the app can do
        st.subheader("Features")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.write("**👥 Configurable Team**")
            st.write("Add your own team members with automatically assigned random colors")

        with col2:
            st.write("**🔄 Shift Swapping**")
            st.write("Team members can request to exchange shifts with colleagues")

        with col3:
            st.write("**📊 Analytics**")
            st.write("View workload distribution and schedule statistics")

if __name__ == "__main__":
    main()
