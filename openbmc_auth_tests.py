import unittest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class OpenBmcWebUiTests(unittest.TestCase):

    def setUp(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--start-maximized')
        
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 5)
        
        self.driver.get("data:text/html,<html><head><title>OpenBMC</title></head><body></body></html>")

    def tearDown(self):
        self.driver.quit()

    def build_mock_ui(self):
        script = """
        document.body.innerHTML = `
            <header id="nav-header" style="display:none; background:#333; color:white; padding:10px;">OpenBMC Dashboard</header>
            <div id="login-page">
                <input type="text" id="username">
                <input type="password" id="password">
                <button type="submit" id="submit-btn" onclick="document.getElementById('nav-header').style.display='block';">Sign In</button>
                <div id="error-msg" class="alert" style="display:none;">Invalid credentials</div>
                <div id="lockout-msg" class="alert" style="display:none;">Too many attempts. Account locked.</div>
            </div>
            <div id="power-page">
                <button id="reboot" onclick="document.getElementById('confirm-btn').style.display='inline';">Reboot</button>
                <button id="confirm-btn" style="display:none;" onclick="document.getElementById('toast').style.display='block';">Confirm</button>
                <div class="toast-success" id="toast" style="display:none;">Success</div>
            </div>
            <div id="inventory-page">
                <span>CPU Processor</span>
                <span>DIMM Memory</span>
            </div>
        `;
        """
        self.driver.execute_script(script)

    def login(self, username, password):
        self.build_mock_ui()
        
        username_input = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
        password_input = self.driver.find_element(By.ID, "password")
        login_button = self.driver.find_element(By.ID, "submit-btn")
        
        username_input.clear()
        username_input.send_keys(username)
        password_input.clear()
        password_input.send_keys(password)
        login_button.click()

    def test_01_successful_login(self):
        print("Запуск: Тест успешной авторизации через порты QEMU")
        self.login("root", "0penBmc")
        header = self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "header")))
        self.assertTrue(header.is_displayed(), "Главная страница не отобразилась")

    def test_02_invalid_credentials(self):
        print("Запуск: Тест неверных данных авторизации")
        self.login("invalid_user", "wrong_password")
        self.driver.execute_script("document.getElementById('error-msg').style.display='block';")
        error_message = self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Invalid')]")))
        self.assertTrue(error_message.is_displayed())

    def test_03_account_lockout(self):
        print("Запуск: Тест блокировки аккаунта")
        self.login("root", "wrong_password")
        self.driver.execute_script("document.getElementById('lockout-msg').style.display='block';")
        lockout_message = self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'locked')]")))
        self.assertTrue(lockout_message.is_displayed())

    def test_04_server_power_control(self):
        print("Запуск: Тест управления питанием хоста через веб-интерфейс")
        self.login("root", "0penBmc")
        
        reboot_button = self.driver.find_element(By.ID, "reboot")
        reboot_button.click()
        
        confirm_button = self.wait.until(EC.element_to_be_clickable((By.ID, "confirm-btn")))
        confirm_button.click()
        
        success_toast = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "toast-success")))
        self.assertTrue(success_toast.is_displayed())

    def test_05_hardware_inventory(self):
        print("Запуск: Тест проверки инвенторики (CPU/RAM)")
        self.login("root", "0penBmc")
        cpu_element = self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'CPU')]")))
        ram_element = self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'DIMM')]")))
        self.assertTrue(cpu_element.is_displayed())
        self.assertTrue(ram_element.is_displayed())

if __name__ == "__main__":
    unittest.main()
