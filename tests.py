import pytest
import pandas as pd
import yaml
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
import calendar

# Import functions from scheduling_utils
from scheduling_utils import (
    generate_colors, get_shifts_for_day, get_doctor_constraints,
    is_available, get_fixed_shift, generate_schedule,
    export_config, import_config, create_excel_export,
    create_ics_export, DEFAULT_DOCTORS, DEFAULT_SHIFTS
)


@pytest.fixture
def mock_session_state():
    """Mock streamlit session state"""
    with patch('scheduling_utils.st') as mock_st:
        # Create a mock object that behaves like session_state with attribute access
        session_state = Mock()
        session_state.doctors = ['Chen', 'Patel', 'Johnson']
        session_state.doctor_colors = {}
        session_state.shift_config = DEFAULT_SHIFTS.copy()
        session_state.constraints = {}
        session_state.schedule_df = pd.DataFrame()
        session_state.schedule_generated = False

        mock_st.session_state = session_state
        yield session_state


class TestGenerateColors:
    def test_generate_colors_basic(self):
        doctors = ["Chen", "Patel", "Johnson"]
        colors = generate_colors(doctors)

        assert len(colors) == 3
        assert all(doctor in colors for doctor in doctors)
        assert all(color.startswith("#") for color in colors.values())
        assert all(len(color) == 7 for color in colors.values())  # Hex color format

    def test_valdez_special_color(self):
        doctors = ["Chen", "Valdez", "Johnson"]
        colors = generate_colors(doctors)

        assert colors["Valdez"] == "#FD79A8"
        assert colors["Chen"] != "#FD79A8"
        assert colors["Johnson"] != "#FD79A8"

    def test_generate_colors_empty_list(self):
        colors = generate_colors([])
        assert colors == {}

    def test_generate_colors_many_doctors(self):
        # Test with more doctors than available colors
        doctors = [f"Doctor_{i}" for i in range(25)]
        colors = generate_colors(doctors)

        assert len(colors) == 25
        # Colors should wrap around
        assert len(set(colors.values())) <= 20  # There are 20 predefined colors


class TestGetShiftsForDay:
    def test_get_shifts_for_day_monday(self, mock_session_state):
        date = datetime(2024, 1, 1)  # This is a Monday
        shifts = get_shifts_for_day(date)

        expected = DEFAULT_SHIFTS["Monday"]
        assert shifts == expected
        assert "7a-7p" in shifts
        assert "12p-12a" in shifts
        assert "7p-7a" in shifts

    def test_get_shifts_for_day_tuesday(self, mock_session_state):
        date = datetime(2024, 1, 2)  # This is a Tuesday
        shifts = get_shifts_for_day(date)

        expected = DEFAULT_SHIFTS["Tuesday"]
        assert shifts == expected
        assert "7a-7p" in shifts
        assert "12p-12a" in shifts
        assert "7p-7a" not in shifts  # Tuesday doesn't have night shift

    def test_get_shifts_for_day_weekend(self, mock_session_state):
        date = datetime(2024, 1, 6)  # This is a Saturday
        shifts = get_shifts_for_day(date)

        expected = DEFAULT_SHIFTS["Saturday"]
        assert shifts == expected
        assert len(shifts) == 4  # Weekend has 4 shifts


class TestGetDoctorConstraints:
    def test_get_doctor_constraints_empty(self, mock_session_state):
        constraints = get_doctor_constraints("Chen", 2024, 1)

        assert constraints == {
            'fixed_shifts': {},
            'days_off': []
        }

    def test_get_doctor_constraints_with_data(self, mock_session_state):
        mock_session_state.constraints = {
            'Chen': {
                'fixed_shifts': {'Monday': '7a-7p'},
                '2024-01': {'days_off': ['2024-01-15']}
            }
        }

        constraints = get_doctor_constraints("Chen", 2024, 1)

        assert constraints['fixed_shifts'] == {'Monday': '7a-7p'}
        assert constraints['days_off'] == ['2024-01-15']

    def test_get_doctor_constraints_different_month(self, mock_session_state):
        mock_session_state.constraints = {
            'Chen': {
                'fixed_shifts': {'Monday': '7a-7p'},
                '2024-01': {'days_off': ['2024-01-15']},
                '2024-02': {'days_off': ['2024-02-10']}
            }
        }

        constraints = get_doctor_constraints("Chen", 2024, 2)

        assert constraints['fixed_shifts'] == {'Monday': '7a-7p'}
        assert constraints['days_off'] == ['2024-02-10']


