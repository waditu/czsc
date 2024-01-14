import os
import pandas as pd
from czsc.utils.cache import disk_cache, home_path

temp_path = os.path.join(home_path, "temp")

# Create a simple function for testing
@disk_cache(path=temp_path, suffix="pkl", ttl=100)
def test_func(x):
    return x * 2

@disk_cache(path=temp_path, suffix="xlsx", ttl=100)
def test_xlsx(x):
    df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6], 'x': [x, x, x]})
    return df


def test_disk_cache():
    # Call the function
    result = test_func(5)

    # Check if the output is correct
    assert result == 10

    # Call the function again with the same argument
    result = test_func(5)

    # Check if the output is still correct
    assert result == 10

    # Check if the cache file exists
    files = os.listdir(temp_path)
    assert len(files) == 1

    # Call the function with a different argument
    result = test_xlsx(5)
    files = os.listdir(temp_path)
    assert len(files) == 2
    df = pd.read_excel(os.path.join(temp_path, files[1]))
    assert isinstance(df, pd.DataFrame)
