import os
import unittest
import time

from common.driver_factory import DriverFactory
from common.login_helper import LoginHelper
from common.csv_reader import CSVReader

from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "glossary_level1.csv")

class GlossaryLevel1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver = DriverFactory.get_driver()
        cls.wait = WebDriverWait(cls.driver, 15)
        LoginHelper.login(cls.driver, username="student", password="moodle26")

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def test_glossary_data_driven(self):
        test_data = CSVReader.read_data(DATA_FILE, delimiter=",")

        for row in test_data:
            test_case_id = row["test_case_id"]
            print(f"\nRunning {test_case_id} - Expected: {row['expected_type']}")

            with self.subTest(test_case_id=test_case_id):
                action_type = row["action_type"]

                if row["expected_type"] in ("success", "success_search") and "add" in action_type:
                    import uuid
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
        
        # Click Add a new entry
        try:
            add_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Add entry') or contains(text(), 'Add a new entry')]")))
            self.driver.execute_script("arguments[0].click();", add_btn)
        except TimeoutException:
            # Fallback for input type submit
            add_btn = self.driver.find_element(By.XPATH, "//input[@type='submit' and contains(@value, 'Add a new entry')]")
            self.driver.execute_script("arguments[0].click();", add_btn)
            
        self.wait.until(EC.visibility_of_element_located((By.ID, "id_concept")))
        
        self.driver.find_element(By.ID, "id_concept").clear()
        if row["concept"]:
            self.driver.find_element(By.ID, "id_concept").send_keys(row["concept"])
            
        if row["definition"]:
            self.wait.until(EC.frame_to_be_available_and_switch_to_it(0))
            body = self.driver.find_element(By.ID, "tinymce")
            body.clear()
            body.send_keys(row["definition"])
            self.driver.switch_to.default_content()
            
        self.driver.execute_script("if(typeof tinymce !== 'undefined') tinymce.triggerSave();")
            
        submit_btn = self.driver.find_element(By.ID, "id_submitbutton")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
        time.sleep(1)
        try:
            submit_btn.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", submit_btn)
        
        # Wait for submit button to become stale, meaning the page has submitted
        try:
            self.wait.until(EC.staleness_of(submit_btn))
        except TimeoutException:
            pass

    def verify_add(self, row):
        expected_type = row["expected_type"]
        expected_text = row["expected_text"]
        self.driver.save_screenshot(f"debug_{row['test_case_id']}.png")
        
        if expected_type in ("success", "success_search"):
            content_to_check = row["concept"].strip() or row["definition"].strip()
            try:
                self.wait.until(lambda d: content_to_check in d.page_source)
            except TimeoutException:
                print(f"\nDEBUG: Could not find '{content_to_check}'")
                raise
            
            # Additional wait to ensure text is present
            try:
                self.wait.until(lambda d: expected_text in d.page_source)
            except TimeoutException:
                print(f"\nDEBUG: Could not find '{expected_text}' in page source.")
                raise AssertionError(f"'{expected_text}' not found in page source.")
            
        elif expected_type == "error_concept":
            error = self.wait.until(EC.visibility_of_element_located((By.ID, "id_error_concept")))
            self.assertIn(expected_text, error.text)
            
        elif expected_type == "error_definition":
            error = self.wait.until(EC.visibility_of_element_located((By.ID, "id_error_definition_editor")))
            self.assertIn(expected_text, error.text)
            
        elif expected_type == "error_both":
            error_concept = self.wait.until(EC.visibility_of_element_located((By.ID, "id_error_concept")))
            error_def = self.wait.until(EC.visibility_of_element_located((By.ID, "id_error_definition_editor")))
            self.assertIn("You must supply a value here.", error_concept.text)
            self.assertIn("Required", error_def.text)
            
        elif expected_type == "error_db":
            error = self.wait.until(EC.visibility_of_element_located((By.XPATH, "//p[contains(@class, 'errormessage')]")))
            self.assertIn(expected_text, error.text)
            
        elif expected_type == "error_duplicate":
            error = self.wait.until(EC.visibility_of_element_located((By.ID, "id_error_concept")))
            self.assertIn(expected_text, error.text)

    def search_entry(self, row):
        self.driver.get("https://school.moodledemo.net/mod/glossary/view.php?id=570&mode=letter&hook=ALL")
        
        search_input = self.wait.until(EC.visibility_of_element_located((By.NAME, "hook")))
        search_input.clear()
        if row["search_term"]:
            search_input.send_keys(row["search_term"])
            
        try:
            fullsearch_cb = self.driver.find_element(By.NAME, "fullsearch")
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
                self.wait.until(EC.visibility_of_element_located((By.XPATH, f"//*[contains(., '{expected_text}')]")))
            except TimeoutException:
                print(f"\nDEBUG SEARCH: Could not find '{expected_text}'")
                print("DEBUG SEARCH: Page Source snippet:")
                print(self.driver.page_source[-2000:])
                raise
            self.assertIn(expected_text, self.driver.page_source)
        elif expected_type == "success_multiple":
            texts = expected_text.split('|')
            for t in texts:
                try:
                    self.wait.until(EC.visibility_of_element_located((By.XPATH, f"//*[contains(., '{t}')]")))
                except TimeoutException:
                    print(f"\nDEBUG SEARCH MULTIPLE: Could not find '{t}'")
                    raise
                self.assertIn(t, self.driver.page_source)

    def browse_letter(self, row):
        self.driver.get("https://school.moodledemo.net/mod/glossary/view.php?id=570&mode=letter&hook=ALL")
        letter = row["letter"]
        link = self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, letter)))
        self.driver.execute_script("arguments[0].click();", link)

if __name__ == "__main__":
    unittest.main()