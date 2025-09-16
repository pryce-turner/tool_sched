import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta
from collections import defaultdict
import calendar
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# Configuration
DEFAULT_DOCTORS = ["Dr. Smith", "Dr. Johnson", "Dr. Williams", "Dr. Brown", "Dr. Valdez"]

# Shift types by day of week
WEEKDAY_SHIFTS = {
    "7a-7p": {"start": "07:00", "end": "19:00", "hours": 12},
    "12p-12a": {"start": "12:00", "end": "00:00", "hours": 12}
}

WEEKEND_SHIFTS = {
    "7a-7p": {"start": "07:00", "end": "19:00", "hours": 12},
    "10a-10p": {"start": "10:00", "end": "22:00", "hours": 12},
    "2p-2a": {"start": "14:00", "end": "02:00", "hours": 12},
    "7p-7a": {"start": "19:00", "end": "07:00", "hours": 12}
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

def generate_random_colors(doctors):
    """Generate random colors for doctors"""
    colors = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FECA57",
        "#FF9FF3", "#54A0FF", "#5F27CD", "#00D2D3", "#FF9F43",
        "#10AC84", "#EE5A24", "#0984E3", "#A29BFE", "#FD79A8",
        "#FDCB6E", "#6C5CE7", "#74B9FF", "#00B894", "#E17055"
    ]

    # Shuffle colors for randomness
    random.shuffle(colors)

    doctor_colors = {}
    for i, doctor in enumerate(doctors):
        doctor_colors[doctor] = colors[i % len(colors)]

    return doctor_colors

def get_shifts_for_day(date):
    """Get available shifts for a given date based on day of week"""
    # Monday = 0, Sunday = 6
    day_of_week = date.weekday()

    # Mon-Thu (0-3): weekday shifts
    if day_of_week <= 3:
        return WEEKDAY_SHIFTS
    # Fri-Sun (4-6): weekend shifts
    else:
        return WEEKEND_SHIFTS

def generate_monthly_schedule(year, month, doctors):
    """Generate a schedule for the specified month ensuring minimum 14 shifts per doctor"""
    # Get number of days in the month
    days_in_month = calendar.monthrange(year, month)[1]
    min_shifts_per_doctor = 14

    # Calculate total shifts needed
    total_shifts = 0
    for day in range(1, days_in_month + 1):
        date = datetime(year, month, day)
        shifts_for_day = get_shifts_for_day(date)
        total_shifts += len(shifts_for_day)

    # Check if we have enough shifts for minimum requirement
    min_total_shifts_needed = len(doctors) * min_shifts_per_doctor
    additional_shifts_needed = max(0, min_total_shifts_needed - total_shifts)

    # Initialize shift counters for each doctor
    doctor_shifts = {doctor: 0 for doctor in doctors}

    # Create all regular shift slots
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
                'End_Time': shift_details['end'],
                'is_additional': False
            })

    # Add additional random shifts if needed
    if additional_shifts_needed > 0:
        st.info(f"Adding {additional_shifts_needed} additional shifts to meet minimum requirements")

        # Get all possible shift types
        all_shift_types = list(WEEKDAY_SHIFTS.keys()) + list(WEEKEND_SHIFTS.keys())
        all_shift_types = list(set(all_shift_types))  # Remove duplicates

        for _ in range(additional_shifts_needed):
            # Pick a random day and shift type
            random_day = random.randint(1, days_in_month)
            random_date = datetime(year, month, random_day)
            random_shift_type = random.choice(all_shift_types)

            # Get shift details
            if random_shift_type in WEEKDAY_SHIFTS:
                shift_details = WEEKDAY_SHIFTS[random_shift_type]
            else:
                shift_details = WEEKEND_SHIFTS[random_shift_type]

            shift_slots.append({
                'Date': random_date.strftime("%Y-%m-%d"),
                'Day': random_date.strftime("%A"),
                'Shift': f"{random_shift_type} (extra)",
                'Start_Time': shift_details['start'],
                'End_Time': shift_details['end'],
                'is_additional': True
            })

    # Shuffle shift slots for random assignment
    random.shuffle(shift_slots)

    schedule_data = []

    # Phase 1: Give everyone exactly the minimum (14 shifts)
    shifts_assigned = 0
    doctor_index = 0

    # Assign 14 shifts to each doctor in round-robin fashion
    for shift_slot in shift_slots:
        if all(count >= min_shifts_per_doctor for count in doctor_shifts.values()):
            break

        # Find next doctor who needs shifts
        while doctor_shifts[doctors[doctor_index]] >= min_shifts_per_doctor:
            doctor_index = (doctor_index + 1) % len(doctors)

        assigned_doctor = doctors[doctor_index]
        doctor_shifts[assigned_doctor] += 1

        shift_slot['Doctor'] = assigned_doctor
        schedule_data.append(shift_slot)
        shifts_assigned += 1

        # Move to next doctor
        doctor_index = (doctor_index + 1) % len(doctors)

    # Phase 2: Distribute remaining shifts as evenly as possible
    remaining_slots = shift_slots[shifts_assigned:]

    for shift_slot in remaining_slots:
        # Find doctor(s) with minimum shifts among those who have at least 14
        min_shifts = min(doctor_shifts.values())
        doctors_with_min = [doctor for doctor, count in doctor_shifts.items() if count == min_shifts]

        # Assign to a random doctor from those with minimum shifts
        assigned_doctor = random.choice(doctors_with_min)
        doctor_shifts[assigned_doctor] += 1

        shift_slot['Doctor'] = assigned_doctor
        schedule_data.append(shift_slot)

    return pd.DataFrame(schedule_data)