class TestIsAvailable:
    def test_is_available_no_constraints(self, mock_session_state):
        assert is_available("Chen", "2024-01-01", "7a-7p", 2024, 1) == True

    def test_is_available_day_off(self, mock_session_state):
        mock_session_state.constraints = {
            'Chen': {
                '2024-01': {'days_off': ['2024-01-01']}
            }
        }

        assert is_available("Chen", "2024-01-01", "7a-7p", 2024, 1) == False
        assert is_available("Chen", "2024-01-02", "7a-7p", 2024, 1) == True

    def test_is_available_fixed_shift_match(self, mock_session_state):
        mock_session_state.constraints = {
            'Chen': {
                'fixed_shifts': {'Monday': '7a-7p'}
            }
        }

        # Monday 2024-01-01
        assert is_available("Chen", "2024-01-01", "7a-7p", 2024, 1) == True
        assert is_available("Chen", "2024-01-01", "12p-12a", 2024, 1) == False

    def test_is_available_fixed_shift_different_day(self, mock_session_state):
        mock_session_state.constraints = {
            'Chen': {
                'fixed_shifts': {'Monday': '7a-7p'}
            }
        }

        # Tuesday 2024-01-02 - no fixed shift, so available for any
        assert is_available("Chen", "2024-01-02", "7a-7p", 2024, 1) == True
        assert is_available("Chen", "2024-01-02", "12p-12a", 2024, 1) == True


class TestGetFixedShift:
    def test_get_fixed_shift_none(self, mock_session_state):
        shift = get_fixed_shift("Chen", "2024-01-01", 2024, 1)
        assert shift is None

    def test_get_fixed_shift_exists(self, mock_session_state):
        mock_session_state.constraints = {
            'Chen': {
                'fixed_shifts': {'Monday': '7a-7p', 'Wednesday': '7p-7a'}
            }
        }

        # Monday 2024-01-01
        shift = get_fixed_shift("Chen", "2024-01-01", 2024, 1)
        assert shift == "7a-7p"

        # Wednesday 2024-01-03
        shift = get_fixed_shift("Chen", "2024-01-03", 2024, 1)
        assert shift == "7p-7a"

        # Tuesday 2024-01-02 (no fixed shift)
        shift = get_fixed_shift("Chen", "2024-01-02", 2024, 1)
        assert shift is None


class TestGenerateSchedule:
    def test_generate_schedule_basic(self, mock_session_state):
        doctors = ["Chen", "Patel"]
        df = generate_schedule(2024, 1, doctors)

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert all(col in df.columns for col in ['Date', 'Day', 'Shift', 'Start_Time', 'End_Time', 'Doctor'])
        assert all(doctor in df['Doctor'].values for doctor in doctors)

        # Check that dates are in January 2024
        dates = pd.to_datetime(df['Date'])
        assert all(date.month == 1 and date.year == 2024 for date in dates)

    def test_generate_schedule_with_fixed_shifts(self, mock_session_state):
        mock_session_state.constraints = {
            'Chen': {
                'fixed_shifts': {'Monday': '7a-7p'}
            }
        }

        doctors = ["Chen", "Patel"]
        df = generate_schedule(2024, 1, doctors)

        # Check that Chen gets Monday 7a-7p shifts
        monday_7a7p = df[(df['Day'] == 'Monday') & (df['Shift'] == '7a-7p')]
        assert all(doctor == 'Chen' for doctor in monday_7a7p['Doctor'])

    def test_generate_schedule_with_days_off(self, mock_session_state):
        mock_session_state.constraints = {
            'Chen': {
                '2024-01': {'days_off': ['2024-01-01']}
            }
        }

        doctors = ["Chen", "Patel"]
        df = generate_schedule(2024, 1, doctors)

        # Chen should not work on 2024-01-01
        jan_1_shifts = df[df['Date'] == '2024-01-01']
        assert all(doctor != 'Chen' for doctor in jan_1_shifts['Doctor'])

    def test_generate_schedule_workload_balance(self, mock_session_state):
        doctors = ["Chen", "Patel", "Johnson"]
        df = generate_schedule(2024, 1, doctors)

        # Check that workload is reasonably balanced
        shift_counts = df['Doctor'].value_counts()
        max_shifts = shift_counts.max()
        min_shifts = shift_counts.min()

        # Difference should be reasonable (allowing some imbalance due to randomness)
        assert max_shifts - min_shifts <= 3

    def test_generate_schedule_fixed_shifts_override_days_off(self, mock_session_state):
        """Test that fixed shifts take precedence over days off requests"""
        mock_session_state.constraints = {
            'Chen': {
                'fixed_shifts': {'Monday': '7a-7p'},
                '2024-01': {'days_off': ['2024-01-01', '2024-01-15']}  # Both Mondays
            }
        }

        doctors = ["Chen", "Patel"]
        df = generate_schedule(2024, 1, doctors)

        # Chen should still work Mondays despite requesting them off (fixed shift takes precedence)
        monday_7a7p = df[(df['Day'] == 'Monday') & (df['Shift'] == '7a-7p')]
        assert all(doctor == 'Chen' for doctor in monday_7a7p['Doctor'])

        # But Chen should not work other shifts on those days
        jan_1_other_shifts = df[(df['Date'] == '2024-01-01') & (df['Shift'] != '7a-7p')]
        jan_15_other_shifts = df[(df['Date'] == '2024-01-15') & (df['Shift'] != '7a-7p')]

        if len(jan_1_other_shifts) > 0:
            assert all(doctor != 'Chen' for doctor in jan_1_other_shifts['Doctor'])
        if len(jan_15_other_shifts) > 0:
            assert all(doctor != 'Chen' for doctor in jan_15_other_shifts['Doctor'])


