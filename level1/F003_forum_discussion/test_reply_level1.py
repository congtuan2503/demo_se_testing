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
DATA_FILE = os.path.join(BASE_DIR, "data", "reply_level1.csv")


class ForumReplyLevel1(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.driver = DriverFactory.get_driver()
        cls.wait = WebDriverWait(cls.driver, 15)
        LoginHelper.login(cls.driver)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def ensure_logged_in(self, return_url=None):
        LoginHelper.ensure_logged_in(self.driver, return_url=return_url)

    def read_test_data(self):
        return CSVReader.read_data(DATA_FILE)


    def input_tinymce_message(self, message):
        driver = self.driver
        wait = self.wait

        iframe = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.tox-edit-area__iframe"))
        )
        driver.switch_to.frame(iframe)

        body = wait.until(EC.presence_of_element_located((By.ID, "tinymce")))

        driver.execute_script("arguments[0].innerHTML = '';", body)

        if message:
            driver.execute_script("arguments[0].innerHTML = arguments[1];", body, message)

        driver.switch_to.default_content()

    def click_add_discussion(self):
        short_wait = WebDriverWait(self.driver, 5)

        locators = [
            (By.CSS_SELECTOR, "[data-action='new-discussion']"),
            (By.CSS_SELECTOR, "a[href*='mod/forum/post.php']"),
            (By.LINK_TEXT, "Add a new discussion topic"),
            (By.LINK_TEXT, "Add discussion topic"),
            (By.PARTIAL_LINK_TEXT, "Add a new discussion"),
            (By.PARTIAL_LINK_TEXT, "Add a new"),
        ]

        for locator in locators:
            try:
                short_wait.until(EC.element_to_be_clickable(locator)).click()
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
            EC.visibility_of_element_located((By.ID, "id_subject"))
        )
        subject_input.clear()
        subject_input.send_keys(unique_subject)

        self.input_tinymce_message(seed_message)

        wait.until(
            EC.element_to_be_clickable((By.ID, "id_submitbutton"))
        ).click()

        wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//*[contains(text(), 'Your post was successfully added.')]")
            )
        )

        # Go back to forum list and open the newly created discussion.
        driver.get(forum_url)

        wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, unique_subject))
        ).click()

        wait.until(
            EC.presence_of_element_located((By.XPATH, f"//*[contains(text(), '{unique_subject}')]"))
        )

        return unique_subject

    def click_reply(self):
        wait = self.wait

        wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Reply"))
        ).click()

    def submit_inline_reply(self, reply_message):
        driver = self.driver
        wait = self.wait

        textarea = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "textarea[name='post']"))
        )

        textarea.clear()
        textarea.send_keys(reply_message)

        form = textarea.find_element(By.XPATH, "./ancestor::form")

        submit_button = form.find_element(
            By.XPATH,
            ".//button[contains(normalize-space(), 'Post to forum') or contains(@class, 'btn-primary')]"
        )

        driver.execute_script("arguments[0].click();", submit_button)

    def submit_empty_reply_using_advanced_form(self):
        driver = self.driver
        wait = self.wait

        # Moodle usually requires going to Advanced form to show the required-message validation.
        advanced_button = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//form[contains(@id, 'inpage-reply')]//button[contains(normalize-space(), 'Advanced')]"
                )
            )
        )

        driver.execute_script("arguments[0].click();", advanced_button)

        wait.until(
            EC.element_to_be_clickable((By.ID, "id_submitbutton"))
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
                    (
                        By.XPATH,
                        f"//*[contains(normalize-space(), '{expected_text}')]"
                    )
                )
            )
            self.assertIn(expected_text, result_element.text)

        elif expected_type == "error_message":
            result_element = wait.until(
                EC.visibility_of_element_located((By.ID, "id_error_message"))
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