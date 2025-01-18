import subprocess
import re

def uninstall_and_install_edmt():
    try:
        rm = subprocess.run(["pip", "uninstall", "edmt", "-y"], capture_output=True, text=True)
        if "Successfully uninstalled edmt" in rm.stdout:
            rm_match = re.search(r"Successfully uninstalled edmt-([\d\.]+)", rm.stdout)
            if rm_match:
                rm_version = rm_match.group(1)
                print(f"Successfully uninstalled edmt-{rm_version}")
        else:
            print("No matching version of edmt found to uninstall or uninstallation failed.")

        result = subprocess.run(["pip", "install", "."], capture_output=True, text=True)
        if "Successfully installed edmt" in result.stdout:
            match = re.search(r"Successfully installed edmt-([\d\.]+)", result.stdout)
            if match:
                version = match.group(1)
                print(f"Successfully installed edmt-{version}")
            else:
                print("Installation succeeded, but version information was not found.")
        else:
            print("Installation failed or no matching output found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    uninstall_and_install_edmt()
