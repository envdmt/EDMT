edmt.base.base
==============

.. py:module:: edmt.base.base








Module Contents
---------------

.. py:data:: logger

.. py:class:: AirdataBaseClass(api_key)

   .. py:attribute:: api_key


   .. py:attribute:: base_url
      :value: 'api.airdata.com'



   .. py:attribute:: authenticated
      :value: False



   .. py:attribute:: auth_header


   .. py:method:: _get_auth_header()


   .. py:method:: authenticate(validate=True)

      Authenticates with the API by calling /version or /flights.



.. py:function:: ExtractCSV(row, col: str, max_retries: int = 3, timeout: int = 15) -> pandas.DataFrame

   Fetches a CSV file from a URL specified in a given column of a metadata record.

   This function retrieves a CSV file from the URL found in the specified column (`col`)
   of the input `row`, parses it into a pandas DataFrame, and returns the result.
   It includes retry logic with exponential backoff to handle transient network errors.

   Args:
       row (dict or pandas.Series): A metadata record containing a URL string in the 
           column specified by `col`.
       col (str): The key or column name in `row` that contains the URL to the CSV file.
       max_retries (int, optional): Maximum number of retry attempts in case of failure.
           Defaults to 3.
       timeout (int or float, optional): Timeout for each HTTP request in seconds.
           Defaults to 15 seconds.

   Returns:
       pandas.DataFrame or None:
           - A pandas DataFrame containing the parsed CSV data if successful.
           - `None` if the URL is missing, invalid, or if all retry attempts fail.

   Raises:
       None


