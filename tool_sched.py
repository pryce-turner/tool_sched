import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta
from collections import defaultdict
import calendar
import numpy as np
import json
import time
from io import BytesIO
from openpyxl.styles import Alignment

# Default configuration
DEFAULT_DOCTORS = ["Dr. Smith", "Dr. Johnson", "Dr. Williams", "Dr. Brown", "Dr. Valdez"]

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
    return st.session_state.constraints.get(month_key, {}).get(doctor, {
        'fixed_shifts': [],
        'days_off': [],
        'preferred_shifts': []
    })

def is_available(doctor, date_str, shift_name, year, month):
    """Check if doctor is available"""
    constraints = get_doctor_constraints(doctor, year, month)

    # Check days off
    if date_str in constraints.get('days_off', []):
        return False

    # Check fixed shifts
    for fixed in constraints.get('fixed_shifts', []):
        if fixed['date'] == date_str and fixed['shift'] != shift_name:
            return False

    return True

def get_fixed_shift(doctor, date_str, year, month):
    """Get fixed shift for doctor on date"""
    constraints = get_doctor_constraints(doctor, year, month)
    for fixed in constraints.get('fixed_shifts', []):
        if fixed['date'] == date_str:
            return fixed['shift']
    return None

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
    """Export configuration as JSON with examples"""
    # Create example constraints if none exist
    example_constraints = {}
    if not st.session_state.constraints and st.session_state.doctors:
        current_date = datetime.now()
        month_key = f"{current_date.year}-{current_date.month:02d}"
        days_in_month = calendar.monthrange(current_date.year, current_date.month)[1]

        example_constraints[month_key] = {}

        # Example for first doctor - has set schedule
        if len(st.session_state.doctors) > 0:
            doctor1 = st.session_state.doctors[0]
            example_constraints[month_key][doctor1] = {
                "fixed_shifts": [
                    {"date": f"{current_date.year}-{current_date.month:02d}-01", "shift": "7a-7p"},
                    {"date": f"{current_date.year}-{current_date.month:02d}-08", "shift": "7a-7p"},
                    {"date": f"{current_date.year}-{current_date.month:02d}-15", "shift": "7a-7p"},
                    {"date": f"{current_date.year}-{current_date.month:02d}-22", "shift": "7a-7p"}
                ],
                "days_off": [
                    f"{current_date.year}-{current_date.month:02d}-05",
                    f"{current_date.year}-{current_date.month:02d}-12"
                ],
                "preferred_shifts": ["7a-7p", "12p-12a"],
                "notes": "Works every Monday, prefers day shifts"
            }

        # Example for second doctor - has days off requests
        if len(st.session_state.doctors) > 1:
            doctor2 = st.session_state.doctors[1]
            example_constraints[month_key][doctor2] = {
                "fixed_shifts": [],
                "days_off": [
                    f"{current_date.year}-{current_date.month:02d}-10",
                    f"{current_date.year}-{current_date.month:02d}-11",
                    f"{current_date.year}-{current_date.month:02d}-25"
                ],
                "preferred_shifts": ["10a-10p", "2p-2a"],
                "notes": "Prefers weekend shifts, vacation mid-month"
            }

        # Example for third doctor - night shift specialist
        if len(st.session_state.doctors) > 2:
            doctor3 = st.session_state.doctors[2]
            example_constraints[month_key][doctor3] = {
                "fixed_shifts": [
                    {"date": f"{current_date.year}-{current_date.month:02d}-02", "shift": "7p-7a"},
                    {"date": f"{current_date.year}-{current_date.month:02d}-09", "shift": "7p-7a"},
                    {"date": f"{current_date.year}-{current_date.month:02d}-16", "shift": "7p-7a"},
                    {"date": f"{current_date.year}-{current_date.month:02d}-23", "shift": "7p-7a"}
                ],
                "days_off": [],
                "preferred_shifts": ["7p-7a", "2p-2a"],
                "notes": "Night shift specialist, works every Tuesday night"
            }

    config = {
        'team_members': st.session_state.doctors,
        'shift_configuration': st.session_state.shift_config,
        'constraints': st.session_state.constraints or example_constraints,
        'export_date': datetime.now().isoformat(),
        'examples': {
            'description': 'This configuration includes example constraints',
            'constraint_types': {
                'fixed_shifts': 'Specific shift assignments that must be honored',
                'days_off': 'Dates when the team member is unavailable',
                'preferred_shifts': 'Shift types the team member prefers to work',
                'notes': 'Additional information about the team member'
            }
        }
    }
    return json.dumps(config, indent=2)

