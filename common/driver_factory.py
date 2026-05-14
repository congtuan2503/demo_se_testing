from selenium import webdriver

class DriverFactory:
    @staticmethod
    def get_driver(browser="chrome"):
        if browser.lower() == "chrome":
            driver = webdriver.Chrome()
        elif browser.lower() == "firefox":
            driver = webdriver.Firefox()
        elif browser.lower() == "edge":
            driver = webdriver.Edge()
        else:
            raise ValueError(f"Browser {browser} is not supported.")
        
        # driver.maximize_window()
        return driver
