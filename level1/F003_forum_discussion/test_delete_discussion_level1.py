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
DATA_FILE = os.path.join(BASE_DIR, "data", "delete_discussion_level1.csv")


class ForumDeleteDiscussionLevel1(unittest.TestCase):

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

        wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe.tox-edit-area__iframe"))
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

        unique_suffix = uuid.uuid4().hex[:6]
        unique_subject = f"{seed_subject} {unique_suffix}"

        driver.get(forum_url)
        self.ensure_logged_in(return_url=forum_url)
        wait.until(EC.presence_of_element_located((By.ID, "page")))

        self.click_add_discussion()

        subject_input = wait.until(EC.visibility_of_element_located((By.ID, "id_subject")))
        subject_input.clear()
        subject_input.send_keys(unique_subject)

        self.input_tinymce_message(seed_message)

        wait.until(EC.element_to_be_clickable((By.ID, "id_submitbutton"))).click()

        wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//*[contains(text(), 'Your post was successfully added.')]")
            )
        )

        driver.get(forum_url)

        wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, unique_subject))
        ).click()

        wait.until(
            EC.presence_of_element_located(
                (By.XPATH, f"//*[contains(normalize-space(), '{unique_subject}')]")
            )
        )

        return unique_subject

    def delete_discussion(self):
        driver = self.driver
        wait = self.wait

        delete_link = wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Delete"))
        )
        delete_link.click()

        # Moodle shows a confirmation page. The confirm button text varies by
        # version ("Continue", "Delete", or "Yes"). Use a single combined XPath
        # to match any of them without burning timeout on each separately.
        confirm_btn = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(normalize-space(), 'Continue')]"
                    " | //input[@type='submit' and contains(@value, 'Continue')]"
                    " | //button[contains(normalize-space(), 'Delete')]"
                    " | //input[@type='submit' and contains(@value, 'Delete')]"
                    " | //button[contains(normalize-space(), 'Yes')]"
                    " | //input[@type='submit' and contains(@value, 'Yes')]"
                )
            )
        )
        confirm_btn.click()

        # Wait for the confirmation page to go away (redirect to forum list).
        try:
            WebDriverWait(driver, 15).until(EC.staleness_of(confirm_btn))
        except TimeoutException:
            pass

    def verify_deleted(self, forum_url, unique_subject):
        driver = self.driver
        wait = self.wait

        driver.get(forum_url)
        self.ensure_logged_in(return_url=forum_url)

        # Wait for the forum page to fully render.
        wait.until(EC.presence_of_element_located((By.ID, "page")))
        time.sleep(1)

        matching_links = driver.find_elements(
            By.XPATH,
            f"//a[contains(normalize-space(), '{unique_subject}')]"
        )

        self.assertEqual(
            len(matching_links),
            0,
            f"Discussion was not deleted. Still found: {unique_subject}"
        )

    def test_delete_discussion_data_driven(self):
        test_data = self.read_test_data()

        for row in test_data:
            test_case_id = row["test_case_id"]
            print(f"\nRunning {test_case_id} - Expected: {row['expected_type']}")

            with self.subTest(test_case_id=test_case_id):
                unique_subject = self.create_seed_discussion(
                    forum_url=row["forum_url"],
                    seed_subject=row["seed_subject"],
                    seed_message=row["seed_message"]
                )

                self.delete_discussion()

                self.verify_deleted(
                    forum_url=row["forum_url"],
                    unique_subject=unique_subject
                )

                print(f"PASSED {test_case_id}")


if __name__ == "__main__":
    unittest.main()