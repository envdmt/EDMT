def test_example():
    assert 1 + 1 == 2


# import edmt
# import pandas as pd

# def test_generate_uuid():
#     """
#     Test the 'generate_uuid' function from the 'edmt.conversion' module.

#     Steps:
#     1. Create a sample DataFrame with dummy data.
#     2. Pass the DataFrame to the 'generate_uuid' function.
#     3. Verify that the returned DataFrame includes a 'uuid' column.
#     4. Ensure all values in the 'uuid' column are unique.
#     """

#     # Step 1: Create a sample DataFrame
#     df = pd.DataFrame(
#         {
#             "name": ["Odero", "Kuloba", "Musasia"],
#             "place": ["Narok", "Narok", "Nairobi"]
#         }
#     )

#     # Step 2: Call the 'generate_uuid' function
#     updated_df = edmt.conversion.generate_uuid(df)

#     # Step 3: Assert that the 'uuid' column exists in the DataFrame
#     assert "uuid" in updated_df.columns, "The 'uuid' column should be present in the DataFrame."

#     # Step 4: Assert that all UUIDs are unique
#     assert updated_df["uuid"].nunique() == len(updated_df), "All UUIDs should be unique for each row."
