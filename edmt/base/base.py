import logging
logger = logging.getLogger(__name__)
import base64
import http.client
import requests
import pandas as pd
import requests
from io import StringIO
import time

logging.basicConfig(level=logging.WARNING)

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


def AirdataCSV(row, retries=3, timeout=10):
    """
    Fetch a single CSV from a URL with retry logic.
    Returns the parsed DataFrame or None on failure.
    """
    csv_link = row.get('csvLink')
    if not isinstance(csv_link, str) or not csv_link.strip():
        return None

    for attempt in range(retries):
        try:
            resp = requests.get(csv_link.strip(), timeout=timeout)
            resp.raise_for_status()
            csv_data = StringIO(resp.text)
            df = pd.read_csv(csv_data, low_memory=False)
            df['_source_url'] = csv_link
            return df
        except Exception as e:
            if attempt == retries - 1:
                # logging.warning(f"Failed to fetch {csv_link} after {retries} attempts: {e}")
                return None
            time.sleep(0.5 * (2 ** attempt))