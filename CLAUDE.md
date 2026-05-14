# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Selenium WebDriver UI test suite for **Moodle LMS** (`https://school.moodledemo.net`) using Python's `unittest` framework. Tests cover three features at multiple levels:

- **F001 Quiz Attempt and Result Review** — 10 test cases (TC001001 through TC001010), student role
- **F003 Forum Discussion** — 14 test cases (TC-003-001 through TC-003-014), student role
- **F005 Add Course** — 12 test cases (TC-005-001 through TC-005-012), manager role

| Level | Purpose | Locator source |
|-------|---------|---------------|
| **Level 1** | Functional UI tests | Hardcoded `By.*` tuples in Python |
| **Level 2** | Data-driven with externalized locators | `data/locators.json` resolved via `get_by()` or `_get_locator()` |
| **Non-functional** | Accessibility, reliability, performance, responsive | Data-driven CSV config |

## Credentials

| Role | Username | Password | Used by |
|------|----------|----------|---------|
| Student | `student` | `moodle26` | F001 (quiz), F003 (forum) |
| Manager | `manager` | `moodle26` | F005 (course) |

## Running Tests

All commands from project root (`proj_3/`). Requires Chrome + ChromeDriver on PATH.

```bash
pip install -r requirements.txt

# Run all suites
python run_all.py

# Run a single feature/level
python -m unittest discover -s level1/F001_quiz_attempt_review -p "test_*.py" -v
python -m unittest discover -s level2/F001_quiz_attempt_review -p "test_*.py" -v
python -m unittest discover -s level1/F003_forum_discussion -p "test_*.py" -v
python -m unittest discover -s level2/F003_forum_discussion -p "test_*.py" -v
python -m unittest discover -s level1/F005_add_course -p "test_*.py" -v
python -m unittest discover -s level2/F005_add_course -p "test_*.py" -v
python -m unittest discover -s non_functional/F001_quiz_attempt_review -p "test_*.py" -v
python -m unittest discover -s non_functional/F003_forum_discussion -p "test_*.py" -v
python -m unittest discover -s non_functional/F005_add_course -p "test_*.py" -v

# Run a single test module
python -m unittest level2.F003_forum_discussion.test_create_discussion_level2 -v
python -m unittest level1.F001_quiz_attempt_review.test_level_1 -v
```

Tests require live network access to `https://school.moodledemo.net`. The Moodle demo site resets periodically; transient failures on attachment/image-upload tests (TC-003-013) are a known flaky area.

## Architecture

### `common/` — Shared Utilities

All static-method classes, no instantiation needed:

- **`DriverFactory.get_driver(browser="chrome")`** — creates a maximized WebDriver
- **`LoginHelper.login(driver, url, username, password)`** — navigates to login page, fills credentials, waits for `#page`
- **`LoginHelper.ensure_logged_in(driver, return_url)`** — checks `#user-menu-toggle`; re-logins if session expired
- **`CSVReader.read_data(file_path, delimiter="\t")`** — returns `list[dict]` from tab-separated CSV
- **`Assertions`** — defined but unused; all tests use `self.assertIn()` directly

### Level 1 → Level 2 Difference

**F003/F005**: Level 1 and Level 2 have **identical test logic and CSV data**. The only difference is locator resolution:

- **Level 1**: `(By.ID, "id_subject")` hardcoded inline
- **Level 2**: `self.get_by("subject_input")` → reads `["id", "id_subject"]` from `locators.json` → returns `(By.ID, "id_subject")`

The `get_by()` method supports template interpolation for dynamic locators:
```python
self.get_by("discussion_link_template", subject="My Topic")
# locators.json: "discussion_link_template": ["xpath", "//a[contains(normalize-space(), '{subject}')]"]
# returns: (By.XPATH, "//a[contains(normalize-space(), 'My Topic')]")
```

Supported strategies in `locators.json`: `id`, `css selector`, `xpath`, `link text`, `partial link text`.

**F001**: Uses a different locator externalization pattern:
- **Level 1**: Locators hardcoded in `setUp()` as `self.loc_*` tuples
- **Level 2**: `locators.json` uses `{"by": "XPATH", "value": "..."}` dict format, resolved via `_get_locator(key)` → returns `(By.XPATH, "...")`
- F001 CSV uses **comma-separated** format (not tab-separated), read via Python's `csv.DictReader` directly (not `CSVReader`)
- F001 creates a fresh browser per CSV row (setUp/tearDown per row), unlike F003/F005 which share one driver across all rows

### Test Class Pattern

**F003/F005** test classes follow this skeleton:

1. **`setUpClass()`** — load locators (L2), create driver, login, create prerequisite data if needed
2. **`tearDownClass()`** — quit driver
3. **`ensure_logged_in()`** — session guard delegating to `LoginHelper`
4. **`input_tinymce_message()`** — TinyMCE content entry (see below)
5. **Action helpers** — `create_seed_discussion()`, `click_reply()`, etc.
6. **`verify_result(expected_type, expected_text)`** — dispatches assertion by type
7. **Single `test_*_data_driven()` method** — iterates CSV rows with `self.subTest(test_case_id=...)`

**F001** test classes use a different pattern:

