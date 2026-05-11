import os
import unittest
import time
import uuid
import json



from common.driver_factory import DriverFactory
from common.login_helper import LoginHelper
from common.csv_reader import CSVReader

from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "add_course_level2.csv")
LOCATORS_FILE = os.path.join(BASE_DIR, "data", "locators.json")

class CourseCreateLevel2(unittest.TestCase):
    locators = {}

    @classmethod
    def setUpClass(cls):
        with open(LOCATORS_FILE, "r", encoding="utf-8") as f:
            cls.locators = json.load(f)

        cls.driver = DriverFactory.get_driver()
        cls.wait = WebDriverWait(cls.driver, 15)
        LoginHelper.login(cls.driver, username="manager", password="moodle26")

        cls.create_prerequisite_course("EXIST-01")

    @classmethod
    def get_by(cls, locator_name):
        strategy, value = cls.locators.get(locator_name, [None, None])
        if strategy == "id":
            return (By.ID, value)
        elif strategy == "css selector":
            return (By.CSS_SELECTOR, value)
        elif strategy == "xpath":
            return (By.XPATH, value)
        return (By.ID, value)

    @classmethod
    def navigate_to_add_course(cls):
        # Go to home page to ensure navbar is present if we are lost
        cls.driver.get("https://school.moodledemo.net/")
        
        try:
            cls.wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "My course"))).click()
        except TimeoutException:
            cls.driver.find_element(By.XPATH, "//a[contains(text(), 'My course')]").click()
            
        locators = [
            (By.XPATH, "//*[contains(text(), 'Create course')]"),
            (By.XPATH, "//*[contains(text(), 'Add a new course')]"),
            (By.PARTIAL_LINK_TEXT, "Create course"),
            (By.PARTIAL_LINK_TEXT, "Add a new course"),
        ]
        found = False
        for loc in locators:
            try:
                WebDriverWait(cls.driver, 3).until(EC.element_to_be_clickable(loc)).click()
                found = True
                break
            except Exception:
                pass
        if not found:
            raise Exception("Could not find 'Create course' button")

    @classmethod
    def create_prerequisite_course(cls, short_name):
        try:
            cls.navigate_to_add_course()
            cls.wait.until(EC.visibility_of_element_located(cls.get_by("fullname_input"))).send_keys(f"Pre-existing {short_name}")
            cls.driver.find_element(*cls.get_by("shortname_input")).send_keys(short_name)
            
            category_select = Select(cls.driver.find_element(*cls.get_by("category_select")))
            if len(category_select.options) > 1:
                category_select.select_by_index(1)
                
            cls.driver.find_element(*cls.get_by("save_display_btn")).click()
            
            prereq_loc = (By.XPATH, cls.locators["prerequisite_course"][1].format(short_name=short_name))
            cls.wait.until(EC.visibility_of_element_located(prereq_loc))
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
                self.navigate_to_add_course()

                self.fill_course_form(row)
                self.submit_form(row["action"])
                self.verify_result(row["expected_type"], row["expected_text"])

                print(f"PASSED {test_case_id}")

    def set_date(self, prefix, date_str):
        if not date_str:
            return
        parts = date_str.split('-')
        if len(parts) == 3:
            day, month, year = parts
            for suffix, val in [("day", str(int(day))), ("month", str(int(month))), ("year", year)]:
                el = self.driver.find_element(*self.get_by(f"{prefix}_{suffix}"))
                self.driver.execute_script("arguments[0].removeAttribute('disabled')", el)
                Select(el).select_by_value(val)

    def fill_course_form(self, row):
        wait = self.wait
        driver = self.driver
        
        wait.until(EC.visibility_of_element_located(self.get_by("fullname_input")))

        short_name = row["short_name"]
        if row["expected_type"] == "success" or row["expected_type"] == "success_return":
            short_name += "-" + uuid.uuid4().hex[:4]

        driver.find_element(*self.get_by("fullname_input")).clear()
        if row["full_name"]:
            driver.find_element(*self.get_by("fullname_input")).send_keys(row["full_name"])

        driver.find_element(*self.get_by("shortname_input")).clear()
        if row["short_name"]:
            driver.find_element(*self.get_by("shortname_input")).send_keys(short_name)

        if row["category"]:
            if row["category"] == "0":
                try:
                    badge_x = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'form-autocomplete-selection')]//span[@aria-hidden='true']")))
                    driver.execute_script("arguments[0].click();", badge_x)
                except TimeoutException:
                    pass
            else:
                try:
                    category_select = Select(driver.find_element(*self.get_by("category_select")))
                    category_select.select_by_index(1)
                except NoSuchElementException:
                    pass

        if row["start_date"]:
            self.set_date("startdate", row["start_date"])
            
        if row["end_date"]:
            try:
                automatic_enddate = driver.find_element(By.ID, "id_automaticenddate")
                if automatic_enddate.is_selected():
                    driver.execute_script("arguments[0].click();", automatic_enddate)
                    time.sleep(0.5)
            except NoSuchElementException:
                pass
            try:
                enabled_checkbox = driver.find_element(*self.get_by("enddate_enabled"))
                if not enabled_checkbox.is_selected():
                    driver.execute_script("arguments[0].click();", enabled_checkbox)
                    time.sleep(1) # wait for js to enable fields
                self.set_date("enddate", row["end_date"])
            except NoSuchElementException:
                pass

    def submit_form(self, action):
        if action == "save_display":
            self.driver.find_element(*self.get_by("save_display_btn")).click()
        elif action == "save_return":
            try:
                self.driver.find_element(*self.get_by("save_return_btn")).click()
            except NoSuchElementException:
                self.driver.find_element(*self.get_by("save_display_btn")).click()
                time.sleep(1)
                try:
                    self.driver.find_element(By.XPATH, "//a[contains(text(), 'My course')]").click()
                except:
                    pass
        elif action == "cancel":
            self.driver.find_element(*self.get_by("cancel_btn")).click()

    def verify_result(self, expected_type, expected_text):
        wait = self.wait
        driver = self.driver

        if expected_type == "success":
            wait.until(EC.visibility_of_element_located(self.get_by("page_header")))
            self.assertIn(expected_text, driver.page_source)
            
        elif expected_type == "success_return" or expected_type == "cancel":
            wait.until(EC.visibility_of_element_located(self.get_by("page_heading1")))
            self.assertIn(expected_text, driver.page_source)
            
        elif expected_type == "error_full_name":
            error = wait.until(EC.visibility_of_element_located(self.get_by("error_fullname")))
            self.assertIn(expected_text, error.text)
            
        elif expected_type == "error_short_name":
            error = wait.until(EC.visibility_of_element_located(self.get_by("error_shortname")))
            self.assertIn(expected_text, error.text)
            
        elif expected_type == "error_category":
            error = wait.until(EC.visibility_of_element_located(self.get_by("error_category")))
            self.assertIn(expected_text, error.text)
            
        elif expected_type == "error_date":
            error = wait.until(EC.visibility_of_element_located(self.get_by("error_enddate")))
            self.assertIn(expected_text, error.text)
            
        elif expected_type == "error_multiple":
            wait.until(EC.visibility_of_element_located(self.get_by("invalid_feedback")))
            self.assertIn(expected_text, driver.page_source)

if __name__ == "__main__":
    unittest.main()
