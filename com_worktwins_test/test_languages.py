import time
import pytest
from com_worktwins_languages.Language import Language  # Replace 'your_module' with the actual module name

@pytest.fixture(scope="module")
def language_instance():
    # Initialize the Language class with the path to your YAML file
    yaml_file = 'com_worktwins_data/languages.yml'  # Update with the correct path
    return Language(yaml_file)

def test_get_language_attributes(language_instance):
    language_name = 'Python'
    start_time = time.time()
    attributes = language_instance.get_language_attributes(language_name)
    end_time = time.time()
    print(f"Execution time for get_language_attributes: {end_time - start_time:.6f} seconds")
    assert attributes is not None
    assert attributes['name'] == language_name

def test_find_by_extension(language_instance):
    extension = '.py'
    start_time = time.time()
    languages = language_instance.find_by_extension(extension)
    end_time = time.time()
    print(f"Execution time for find_by_extension: {end_time - start_time:.6f} seconds")
    assert 'Python' in languages

def test_find_by_alias(language_instance):
    alias = 'python3'
    start_time = time.time()
    languages = language_instance.find_by_alias(alias)
    end_time = time.time()
    print(f"Execution time for find_by_alias: {end_time - start_time:.6f} seconds")
    assert 'Python' in languages

def test_find_by_interpreter(language_instance):
    interpreter = 'python3'
    start_time = time.time()
    languages = language_instance.find_by_interpreter(interpreter)
    end_time = time.time()
    print(f"Execution time for find_by_interpreter: {end_time - start_time:.6f} seconds")
    assert 'Python' in languages