1. **`setUp()`** — define locators, initialize `self.driver = None`
2. **`tearDown()`** — call `_stop_driver()` for safety cleanup
3. **Per-row browser lifecycle** — `_start_driver()` / `_stop_driver()` called inside the test loop for each CSV row
4. **Flow methods** — `_login()`, `_open_course_and_quiz()`, `_fill_answers()`, `_finish_attempt()`, `_finish_review()`, `_logout()`
5. **`_verify_expected_parts(expected_text, seen_texts, label)`** — splits expected by comma, checks each part is substring of any seen text
6. **Error collection** — failures are collected in `self.errors[]` and reported at end via `self.fail()`

**Non-functional** test classes (F001, F003) use the F003 pattern: `setUpClass`/`tearDownClass` with shared driver, `CSVReader` for tab-separated config, `self.subTest()` iteration.

### TinyMCE — Two Input Approaches

Moodle embeds TinyMCE in `iframe.tox-edit-area__iframe`. Two approaches coexist:

1. **Two-layer** (Create, Reply, DeleteReply, Attachment): switch into iframe → set `innerHTML` on `#tinymce` body → switch back → then sync via TinyMCE JS API (`setContent`, `fire('change')`, `save()`, `triggerSave()`) + hidden textarea events. More resilient when TinyMCE API hasn't fully initialized.

2. **API-only** (EditDiscussion, EditReply, DeleteDiscussion): wait for iframe presence but don't switch into it → set content purely via TinyMCE JS API + hidden textarea sync + `time.sleep(0.5)`. Works because the editor is already initialized when editing existing content.

### Seed Discussions and UUID Uniqueness

Edit, Reply, Delete, and Attachment tests create a **seed discussion** first with a `uuid.uuid4().hex[:6]` suffix to avoid collisions on the shared demo site. Successful create/edit operations also append UUID suffixes to subjects/short names.

### Locator Fallback Chains

Several methods try multiple locator strategies in sequence with short waits, failing only when all are exhausted:
- `click_add_discussion()` — 6 fallback locators for the "Add discussion" button
- `click_edit_for_reply()` / `click_delete_for_reply()` — 4 ancestor class names (`forumpost`, `forum-post-container`, `post-content-container`, `post`), then fallback to last Edit/Delete link on page

### Delete Confirmation

Combined XPath matching Moodle's version-variable confirm button (`Continue` | `Delete` | `Yes`), followed by `EC.staleness_of()` to confirm page redirect.

### Image Upload via TinyMCE

`upload_image_via_tinymce()` handles image attachment through TinyMCE's toolbar Image button → modal with hidden `input[type='file']` → alt text (5 locator fallbacks) or "Decorative image" checkbox → Save. A 1×1 px `sample_image.png` is auto-generated from base64 if missing.

## Data Files

### CSV Format
- **F003/F005**: **Tab-separated** (`\t` delimiter), header row, one row per test case. Read via `CSVReader.read_data()`.
- **F001 functional**: **Comma-separated**, header row, one row per test case. Read via Python `csv.DictReader` directly.
- **Non-functional configs**: **Tab-separated**, read via `CSVReader.read_data()`.
- Naming: `<action>_level<N>.csv` (functional), `<type>_config.csv` (non-functional)
- `expected_type` values — F003: `success`, `error_subject`, `error_message`, `deleted`; F005: `success`, `success_return`, `cancel`, `error_full_name`, `error_short_name`, `error_category`, `error_date`, `error_multiple`

### `locators.json` Format
```json
{
    "logical_name": ["strategy", "value"],
    "template_name": ["xpath", "//a[contains(text(), '{variable}')]"]
}
```

## Coding Conventions

- `unittest.TestCase` only — no pytest
- `self.subTest(test_case_id=...)` for data-driven iteration
- `WebDriverWait(driver, 15)` with `EC.*` expected conditions — minimize `time.sleep()`
- `EC.staleness_of()` to confirm page navigation after form submission
- Class naming: `Forum<Action>Level<N>` (F003), `CourseCreateLevel<N>` (F005), `Level<N>DataDrivenTest` (F001)
- Non-functional class naming: `Quiz<Type>Test` (F001), `Forum<Type>Test` (F003)
- Console output — functional: `Running TC-003-XXX - Expected: ...` then `PASSED TC-003-XXX`
- Console output — non-functional: `Running NF-F001-XXX-NNN - <scenario>` then `PASSED NF-F001-XXX-NNN`
- Tab-separated CSV in `data/` subdirectory per feature (except F001 functional which uses comma-separated)

## Constraints When Modifying

- Do not change credentials or the Moodle target site URL
- Do not convert away from `unittest` or add pytest
- Do not add dependencies beyond `selenium>=4.0.0`
- Do not modify Level 1 tests when implementing Level 2
- Do not submit/finish quiz attempts in F001 non-functional tests (no "Submit all and finish" confirmation)
- New features: add `__init__.py`, register in `run_all.py`'s `test_dirs` list, update `README.md`
- The `.gitignore` blocks `*.png` — allowlist specific `sample_image.png` paths if adding new features
- F001 quiz has 93 answer inputs across 25 questions; scores are attempt-dependent on the shared demo site