def display_schedule_summary(df):
    """Display summary statistics of the schedule"""
    st.subheader("Schedule Summary")

    # Calculate shifts per doctor
    shifts_per_doctor = df['Doctor'].value_counts()
    min_shifts_required = 14

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Shifts per Doctor:**")
        for doctor, count in shifts_per_doctor.items():
            # Color code based on minimum requirement
            if count < min_shifts_required:
                st.markdown(f"🔴 {doctor}: {count} shifts (needs {min_shifts_required - count} more)")
            elif count == min_shifts_required:
                st.markdown(f"🟡 {doctor}: {count} shifts (at minimum)")
            else:
                st.markdown(f"🟢 {doctor}: {count} shifts (+{count - min_shifts_required} above minimum)")

    with col2:
        st.write("**Shift Distribution:**")
        shift_counts = df['Shift'].value_counts()
        for shift, count in shift_counts.items():
            st.write(f"{shift}: {count} shifts")

        # Add compliance check
        st.write("**Compliance Status:**")
        doctors_below_min = (shifts_per_doctor < min_shifts_required).sum()
        if doctors_below_min == 0:
            st.success(f"✅ All doctors meet minimum {min_shifts_required} shifts requirement")
        else:
            st.warning(f"⚠️ {doctors_below_min} doctor(s) below minimum {min_shifts_required} shifts")

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
        use_container_width=True,
        hide_index=True
    )

    return filtered_df

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
        page_title="Medical Scheduling App",
        page_icon="🏥",
        layout="wide"
    )

    st.title("🏥 Medical Scheduling App")
    st.write("Collaborative scheduling system for medical staff")

    initialize_session_state()

    # Sidebar for schedule generation
    with st.sidebar:
        st.header("Doctor Configuration")

        # Doctor input section
        st.subheader("Add Doctors")

        # Option to use defaults or start fresh
        if st.button("Load Default Doctors"):
            st.session_state.doctors = DEFAULT_DOCTORS.copy()
            st.session_state.doctor_colors = generate_random_colors(st.session_state.doctors)
            st.rerun()

        # Manual doctor entry
        new_doctor = st.text_input("Add Doctor Name:", placeholder="e.g., Dr. Johnson")
        if st.button("Add Doctor") and new_doctor.strip():
            if new_doctor.strip() not in st.session_state.doctors:
                st.session_state.doctors.append(new_doctor.strip())
                st.session_state.doctor_colors = generate_random_colors(st.session_state.doctors)
                st.success(f"Added {new_doctor.strip()}")
                st.rerun()
            else:
                st.warning("Doctor already exists!")

        # Display current doctors with remove option
        if st.session_state.doctors:
            st.subheader("Current Doctors")
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
        st.header("Schedule Generation")

        # Check if we have enough doctors
        if len(st.session_state.doctors) < 2:
            st.warning("⚠️ Add at least 2 doctors before generating schedule")
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
        st.write(f"**Total Doctors:** {len(st.session_state.doctors)}")

        st.write("**Shift Types:**")
        st.write("• **Mon-Thu:** 7a-7p, 12p-12a")
        st.write("• **Fri-Sun:** 7a-7p, 10a-10p, 2p-2a, 7p-7a")

        st.write("**Requirements:**")
        st.write("• Minimum 14 shifts per doctor")
        st.write("• 24/7 coverage")
        st.write("• 12-hour shifts")
        st.write("• Additional shifts added if needed")

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

            # Download option
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="Download Schedule as CSV",
                data=csv,
                file_name=f"schedule_{selected_year}_{selected_month:02d}.csv",
                mime="text/csv"
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
            st.write("**👥 Configurable Doctors**")
            st.write("Add your own doctors with automatically assigned random colors")

        with col2:
            st.write("**🔄 Shift Swapping**")
            st.write("Doctors can request to exchange shifts with colleagues")

        with col3:
            st.write("**📊 Analytics**")
            st.write("View workload distribution and schedule statistics")

if __name__ == "__main__":
    main()
