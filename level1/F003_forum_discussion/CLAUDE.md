# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Selenium WebDriver UI test suite for the **Moodle LMS Forum Discussion** feature (F003). Tests run against the live Moodle demo site at `https://school.moodledemo.net` using credentials `student` / `moodle26`. This is a Level 1 (functional UI) data-driven test suite covering 14 test cases (TC-003-001 through TC-003-014).

## Running Tests

```bash
# Prerequisite: Chrome + ChromeDriver on PATH
pip install selenium

# Run all tests (from F003_forum_discussion directory)
python -m unittest discover -s . -p "test_*.py" -v

# Run a single test module (from F003_forum_discussion directory)
python -m unittest test_create_discussion_level1 -v
python -m unittest test_reply_level1 -v
python -m unittest test_edit_discussion_level1 -v
python -m unittest test_delete_discussion_level1 -v
python -m unittest test_edit_reply_level1 -v
python -m unittest test_delete_reply_level1 -v
python -m unittest test_attachment_level1 -v

# Run from the proj_3 directory (package-style)
python -m unittest -v level1.F003_forum_discussion.test_attachment_level1

# Run directly
python test_create_discussion_level1.py
```

Tests require network access to `https://school.moodledemo.net`.

## Architecture

### Test Modules (7 files, 14 test cases)

| Module | Class | Test Cases | Actions |
|--------|-------|------------|---------|
| `test_create_discussion_level1.py` | `ForumCreateDiscussionLevel1` | TC-003-001 to 003 | Create new forum discussions |
| `test_reply_level1.py` | `ForumReplyLevel1` | TC-003-004 to 005 | Reply to discussions (inline + advanced) |
| `test_edit_discussion_level1.py` | `ForumEditDiscussionLevel1` | TC-003-006 to 008 | Edit existing discussion subject/message |
| `test_delete_discussion_level1.py` | `ForumDeleteDiscussionLevel1` | TC-003-009 | Delete a discussion |
| `test_edit_reply_level1.py` | `ForumEditReplyLevel1` | TC-003-010 to 011 | Edit replies via TinyMCE |
| `test_delete_reply_level1.py` | `ForumDeleteReplyLevel1` | TC-003-012 | Delete a reply |
| `test_attachment_level1.py` | `ForumAttachmentLevel1` | TC-003-013 to 014 | Attach images via TinyMCE Image button |

### Data-Driven Pattern

Each test file has a single `test_*_data_driven()` method that iterates rows from a tab-separated CSV in `data/` using `self.subTest(test_case_id=...)`. Test data is read via `csv.DictReader(file, delimiter="\t")`.

File naming convention: `test_<action>_level1.py` ↔ `data/<action>_level1.csv`.

### Test Class Skeleton

Every test class follows this structure:
- `setUpClass()` — launches Chrome, calls `login()`
- `tearDownClass()` — quits the driver
- `login()` — authenticates at Moodle login page (3-attempt retry loop with `StaleElementReferenceException` handling)
- `ensure_logged_in()` — re-authenticates if session expired (checks for `#user-menu-toggle`)
- `read_test_data()` — reads CSV from `data/`
- `input_tinymce_message()` — handles TinyMCE rich editor content entry
- Action method(s) — the test-specific operations
- `verify_result()` — asserts expected outcome by `expected_type`
- Single `test_*_data_driven()` method — iterates CSV rows with `subTest()`

### Seed Discussions

Edit, Reply, Delete, and Attachment tests first create a **seed discussion** with a UUID hex suffix (`uuid.uuid4().hex[:6]`) to ensure uniqueness, then perform their action on that discussion.

### TinyMCE Interaction — Two Approaches

Moodle uses TinyMCE in an iframe (`iframe.tox-edit-area__iframe`). Two content-setting approaches exist across the codebase:

1. **Two-layer** (Create, Reply, DeleteReply, Attachment): switch into iframe → set `innerHTML` on `#tinymce` → switch back to default content → then sync via TinyMCE API (`setContent`, `fire('change')`, `save()`, `triggerSave()`) + hidden textarea events. More resilient when TinyMCE API hasn't fully initialized.

2. **API-only** (EditDiscussion, EditReply): use TinyMCE API directly (`setContent`, `fire('change')`, `save()`, `triggerSave()`) + hidden textarea sync without iframe switching. Works because the editor is already initialized when editing.

### Image Attachment via TinyMCE

The attachment test uses `upload_image_via_tinymce()` — Moodle's inline forum form has **no filemanager widget**. The upload flow is:
1. Click TinyMCE "Image" toolbar button (`button.tox-tbtn[aria-label="Image"]`)
2. "Insert image" modal appears with a hidden `input[type='file']`
3. Make the file input visible via JS, send the image path
4. Modal transitions to "Image details" — requires filling alt text or checking "Decorative image"
5. Click "Save" to insert the image into the editor

A 1×1 pixel PNG (`sample_image.png`) is auto-generated from base64 if missing via `ensure_sample_image_exists()`.

### Reply Submission Branching

Reply tests use two different submission paths:
- **Non-empty reply**: submits via inline textarea (`textarea[name='post']`) and "Post to forum" button
- **Empty reply**: clicks "Advanced" button to open the full form, then submits `#id_submitbutton` to trigger validation

### Delete Confirmation

Delete tests (discussion and reply) handle Moodle's confirmation page with a combined XPath locator matching Continue/Delete/Yes buttons, then wait for `EC.staleness_of(confirm_btn)`.

### Locator Fallback Chains

The `click_add_discussion()` method tries multiple locator strategies in sequence (CSS selectors, link text, partial link text) with short waits, failing only if all strategies are exhausted. Similar fallback patterns exist in `click_edit_for_reply()` and `click_delete_for_reply()` which try multiple ancestor class names (`forumpost`, `forum-post-container`, `post-content-container`, `post`).

## CSV Column Reference

**Create**: `test_case_id`, `forum_url`, `subject`, `message`, `expected_type`, `expected_text`

**Reply**: `test_case_id`, `forum_url`, `seed_subject`, `seed_message`, `reply_message`, `expected_type`, `expected_text`

**Edit Discussion**: `test_case_id`, `forum_url`, `seed_subject`, `seed_message`, `updated_subject`, `updated_message`, `expected_type`, `expected_text`

**Delete Discussion**: `test_case_id`, `forum_url`, `seed_subject`, `seed_message`, `expected_type`, `expected_text`

**Edit Reply**: `test_case_id`, `forum_url`, `seed_subject`, `seed_message`, `original_reply`, `updated_reply`, `expected_type`, `expected_text`

**Delete Reply**: `test_case_id`, `forum_url`, `seed_subject`, `seed_message`, `reply_message`, `expected_type`, `expected_text`

**Attachment**: `test_case_id`, `forum_url`, `action`, `seed_subject`, `seed_message`, `subject`, `message`, `attachment_path`, `expected_type`, `expected_text`

`expected_type` values: `success`, `error_subject`, `error_message`, `deleted`.

## Coding Conventions

- Use `unittest.TestCase` — not pytest
- Use `self.subTest(test_case_id=...)` for data-driven iteration
- Use explicit `WebDriverWait` (default 15s) with `EC` expected conditions — minimize `time.sleep()`
- Keep test data in `data/` as tab-separated CSV files
- Class naming: `Forum<Action>Level1`
- Print `Running` / `PASSED` per test case for console visibility
- Use `EC.staleness_of()` to confirm page navigation after form submission
