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



class AirtableBaseClass:
    BASE_URL = "https://api.airtable.com/v0"

    def __init__(self, api_key: str, validate: bool = True):
        """
        Initialize the Airtable client with an API key.

        Args:
            api_key (str): Your Airtable Personal Access Token.
            validate (bool): If True, immediately validate the API key via a test request.
        """
        if not api_key or not isinstance(api_key, str):
            raise ValueError("API key must be a non-empty string.")

        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
        self.authenticated = False

        if validate:
            self.authenticate()

    def authenticate(self) -> bool:
        """
        Validate the API key by making a lightweight request to the Airtable API.

        Returns:
            bool: True if authentication is successful.

        Raises:
            requests.HTTPError: If the request fails due to invalid credentials or network issues.
        """
        
        url = f"{self.BASE_URL}/meta/bases"
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                self.authenticated = True
                return True
            elif response.status_code == 401 or response.status_code == 403:
                raise requests.HTTPError(
                    f"Authentication failed: Invalid or missing API key. "
                    f"Status: {response.status_code}, Response: {response.text[:200]}"
                )
            else:
                response.raise_for_status()
        except requests.RequestException as e:
            raise ConnectionError(f"Failed to authenticate with Airtable API: {e}") from e

        return False