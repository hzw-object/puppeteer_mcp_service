import json
import os

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.json")

class ConfigLoader:
    def __init__(self, config_path=None):
        self.config_path = config_path if config_path else DEFAULT_CONFIG_PATH
        self.config = self._load_config()

    def _load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
            # Basic validation (can be expanded)
            if not isinstance(config_data.get("service"), dict):
                raise ValueError("Service configuration is missing or invalid.")
            if not isinstance(config_data.get("browser_type"), str):
                raise ValueError("Browser type configuration is missing or invalid.")
            return config_data
        except FileNotFoundError:
            print(f"Error: Configuration file not found at {self.config_path}")
            # Fallback to some very basic defaults or raise an error
            # For now, let's raise an error as config is crucial
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in configuration file: {self.config_path}")
            raise ValueError(f"Invalid JSON in configuration file: {self.config_path}")
        except ValueError as ve:
            print(f"Error: Configuration validation failed: {ve}")
            raise

    def get(self, key, default=None):
        return self.config.get(key, default)

    def get_browser_config(self):
        return {
            "browser_type": self.get("browser_type", "chromium"),
            "headless": self.get("headless", True),
            "user_agent": self.get("user_agent"),
            "viewport_size": self.get("viewport_size"),
            "slow_mo": self.get("slow_mo", 0),
            "proxy": self.get("proxy")
        }

    def get_service_config(self):
        service_cfg = self.get("service", {})
        return {
            "host": service_cfg.get("host", "0.0.0.0"),
            "port": service_cfg.get("port", 8080),
            "log_level": service_cfg.get("log_level", "INFO"),
            "default_timeout": service_cfg.get("default_timeout", 30000)
        }

    def get_security_config(self):
        return self.get("security", {})

# Example usage (for testing purposes, will be removed or refactored)
if __name__ == '__main__':
    # Create a dummy config.json for testing if it doesn't exist
    # In a real scenario, this would be outside the app directory
    dummy_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.json")
    if not os.path.exists(dummy_config_path):
        print(f"Creating dummy config at {dummy_config_path} for testing config_loader.")
        dummy_data = {
            "browser_type": "chromium",
            "headless": True,
            "user_agent": "Mozilla/5.0 Test",
            "viewport_size": {"width": 1920, "height": 1080},
            "slow_mo": 50,
            "proxy": None,
            "service": {
                "host": "127.0.0.1",
                "port": 8888,
                "log_level": "DEBUG",
                "default_timeout": 60000
            },
            "security": {"api_key": "test_key"}
        }
        with open(dummy_config_path, 'w') as f:
            json.dump(dummy_data, f, indent=4)

    try:
        loader = ConfigLoader()
        print("Config loaded successfully!")
        print("Browser Config:", loader.get_browser_config())
        print("Service Config:", loader.get_service_config())
        print("Security Config:", loader.get_security_config())
        print("Raw 'headless' value:", loader.get("headless"))
    except Exception as e:
        print(f"Error during ConfigLoader test: {e}")

