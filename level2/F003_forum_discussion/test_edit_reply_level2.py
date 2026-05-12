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
DATA_FILE = os.path.join(BASE_DIR, "data", "edit_reply_level2.csv")
LOCATORS_FILE = os.path.join(BASE_DIR, "data", "locators.json")


class ForumEditReplyLevel2(unittest.TestCase):

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

        wait.until(
            EC.presence_of_element_located(self.get_by("tinymce_iframe"))
        )

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

        wait.until(EC.element_to_be_clickable(self.get_by("submit_button"))).click()

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

        return unique_subject

    def click_reply(self):
        self.wait.until(
            EC.element_to_be_clickable(self.get_by("reply_link"))
        ).click()

    def submit_inline_reply(self, reply_message):
        driver = self.driver
        wait = self.wait

        textarea = wait.until(
            EC.visibility_of_element_located(self.get_by("reply_textarea"))
        )

        textarea.clear()
        textarea.send_keys(reply_message)

        form = textarea.find_element(By.XPATH, "./ancestor::form")

        submit_button = form.find_element(*self.get_by("reply_submit_button"))

        driver.execute_script("arguments[0].click();", submit_button)

        wait.until(
            EC.visibility_of_element_located(
                self.get_by("text_contains_template", text=reply_message)
            )
        )

    def create_seed_reply(self, original_reply):
        self.click_reply()
        self.submit_inline_reply(original_reply)
        time.sleep(1)

    def click_edit_for_reply(self, original_reply):
        driver = self.driver
        short_wait = WebDriverWait(driver, 10)

        # Find the post that contains the reply text, then click its own Edit link.
        # Try several ancestor class names that Moodle uses across versions.
        ancestor_locator_keys = [
            "post_ancestor_forumpost",
            "post_ancestor_forum_post_container",
            "post_ancestor_post_content_container",
            "post_ancestor_post",
        ]

        for key in ancestor_locator_keys:
            locator = self.get_by(key, reply_text=original_reply, action_link="Edit")
            try:
                short_wait.until(EC.element_to_be_clickable(locator)).click()
                short_wait.until(
                    EC.presence_of_element_located(self.get_by("tinymce_iframe"))
                )
                return
            except TimeoutException:
                continue

        # Fallback: the reply is the most recent post, so its Edit link is the
        # last one on the page.
        edit_links = driver.find_elements(*self.get_by("edit_link"))
        if not edit_links:
            self.fail("Edit link for reply not found.")
        edit_links[-1].click()

        short_wait.until(
            EC.presence_of_element_located(self.get_by("tinymce_iframe"))
        )

    def edit_reply(self, original_reply, updated_reply):
        driver = self.driver
        wait = self.wait

        self.click_edit_for_reply(original_reply)

        self.input_tinymce_message(updated_reply)

        submit_btn = wait.until(
            EC.element_to_be_clickable(self.get_by("submit_button"))
        )
        submit_btn.click()

        if updated_reply:
            try:
                WebDriverWait(driver, 15).until(EC.staleness_of(submit_btn))
            except TimeoutException:
                pass

    def wait_for_validation_message(self, expected_text):
        short_wait = WebDriverWait(self.driver, 10)

        locator_specs = [
            ("error_message", {}),
            ("error_message_editor", {}),
            ("invalid_feedback", {"text": expected_text}),
            ("form_control_feedback", {"text": expected_text}),
            ("error_id_contains", {"text": expected_text}),
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

        raise TimeoutException("Validation message not found.")

    def verify_result(self, expected_type, expected_text):
        wait = self.wait

        if expected_type == "success":
            result_element = wait.until(
                EC.visibility_of_element_located(
                    self.get_by("text_contains_template", text=expected_text)
                )
            )
            self.assertIn(expected_text, result_element.text)

        elif expected_type == "error_message":
            result_element = self.wait_for_validation_message(expected_text)
            self.assertIn(expected_text, result_element.text)

        else:
            self.fail(f"Unknown expected_type: {expected_type}")

    def test_edit_reply_data_driven(self):
        test_data = self.read_test_data()

        for row in test_data:
            test_case_id = row["test_case_id"]
            print(f"\nRunning {test_case_id} - Expected: {row['expected_type']}")

            with self.subTest(test_case_id=test_case_id):
                self.create_seed_discussion(
                    forum_url=row["forum_url"],
                    seed_subject=row["seed_subject"],
                    seed_message=row["seed_message"]
                )

                self.create_seed_reply(
                    original_reply=row["original_reply"]
                )

                self.edit_reply(
                    original_reply=row["original_reply"],
                    updated_reply=row["updated_reply"]
                )

                self.verify_result(
                    expected_type=row["expected_type"],
                    expected_text=row["expected_text"]
                )

                print(f"PASSED {test_case_id}")


if __name__ == "__main__":
    unittest.main()
