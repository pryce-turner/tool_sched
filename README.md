# 🛠️ Tool Sched

A collaborative scheduling system for any team built with Streamlit. Generate fair, balanced schedules while respecting team member constraints and preferences.

![Tool Sched Interface](https://img.shields.io/badge/Built%20with-Streamlit-red?style=flat-square&logo=streamlit)
![Python](https://img.shields.io/badge/Python-3.7+-blue?style=flat-square&logo=python)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

## ✨ Features

### 🎯 Core Functionality
- **Smart Schedule Generation**: Automatically creates balanced schedules with minimal manual intervention
- **Constraint Management**: Support for fixed weekly schedules, days off requests, and custom availability
- **Real-time Editing**: Modify shift assignments with automatic conflict detection
- **Visual Calendar**: Interactive calendar view with color-coded assignments

### 📊 Advanced Features
- **Analytics Dashboard**: Workload distribution analysis and balance checking
- **Multiple Export Formats**: CSV, Excel, and ICS calendar exports
- **Configuration Management**: Import/export team setups and constraints via YAML
- **Conflict Detection**: Automatic warnings for scheduling conflicts

### 🎨 User Experience
- **Color-coded Team Members**: Visual distinction with randomly generated colors
- **Responsive Design**: Works on desktop and mobile devices
- **Intuitive Interface**: Clean, modern UI with clear navigation

## 🚀 Quick Start

### Prerequisites
- Python 3.7 or higher
- pip package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/tool-sched.git
   cd tool-sched
   ```

2. **Install dependencies**
   ```bash
   pip install streamlit pandas pyyaml openpyxl
   ```

3. **Run the application**
   ```bash
   streamlit run tool_sched.py
   ```

4. **Open your browser** to `http://localhost:8501`

## 📖 Usage Guide

### Getting Started

1. **Load Default Team** (optional): Click "Load Default Team" to start with sample data
2. **Add Team Members**: Use the sidebar to add your team members
3. **Configure Constraints**: Set up days off and fixed weekly schedules
4. **Generate Schedule**: Select month/year and click "Generate"

### Setting Up Constraints

#### Fixed Weekly Schedules
Perfect for team members who work the same shifts each week:
- Monday: 7a-7p (day shift)
- Wednesday: 7a-7p (day shift)
- Friday: 7p-7a (night shift)

#### Days Off Requests
Specify exact dates when team members are unavailable:
- Vacation days
- Personal appointments
- Training sessions

### Editing Schedules

1. Navigate to the **Table** tab
2. Enable **Edit Mode**
3. Use dropdowns to reassign shifts
4. Automatic conflict detection warns of double-bookings

### Exporting Data

Choose from multiple export formats:
- **CSV**: Simple spreadsheet format
- **Excel**: Multi-sheet workbook with calendar view
- **ICS**: Import directly into calendar applications

## 🔧 Configuration

### YAML Configuration Format

Tool Sched uses YAML for importing/exporting configurations:

```yaml
team_members:
  - Dr. Chen
  - Dr. Patel
  - Dr. Johnson

constraints:
  Dr. Chen:
    fixed_shifts:
      Monday: "7a-7p"
      Wednesday: "7a-7p"
      Friday: "7a-7p"
    2024-12:
      days_off:
        - "2024-12-25"
        - "2024-12-26"
    notes: "Prefers day shifts, holiday vacation"

shift_configuration:
  Monday:
    "7a-7p":
      start: "07:00"
      end: "19:00"
      hours: 12
    "7p-7a":
      start: "19:00"
      end: "07:00"
      hours: 12
```

### Customizing Shift Patterns

Modify the `DEFAULT_SHIFTS` configuration to match your organization's needs:
- Different shift times
- Varying shifts by day of week
- Custom shift names and durations

## 🏗️ Architecture

### Core Components

- **Session Management**: Streamlit session state for data persistence
- **Schedule Generator**: Smart algorithm for balanced shift distribution
- **Constraint Engine**: Flexible system for availability rules
- **Export Engine**: Multiple format support with formatting

### Key Files

- `tool_sched.py`: Main application file
- Configuration exports: YAML files for team/constraint backup

## 🛠️ Development

### Adding New Features

The codebase is modular and extensible:

1. **New Shift Types**: Modify `DEFAULT_SHIFTS` configuration
2. **Additional Constraints**: Extend the constraint checking functions
3. **Export Formats**: Add new functions to the export engine
4. **UI Improvements**: Leverage Streamlit's component system

### Testing

Run the application locally and test with sample data:

```bash
# Start with default team
streamlit run tool_sched.py

# Test constraint scenarios
# Test export functionality
# Verify schedule balance
```

## 📊 Use Cases

### Healthcare Teams
- Doctor shift scheduling
- Nurse rotation management
- Specialist coverage

### Retail Operations
- Store manager schedules
- Sales associate shifts
- Holiday coverage planning

### Manufacturing
- Supervisor rotations
- Equipment operator shifts
- Maintenance crew scheduling

### General Business
- Support team coverage
- Project manager assignments
- Training schedule coordination

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Test thoroughly**
5. **Submit a pull request**

### Contribution Ideas
- Additional export formats (PDF, JSON)
- Advanced constraint types (shift preferences, overtime limits)
- Integration with external calendar systems
- Mobile app version
- Advanced analytics and reporting

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/) for the amazing web app framework
- Uses [Pandas](https://pandas.pydata.org/) for data manipulation
- Calendar functionality powered by Python's built-in `calendar` module
- YAML configuration support via [PyYAML](https://pyyaml.org/)

## 📞 Support

Having issues or questions?

- **Create an Issue**: Use GitHub issues for bug reports and feature requests
- **Discussions**: Join conversations in GitHub Discussions
- **Documentation**: Check the in-app help and this README

---

### Designed with ❤️ by Pryce in California
##### Assembled by Claude in a datacenter somewhere 🤷‍♂️
