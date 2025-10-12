import logging
logger = logging.getLogger(__name__)
import base64
import http.client

# API key authentication
class AirdataBaseClass_:
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

# Username and password authentication

class AirdataBaseClass:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.base_url = "api.airdata.com"
        self.authenticated = False
        self.auth_header = self._get_auth_header()
        self.authenticate(validate=True)

    def _get_auth_header(self):
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode("utf-8")
        return {
            "Authorization": f"Basic {encoded_credentials}"
        }

    def authenticate(self, validate=True):
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

            # If /version returns 404, try /flights as fallback
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
                    raise ValueError("Authentication failed: Invalid username/password or permissions.")

        except Exception as e:
            print(f"Network error during authentication: {e}")
            if validate:
                raise