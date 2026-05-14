"""
test_remove_submission_level1.py - Level 1 Data-Driven Tests for Removing Submissions

Tests covered (CSV columns: Test ID, Action, Assignment URL, Expected Result):
    TC-002-010: Remove submission when none exists  (student / moodle26)

Dynamic session switching, direct URL navigation.
"""

import os
import unittest

from common.driver_factory import DriverFactory
from common.login_helper import LoginHelper
from common.csv_reader import CSVReader

from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "remove_submission_level1.csv")


class AssignmentRemoveSubmissionLevel1(unittest.TestCase):

    _current_user = None

    @classmethod
    def setUpClass(cls):
        cls.driver = DriverFactory.get_driver()
        cls.wait = WebDriverWait(cls.driver, 15)
        cls._current_user = None

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    # ---- Credential management ------------------------------------------

    @staticmethod
    def _get_credentials(test_id):
        tc_num = int(test_id.strip().split("-")[-1])
        if 7 <= tc_num <= 9:
            return "ericwebb", "moodle"
        return "student", "moodle26"

    def _switch_user_if_needed(self, test_id):
        username, password = self._get_credentials(test_id)
        if self.__class__._current_user == username:
            return
        self.driver.delete_all_cookies()
        LoginHelper.login(self.driver, username=username, password=password)
        self.__class__._current_user = username
        print(f"    [Auth] Logged in as: {username}")

    # ---- Navigation -----------------------------------------------------

    def _navigate(self, url):
        self.driver.get(url)
        self.wait.until(EC.presence_of_element_located((By.ID, "page")))

    # ---- Remove submission ----------------------------------------------

    def _attempt_remove(self):
        """Click 'Remove submission' and confirm. Returns True if performed."""
        short_wait = WebDriverWait(self.driver, 10)
        for loc in [
            (By.XPATH, "//button[contains(normalize-space(),'Remove submission')]"),
            (By.XPATH, "//a[contains(normalize-space(),'Remove submission')]"),
        ]:
            try:
                short_wait.until(EC.element_to_be_clickable(loc)).click()
                confirm = short_wait.until(EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[contains(normalize-space(),'Continue')]"
                    "|//input[@type='submit'][contains(@value,'Continue')]"
                    "|//button[contains(normalize-space(),'Yes')]"
                )))
                confirm.click()
                try:
                    WebDriverWait(self.driver, 10).until(EC.staleness_of(confirm))
                except TimeoutException:
                    pass
                return True
            except (TimeoutException, StaleElementReferenceException):
                continue
        return False

    # ---- Verification ---------------------------------------------------

    def _verify(self, expected, test_id):
        self.wait.until(EC.presence_of_element_located((By.ID, "page")))
        page = self.driver.page_source
        self.assertTrue(
            expected.lower() in page.lower(),
            f"{test_id}: Expected '{expected}' not found on page.",
        )

    # ---- Main data-driven test ------------------------------------------

    def test_remove_submission_data_driven(self):
        test_data = CSVReader.read_data(DATA_FILE, delimiter=",")

        for row in test_data:
            test_id = row["Test ID"].strip()
            assignment_url = row["Assignment URL"].strip()
            expected = row["Expected Result"].strip()

            print(f"\nRunning {test_id} - {row.get('Action', 'Remove').strip()}")

            with self.subTest(test_id=test_id):
                # 1. Switch user if needed.
                self._switch_user_if_needed(test_id)

                # 2. Navigate directly to the assignment page.
                self._navigate(assignment_url)

                # 3. Attempt removal (may or may not find the button).
                self._attempt_remove()

                # 4. Navigate back and verify the expected state.
                self._navigate(assignment_url)
                self._verify(expected, test_id)

                print(f"PASSED {test_id}")


if __name__ == "__main__":
    unittest.main()
