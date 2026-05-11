import os
import unittest
import time
import uuid

from common.driver_factory import DriverFactory
from common.login_helper import LoginHelper
from common.csv_reader import CSVReader

from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "add_course_level1.csv")

class CourseCreateLevel1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver = DriverFactory.get_driver()
        cls.wait = WebDriverWait(cls.driver, 15)
        LoginHelper.login(cls.driver, username="manager", password="moodle26")

        # Pre-requisite: Create a course with short name EXIST-01
        cls.create_prerequisite_course("EXIST-01")

    @staticmethod
    def navigate_to_add_course(driver, wait):
        # Go to home page to ensure navbar is present if we are lost
        driver.get("https://school.moodledemo.net/")
        
        try:
            wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "My course"))).click()
        except TimeoutException:
            driver.find_element(By.XPATH, "//a[contains(text(), 'My course')]").click()
            
        locators = [
            (By.XPATH, "//*[contains(text(), 'Create course')]"),
            (By.XPATH, "//*[contains(text(), 'Add a new course')]"),
            (By.PARTIAL_LINK_TEXT, "Create course"),
            (By.PARTIAL_LINK_TEXT, "Add a new course"),
        ]
        found = False
        for loc in locators:
            try:
                WebDriverWait(driver, 3).until(EC.element_to_be_clickable(loc)).click()
                found = True
                break
            except Exception:
                pass
        if not found:
            raise Exception("Could not find 'Create course' button")

    @classmethod
    def create_prerequisite_course(cls, short_name):
        try:
            cls.navigate_to_add_course(cls.driver, cls.wait)
            cls.wait.until(EC.visibility_of_element_located((By.ID, "id_fullname"))).send_keys(f"Pre-existing {short_name}")
            cls.driver.find_element(By.ID, "id_shortname").send_keys(short_name)
            
            # Select category 1 (Miscellaneous)
            category_select = Select(cls.driver.find_element(By.ID, "id_category"))
            if len(category_select.options) > 1:
                category_select.select_by_index(1)
                
            cls.driver.find_element(By.ID, "id_saveanddisplay").click()
            cls.wait.until(EC.visibility_of_element_located((By.XPATH, f"//*[contains(text(), '{short_name}')]")))
        except Exception as e:
            print(f"Prerequisite course creation skipped or failed: {e}")

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def test_add_course_data_driven(self):
        test_data = CSVReader.read_data(DATA_FILE)

        for row in test_data:
            test_case_id = row["test_case_id"]
            print(f"\nRunning {test_case_id} - Expected: {row['expected_type']}")

            with self.subTest(test_case_id=test_case_id):
                LoginHelper.ensure_logged_in(self.driver, return_url=None, username="manager", password="moodle26")
                self.navigate_to_add_course(self.driver, self.wait)

                self.fill_course_form(row)
                self.submit_form(row["action"])
                self.verify_result(row["expected_type"], row["expected_text"])

                print(f"PASSED {test_case_id}")

    def set_date(self, field_prefix, date_str):
        if not date_str:
            return
        parts = date_str.split('-')
        if len(parts) == 3:
            day, month, year = parts
            for suffix, val in [("day", str(int(day))), ("month", str(int(month))), ("year", year)]:
                el = self.driver.find_element(By.ID, f"{field_prefix}_{suffix}")
                self.driver.execute_script("arguments[0].removeAttribute('disabled')", el)
                Select(el).select_by_value(val)

    def fill_course_form(self, row):
        wait = self.wait
        driver = self.driver
        
        # Make sure form is loaded
        wait.until(EC.visibility_of_element_located((By.ID, "id_fullname")))

        # Suffix with UUID if necessary to ensure uniqueness on success cases except the ones testing duplicates
        short_name = row["short_name"]
        if row["expected_type"] == "success" or row["expected_type"] == "success_return":
            short_name += "-" + uuid.uuid4().hex[:4]

        # Fill text fields
        driver.find_element(By.ID, "id_fullname").clear()
        if row["full_name"]:
            driver.find_element(By.ID, "id_fullname").send_keys(row["full_name"])

        driver.find_element(By.ID, "id_shortname").clear()
        if row["short_name"]:
            driver.find_element(By.ID, "id_shortname").send_keys(short_name)

        # Category
        if row["category"]:
            if row["category"] == "0":
                try:
                    badge_x = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'form-autocomplete-selection')]//span[@aria-hidden='true']")))
                    driver.execute_script("arguments[0].click();", badge_x)
                except TimeoutException:
                    pass
            else:
                try:
                    category_select = Select(driver.find_element(By.ID, "id_category"))
                    category_select.select_by_index(1)
                except NoSuchElementException:
                    pass

        # Dates
        if row["start_date"]:
            self.set_date("id_startdate", row["start_date"])
            
        if row["end_date"]:
            try:
                automatic_enddate = driver.find_element(By.ID, "id_automaticenddate")
                if automatic_enddate.is_selected():
                    driver.execute_script("arguments[0].click();", automatic_enddate)
                    time.sleep(0.5)
            except NoSuchElementException:
                pass
            try:
                enabled_checkbox = driver.find_element(By.ID, "id_enddate_enabled")
                if not enabled_checkbox.is_selected():
                    driver.execute_script("arguments[0].click();", enabled_checkbox)
                    time.sleep(1) # wait for js to enable fields
                self.set_date("id_enddate", row["end_date"])
            except NoSuchElementException:
                pass

    def submit_form(self, action):
        if action == "save_display":
            self.driver.find_element(By.ID, "id_saveanddisplay").click()
        elif action == "save_return":
            try:
                self.driver.find_element(By.ID, "id_saveandreturn").click()
            except NoSuchElementException:
                self.driver.find_element(By.ID, "id_saveanddisplay").click()
                time.sleep(1)
                try:
                    self.driver.find_element(By.XPATH, "//a[contains(text(), 'My course')]").click()
                except:
                    pass
        elif action == "cancel":
            self.driver.find_element(By.ID, "id_cancel").click()

    def verify_result(self, expected_type, expected_text):
        wait = self.wait
        driver = self.driver

        if expected_type == "success":
            wait.until(EC.visibility_of_element_located((By.XPATH, "//header")))
            # Just verify the page title or header contains the course name
            self.assertIn(expected_text, driver.page_source)
            
        elif expected_type == "success_return" or expected_type == "cancel":
            # Manage courses page
            wait.until(EC.visibility_of_element_located((By.XPATH, "//h1")))
            self.assertIn(expected_text, driver.page_source)
            
        elif expected_type == "error_full_name":
            error = wait.until(EC.visibility_of_element_located((By.ID, "id_error_fullname")))
            self.assertIn(expected_text, error.text)
            
        elif expected_type == "error_short_name":
            error = wait.until(EC.visibility_of_element_located((By.ID, "id_error_shortname")))
            self.assertIn(expected_text, error.text)
            
        elif expected_type == "error_category":
            error = wait.until(EC.visibility_of_element_located((By.ID, "id_error_category")))
            self.assertIn(expected_text, error.text)
            
        elif expected_type == "error_date":
            error = wait.until(EC.visibility_of_element_located((By.ID, "id_error_enddate")))
            self.assertIn(expected_text, error.text)
            
        elif expected_type == "error_multiple":
            # For multiple errors, just check if expected_text is in page source
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".invalid-feedback")))
            self.assertIn(expected_text, driver.page_source)

if __name__ == "__main__":
    unittest.main()
