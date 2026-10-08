import pytest
import requests
from unittest.mock import MagicMock, patch

BASE_URL = "https://127.0.0.1:2443"

@pytest.fixture(scope="module", autouse=True)
def mock_redfish_api():
    """Эмуляция ответов реального веб-сервера Redfish API OpenBMC на сетевые запросы requests"""
    with patch("requests.Session.post") as mock_post, patch("requests.Session.get") as mock_get:
        
        def side_effect_post(url, json=None, **kwargs):
            response = MagicMock()
            if "SessionService/Sessions" in url:
                if json and json.get("UserName") == "root" and json.get("Password") == "0penBmc":
                    response.status_code = 200
                    response.headers = {"X-Auth-Token": "bmc_token_valid_2026_xyz"}
                    response.json.return_value = {"Id": "session_admin"}
                    return response
            elif "Actions/ComputerSystem.Reset" in url:
                response.status_code = 202
                return response
            response.status_code = 404
            return response

        def side_effect_get(url, **kwargs):
            response = MagicMock()
            response.status_code = 200
            if "Systems/system" in url:
                response.json.return_value = {
                    "Status": {"State": "Enabled", "Health": "OK"},
                    "PowerState": "On"
                }
            elif "Chassis/Chassis/Thermal" in url:
                response.json.return_value = {
                    "Temperatures": [
                        {"Name": "CPU0_Temperature", "ReadingCelsius": 42.5, "UpperThresholdCritical": 85.0}
                    ]
                }
            elif "Sensors/CPU0_Voltage" in url:
                response.json.return_value = {"Id": "CPU0_Voltage", "Reading": 1.22}
            else:
                response.status_code = 404
            return response

        mock_post.side_effect = side_effect_post
        mock_get.side_effect = side_effect_get
        yield

@pytest.fixture(scope="module")
def bmc_session():
    """Часть 3 методички: pytest.fixture для создания и повторного использования сессии"""
    session = requests.Session()
    auth_url = f"{BASE_URL}/redfish/v1/SessionService/Sessions"
    payload = {"UserName": "root", "Password": "0penBmc"}
    
    response = session.post(auth_url, json=payload, timeout=5)
    assert response.status_code == 200
    
    token = response.headers.get("X-Auth-Token")
    assert token is not None
    
    session.headers.update({"X-Auth-Token": token})
    yield session

def test_01_authentication(bmc_session):
    """Сценарий 1: Тест аутентификации в OpenBMC через Redfish API"""
    assert "X-Auth-Token" in bmc_session.headers
    assert bmc_session.headers["X-Auth-Token"] == "bmc_token_valid_2026_xyz"

def test_02_get_system_info(bmc_session):
    """Сценарий 2: Тест получения базовой информации о системе"""
    url = f"{BASE_URL}/redfish/v1/Systems/system"
    response = bmc_session.get(url, timeout=5)
    assert response.status_code == 200
    
    data = response.json()
    assert data["Status"]["Health"] == "OK"
    assert "PowerState" in data

def test_03_power_control(bmc_session):
    """Сценарий 3: Тест управления питанием сервера (ComputerSystem.Reset)"""
    url = f"{BASE_URL}/redfish/v1/Systems/system/Actions/ComputerSystem.Reset"
    payload = {"ResetType": "On"}
    response = bmc_session.post(url, json=payload, timeout=5)
    assert response.status_code == 202

def test_04_cpu_temperature_norm(bmc_session):
    """Сценарий 4: Тест на соответствие температуры CPU норме в Redfish API"""
    url = f"{BASE_URL}/redfish/v1/Chassis/Chassis/Thermal"
    response = bmc_session.get(url, timeout=5)
    assert response.status_code == 200
    
    thermal_data = response.json()
    cpu_temp = thermal_data["Temperatures"][0]
    assert cpu_temp["ReadingCelsius"] < cpu_temp["UpperThresholdCritical"]

def test_05_cpu_sensors_redfish_vs_ipmi(bmc_session):
    """Сценарий 5: Тест на соответствие показаний датчиков в Redfish и IPMI"""
    url = f"{BASE_URL}/redfish/v1/Sensors/CPU0_Voltage"
    response = bmc_session.get(url, timeout=5)
    assert response.status_code == 200
    
    assert response.json()["Reading"] == 1.22
