# Moodle Selenium Test Suite

Automated UI testing suite for the **Moodle LMS** using Selenium WebDriver. Tests run against the live demo site at `https://school.moodledemo.net`.

## Prerequisites

- **Python** 3.10+
- **Google Chrome** (latest)
- **ChromeDriver** on PATH (matching your Chrome version)

## Installation

```bash
pip install -r requirements.txt
```

## Project Structure

```
proj_3/
├── common/                          # Shared utilities
│   ├── driver_factory.py            # Browser driver initialization
│   ├── login_helper.py              # Moodle authentication helpers
│   ├── csv_reader.py                # Tab-separated CSV parser
│   └── assertions.py                # Reusable assertion helpers
│
├── level1/                          # Level 1: Functional UI tests (hardcoded locators)
│   ├── F001_quiz_attempt_review/    # Quiz attempt & result review tests
│   │   ├── data/                    # Test data CSV (comma-separated)
│   │   └── test_level_1.py          # 1 test module, 10 test cases
│   │
│   ├── F003_forum_discussion/       # Forum discussion CRUD tests
│   │   ├── data/                    # Test data CSVs + sample assets
│   │   └── test_*.py                # 7 test modules, 14 test cases
│   │
│   └── F005_add_course/             # Add course tests
│       ├── data/                    # Test data CSV
│       └── test_add_course_level1.py
│
├── level2/                          # Level 2: Same tests with externalized locators
│   ├── F001_quiz_attempt_review/
│   │   ├── data/                    # CSV + locators.json
│   │   └── test_level_2.py
│   │
│   ├── F003_forum_discussion/
│   │   ├── data/                    # CSVs + locators.json
│   │   └── test_*.py
│   │
│   └── F005_add_course/
│       ├── data/                    # CSV + locators.json
│       └── test_add_course_level2.py
│
├── non_functional/                  # Non-functional tests
│   ├── F001_quiz_attempt_review/
│   │   ├── data/                    # accessibility + reliability configs
│   │   ├── test_quiz_accessibility.py   # Keyboard usability & accessible names
│   │   └── test_quiz_reliability.py     # Refresh/navigation recoverability
│   │
│   ├── F003_forum_discussion/
│   │   ├── data/                    # performance + responsive configs
│   │   ├── test_forum_performance.py    # Response time measurement
│   │   └── test_forum_responsive.py     # Viewport compatibility
│   │
│   └── F005_add_course/
│       ├── test_course_authorization.py   # Role-based access control
│       └── test_course_creation_performance.py  # Response time
│
├── .gitignore
├── requirements.txt
├── run_all.py                       # Run all tests at once
├── CLAUDE.md                        # AI assistant guidance
└── README.md
```

## Running Tests

All commands should be run **from the project root** (`proj_3/`).

### Run tests for a specific feature

```bash
# F001 Quiz Attempt and Result Review (Level 1)
python -m unittest discover -s level1/F001_quiz_attempt_review -p "test_*.py" -v

# F001 Quiz Attempt and Result Review (Level 2)
python -m unittest discover -s level2/F001_quiz_attempt_review -p "test_*.py" -v

# F003 Forum Discussion (Level 1)
python -m unittest discover -s level1/F003_forum_discussion -p "test_*.py" -v

# F005 Add Course (Level 1)
python -m unittest discover -s level1/F005_add_course -p "test_*.py" -v

# F003 Forum Discussion (Level 2)
python -m unittest discover -s level2/F003_forum_discussion -p "test_*.py" -v

# F005 Add Course (Level 2)
python -m unittest discover -s level2/F005_add_course -p "test_*.py" -v

# F001 Quiz Attempt and Result Review (Non-functional)
python -m unittest discover -s non_functional/F001_quiz_attempt_review -p "test_*.py" -v

# F003 Forum Discussion (Non-functional)
python -m unittest discover -s non_functional/F003_forum_discussion -p "test_*.py" -v

# F005 Non-functional tests
python -m unittest discover -s non_functional/F005_add_course -p "test_*.py" -v
```

### Run all tests

```bash
python run_all.py
```

### Run a single test module

```bash
python -m unittest level1.F001_quiz_attempt_review.test_level_1 -v
python -m unittest level1.F005_add_course.test_add_course_level1 -v
```

## Test Data Format

- **F003/F005**: Test data stored as **tab-separated CSV** files in each feature's `data/` directory. Each file has a header row and one row per test case.
- **F001**: Test data stored as **comma-separated CSV** files, read via Python's `csv.DictReader`.
- **Non-functional configs**: Tab-separated CSV with scenario definitions and expected controls/results.

## Credentials

| Role    | Username  | Password   | Used by              |
|---------|-----------|------------|----------------------|
| Student | `student` | `moodle26` | F001, F003 tests     |
| Manager | `manager` | `moodle26` | F005 tests           |

## Adding a New Feature

1. Create directories: `level1/F0XX_feature_name/data/`
2. Add test data CSV to `data/`
3. Create `test_*.py` using the pattern from existing features
4. Use `common.driver_factory.DriverFactory` for browser setup
5. Use `common.login_helper.LoginHelper` for authentication
6. Use `common.csv_reader.CSVReader` for test data loading
7. Add `__init__.py` to the new directory
8. Register the directory in `run_all.py`'s `test_dirs` list
9. Add the run command to this README
