import sys
print("STARTING SCRIPT")
sys.stdout.flush()
import os
print(f"CWD: {os.getcwd()}")
sys.stdout.flush()
try:
    import requests
    print("Requests imported")
except ImportError:
    print("Requests NOT found")
sys.stdout.flush()
print("FINISHED TEST")
