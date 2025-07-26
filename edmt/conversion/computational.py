# https://numpy.org/devdocs/reference/index.html
import numpy as np


import pandas as pd

def create_dataframe():
    data = {
        'A': [1, 2, 3],
        'B': [4, 5, 6],
        'C': [7, 8, 9]
    }
    df = pd.DataFrame(data)
    print("DataFrame created")
    return df