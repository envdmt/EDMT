import logging
logger = logging.getLogger(__name__)
import base64
import http.client
from typing import Optional
import requests


# API key authentication
class AirdataBaseClass:
        def __init__(self, api_key):
            self.api_key = api_key
            self.base_url = "api.airdata.com"
            self.authenticated = False
            self.auth_header = self._get_auth_header()

            self.authenticate(validate=True)

        def _get_auth_header(self):
            key_with_colon = self.api_key + ":"
            encoded_key = base64.b64encode(key_with_colon.encode()).decode("utf-8")
            return {
                "Authorization": f"Basic {encoded_key}"
            }

        def authenticate(self,validate=True):
            """
            Authenticates with the API by calling /version or /flights.
            """
            conn = http.client.HTTPSConnection(self.base_url)
            payload = ''

            try:
                conn.request("GET", "/version", payload, self.auth_header)
                res = conn.getresponse()
                
                if res.status == 200:
                    self.authenticated = True
                    print("Authentication successful.")
                    return

                if res.status == 404:
                    conn = http.client.HTTPSConnection(self.base_url)
                    conn.request("GET", "/flights", payload, self.auth_header)
                    res = conn.getresponse()

                if res.status == 200:
                    self.authenticated = True
                    print("Authentication successful.")
                else:
                    print(f"Authentication failed. Status code: {res.status}")
                    print(f"Response: {res.read().decode('utf-8')[:200]}")
                    if validate:
                        raise ValueError("Authentication failed: Invalid API key or permissions.")

            except Exception as e:
                print(f"Network error during authentication: {e}")
                if validate:
                    raise



# Configure logging (you can adjust level/format as needed)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AirtableBaseClass:
    BASE_URL = "https://api.airtable.com/v0"

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
    ):
        """
        Initialize the Airtable client with an API key.

        Args:
            api_key (str): Your Airtable Personal Access Token.
            base_url (str, optional): Override the default API base URL (useful for mocking/testing).
        """
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("API key must be a non-empty string.")

        self.api_key = api_key.strip()
        self.base_url = (base_url or self.BASE_URL).rstrip('/')

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })

        logger.info("Airtable client initialized successfully.")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make a request to the Airtable API with error handling.

        Args:
            method (str): HTTP method (e.g., 'GET', 'POST').
            endpoint (str): API endpoint (e.g., '/appXXX/TableName').
            **kwargs: Additional arguments passed to requests (e.g., json, params).

        Returns:
            requests.Response: The API response.

        Raises:
            requests.exceptions.HTTPError: For HTTP error responses.
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Making {method} request to {url}")

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error occurred: {e} - Response: {response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

    def close(self):
        """Close the session."""
        self.session.close()
        logger.debug("Airtable session closed.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
