import os
import unittest



from common.driver_factory import DriverFactory
from common.login_helper import LoginHelper

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class CourseAuthorizationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver = DriverFactory.get_driver()
        cls.wait = WebDriverWait(cls.driver, 15)
        # Using student role, which should NOT have course creation rights
        LoginHelper.login(cls.driver, username="student", password="moodle26")

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def test_student_cannot_add_course(self):
        driver = self.driver
        wait = self.wait

        driver.get("https://school.moodledemo.net/course/edit.php?category=0")
        
        # We expect Moodle to either show an error message like "Sorry, but you do not currently have permissions to do that (Create new courses)."
        # Or redirect somewhere else or show a general error
        
        try:
            error_element = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-danger, .errormessage")))
            self.assertTrue(error_element.is_displayed())
            print(f"Authorization blocked correctly. Message: {error_element.text}")
        except Exception:
            # If we don't see an error message, check if the form is missing
            elements = driver.find_elements(By.ID, "id_fullname")
            self.assertEqual(len(elements), 0, "Security issue: Student can see the Add Course form!")

if __name__ == "__main__":
    unittest.main()
