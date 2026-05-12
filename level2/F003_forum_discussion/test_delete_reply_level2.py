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
DATA_FILE = os.path.join(BASE_DIR, "data", "delete_reply_level2.csv")
LOCATORS_FILE = os.path.join(BASE_DIR, "data", "locators.json")


class ForumDeleteReplyLevel2(unittest.TestCase):

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

        iframe = wait.until(
            EC.presence_of_element_located(self.get_by("tinymce_iframe"))
        )

        # Set content via the iframe body first (works even if TinyMCE API
        # hasn't fully initialised yet).
        driver.switch_to.frame(iframe)
        body = wait.until(EC.presence_of_element_located(self.get_by("tinymce_body")))
        driver.execute_script("arguments[0].innerHTML = arguments[1];", body, message or "")
        driver.switch_to.default_content()

        # Then sync through the TinyMCE API + hidden textarea so Moodle's
        # form validation sees the value.
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

        unique_subject = f"{seed_subject} {uuid.uuid4().hex[:6]}"

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

        time.sleep(0.5)
        submit_btn = wait.until(EC.element_to_be_clickable(self.get_by("submit_button")))
        submit_btn.click()

        # Wait for the page to navigate away from the form.
        try:
            WebDriverWait(driver, 15).until(EC.staleness_of(submit_btn))
        except TimeoutException:
            pass

        # Wait for submission to complete — either success message or page redirect.
        try:
            WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located(self.get_by("success_post_added"))
            )
        except TimeoutException:
            # The page may have already redirected past the success message.
            pass

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

    def create_seed_reply(self, reply_message):
        self.click_reply()
        self.submit_inline_reply(reply_message)
        time.sleep(1)

    def click_delete_for_reply(self, reply_message):
        driver = self.driver
        short_wait = WebDriverWait(driver, 10)

        ancestor_locator_keys = [
            "post_ancestor_forumpost",
            "post_ancestor_forum_post_container",
            "post_ancestor_post_content_container",
            "post_ancestor_post",
        ]

        for key in ancestor_locator_keys:
            locator = self.get_by(key, reply_text=reply_message, action_link="Delete")
            try:
                short_wait.until(EC.element_to_be_clickable(locator)).click()
                return
            except TimeoutException:
                continue

        # Fallback: the reply is usually the newest post, so its Delete link is
        # usually the last Delete link on the page.
        delete_links = driver.find_elements(*self.get_by("delete_link"))
        if not delete_links:
            self.fail("Delete link for reply not found.")

        delete_links[-1].click()

    def confirm_delete(self):
        driver = self.driver
        wait = self.wait

        confirm_btn = wait.until(
            EC.element_to_be_clickable(self.get_by("confirm_delete_button"))
        )

        confirm_btn.click()

        try:
            WebDriverWait(driver, 15).until(EC.staleness_of(confirm_btn))
        except TimeoutException:
            pass

    def delete_reply(self, reply_message):
        self.click_delete_for_reply(reply_message)
        self.confirm_delete()

    def verify_reply_deleted(self, reply_message):
        driver = self.driver
        wait = self.wait

        wait.until(EC.presence_of_element_located(self.get_by("page")))
        time.sleep(1)

        matching_elements = driver.find_elements(
            *self.get_by("text_contains_template", text=reply_message)
        )

        self.assertEqual(
            len(matching_elements),
            0,
            f"Reply was not deleted. Still found: {reply_message}"
        )

    def test_delete_reply_data_driven(self):
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
                    reply_message=row["reply_message"]
                )

                self.delete_reply(
                    reply_message=row["reply_message"]
                )

                self.verify_reply_deleted(
                    reply_message=row["reply_message"]
                )

                print(f"PASSED {test_case_id}")


if __name__ == "__main__":
    unittest.main()
