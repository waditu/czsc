import os
import pandas as pd
from czsc.utils.cache import disk_cache, home_path, empty_cache_path

empty_cache_path()
temp_path = os.path.join(home_path, "temp")


# Create a simple function for testing
@disk_cache(path=temp_path, suffix="pkl", ttl=100)
def run_func_x(x):
    return x * 2


@disk_cache(path=temp_path, suffix="txt", ttl=100)
def run_func_text(x):
    return f"hello {x}"


@disk_cache(path=temp_path, suffix="json", ttl=100)
def run_func_json(x):
    return {"a": 1, "b": 2, "x": x}


@disk_cache(path=temp_path, suffix="xlsx", ttl=100)
def run_func_y(x):
    df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6], 'x': [x, x, x]})
    return df


@disk_cache(path=temp_path, suffix="feather", ttl=100)
def run_feather(x):
    df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6], 'x': [x, x, x]})
    return df


@disk_cache(path=temp_path, suffix="parquet", ttl=100)
def run_parquet(x):
    df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6], 'x': [x, x, x]})
    return df


def test_disk_cache():
    # Call the function
    result = run_func_x(5)

    # Check if the output is correct
    assert result == 10

    # Call the function again with the same argument
    result = run_func_x(5)

    # Check if the output is still correct
    assert result == 10

    # Call the function with a different argument
    result = run_func_text(6)
    result = run_func_text(6)
    assert result == "hello 6"

    # Call the function with a different argument
    result = run_func_json(7)
    result = run_func_json(7)
    assert result == {"a": 1, "b": 2, "x": 7}

    result = run_feather(8)
    result = run_feather(8)
    assert isinstance(result, pd.DataFrame)

    result = run_parquet(9)
    result = run_parquet(9)
    assert isinstance(result, pd.DataFrame)

    # Check if the cache file exists
    files = os.listdir(os.path.join(temp_path, "run_func_x"))
    assert len(files) == 1

    # Call the function with a different argument
    result = run_func_y(5)
    files = os.listdir(os.path.join(temp_path, "run_func_y"))
    assert len(files) == 1
    file_xlsx = [x for x in files if x.endswith("xlsx")][0]
    df = pd.read_excel(os.path.join(temp_path, f"run_func_y/{file_xlsx}"))
    assert isinstance(df, pd.DataFrame)
