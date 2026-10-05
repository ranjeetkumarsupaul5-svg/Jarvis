from backend.tools.system_tools import (
    open_application,
    get_system_info,
    take_screenshot,
    get_screen_size,
    minimize_all_windows
)


print("\n--- SYSTEM INFO ---")
print(get_system_info())

print("\n--- SCREEN SIZE ---")
print(get_screen_size())

print("\n--- OPENING NOTEPAD ---")
print(open_application("notepad"))

print("\n--- TAKING SCREENSHOT ---")
print(take_screenshot())