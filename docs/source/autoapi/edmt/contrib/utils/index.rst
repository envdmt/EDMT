edmt.contrib.utils
==================

.. py:module:: edmt.contrib.utils




Module Contents
---------------

.. py:function:: clean_vars(addl_kwargs={}, **kwargs)

.. py:function:: normalize_column(df, col)

.. py:function:: clean_time_cols(df, columns=[])

.. py:function:: format_iso_time(date_string: str) -> str

.. py:function:: norm_exp(df: pandas.DataFrame, cols: Union[str, list]) -> pandas.DataFrame

   Normalizes specified columns containing list of dicts,
   expands them into separate rows if needed,
   and appends new columns to the original dataframe with prefixing.

   Parameters:
   - df: Original pandas DataFrame
   - cols: str or list of str, names of columns to normalize

   Returns:
   - Modified DataFrame with normalized and expanded data


.. py:function:: append_cols(df: pandas.DataFrame, cols: Union[str, list])

   Move specified column(s) to the end of the DataFrame.

   Parameters:
       df (pd.DataFrame): Input DataFrame.
       cols (str or list): Column name(s) to move to the end.

   Returns:
       pd.DataFrame: DataFrame with columns reordered.


.. py:function:: dict_expand(data, cols)

