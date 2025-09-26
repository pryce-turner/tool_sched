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
DEFAULT_DOCTORS = ["Dr. Chen", "Dr. Patel", "Dr. Johnson", "Dr. Okafor", "Dr. Valdez"]

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

    # Special color for Dr. Valdez
    if "Dr. Valdez" in doctor_colors:
        doctor_colors["Dr. Valdez"] = "#FD79A8"

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
    """Create Excel export"""
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

        # Calendar sheet
        cal = calendar.monthcalendar(year, month)
        calendar_data = [['Week'] + ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']]

        for week_num, week in enumerate(cal):
            week_row = [f'Week {week_num + 1}']
            for day in week:
                if day == 0:
                    week_row.append('')
                else:
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    day_shifts = df[df['Date'] == date_str]
                    cell_content = f"{day}\n"
                    for _, shift in day_shifts.iterrows():
                        cell_content += f"{shift['Shift']}: {shift['Doctor']}\n"
                    week_row.append(cell_content.strip())
            calendar_data.append(week_row)

        cal_df = pd.DataFrame(calendar_data[1:], columns=calendar_data[0])
        cal_df.to_excel(writer, sheet_name='Calendar', index=False)

        # Format calendar sheet
        workbook = writer.book
        cal_sheet = writer.sheets['Calendar']
        for col in range(1, 8):
            cal_sheet.column_dimensions[chr(65 + col)].width = 20
        for row in range(2, len(calendar_data) + 1):
            cal_sheet.row_dimensions[row].height = 80
            for col in range(1, 8):
                cell = cal_sheet.cell(row=row, column=col + 1)
                cell.alignment = Alignment(wrap_text=True, vertical='top')

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

def main():
    st.set_page_config(page_title="Tool Sched", page_icon="🛠️", layout="wide")
    st.title("🛠️ Tool Sched")
    st.write("Collaborative scheduling system for any team")

    init_session()

    # Sidebar
    with st.sidebar:
        st.header("Team Members")

        # Load defaults
        if st.button("Load Default Team", key="load_defaults"):
            st.session_state.doctors = DEFAULT_DOCTORS.copy()
            st.session_state.doctor_colors = generate_colors(st.session_state.doctors)
            st.success("Default team loaded!")
            st.rerun()

        # Add member
        new_member = st.text_input("Add team member:", placeholder="e.g., Dr. Johnson", key="new_member")
        if st.button("Add Member", key="add_member") and new_member.strip():
            if new_member.strip() not in st.session_state.doctors:
                st.session_state.doctors.append(new_member.strip())
                st.session_state.doctor_colors = generate_colors(st.session_state.doctors)
                st.success(f"Added {new_member.strip()}")
                st.rerun()
            else:
                st.warning("Already exists!")

        # Display members
        if st.session_state.doctors:
            st.write("**Current Team:**")
            for i, doctor in enumerate(st.session_state.doctors):
                col1, col2 = st.columns([3, 1])
                with col1:
                    color = st.session_state.doctor_colors.get(doctor, "#CCCCCC") if st.session_state.doctor_colors else "#CCCCCC"
                    st.markdown(f'<div style="background-color: {color}; color: white; padding: 3px; border-radius: 3px; text-align: center; margin: 2px;">{doctor}</div>', unsafe_allow_html=True)
                with col2:
                    if st.button("❌", key=f"remove_{i}"):
                        st.session_state.doctors.remove(doctor)
                        if st.session_state.doctors:
                            st.session_state.doctor_colors = generate_colors(st.session_state.doctors)
                        st.rerun()

            if st.button("🎨 New Colors", key="regen_colors"):
                st.session_state.doctor_colors = generate_colors(st.session_state.doctors)
                st.rerun()

        st.divider()

        # Import/Export
        st.header("Configuration")

        # Export
        if st.session_state.doctors or st.session_state.constraints:
            config_yaml = export_config()
            st.download_button(
                "📥 Export Config",
                config_yaml,
                f"tool_sched_config_{datetime.now().strftime('%Y%m%d')}.yaml",
                "text/yaml",
                key="export_config"
            )

        # Import
        uploaded = st.file_uploader("📤 Import Config", type=['yaml', 'yml'], key="import_config")
        if uploaded is not None:
            try:
                content = uploaded.read().decode('utf-8')
                success, msg = import_config(content)

                if success:
                    st.success(msg)
                    # Clear the file uploader by forcing a rerun after successful import
                    if st.session_state.get('import_success') != uploaded.file_id:
                        st.session_state.import_success = uploaded.file_id
                        time.sleep(0.5)
                        st.rerun()
                else:
                    st.error(msg)
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")

        # Clear import success flag if no file is uploaded
        if uploaded is None and 'import_success' in st.session_state:
            del st.session_state.import_success

        st.divider()

        # Schedule generation
        st.header("Generate Schedule")

        current_date = datetime.now()
        sched_month = st.selectbox("Month:", range(1, 13), index=current_date.month-1, format_func=lambda x: calendar.month_name[x], key="sched_month")
        sched_year = st.number_input("Year:", min_value=2024, max_value=2030, value=current_date.year, key="sched_year")

        can_generate = len(st.session_state.doctors) >= 2

        if not can_generate:
            st.warning("Need at least 2 team members")

        if st.button("🗓️ Generate", disabled=not can_generate, key="generate"):
            st.session_state.schedule_df = generate_schedule(sched_year, sched_month, st.session_state.doctors)
            st.session_state.schedule_generated = True
            st.success("Schedule generated!")
            st.rerun()

    # Main content
    if st.session_state.schedule_generated and not st.session_state.schedule_df.empty:
        tab1, tab2, tab3, tab4 = st.tabs(["📅 Calendar", "📋 Table", "⚙️ Edit Constraints", "📊 Analytics"])

        with tab1:
            # Calendar view
            st.subheader("Calendar View")
            year = st.session_state.schedule_df.iloc[0]['Date'][:4]
            month = int(st.session_state.schedule_df.iloc[0]['Date'][5:7])

            cal = calendar.monthcalendar(int(year), month)
            month_name = calendar.month_name[month]

            st.write(f"### {month_name} {year}")

            # HTML calendar
            html = "<table style='width: 100%; border-collapse: collapse;'>"
            html += "<tr>" + "".join(f"<th style='border: 1px solid #ddd; padding: 8px; background: #f2f2f2; color: black;'>{day[:3]}</th>" for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']) + "</tr>"

            for week in cal:
                html += "<tr style='height: 120px;'>"
                for day in week:
                    if day == 0:
                        html += "<td style='border: 1px solid #ddd; background: #f9f9f9;'></td>"
                    else:
                        date_str = f"{year}-{month:02d}-{day:02d}"
                        day_shifts = st.session_state.schedule_df[st.session_state.schedule_df['Date'] == date_str]

                        cell = f"<div style='font-weight: bold; margin-bottom: 5px;'>{day}</div>"
                        for _, shift in day_shifts.iterrows():
                            color = st.session_state.doctor_colors.get(shift['Doctor'], '#CCCCCC') if st.session_state.doctor_colors else '#CCCCCC'
                            cell += f"<div style='background: {color}; color: white; padding: 2px; margin: 1px; border-radius: 3px; font-size: 10px; text-align: center;'>"
                            cell += f"<b>{shift['Shift']}</b><br>{shift['Doctor'].replace('Dr. ', '')}</div>"

                        html += f"<td style='border: 1px solid #ddd; padding: 4px; vertical-align: top;'>{cell}</td>"
                html += "</tr>"

            html += "</table>"
            st.markdown(html, unsafe_allow_html=True)

            # Legend
            if st.session_state.doctor_colors:
                st.write("**Legend:**")
                cols = st.columns(len(st.session_state.doctors))
                for i, (doctor, color) in enumerate(st.session_state.doctor_colors.items()):
                    with cols[i]:
                        st.markdown(f'<div style="background: {color}; color: white; padding: 5px; text-align: center; border-radius: 5px;">{doctor}</div>', unsafe_allow_html=True)

        with tab2:
            # Table view with editing
            st.subheader("Schedule Table")

            # Edit mode toggle
            edit_mode = st.checkbox("✏️ Edit Mode - Reassign shifts by changing dropdowns", key="edit_mode")

            if edit_mode:
                st.info("🔄 **Edit Mode Active** - Use the dropdowns in the 'Reassign To' column to change shift assignments. Changes save automatically.")

            # Filters
            col1, col2 = st.columns(2)
            with col1:
                filter_doctors = st.multiselect("Filter by team member:", st.session_state.doctors, default=st.session_state.doctors, key="filter_doctors")
            with col2:
                filter_shifts = st.multiselect("Filter by shift:", st.session_state.schedule_df['Shift'].unique(), default=st.session_state.schedule_df['Shift'].unique(), key="filter_shifts")

            # Filter data
            filtered = st.session_state.schedule_df[
                (st.session_state.schedule_df['Doctor'].isin(filter_doctors)) &
                (st.session_state.schedule_df['Shift'].isin(filter_shifts))
            ].copy()

            if edit_mode:
                # Display editable table
                st.write("**Click dropdowns to reassign shifts:**")

                changes_made = False
                for idx, row in filtered.iterrows():
                    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])

                    with col1:
                        st.write(f"**{row['Date']}**")
                        st.write(f"{row['Day']}")

                    with col2:
                        st.write(f"**{row['Shift']}**")
                        st.write(f"{row['Start_Time']} - {row['End_Time']}")

                    with col3:
                        # Current assignment
                        current_color = st.session_state.doctor_colors.get(row['Doctor'], '#CCCCCC') if st.session_state.doctor_colors else '#CCCCCC'
                        st.markdown(f"<div style='background: {current_color}; color: white; padding: 8px; border-radius: 5px; text-align: center; margin: 2px;'>{row['Doctor']}</div>", unsafe_allow_html=True)

                    with col4:
                        st.write("**→**")

                    with col5:
                        # Dropdown for reassignment
                        current_doctor = row['Doctor']
                        new_doctor = st.selectbox(
                            "Reassign to:",
                            options=st.session_state.doctors,
                            index=st.session_state.doctors.index(current_doctor) if current_doctor in st.session_state.doctors else 0,
                            key=f"reassign_{idx}_{row['Date']}_{row['Shift']}"
                        )

                        # Check for conflicts
                        if new_doctor != current_doctor:
                            # Check if new doctor already works this day
                            same_day_shifts = st.session_state.schedule_df[
                                (st.session_state.schedule_df['Date'] == row['Date']) &
                                (st.session_state.schedule_df['Doctor'] == new_doctor)
                            ]

                            if len(same_day_shifts) > 0:
                                st.warning(f"⚠️ {new_doctor} already works on {row['Date']}")

                            # Update the schedule
                            st.session_state.schedule_df.loc[idx, 'Doctor'] = new_doctor
                            changes_made = True

                    st.divider()

                if changes_made:
                    st.success("✅ Schedule updated! Changes are automatically saved.")
                    time.sleep(0.5)  # Brief pause to show success message
                    st.rerun()

            else:
                # Display regular table
                st.dataframe(filtered, width='stretch', hide_index=True)

            # Export options
            st.subheader("Export Options")
            col1, col2, col3 = st.columns(3)

            with col1:
                csv = filtered.to_csv(index=False)
                st.download_button("📄 CSV", csv, f"schedule_{year}_{month:02d}.csv", "text/csv", key="export_csv")

            with col2:
                excel = create_excel_export(st.session_state.schedule_df, int(year), month)
                st.download_button("📊 Excel", excel, f"schedule_{year}_{month:02d}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="export_excel")

            with col3:
                ics = create_ics_export(st.session_state.schedule_df)
                st.download_button("📅 Calendar", ics, f"schedule_{year}_{month:02d}.ics", "text/calendar", key="export_ics")

        with tab3:
            # Constraints configuration
            st.subheader("Scheduling Constraints")

            if not st.session_state.doctors:
                st.info("Add team members first")
            else:
                # Month/year for constraints (for days off only)
                col1, col2 = st.columns(2)
                with col1:
                    const_month = st.selectbox("Month:", range(1, 13), index=datetime.now().month-1, format_func=lambda x: calendar.month_name[x], key="const_month")
                with col2:
                    const_year = st.number_input("Year:", min_value=2024, max_value=2030, value=datetime.now().year, key="const_year")

                # Select doctor
                selected_doctor = st.selectbox("Team member:", st.session_state.doctors, key="const_doctor")

                if selected_doctor:
                    # Get doctor's constraints
                    doctor_constraints = st.session_state.constraints.get(selected_doctor, {})
                    month_key = f"{const_year}-{const_month:02d}"
                    month_constraints = doctor_constraints.get(month_key, {})

                    # Days off (month-specific)
                    days_in_month = calendar.monthrange(const_year, const_month)[1]
                    all_dates = [f"{const_year}-{const_month:02d}-{d:02d}" for d in range(1, days_in_month + 1)]
                    days_off = st.multiselect("Days off:", all_dates, default=month_constraints.get('days_off', []), key="days_off")

                    # Fixed shifts (day of week based)
                    st.write("**Fixed Weekly Schedule:**")
                    st.write("*Recurring shifts by day of the week (portable across months)*")

                    current_fixed = doctor_constraints.get('fixed_shifts', {})
                    fixed_shifts = {}

                    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

                    for day in days:
                        # Get available shifts for this day (from shift config)
                        day_shifts = st.session_state.shift_config.get(day, {})
                        shift_options = ['None'] + list(day_shifts.keys())

                        current_value = current_fixed.get(day, 'None')
                        if current_value and current_value not in shift_options:
                            shift_options.append(current_value)

                        selected_shift = st.selectbox(
                            f"{day}:",
                            options=shift_options,
                            index=shift_options.index(current_value) if current_value in shift_options else 0,
                            key=f"fixed_{day}"
                        )

                        if selected_shift != 'None':
                            fixed_shifts[day] = selected_shift

                    # Save
                    if st.button("💾 Save", key="save_constraints"):
                        if selected_doctor not in st.session_state.constraints:
                            st.session_state.constraints[selected_doctor] = {}

                        # Save fixed shifts (day of week based)
                        st.session_state.constraints[selected_doctor]['fixed_shifts'] = fixed_shifts

                        # Save days off (month specific)
                        if month_key not in st.session_state.constraints[selected_doctor]:
                            st.session_state.constraints[selected_doctor][month_key] = {}
                        st.session_state.constraints[selected_doctor][month_key]['days_off'] = days_off

                        st.success("Constraints saved!")

                st.divider()

                # Show all constraints summary
                if st.session_state.constraints:
                    st.subheader("📋 Current Constraints Summary")
                    for doctor, doctor_constraints in st.session_state.constraints.items():
                        with st.expander(f"📝 {doctor}"):
                            # Fixed shifts (day of week)
                            fixed_shifts = doctor_constraints.get('fixed_shifts', {})
                            if fixed_shifts:
                                st.write("**Fixed weekly schedule:**")
                                for day, shift in fixed_shifts.items():
                                    st.write(f"  • {day}: {shift}")

                            # Days off (month specific)
                            has_days_off = False
                            for month_key, month_data in doctor_constraints.items():
                                if month_key.count('-') == 1 and isinstance(month_data, dict):  # YYYY-MM format
                                    days_off = month_data.get('days_off', [])
                                    if days_off:
                                        if not has_days_off:
                                            st.write("**Days off:**")
                                            has_days_off = True
                                        month_name = datetime.strptime(month_key + "-01", "%Y-%m-%d").strftime("%B %Y")
                                        st.write(f"  • {month_name}: {', '.join(days_off)}")

                            # Notes
                            notes = doctor_constraints.get('notes', '')
                            if notes:
                                st.write(f"**Notes:** {notes}")

                            if not fixed_shifts and not has_days_off and not notes:
                                st.write("No constraints set")

            st.divider()

            # YAML Editor
            st.subheader("Advanced Configuration Editor")

            if st.button("📝 Open Config Editor", key="open_editor"):
                st.session_state.show_editor = not st.session_state.get('show_editor', False)

            if st.session_state.get('show_editor', False):
                st.write("**Edit Full Configuration (YAML format):**")

                # Get current config as YAML
                current_yaml = export_config()

                # YAML editor with more space
                edited_yaml = st.text_area(
                    "Configuration:",
                    value=current_yaml,
                    height=400,
                    key="yaml_editor",
                    help="Edit the complete configuration in YAML format. Includes team members, shifts, and constraints. Be careful with indentation!"
                )

                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("💾 Apply Changes", key="apply_yaml"):
                        try:
                            success, msg = import_config(edited_yaml)
                            if success:
                                st.success("Configuration updated from YAML!")
                                st.rerun()
                            else:
                                st.error(f"Error applying changes: {msg}")
                        except Exception as e:
                            st.error(f"Error parsing YAML: {str(e)}")

                with col2:
                    if st.button("🔄 Reset to Current", key="reset_yaml"):
                        st.rerun()

                with col3:
                    # Download current YAML
                    st.download_button(
                        "📥 Download YAML",
                        current_yaml,
                        f"tool_sched_config_{datetime.now().strftime('%Y%m%d')}.yaml",
                        "text/yaml",
                        key="download_yaml_editor"
                    )

                st.info("💡 **Tip:** This editor shows the complete configuration including example constraints with set schedules, days off requests, and notes. Changes here affect everything: team members, shift patterns, and all constraints.")

        with tab4:
            # Analytics
            st.subheader("Schedule Analytics")

            # Workload distribution
            shifts_per_doctor = st.session_state.schedule_df['Doctor'].value_counts()
            st.bar_chart(shifts_per_doctor)

            # Balance check
            if len(shifts_per_doctor) > 0:
                min_shifts = shifts_per_doctor.min()
                max_shifts = shifts_per_doctor.max()
                diff = max_shifts - min_shifts

                if diff <= 1:
                    st.success(f"✅ Well balanced (max difference: {diff})")
                elif diff <= 2:
                    st.info(f"📊 Reasonably balanced (max difference: {diff})")
                else:
                    st.warning(f"⚠️ Imbalanced (max difference: {diff})")

    else:
        st.info("👈 Configure your team and generate a schedule to get started!")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.write("**👥 Team Management**")
            st.write("Add team members with random color assignment")
        with col2:
            st.write("**📋 Constraints**")
            st.write("Set days off and fixed shifts for each team member")
        with col3:
            st.write("**📊 Export Options**")
            st.write("Download as CSV, Excel, or calendar file")

if __name__ == "__main__":
    main()