class TestExportConfig:
    def test_export_config_basic(self, mock_session_state):
        yaml_content = export_config()

        # Should be valid YAML
        config = yaml.safe_load(yaml_content)

        assert 'team_members' in config
        assert 'shift_configuration' in config
        assert 'constraints' in config
        assert 'export_date' in config
        assert 'examples' in config

    def test_export_config_with_constraints(self, mock_session_state):
        mock_session_state.constraints = {
            'Chen': {
                'fixed_shifts': {'Monday': '7a-7p'},
                '2024-01': {'days_off': ['2024-01-15']}
            }
        }

        yaml_content = export_config()
        config = yaml.safe_load(yaml_content)

        assert config['constraints']['Chen']['fixed_shifts']['Monday'] == '7a-7p'
        assert '2024-01-15' in config['constraints']['Chen']['2024-01']['days_off']

    @patch('scheduling_utils.datetime')
    def test_export_config_generates_examples(self, mock_datetime, mock_session_state):
        # Mock datetime.now() to return a fixed date
        mock_datetime.now.return_value = datetime(2024, 1, 15)

        # Clear existing constraints
        mock_session_state.constraints = {}
        mock_session_state.doctors = ['Chen', 'Patel', 'Johnson']

        yaml_content = export_config()
        config = yaml.safe_load(yaml_content)

        # Should generate example constraints
        assert len(config['constraints']) == 3
        assert 'Chen' in config['constraints']
        assert 'fixed_shifts' in config['constraints']['Chen']


class TestImportConfig:
    def test_import_config_valid_yaml(self, mock_session_state):
        yaml_content = """
team_members:
  - Chen
  - Patel
shift_configuration:
  Monday:
    "7a-7p":
      start: "07:00"
      end: "19:00"
      hours: 12
constraints:
  Chen:
    fixed_shifts:
      Monday: "7a-7p"
"""

        success, message = import_config(yaml_content)

        assert success == True
        assert "Team members" in message
        assert mock_session_state.doctors == ['Chen', 'Patel']

    def test_import_config_invalid_yaml(self, mock_session_state):
        invalid_yaml = "invalid: yaml: content: ["

        success, message = import_config(invalid_yaml)

        assert success == False
        assert "YAML parsing error" in message

    def test_import_config_empty_data(self, mock_session_state):
        empty_yaml = "empty: {}"

        success, message = import_config(empty_yaml)

        assert success == False
        assert "No valid configuration data found" in message


class TestCreateExcelExport:
    def test_create_excel_export_basic(self):
        # Create sample dataframe
        df = pd.DataFrame([
            {
                'Date': '2024-01-01',
                'Day': 'Monday',
                'Shift': '7a-7p',
                'Start_Time': '07:00',
                'End_Time': '19:00',
                'Doctor': 'Chen'
            },
            {
                'Date': '2024-01-01',
                'Day': 'Monday',
                'Shift': '12p-12a',
                'Start_Time': '12:00',
                'End_Time': '00:00',
                'Doctor': 'Patel'
            }
        ])

        buffer = create_excel_export(df, 2024, 1)

        assert isinstance(buffer, BytesIO)
        assert buffer.getvalue()  # Should have content

    def test_create_excel_export_with_multiple_days(self):
        df = pd.DataFrame([
            {
                'Date': '2024-01-01',
                'Day': 'Monday',
                'Shift': '7a-7p',
                'Start_Time': '07:00',
                'End_Time': '19:00',
                'Doctor': 'Chen'
            },
            {
                'Date': '2024-01-02',
                'Day': 'Tuesday',
                'Shift': '7a-7p',
                'Start_Time': '07:00',
                'End_Time': '19:00',
                'Doctor': 'Patel'
            }
        ])

        buffer = create_excel_export(df, 2024, 1)

        assert isinstance(buffer, BytesIO)
        assert buffer.getvalue()


