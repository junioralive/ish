import os
import subprocess
import sys

app_path = "C:/ish/app.py"
cf_app_path = "C:/ish/app_cf.py"

def local_start():
    """
    Entry point for the `ish` command.
    Assumes app.py is in the same directory where the `ish` command is run.
    """
    try:

        # Check if app.py exists in the current directory
        if not os.path.exists(app_path):
            print(f"Error: app.py not found in the current directory: {app_path}")
            sys.exit(1)

        # Start the Flask app using subprocess
        subprocess.run([sys.executable, app_path], check=True)
    except KeyboardInterrupt:
        print("\nServer stopped manually.")
    except Exception as e:
        print(f"Error: {e}")

def cf_start():
    """
    Entry point for the `ish` command.
    Assumes app_cf.py is in the same directory where the `ish` command is run.
    """
    try:

        # Check if app.py exists in the current directory
        if not os.path.exists(cf_app_path):
            print(f"Error: app.py not found in the current directory: {cf_app_path}")
            sys.exit(1)

        # Start the Flask app using subprocess
        subprocess.run([sys.executable, cf_app_path], check=True)
    except KeyboardInterrupt:
        print("\nServer stopped manually.")
    except Exception as e:
        print(f"Error: {e}")