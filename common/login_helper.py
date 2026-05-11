from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class LoginHelper:
    @staticmethod
    def login(driver, url="https://school.moodledemo.net/login/index.php", username="student", password="moodle26", timeout=15):
        wait = WebDriverWait(driver, timeout)
        driver.get(url)
        
        wait.until(EC.visibility_of_element_located((By.ID, "username"))).send_keys(username)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.ID, "loginbtn").click()
        
        wait.until(EC.presence_of_element_located((By.ID, "page")))

    @staticmethod
    def ensure_logged_in(driver, return_url=None, username="student", password="moodle26", timeout=5):
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.ID, "user-menu-toggle"))
            )
            return
        except TimeoutException:
            LoginHelper.login(driver, username=username, password=password)
            if return_url:
                driver.get(return_url)
