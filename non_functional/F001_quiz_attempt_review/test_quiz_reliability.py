import os
import unittest

from common.driver_factory import DriverFactory
from common.login_helper import LoginHelper
from common.csv_reader import CSVReader

from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "reliability_config.csv")


class QuizReliabilityTest(unittest.TestCase):
    """Non-functional reliability / recoverability tests for F001 Quiz.

    Testing type: Reliability / recoverability testing.
    Testing approach: Verify the quiz attempt flow remains usable after
        page refresh, navigation away and back, and reopening the quiz.
    Testing tool: Python Selenium WebDriver with unittest.
    """

    BASE_URL = "https://school.moodledemo.net/"

    # Locators reused from F001 Level 1
    LOC_LINK_MY_COURSES = (By.LINK_TEXT, "My courses")
    LOC_LINK_COURSE = (By.PARTIAL_LINK_TEXT, "Chemical Nomenclature")
    LOC_LINK_QUIZ = (By.PARTIAL_LINK_TEXT, "Balancing Chemical Equations")
    LOC_BTN_ATTEMPT = (
        By.XPATH,
        "//button[contains(., 'Attempt quiz') or contains(., 'Re-attempt quiz')"
        " or contains(., 'Continue your attempt')]"
        " | //input[contains(@value, 'Attempt quiz') or contains(@value, 'Re-attempt quiz')"
        " or contains(@value, 'Continue your attempt')]",
    )
    LOC_INPUTS_QUIZ = (By.XPATH, "//input[contains(@id, '_answer')]")
    LOC_BTN_NEXT = (By.ID, "mod_quiz-next-nav")
    LOC_FINISH_ATTEMPT = (
        By.XPATH,
        "//a[contains(., 'Finish attempt...')]"
        " | //button[contains(., 'Finish attempt...')]"
        " | //input[contains(@value, 'Finish attempt...')]",
    )

    @classmethod
    def setUpClass(cls):
        cls.driver = DriverFactory.get_driver()
        cls.wait = WebDriverWait(cls.driver, 15)
        LoginHelper.login(cls.driver)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def read_test_data(self):
        return CSVReader.read_data(DATA_FILE)

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------

    def _try_click(self, locator, timeout=5):
        """Click if element becomes clickable within timeout; return True/False."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable(locator)
            ).click()
            return True
        except TimeoutException:
            return False

    def navigate_to_quiz_page(self):
        """Navigate from logged-in state to the quiz info page."""
        driver = self.driver
        driver.get(self.BASE_URL)
        LoginHelper.ensure_logged_in(driver)
        self._try_click(self.LOC_LINK_MY_COURSES, timeout=5)
        self.wait.until(EC.element_to_be_clickable(self.LOC_LINK_COURSE)).click()
        self.wait.until(EC.element_to_be_clickable(self.LOC_LINK_QUIZ)).click()

    def open_attempt_page(self):
        """Navigate to quiz page and click Attempt/Re-attempt/Continue."""
        self.navigate_to_quiz_page()
        self.wait.until(EC.element_to_be_clickable(self.LOC_BTN_ATTEMPT)).click()

    def verify_attempt_ui_available(self):
        """Verify that the attempt page has usable quiz controls.

        Returns True if answer inputs, Next button, or Finish attempt are found.
        Fails the test with a clear message if none are found.
        """
        found_controls = []

        # Check for answer inputs
        try:
            inputs = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(self.LOC_INPUTS_QUIZ)
            )
            if inputs:
                found_controls.append(f"answer_inputs({len(inputs)})")
        except TimeoutException:
            pass

        # Check for Next page button
        try:
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located(self.LOC_BTN_NEXT)
            )
            found_controls.append("next_button")
        except TimeoutException:
            pass

        # Check for Finish attempt link
        try:
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located(self.LOC_FINISH_ATTEMPT)
            )
            found_controls.append("finish_attempt")
        except TimeoutException:
            pass

        self.assertGreater(
            len(found_controls), 0,
            "Attempt UI not available: no answer inputs, Next button, "
            "or Finish attempt link found after action",
        )

        return found_controls

    # ------------------------------------------------------------------
    # Scenario methods
    # ------------------------------------------------------------------

    def scenario_refresh_attempt_page(self):
        """Verify attempt UI survives a page refresh."""
        driver = self.driver

        # 1. Open the attempt page
        self.open_attempt_page()

        # 2. Verify attempt UI is available before refresh
        controls_before = self.verify_attempt_ui_available()

        # 3. Refresh the page
        driver.refresh()

        # 4. Re-login if session was lost
        LoginHelper.ensure_logged_in(driver)

        # 5. Verify attempt UI is still available after refresh
        controls_after = self.verify_attempt_ui_available()

        # Verify at least answer inputs survived the refresh
        has_inputs_after = any("answer_inputs" in c for c in controls_after)
        self.assertTrue(
            has_inputs_after,
            f"Answer inputs not found after refresh. "
            f"Before: {controls_before}, After: {controls_after}",
        )

    def scenario_leave_and_continue_attempt(self):
        """Verify leaving and returning to quiz allows continuing the attempt."""
        driver = self.driver

        # 1. Open the attempt page
        self.open_attempt_page()

        # 2. Verify attempt UI is loaded
        self.verify_attempt_ui_available()

        # 3. Navigate away to the course page
        driver.get(self.BASE_URL)
        LoginHelper.ensure_logged_in(driver)
        self._try_click(self.LOC_LINK_MY_COURSES, timeout=5)
        self.wait.until(EC.element_to_be_clickable(self.LOC_LINK_COURSE)).click()

        # 4. Reopen Balancing Chemical Equations
        self.wait.until(EC.element_to_be_clickable(self.LOC_LINK_QUIZ)).click()

        # 5. Verify Attempt/Re-attempt/Continue is available
        attempt_btn = self.wait.until(
            EC.element_to_be_clickable(self.LOC_BTN_ATTEMPT)
        )
        btn_text = (
            attempt_btn.text.strip()
            or (attempt_btn.get_attribute("value") or "").strip()
        )
        self.assertTrue(
            btn_text,
            "Attempt/Re-attempt/Continue button found but has no visible text",
        )

        # 6. Click it to verify the attempt can actually continue
        attempt_btn.click()

        # 7. Verify attempt UI loads again
        self.verify_attempt_ui_available()

    def scenario_reopen_quiz_after_navigation(self):
        """Verify quiz flow is usable after navigating away and back."""
        driver = self.driver

        # 1. Navigate to course and open quiz
        self.navigate_to_quiz_page()

        # 2. Verify attempt button is available
        self.wait.until(EC.element_to_be_clickable(self.LOC_BTN_ATTEMPT))

        # 3. Navigate away to My courses
        driver.get(self.BASE_URL)
        LoginHelper.ensure_logged_in(driver)
        self._try_click(self.LOC_LINK_MY_COURSES, timeout=5)

        # 4. Re-navigate into course
        self.wait.until(EC.element_to_be_clickable(self.LOC_LINK_COURSE)).click()

        # 5. Reopen quiz
        self.wait.until(EC.element_to_be_clickable(self.LOC_LINK_QUIZ)).click()

        # 6. Verify the quiz flow is still usable
        attempt_btn = self.wait.until(
            EC.element_to_be_clickable(self.LOC_BTN_ATTEMPT)
        )
        btn_text = (
            attempt_btn.text.strip()
            or (attempt_btn.get_attribute("value") or "").strip()
        )
        self.assertTrue(
            btn_text,
            "Quiz flow broken: Attempt/Re-attempt/Continue button has no text "
            "after navigating away and back",
        )

    # ------------------------------------------------------------------
    # Data-driven test method
    # ------------------------------------------------------------------

    def test_quiz_reliability_data_driven(self):
        test_data = self.read_test_data()

        for row in test_data:
            test_case_id = row["test_case_id"]
            scenario = row["scenario"]

            print(f"\nRunning {test_case_id} - {scenario}")

            with self.subTest(test_case_id=test_case_id):
                if scenario == "refresh_attempt_page_keeps_attempt_usable":
                    self.scenario_refresh_attempt_page()

                elif scenario == "leave_and_continue_attempt_restores_attempt":
                    self.scenario_leave_and_continue_attempt()

                elif scenario == "reopen_quiz_page_after_navigation_keeps_flow_usable":
                    self.scenario_reopen_quiz_after_navigation()

                else:
                    self.fail(f"Unknown scenario: {scenario}")

                print(f"PASSED {test_case_id}")


if __name__ == "__main__":
    unittest.main()
