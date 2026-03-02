import ctypes
import sys

print("Testing mutex...")

_APP_MUTEX = ctypes.windll.kernel32.CreateMutexW(None, True, "Global\\ZhiMoAI_AppBackend_SingleInstance")
error = ctypes.windll.kernel32.GetLastError()

print(f"Mutex handle: {_APP_MUTEX}")
print(f"GetLastError: {error}")

if error == 183:
    print("ERROR: Mutex already exists! Another instance is running.")
    ctypes.windll.kernel32.CloseHandle(_APP_MUTEX)
    sys.exit(1)
else:
    print("OK: Mutex acquired successfully")
    input("Press Enter to release mutex and exit...")
    ctypes.windll.kernel32.CloseHandle(_APP_MUTEX)