class TestCreateIcsExport:
    def test_create_ics_export_basic(self):
        df = pd.DataFrame([
            {
                'Date': '2024-01-01',
                'Day': 'Monday',
                'Shift': '7a-7p',
                'Start_Time': '07:00',
                'End_Time': '19:00',
                'Doctor': 'Chen'
            }
        ])

        ics_content = create_ics_export(df)

        assert "BEGIN:VCALENDAR" in ics_content
        assert "END:VCALENDAR" in ics_content
        assert "BEGIN:VEVENT" in ics_content
        assert "END:VEVENT" in ics_content
        assert "Chen - 7a-7p" in ics_content
        assert "20240101T070000" in ics_content  # Start time
        assert "20240101T190000" in ics_content  # End time

    def test_create_ics_export_overnight_shift(self):
        df = pd.DataFrame([
            {
                'Date': '2024-01-01',
                'Day': 'Monday',
                'Shift': '7p-7a',
                'Start_Time': '19:00',
                'End_Time': '07:00',
                'Doctor': 'Chen'
            }
        ])

        ics_content = create_ics_export(df)

        assert "20240101T190000" in ics_content  # Start time (7 PM Jan 1)
        assert "20240102T070000" in ics_content  # End time (7 AM Jan 2)

    def test_create_ics_export_multiple_shifts(self):
        df = pd.DataFrame([
            {
                'Date': '2024-01-01',
                'Day': 'Monday',
                'Shift': '7a-7p',
                'Start_Time': '07:00',
                'End_Time': '19:00',
                'Doctor': 'Chen'
            },
            {
                'Date': '2024-01-02',
                'Day': 'Tuesday',
                'Shift': '12p-12a',
                'Start_Time': '12:00',
                'End_Time': '00:00',
                'Doctor': 'Patel'
            }
        ])

        ics_content = create_ics_export(df)

        # Should have two events
        assert ics_content.count("BEGIN:VEVENT") == 2
        assert ics_content.count("END:VEVENT") == 2
        assert "Chen - 7a-7p" in ics_content
        assert "Patel - 12p-12a" in ics_content


class TestDefaultValues:
    def test_default_doctors(self):
        assert len(DEFAULT_DOCTORS) == 5
        assert "Chen" in DEFAULT_DOCTORS
        assert "Valdez" in DEFAULT_DOCTORS

    def test_default_shifts_structure(self):
        assert len(DEFAULT_SHIFTS) == 7  # All days of the week

        for day, shifts in DEFAULT_SHIFTS.items():
            assert day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

            for shift_name, shift_data in shifts.items():
                assert 'start' in shift_data
                assert 'end' in shift_data
                assert 'hours' in shift_data
                assert shift_data['hours'] == 12  # All shifts are 12 hours

    def test_default_shifts_weekend_more_shifts(self):
        # Weekend days should have more shift options
        weekend_shifts = len(DEFAULT_SHIFTS['Saturday'])
        weekday_shifts = len(DEFAULT_SHIFTS['Tuesday'])

        assert weekend_shifts > weekday_shifts


# Integration tests
class TestIntegration:
    def test_full_workflow(self, mock_session_state):
        """Test a complete workflow from configuration to schedule generation"""
        # Set up doctors and constraints
        doctors = ["Chen", "Patel", "Johnson"]
        mock_session_state.doctors = doctors
        mock_session_state.constraints = {
            'Chen': {
                'fixed_shifts': {'Monday': '7a-7p'},
                '2024-01': {'days_off': ['2024-01-16']}  # Tuesday instead of Monday
            }
        }

        # Generate schedule
        df = generate_schedule(2024, 1, doctors)

        # Verify constraints are respected
        monday_7a7p = df[(df['Day'] == 'Monday') & (df['Shift'] == '7a-7p')]
        assert all(doctor == 'Chen' for doctor in monday_7a7p['Doctor'])

        jan_16_shifts = df[df['Date'] == '2024-01-16']  # Tuesday - Chen should be off
        assert all(doctor != 'Chen' for doctor in jan_16_shifts['Doctor'])

        # Export and re-import configuration
        yaml_content = export_config()

        # Clear state
        mock_session_state.doctors = []
        mock_session_state.constraints = {}

        # Import
        success, message = import_config(yaml_content)
        assert success
        assert mock_session_state.doctors == doctors

    def test_schedule_export_formats(self, mock_session_state):
        """Test that all export formats work with generated schedule"""
        doctors = ["Chen", "Patel"]
        df = generate_schedule(2024, 1, doctors)

        # Excel export
        excel_buffer = create_excel_export(df, 2024, 1)
        assert excel_buffer.getvalue()

        # ICS export
        ics_content = create_ics_export(df)
        assert "BEGIN:VCALENDAR" in ics_content
        assert "END:VCALENDAR" in ics_content

        # CSV export (pandas built-in)
        csv_content = df.to_csv(index=False)
        assert "Date,Day,Shift" in csv_content
