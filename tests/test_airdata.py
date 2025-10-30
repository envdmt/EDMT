import edmt
from edmt.conversion import to_gdf

# print(f"EDMT Version: {edmt.__version__}")
# # print all funtions in Airdata
# airdata_functions = [func for func in dir(Airdata) if callable(getattr(Airdata, func)) and not func.startswith("__")]
# print("Airdata Functions:")
# for func in airdata_functions:
#     print(f"- {func}")


def test_airdata():
    assert 1 + 1 == 2
