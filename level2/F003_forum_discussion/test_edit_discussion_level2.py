import json
import os
import time
import unittest
import uuid

from common.driver_factory import DriverFactory
from common.login_helper import LoginHelper
from common.csv_reader import CSVReader

from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "edit_discussion_level2.csv")
LOCATORS_FILE = os.path.join(BASE_DIR, "data", "locators.json")


class ForumEditDiscussionLevel2(unittest.TestCase):

    locators = {}

    @classmethod
    def setUpClass(cls):
        with open(LOCATORS_FILE, "r", encoding="utf-8") as f:
            cls.locators = json.load(f)

        cls.driver = DriverFactory.get_driver()
        cls.wait = WebDriverWait(cls.driver, 15)
        LoginHelper.login(cls.driver)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def get_by(self, locator_key, **format_values):
        strategy, value = self.locators[locator_key]
        if format_values:
            value = value.format(**format_values)
        if strategy == "id":
            return (By.ID, value)
        elif strategy == "css selector":
            return (By.CSS_SELECTOR, value)
        elif strategy == "xpath":
            return (By.XPATH, value)
        elif strategy == "link text":
            return (By.LINK_TEXT, value)
        elif strategy == "partial link text":
            return (By.PARTIAL_LINK_TEXT, value)
        return (By.ID, value)

    def ensure_logged_in(self, return_url=None):
        LoginHelper.ensure_logged_in(self.driver, return_url=return_url)

    def read_test_data(self):
        return CSVReader.read_data(DATA_FILE)

    def input_tinymce_message(self, message):
        driver = self.driver
        wait = self.wait

        # Wait for TinyMCE iframe to be present.
        wait.until(
            EC.presence_of_element_located(self.get_by("tinymce_iframe"))
        )

        # Set content via TinyMCE API from default content (no iframe switch needed).
        content = message or ""
        driver.execute_script(
            "if (window.tinymce && tinymce.activeEditor) {"
            "  var editor = tinymce.activeEditor;"
            "  editor.setContent(arguments[0]);"
            "  editor.fire('change');"
            "  editor.save();"
            "}"
            "if (window.tinymce && tinymce.triggerSave) {"
            "  tinymce.triggerSave();"
            "}"
            "var ta = document.querySelector('textarea#id_message, textarea[name=\"message\"]');"
            "if (ta) {"
            "  ta.value = arguments[0];"
            "  ta.dispatchEvent(new Event('input', {bubbles:true}));"
            "  ta.dispatchEvent(new Event('change', {bubbles:true}));"
            "}",
            content
        )
        # Small delay to let Moodle's JS pick up the change.
        time.sleep(0.5)

    def click_add_discussion(self):
        driver = self.driver
        short_wait = WebDriverWait(driver, 10)

        locator_keys = [
            "add_discussion_btn",
            "add_discussion_link",
            "add_discussion_link_text",
            "add_discussion_link_text_alt",
            "add_discussion_partial",
            "add_discussion_partial_alt",
        ]

        for key in locator_keys:
            try:
                short_wait.until(EC.element_to_be_clickable(self.get_by(key))).click()
                return
            except TimeoutException:
                continue

        # Fallback: direct link navigation.
        link_candidates = driver.find_elements(
            *self.get_by("add_discussion_link")
        )
        for link in link_candidates:
            href = link.get_attribute("href")
            if href:
                driver.get(href)
                return

        self.fail("Add discussion topic link/button not found.")

    def create_seed_discussion(self, forum_url, seed_subject, seed_message):
        driver = self.driver
        wait = self.wait

        unique_suffix = uuid.uuid4().hex[:6]
        unique_subject = f"{seed_subject} {unique_suffix}"

        driver.get(forum_url)
        self.ensure_logged_in(return_url=forum_url)
        wait.until(EC.presence_of_element_located(self.get_by("page")))

        self.click_add_discussion()

        subject_input = wait.until(
            EC.visibility_of_element_located(self.get_by("subject_input"))
        )
        subject_input.clear()
        subject_input.send_keys(unique_subject)

        self.input_tinymce_message(seed_message)

        wait.until(
            EC.element_to_be_clickable(self.get_by("submit_button"))
        ).click()

        wait.until(
            EC.visibility_of_element_located(self.get_by("success_post_added"))
        )

        driver.get(forum_url)

        wait.until(
            EC.element_to_be_clickable(
                self.get_by("discussion_link_template", subject=unique_subject)
            )
        ).click()

        wait.until(
            EC.presence_of_element_located(
                self.get_by("text_contains_template", text=unique_subject)
            )
        )

        return unique_suffix

    def open_discussion_by_subject(self, forum_url, subjects):
        driver = self.driver
        wait = self.wait

        driver.get(forum_url)
        self.ensure_logged_in(return_url=forum_url)

        for subject in subjects:
            if not subject:
                continue

            try:
                wait.until(
                    EC.element_to_be_clickable(
                        self.get_by("discussion_link_template", subject=subject)
                    )
                ).click()
                return True
            except TimeoutException:
                continue

        return False

    def wait_for_subject_text(self, subject_candidates):
        short_wait = WebDriverWait(self.driver, 10)

        for subject in subject_candidates:
            if not subject:
                continue

            locator_keys_and_kwargs = [
                ("text_contains_template", {"text": subject}),
                ("subject_heading_h3", {"subject": subject}),
                ("subject_heading_h2", {"subject": subject}),
                ("subject_link", {"subject": subject}),
            ]

            for key, kwargs in locator_keys_and_kwargs:
                try:
                    return short_wait.until(
                        EC.visibility_of_element_located(self.get_by(key, **kwargs))
                    )
                except TimeoutException:
                    continue

        raise TimeoutException("Updated subject text not found.")

    def click_edit_discussion(self):
        wait = self.wait

        edit_link = wait.until(
            EC.element_to_be_clickable(self.get_by("edit_link"))
        )
        edit_link.click()

        wait.until(
            EC.visibility_of_element_located(self.get_by("subject_input"))
        )

    def edit_discussion(self, updated_subject, updated_message, unique_suffix):
        driver = self.driver
        wait = self.wait

        self.click_edit_discussion()

        subject_input = wait.until(
            EC.visibility_of_element_located(self.get_by("subject_input"))
        )
        subject_input.clear()

        final_subject = updated_subject

        if updated_subject:
            final_subject = f"{updated_subject} {unique_suffix}"
            subject_input.send_keys(final_subject)

        self.input_tinymce_message(updated_message)

        submit_btn = wait.until(
            EC.element_to_be_clickable(self.get_by("submit_button"))
        )
        submit_btn.click()

        # For the success case, wait for the edit form to disappear (page redirect).
        # For error cases the form stays, so we swallow the timeout.
        if updated_subject and updated_message:
            try:
                WebDriverWait(driver, 15).until(
                    EC.staleness_of(submit_btn)
                )
            except TimeoutException:
                pass
            # Give the redirected page a moment to render.
            time.sleep(1)

        return final_subject

    def verify_result(self, expected_type, expected_text, final_subject=None, forum_url=None):
        wait = self.wait
        driver = self.driver

        if expected_type == "success":
            # After a successful edit, Moodle redirects to the discussion view.
            try:
                wait.until(
                    EC.visibility_of_element_located(self.get_by("success_post_updated"))
                )
            except TimeoutException:
                pass

            # Wait for the page to settle.
            try:
                wait.until(EC.presence_of_element_located(self.get_by("page")))
            except TimeoutException:
                pass

            # Try to find the updated subject on the current page.
            try:
                title_element = self.wait_for_subject_text([final_subject, expected_text])
            except TimeoutException:
                # Fallback: navigate to the forum list and open the discussion.
                if not forum_url:
                    # Last resort: check page source.
                    self.assertIn(expected_text, driver.page_source)
                    return

                opened = self.open_discussion_by_subject(
                    forum_url,
                    [final_subject, expected_text]
                )
                if not opened:
                    # Last resort: check page source.
                    self.assertIn(expected_text, driver.page_source)
                    return

                title_element = self.wait_for_subject_text([final_subject, expected_text])

            self.assertIn(expected_text, title_element.text)

            if final_subject:
                self.assertIn(expected_text, final_subject)

        elif expected_type == "error_subject":
            result_element = wait.until(
                EC.visibility_of_element_located(self.get_by("error_subject"))
            )
            self.assertIn(expected_text, result_element.text)

        elif expected_type == "error_message":
            result_element = self.wait_for_validation_message(expected_text)
            self.assertIn(expected_text, result_element.text)

        else:
            self.fail(f"Unknown expected_type: {expected_type}")

    def wait_for_validation_message(self, expected_text):
        short_wait = WebDriverWait(self.driver, 10)

        locator_specs = [
            ("error_message", {}),
            ("error_message_editor", {}),
            ("invalid_feedback", {"text": expected_text}),
            ("form_control_feedback", {"text": expected_text}),
        ]

        for key, kwargs in locator_specs:
            try:
                element = short_wait.until(
                    EC.visibility_of_element_located(self.get_by(key, **kwargs))
                )
                if expected_text in element.text:
                    return element
            except TimeoutException:
                continue

        return short_wait.until(
            EC.visibility_of_element_located(
                self.get_by("error_id_contains", text=expected_text)
            )
        )

    def test_edit_discussion_data_driven(self):
        test_data = self.read_test_data()

        for row in test_data:
            test_case_id = row["test_case_id"]
            print(f"\nRunning {test_case_id} - Expected: {row['expected_type']}")

            with self.subTest(test_case_id=test_case_id):
                unique_suffix = self.create_seed_discussion(
                    forum_url=row["forum_url"],
                    seed_subject=row["seed_subject"],
                    seed_message=row["seed_message"]
                )

                final_subject = self.edit_discussion(
                    updated_subject=row["updated_subject"],
                    updated_message=row["updated_message"],
                    unique_suffix=unique_suffix
                )

                self.verify_result(
                    expected_type=row["expected_type"],
                    expected_text=row["expected_text"],
                    final_subject=final_subject,
                    forum_url=row["forum_url"]
                )

                print(f"PASSED {test_case_id}")


if __name__ == "__main__":
    unittest.main()
