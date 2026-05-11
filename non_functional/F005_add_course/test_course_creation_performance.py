import os
import unittest
import time
import uuid



from common.driver_factory import DriverFactory
from common.login_helper import LoginHelper

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

class CourseCreationPerformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver = DriverFactory.get_driver()
        cls.wait = WebDriverWait(cls.driver, 15)
        # Using manager to ensure course creation rights
        LoginHelper.login(cls.driver, username="manager", password="moodle26")

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def test_course_creation_response_time(self):
        driver = self.driver
        wait = self.wait

        short_name = "PERF-" + uuid.uuid4().hex[:6]
        
        # Navigate to Add Course via UI clicks
        driver.get("https://school.moodledemo.net/")
        try:
            wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "My course"))).click()
        except Exception:
            driver.find_element(By.XPATH, "//a[contains(text(), 'My course')]").click()
            
        locators = [
            (By.XPATH, "//*[contains(text(), 'Create course')]"),
            (By.XPATH, "//*[contains(text(), 'Add a new course')]"),
            (By.PARTIAL_LINK_TEXT, "Create course"),
            (By.PARTIAL_LINK_TEXT, "Add a new course"),
        ]
        for loc in locators:
            try:
                WebDriverWait(driver, 3).until(EC.element_to_be_clickable(loc)).click()
                break
            except Exception:
                pass
        
        wait.until(EC.visibility_of_element_located((By.ID, "id_fullname"))).send_keys("Performance Test Course")
        driver.find_element(By.ID, "id_shortname").send_keys(short_name)
        
        try:
            category_select = Select(driver.find_element(By.ID, "id_category"))
            category_select.select_by_index(1)
        except:
            pass
            
        # Measure time for saving course
        start_time = time.time()
        
        driver.find_element(By.ID, "id_saveanddisplay").click()
        
        # Wait until the course is created and page redirected
        wait.until(EC.visibility_of_element_located((By.XPATH, "//header")))
        self.assertIn("Performance Test Course", driver.page_source)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        print(f"Course creation response time: {response_time:.2f} seconds")
        
        # Performance requirement: Should be less than 10 seconds for demo server
        self.assertLess(response_time, 10.0, "Course creation took longer than 10 seconds!")

if __name__ == "__main__":
    unittest.main()