def json_to_yaml(json_str):
    """Convert JSON to YAML-style format"""
    try:
        data = json.loads(json_str)
        return dict_to_yaml(data, 0)
    except:
        return json_str

def dict_to_yaml(obj, indent=0):
    """Convert dictionary to YAML format"""
    yaml_str = ""
    indent_str = "  " * indent

    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                yaml_str += f"{indent_str}{key}:\n"
                yaml_str += dict_to_yaml(value, indent + 1)
            else:
                yaml_str += f"{indent_str}{key}: {json.dumps(value) if isinstance(value, str) else value}\n"
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                yaml_str += f"{indent_str}-\n"
                yaml_str += dict_to_yaml(item, indent + 1)
            else:
                yaml_str += f"{indent_str}- {json.dumps(item) if isinstance(item, str) else item}\n"

    return yaml_str

def yaml_to_json(yaml_str):
    """Convert YAML-style format to JSON"""
    try:
        # Simple YAML to JSON conversion for basic structures
        # This is a simplified parser - for production use a proper YAML library
        lines = yaml_str.strip().split('\n')
        result = {}
        current_dict = result
        dict_stack = [result]
        key_stack = []

        for line in lines:
            if line.strip().startswith('#') or not line.strip():
                continue

            indent_level = (len(line) - len(line.lstrip())) // 2
            content = line.strip()

            if ':' in content and not content.startswith('-'):
                key, value = content.split(':', 1)
                key = key.strip().strip('"')
                value = value.strip()

                # Adjust stack based on indent level
                while len(dict_stack) > indent_level + 1:
                    dict_stack.pop()
                    key_stack.pop()

                current_dict = dict_stack[-1]

                if value:
                    # Simple value
                    try:
                        if value.startswith('"') and value.endswith('"'):
                            current_dict[key] = value[1:-1]
                        elif value.lower() in ['true', 'false']:
                            current_dict[key] = value.lower() == 'true'
                        elif value.isdigit():
                            current_dict[key] = int(value)
                        else:
                            current_dict[key] = value
                    except:
                        current_dict[key] = value
                else:
                    # Nested object
                    current_dict[key] = {}
                    dict_stack.append(current_dict[key])
                    key_stack.append(key)

        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error parsing YAML: {str(e)}"

