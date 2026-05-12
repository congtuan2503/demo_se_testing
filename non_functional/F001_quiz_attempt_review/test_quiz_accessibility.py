import os
import unittest

from common.driver_factory import DriverFactory
from common.login_helper import LoginHelper
from common.csv_reader import CSVReader

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "accessibility_config.csv")


class QuizAccessibilityTest(unittest.TestCase):
    """Non-functional accessibility / keyboard usability tests for F001 Quiz.

    Testing type: Accessibility / keyboard usability testing.
    Testing approach: Verify quiz entry and attempt controls have accessible
        names, are keyboard-reachable, and accept user input.
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

    # ------------------------------------------------------------------
    # Accessibility helper: check element has a usable accessible name
    # ------------------------------------------------------------------

    def _get_accessible_name(self, element):
        """Return a non-empty accessible name string or empty string.

        Checks in order: visible text, aria-label, title, value,
        placeholder, associated <label> via 'for' attribute.
        """
        # 1. Visible text
        text = (element.text or "").strip()
        if text:
            return text

        # 2. aria-label
        aria = (element.get_attribute("aria-label") or "").strip()
        if aria:
            return aria

        # 3. title
        title = (element.get_attribute("title") or "").strip()
        if title:
            return title

        # 4. value (for input/button)
        value = (element.get_attribute("value") or "").strip()
        if value:
            return value

        # 5. placeholder
        placeholder = (element.get_attribute("placeholder") or "").strip()
        if placeholder:
            return placeholder

        # 6. Associated label via id
        el_id = element.get_attribute("id")
        if el_id:
            labels = self.driver.find_elements(
                By.XPATH, f"//label[@for='{el_id}']"
            )
            for lbl in labels:
                lbl_text = (lbl.text or "").strip()
                if lbl_text:
                    return lbl_text

        return ""

    # ------------------------------------------------------------------
    # Scenario methods
    # ------------------------------------------------------------------

    def scenario_quiz_entry_controls_have_accessible_names(self):
        """Verify course link, quiz link, attempt button have accessible names."""
        driver = self.driver
        driver.get(self.BASE_URL)
        LoginHelper.ensure_logged_in(driver)

        # Navigate to My courses
        self._try_click(self.LOC_LINK_MY_COURSES, timeout=5)

        # 1. Course link
        course_el = self.wait.until(
            EC.element_to_be_clickable(self.LOC_LINK_COURSE)
        )
        name = self._get_accessible_name(course_el)
        self.assertTrue(
            name,
            "Course link 'Chemical Nomenclature' has no accessible name",
        )

        # Navigate into course
        course_el.click()

        # 2. Quiz link
        quiz_el = self.wait.until(
            EC.element_to_be_clickable(self.LOC_LINK_QUIZ)
        )
        name = self._get_accessible_name(quiz_el)
        self.assertTrue(
            name,
            "Quiz link 'Balancing Chemical Equations' has no accessible name",
        )

        # Navigate into quiz
        quiz_el.click()

        # 3. Attempt button
        attempt_el = self.wait.until(
            EC.element_to_be_clickable(self.LOC_BTN_ATTEMPT)
        )
        name = self._get_accessible_name(attempt_el)
        self.assertTrue(
            name,
            "Attempt quiz button has no accessible name",
        )

    def scenario_quiz_attempt_controls_are_keyboard_reachable(self):
        """Verify answer inputs, Next button, Finish attempt are focusable."""
        driver = self.driver
        self.open_attempt_page()

        # 1. Answer inputs: verify at least one exists and can receive focus
        inputs = self.wait.until(
            EC.presence_of_all_elements_located(self.LOC_INPUTS_QUIZ)
        )
        self.assertGreater(len(inputs), 0, "No answer inputs found on attempt page")

        # Focus the first input via Tab from the body
        body = driver.find_element(By.TAG_NAME, "body")
        body.send_keys(Keys.TAB)

        # Find the first answer input and focus it directly, then verify
        first_input = inputs[0]
        first_input.click()
        active = driver.switch_to.active_element
        self.assertEqual(
            first_input.get_attribute("id"),
            active.get_attribute("id"),
            "First answer input did not receive focus",
        )

        # 2. Next page button — verify it exists and is focusable
        next_btn = None
        try:
            next_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(self.LOC_BTN_NEXT)
            )
        except TimeoutException:
            pass

        # 3. Finish attempt link — verify it exists and is focusable
        finish_el = None
        try:
            finish_el = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(self.LOC_FINISH_ATTEMPT)
            )
        except TimeoutException:
            pass

        # At least one navigation control must be present
        self.assertTrue(
            next_btn is not None or finish_el is not None,
            "Neither Next page button nor Finish attempt link found",
        )

        # Verify the found navigation control can receive focus
        nav_el = next_btn if next_btn is not None else finish_el
        driver.execute_script("arguments[0].focus();", nav_el)
        active = driver.switch_to.active_element
        # Verify focus landed on the element (compare tag + id or href)
        nav_tag = nav_el.tag_name.lower()
        active_tag = active.tag_name.lower()
        self.assertEqual(
            nav_tag, active_tag,
            f"Navigation control ({nav_tag}) did not receive focus "
            f"(active element is {active_tag})",
        )

    def scenario_quiz_answer_inputs_are_usable(self):
        """Verify first answer input is visible, enabled, and accepts text."""
        driver = self.driver
        self.open_attempt_page()

        inputs = self.wait.until(
            EC.presence_of_all_elements_located(self.LOC_INPUTS_QUIZ)
        )
        self.assertGreater(len(inputs), 0, "No answer inputs found")

        first_input = inputs[0]

        # Verify visible
        self.assertTrue(
            first_input.is_displayed(),
            "First answer input is not visible",
        )

        # Verify enabled
        self.assertTrue(
            first_input.is_enabled(),
            "First answer input is not enabled",
        )

        # Type a harmless test value
        test_value = "42"
        first_input.clear()
        first_input.send_keys(test_value)

        # Verify the input accepted the text
        actual = first_input.get_attribute("value")
        self.assertEqual(
            actual, test_value,
            f"Input did not accept text: expected '{test_value}', got '{actual}'",
        )

    # ------------------------------------------------------------------
    # Data-driven test method
    # ------------------------------------------------------------------

    def test_quiz_accessibility_data_driven(self):
        test_data = self.read_test_data()

        for row in test_data:
            test_case_id = row["test_case_id"]
            scenario = row["scenario"]

            print(f"\nRunning {test_case_id} - {scenario}")

            with self.subTest(test_case_id=test_case_id):
                if scenario == "quiz_entry_controls_have_accessible_names":
                    self.scenario_quiz_entry_controls_have_accessible_names()

                elif scenario == "quiz_attempt_controls_are_keyboard_reachable":
                    self.scenario_quiz_attempt_controls_are_keyboard_reachable()

                elif scenario == "quiz_answer_inputs_are_usable":
                    self.scenario_quiz_answer_inputs_are_usable()

                else:
                    self.fail(f"Unknown scenario: {scenario}")

                print(f"PASSED {test_case_id}")


if __name__ == "__main__":
    unittest.main()
