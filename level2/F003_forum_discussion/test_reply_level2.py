import json
import os
import time
import unittest
import uuid

from common.driver_factory import DriverFactory
from common.login_helper import LoginHelper
from common.csv_reader import CSVReader

from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "reply_level2.csv")
LOCATORS_FILE = os.path.join(BASE_DIR, "data", "locators.json")


class ForumReplyLevel2(unittest.TestCase):

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
        driver.switch_to.frame(iframe)

        body = wait.until(EC.presence_of_element_located(self.get_by("tinymce_body")))

        driver.execute_script("arguments[0].innerHTML = '';", body)

        if message:
            driver.execute_script("arguments[0].innerHTML = arguments[1];", body, message)

        driver.switch_to.default_content()

    def click_add_discussion(self):
        short_wait = WebDriverWait(self.driver, 5)

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

        # Go back to forum list and open the newly created discussion.
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

    def submit_empty_reply_using_advanced_form(self):
        driver = self.driver
        wait = self.wait

        # Moodle usually requires going to Advanced form to show the
        # required-message validation.
        advanced_button = wait.until(
            EC.element_to_be_clickable(self.get_by("advanced_button"))
        )

        driver.execute_script("arguments[0].click();", advanced_button)

        wait.until(
            EC.element_to_be_clickable(self.get_by("submit_button"))
        ).click()

    def reply_to_discussion(self, reply_message):
        self.click_reply()

        if reply_message:
            self.submit_inline_reply(reply_message)
        else:
            self.submit_empty_reply_using_advanced_form()

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
            result_element = wait.until(
                EC.visibility_of_element_located(self.get_by("error_message"))
            )
            self.assertIn(expected_text, result_element.text)

        else:
            self.fail(f"Unknown expected_type: {expected_type}")

    def test_reply_data_driven(self):
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

                self.reply_to_discussion(
                    reply_message=row["reply_message"]
                )

                self.verify_result(
                    expected_type=row["expected_type"],
                    expected_text=row["expected_text"]
                )

                print(f"PASSED {test_case_id}")


if __name__ == "__main__":
    unittest.main()