def import_config(content):
    """Import configuration from JSON or YAML"""
    try:
        # Try JSON first
        if content.strip().startswith('{'):
            config = json.loads(content)
        else:
            # Convert YAML to JSON first
            json_content = yaml_to_json(content)
            config = json.loads(json_content)

        if 'team_members' in config:
            st.session_state.doctors = config['team_members']
            st.session_state.doctor_colors = generate_colors(st.session_state.doctors)

        if 'shift_configuration' in config:
            st.session_state.shift_config = config['shift_configuration']

        if 'constraints' in config:
            st.session_state.constraints = config['constraints']

        return True, "Configuration imported successfully!"
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
            config_json = export_config()
            st.download_button(
                "📥 Export Config (JSON)",
                config_json,
                f"tool_sched_config_{datetime.now().strftime('%Y%m%d')}.json",
                "application/json",
                key="export_config"
            )

            config_yaml = json_to_yaml(config_json)
            st.download_button(
                "📥 Export Config (YAML)",
                config_yaml,
                f"tool_sched_config_{datetime.now().strftime('%Y%m%d')}.yaml",
                "text/yaml",
                key="export_yaml"
            )

        # Import
        uploaded = st.file_uploader("📤 Import Config", type=['json', 'yaml', 'yml'], key="import_config")
        if uploaded:
            content = uploaded.read().decode('utf-8')
            success, msg = import_config(content)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

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
            # Constraints configuration with YAML editor
            st.subheader("Scheduling Constraints")

            if not st.session_state.doctors:
                st.info("Add team members first")
            else:
                # Month/year for constraints
                col1, col2 = st.columns(2)
                with col1:
                    const_month = st.selectbox("Month:", range(1, 13), index=datetime.now().month-1, format_func=lambda x: calendar.month_name[x], key="const_month")
                with col2:
                    const_year = st.number_input("Year:", min_value=2024, max_value=2030, value=datetime.now().year, key="const_year")

                # Select doctor
                selected_doctor = st.selectbox("Team member:", st.session_state.doctors, key="const_doctor")

                if selected_doctor:
                    constraints = get_doctor_constraints(selected_doctor, const_year, const_month)

                    # Days off
                    days_in_month = calendar.monthrange(const_year, const_month)[1]
                    all_dates = [f"{const_year}-{const_month:02d}-{d:02d}" for d in range(1, days_in_month + 1)]

                    days_off = st.multiselect("Days off:", all_dates, default=constraints.get('days_off', []), key="days_off")

                    # Fixed shifts
                    st.write("**Fixed Shifts:**")
                    fixed_shifts = constraints.get('fixed_shifts', []).copy()

                    # Show existing
                    for i, fs in enumerate(fixed_shifts):
                        col1, col2, col3 = st.columns([2, 2, 1])
                        with col1:
                            st.write(fs['date'])
                        with col2:
                            st.write(fs['shift'])
                        with col3:
                            if st.button("🗑️", key=f"del_fixed_{i}"):
                                fixed_shifts.pop(i)
                                st.rerun()

                    # Add new
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        new_date = st.selectbox("Date:", all_dates, key="new_fixed_date")
                    with col2:
                        date_obj = datetime.strptime(new_date, "%Y-%m-%d")
                        shifts_available = list(get_shifts_for_day(date_obj).keys())
                        if shifts_available:
                            new_shift = st.selectbox("Shift:", shifts_available, key="new_fixed_shift")
                        else:
                            st.write("No shifts configured")
                            new_shift = None
                    with col3:
                        if st.button("➕", key="add_fixed") and new_shift:
                            fixed_shifts.append({'date': new_date, 'shift': new_shift})
                            st.rerun()

                    # Save
                    if st.button("💾 Save", key="save_constraints"):
                        month_key = f"{const_year}-{const_month:02d}"
                        if month_key not in st.session_state.constraints:
                            st.session_state.constraints[month_key] = {}
                        st.session_state.constraints[month_key][selected_doctor] = {
                            'fixed_shifts': fixed_shifts,
                            'days_off': days_off,
                            'preferred_shifts': []
                        }
                        st.success("Constraints saved!")

            st.divider()

            # YAML Editor (moved from sidebar)
            st.subheader("Advanced Configuration Editor")

            if st.button("📝 Open Config Editor", key="open_editor"):
                st.session_state.show_editor = not st.session_state.get('show_editor', False)

            if st.session_state.get('show_editor', False):
                st.write("**Edit Full Configuration (YAML format):**")

                # Get current config as YAML
                current_config = export_config()
                current_yaml = json_to_yaml(current_config)

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
                            # Convert YAML back to JSON
                            json_content = yaml_to_json(edited_yaml)
                            success, msg = import_config(json_content)
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

                st.info("💡 **Tip:** This editor shows the complete configuration including example constraints with set schedules, days off requests, and preferred shifts. Changes here affect everything: team members, shift patterns, and all constraints.")

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
