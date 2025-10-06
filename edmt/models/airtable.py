import requests
from datetime import datetime
from typing import Optional, Union
import pandas as pd
from urllib.parse import urlencode, quote

class Airtable:
    """
    A clean, modular Airtable API client with support for:
    - Authentication via Personal Access Token
    - Table-scoped operations
    - Date-based filtering
    - Pagination
    - Long URL safety (falls back to POST)
    """

    BASE_URL = "https://api.airtable.com/v0"

    def __init__(self, api_key: str):
        """
        Initialize the Airtable client with an API key.

        Args:
            api_key (str): Your Airtable Personal Access Token.
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })

    def table(self, base_id: str, table_id_or_name: str):
        """
        Bind to a specific Airtable table.

        Args:
            base_id (str): The base ID (e.g., appgA5zXXXXXXX).
            table_id_or_name (str): Table name or ID (e.g., 'Tasks', 'tbl...').

        Returns:
            TableContext: Inner class instance bound to the table.
        """
        return self.TableContext(
            base_id=base_id,
            table_id_or_name=table_id_or_name,
            base_url=f"{self.BASE_URL}/{base_id}/{table_id_or_name}",
            client=self.session
        )

    class TableContext:
        """
        Represents a specific table in a base. All data operations happen here.
        """

        def __init__(self, base_id: str, table_id_or_name: str, base_url: str, client: requests.Session):
            self.base_id = base_id
            self.table_id_or_name = table_id_or_name
            self.base_url = base_url
            self.client = client

        def get_events(
            self,
            since: Optional[Union[str, datetime]] = None,
            until: Optional[Union[str, datetime]] = None,
          ) -> pd.DataFrame:
          """
          Fetch records filtered by a date field and return as a pandas DataFrame.

          Uses only the essential parameters: date_field, start_date, end_date.
          All other options use safe defaults.

          Args:
              date_field (str): Name of the date field to filter on (default: 'Created Time').
              start_date (str or datetime, optional): Lower bound (inclusive).
              end_date (str or datetime, optional): Upper bound (inclusive).

          Returns:
              pd.DataFrame: DataFrame with columns 'id', 'createdTime', and all field values.
          """

          def format_date(d):
              if isinstance(d, datetime):
                  return d.isoformat()
              return d

          params = {
              "pageSize": 100,
              "cellFormat": "json"
          }

          all_records = []
          offset = None

          while True:
              if offset:
                  params["offset"] = offset

              encoded_params = urlencode(params, doseq=True, safe='', quote_via=quote)
              full_url = f"{self.base_url}?{encoded_params}"

              if len(full_url) >= 16000:
                  response = self.client.post(f"{self.base_url}/listRecords", json=params)
              else:
                  response = self.client.get(self.base_url, params=params)

              if response.status_code != 200:
                  try:
                      error = response.json()
                  except:
                      error = response.text
                  raise Exception(f"Airtable API Error [{response.status_code}]: {error}")

              data = response.json()
              records = data.get("records", [])
              all_records.extend(records)

              offset = data.get("offset")
              if not offset:
                  break

              __import__('time').sleep(0.2)

          rows = []
          for rec in all_records:
              row = {
                  "id": rec["id"],
                  "createdTime": rec["createdTime"]
              }
              row.update(rec["fields"])
              rows.append(row)

          df = pd.DataFrame(rows)

          df["createdTime"] = pd.to_datetime(df["createdTime"])
          if since and until is not None:
              df = df[(df["createdTime"] >= format_date(since)) & (df["createdTime"] <= format_date(until))]

          return df