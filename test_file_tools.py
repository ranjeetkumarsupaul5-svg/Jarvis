from backend.tools.file_tools import (
    create_folder,
    create_file,
    read_file,
    list_folder,
    search_files,
    delete_file
)


TEST_FOLDER = "jarvis_test"
TEST_FILE = "jarvis_test/test.txt"


print("\n--- CREATE FOLDER ---")
print(create_folder(TEST_FOLDER))


print("\n--- CREATE FILE ---")
print(
    create_file(
        TEST_FILE,
        "Hello! This file was created by JARVIS."
    )
)


print("\n--- READ FILE ---")
print(read_file(TEST_FILE))


print("\n--- LIST FOLDER ---")
print(list_folder(TEST_FOLDER))


print("\n--- SEARCH FILE ---")
print(search_files(".", "test.txt"))


print("\n--- DELETE FILE ---")
print(delete_file(TEST_FILE))