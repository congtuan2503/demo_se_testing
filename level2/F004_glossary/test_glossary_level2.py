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
from selenium.webdriver.common.keys import Keys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "glossary_level2.csv")
LOCATORS_FILE = os.path.join(BASE_DIR, "data", "locators.json")

class GlossaryLevel2(unittest.TestCase):
    locators = {}

    @classmethod
    def setUpClass(cls):
        with open(LOCATORS_FILE, "r", encoding="utf-8") as f:
            cls.locators = json.load(f)

        cls.driver = DriverFactory.get_driver()
        cls.wait = WebDriverWait(cls.driver, 15)
        LoginHelper.login(cls.driver, username="student", password="moodle26")

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
        elif strategy == "name":
            return (By.NAME, value)
        return (By.ID, value)

    def ensure_logged_in(self, return_url=None):
        LoginHelper.ensure_logged_in(self.driver, return_url=return_url, username="student", password="moodle26")

    def read_test_data(self):
        return CSVReader.read_data(DATA_FILE, delimiter=",")

    def test_glossary_data_driven(self):
        test_data = self.read_test_data()

        for row in test_data:
            test_case_id = row["test_case_id"]
            print(f"\nRunning {test_case_id} - Expected: {row['expected_type']}")

            with self.subTest(test_case_id=test_case_id):
                self.ensure_logged_in(return_url="https://school.moodledemo.net/mod/glossary/view.php?id=570&mode=letter&hook=ALL")
                action_type = row["action_type"]

                if row["expected_type"] in ("success", "success_search") and "add" in action_type:
                    suffix = " " + uuid.uuid4().hex[:4]
                    original_concept = row["concept"]
                    
                    row["concept"] += suffix
                    if row["search_term"] == original_concept:
                        row["search_term"] += suffix
                    if row["expected_text"] == original_concept:
                        row["expected_text"] += suffix

                if action_type == "add":
                    self.add_entry(row)
                    self.verify_add(row)
                elif action_type == "search":
                    self.search_entry(row)
                    self.verify_search(row)
                elif action_type == "browse":
                    self.browse_letter(row)
                    self.verify_search(row)
                elif action_type == "add_and_search_and_browse":
                    self.add_entry(row)
                    self.verify_add(row)
                    self.search_entry(row)
                    self.verify_search(row)
                    self.browse_letter(row)
                    self.verify_search(row)

                print(f"PASSED {test_case_id}")

    def add_entry(self, row):
        self.driver.get("https://school.moodledemo.net/mod/glossary/view.php?id=570&mode=letter&hook=ALL")
        
        try:
            add_btn = self.wait.until(EC.element_to_be_clickable(self.get_by("add_entry_btn")))
            self.driver.execute_script("arguments[0].click();", add_btn)
        except TimeoutException:
            add_btn = self.driver.find_element(*self.get_by("add_entry_btn_alt"))
            self.driver.execute_script("arguments[0].click();", add_btn)
            
        self.wait.until(EC.visibility_of_element_located(self.get_by("concept_input")))
        
        self.driver.find_element(*self.get_by("concept_input")).clear()
        if row["concept"]:
            self.driver.find_element(*self.get_by("concept_input")).send_keys(row["concept"])
            
        if row["definition"]:
            self.wait.until(EC.frame_to_be_available_and_switch_to_it(0))
            body = self.driver.find_element(*self.get_by("tinymce_body"))
            body.clear()
            body.send_keys(row["definition"])
            self.driver.switch_to.default_content()
            
        self.driver.execute_script("if(typeof tinymce !== 'undefined') tinymce.triggerSave();")
            
        submit_btn = self.driver.find_element(*self.get_by("submit_btn"))
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
        time.sleep(1)
        try:
            submit_btn.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", submit_btn)
        
        try:
            self.wait.until(EC.staleness_of(submit_btn))
        except TimeoutException:
            pass

    def verify_add(self, row):
        expected_type = row["expected_type"]
        expected_text = row["expected_text"]
        
        if expected_type in ("success", "success_search"):
            content_to_check = row["concept"].strip() or row["definition"].strip()
            try:
                self.wait.until(lambda d: content_to_check in d.page_source)
            except TimeoutException:
                print(f"\nDEBUG: Could not find '{content_to_check}'")
                raise
            
            try:
                self.wait.until(lambda d: expected_text in d.page_source)
            except TimeoutException:
                print(f"\nDEBUG: Could not find '{expected_text}' in page source.")
                raise AssertionError(f"'{expected_text}' not found in page source.")
            
        elif expected_type == "error_concept":
            error = self.wait.until(EC.visibility_of_element_located(self.get_by("error_concept")))
            self.assertIn(expected_text, error.text)
            
        elif expected_type == "error_definition":
            error = self.wait.until(EC.visibility_of_element_located(self.get_by("error_definition")))
            self.assertIn(expected_text, error.text)
            
        elif expected_type == "error_both":
            error_concept = self.wait.until(EC.visibility_of_element_located(self.get_by("error_concept")))
            error_def = self.wait.until(EC.visibility_of_element_located(self.get_by("error_definition")))
            self.assertIn("You must supply a value here.", error_concept.text)
            self.assertIn("Required", error_def.text)
            
        elif expected_type == "error_db":
            error = self.wait.until(EC.visibility_of_element_located(self.get_by("error_db")))
            self.assertIn(expected_text, error.text)
            
        elif expected_type == "error_duplicate":
            error = self.wait.until(EC.visibility_of_element_located(self.get_by("error_concept")))
            self.assertIn(expected_text, error.text)

    def search_entry(self, row):
        self.driver.get("https://school.moodledemo.net/mod/glossary/view.php?id=570&mode=letter&hook=ALL")
        
        search_input = self.wait.until(EC.visibility_of_element_located(self.get_by("search_input")))
        search_input.clear()
        if row["search_term"]:
            search_input.send_keys(row["search_term"])
            
        try:
            fullsearch_cb = self.driver.find_element(*self.get_by("fullsearch_cb"))
            if not fullsearch_cb.is_selected():
                self.driver.execute_script("arguments[0].click();", fullsearch_cb)
        except NoSuchElementException:
            pass
            
        search_input.send_keys(Keys.RETURN)
        
    def verify_search(self, row):
        expected_type = row["expected_type"]
        expected_text = row["expected_text"]
        
        if expected_type in ("success", "success_search", "not_found"):
            try:
                self.wait.until(EC.visibility_of_element_located(self.get_by("text_xpath", text=expected_text)))
            except TimeoutException:
                print(f"\nDEBUG SEARCH: Could not find '{expected_text}'")
                raise
            self.assertIn(expected_text, self.driver.page_source)
        elif expected_type == "success_multiple":
            texts = expected_text.split('|')
            for t in texts:
                try:
                    self.wait.until(EC.visibility_of_element_located(self.get_by("text_xpath", text=t)))
                except TimeoutException:
                    print(f"\nDEBUG SEARCH MULTIPLE: Could not find '{t}'")
                    raise
                self.assertIn(t, self.driver.page_source)

    def browse_letter(self, row):
        self.driver.get("https://school.moodledemo.net/mod/glossary/view.php?id=570&mode=letter&hook=ALL")
        letter = row["letter"]
        link = self.wait.until(EC.element_to_be_clickable(self.get_by("letter_link", letter=letter)))
        self.driver.execute_script("arguments[0].click();", link)

if __name__ == "__main__":
    unittest.main()
