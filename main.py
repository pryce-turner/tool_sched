import streamlit as st
import pandas as pd
import calendar
import time
from datetime import datetime

# Import all utility functions
from scheduling_utils import (
    DEFAULT_DOCTORS, DEFAULT_SHIFTS, init_session, generate_colors,
    get_shifts_for_day, get_doctor_constraints, is_available,
    get_fixed_shift, generate_schedule, export_config, import_config,
    create_excel_export, create_ics_export
)

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