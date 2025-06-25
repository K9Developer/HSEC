import os
import sys
import subprocess
import urllib.request
import shutil
import time

def check_python_version():
    """Ensure Python 3.12.0 or higher is being used"""
    required_version = (3, 12, 0)
    current_version = sys.version_info[:3]
    
    if current_version < required_version:
        print(f"ERROR: Python {'.'.join(map(str, required_version))} or higher is required.")
        print(f"Current Python version: {'.'.join(map(str, current_version))}")
        print("Please install Python 3.12.0 or higher and run this script again.")
        sys.exit(1)
    
    print(f"Python version check passed: {'.'.join(map(str, current_version))}")

# Check Python version before proceeding
check_python_version()

def ensure_vc_redist():
    from pathlib import Path

    def dll_exists(dll_name):
        sys_dirs = [
            os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32"),
            os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "SysWOW64"),
        ]
        return any((Path(d) / dll_name).exists() for d in sys_dirs)

    if dll_exists("vcruntime140.dll"):
        print("Microsoft Visual C++ Redistributable appears to be installed.")
        return

    print("Microsoft Visual C++ Redistributable is not installed or not found.")
    url = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
    out = "vc_redist.x64.exe"
    
    try:
        print("Downloading Microsoft Visual C++ Redistributable...")
        urllib.request.urlretrieve(url, out)
        print("Installing Microsoft Visual C++ Redistributable (silent)...")
        # Silent install: /quiet /install
        ret = subprocess.run([out, "/quiet", "/install"], shell=True, capture_output=True, text=True)
        if ret.returncode == 0:
            print("VC++ Redistributable installed successfully.")
        else:
            error_msg = f"VC++ Redistributable installer returned error code {ret.returncode}"
            if ret.stderr.strip():
                error_msg += f"\nError output: {ret.stderr.strip()}"
            print(error_msg)
    except Exception as e:
        print(f"Error during VC++ Redistributable installation: {e}")
    finally:
        try:
            os.remove(out)
        except Exception:
            pass

def force_delete(path):
    try:
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        elif os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"Error deleting {path}: {e}")

def get_request(url: str):
    try:
        response = urllib.request.urlopen(url)
        return response.read()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def is_command_available(cmd):
    """Check if a command is available in PATH"""
    subprocess.run(
        ["cmd.exe", "/c", f"where {cmd}"],
        capture_output=True,
        text=True
    )
    available = shutil.which(cmd) is not None
    if not available:
        print(f"Command '{cmd}' not found in PATH")
    return available

def run(cmd, cwd=None, check=True):
    print(f"> {cmd}")
    result = subprocess.run(
        ["cmd.exe", "/c", cmd],
        cwd=cwd,
        shell=False,
        capture_output=True,
        text=True
    )
    if check and result.returncode != 0:
        error_msg = f"Command failed: {cmd}\nReturn code: {result.returncode}"
        if result.stderr.strip():
            error_msg += f"\nError output: {result.stderr.strip()}"
        if result.stdout.strip():
            error_msg += f"\nStdout: {result.stdout.strip()}"
        raise RuntimeError(error_msg)
    return result.returncode

def install_packages(packages, max_retries=3):
    for package, version in packages:
        attempt = 1
        while attempt <= max_retries:
            try:
                print(f"Installing {package}=={version} (attempt {attempt}/{max_retries})")
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", f"{package}=={version}", "--force-reinstall", "--user"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                if result.returncode == 0:
                    print(f"{package}=={version} installed successfully.")
                    break
                else:
                    print(f"pip install failed with code {result.returncode}")
                    if result.stderr.strip():
                        print(f"Error details: {result.stderr.strip()}")
            except Exception as e:
                print(f"Error installing {package}: {e}")
            if attempt == max_retries:
                error_msg = f"Failed to install {package}=={version} after {max_retries} attempts."
                if 'result' in locals() and result.stderr:
                    error_msg += f"\nLast error: {result.stderr.strip()}"
                raise RuntimeError(error_msg)
            print(f"Retrying {package}...")
            time.sleep(2)
            attempt += 1

def ensure_node_installed():
    if is_command_available("node"):
        print("Node.js is already installed.")
        return False
    
    print("Node.js not found. Downloading and installing Node.js v22.16.0...")
    try:
        os.makedirs("nodetmp", exist_ok=True)
        msi_path = "nodetmp/nodejs.msi"
        print("Downloading Node.js installer...")
        urllib.request.urlretrieve("https://nodejs.org/dist/v22.16.0/node-v22.16.0-x64.msi", msi_path)
        while not os.path.exists(msi_path):
            time.sleep(1)
        print("Installing Node.js...")
        run("cd nodetmp && msiexec /i nodejs.msi /qn /norestart")
        print("\n[INFO] Node.js installed successfully.")
    except Exception as e:
        raise RuntimeError(f"Failed to install Node.js: {e}")

    print("============================================")
    print("Node.js has just been installed.")
    print("To continue, please:")
    print("  1. Close this terminal window.")
    print("  2. Open a **new Command Prompt** (Win+R, type 'cmd', press Enter).")
    print("  3. Run this script again: python setup.py")
    print("============================================")
    sys.exit(0)
    
def ensure_yarn_installed():
    if is_command_available("yarn"):
        print("Yarn is already installed.")
        return
    print("Yarn not found. Installing yarn globally via npm...")
    run("npm install -g yarn")

def ensure_vite_installed():
    if run("npm list -g vite@latest", check=False) == 0:
        print("Vite is already installed.")
        return
    print("Installing vite globally...")
    run("npm install -g vite@latest")

def install_client_deps():
    print("Installing client dependencies via yarn...")
    run("yarn install --force", cwd="HSEC/hsec-client")

def validate_client_installation():
    """Validate that the client installation is complete and correct"""
    print("Validating client installation...")
    
    # Check if package.json exists
    package_json_path = "HSEC/hsec-client/package.json"
    if not os.path.exists(package_json_path):
        raise RuntimeError("Client validation failed: package.json not found in HSEC/hsec-client/")
    
    # Check if node_modules exists
    node_modules_path = "HSEC/hsec-client/node_modules"
    if not os.path.exists(node_modules_path):
        raise RuntimeError("Client validation failed: node_modules directory not found. Dependencies may not be installed.")
    
    # Check if yarn.lock exists (indicates successful yarn install)
    yarn_lock_path = "HSEC/hsec-client/yarn.lock"
    if not os.path.exists(yarn_lock_path):
        print("Warning: yarn.lock not found. This might indicate an incomplete installation.")
    
    # Test if yarn dev command would work by checking if vite is available
    try:
        result = subprocess.run(
            ["cmd.exe", "/c", "yarn", "list", "--pattern", "vite"],
            cwd="HSEC/hsec-client",
            capture_output=True,
            text=True
        )
        if result.returncode != 0 or "vite" not in result.stdout.lower():
            raise RuntimeError("Client validation failed: Vite not found in dependencies. Client may not run properly.")
    except Exception as e:
        print(f"Warning: Could not verify Vite installation: {e}")
    
    # Check critical files exist
    critical_files = [
        "HSEC/hsec-client/index.html",
        "HSEC/hsec-client/vite.config.ts",
        "HSEC/hsec-client/src/main.tsx"
    ]
    
    for file_path in critical_files:
        if not os.path.exists(file_path):
            raise RuntimeError(f"Client validation failed: Critical file missing: {file_path}")
    
    print("Client installation validation passed!")

def validate_node_and_yarn():
    """Validate that Node.js and Yarn are properly installed"""
    # Check Node.js version
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            raise RuntimeError(f"Node.js validation failed: {result.stderr.strip()}")
        
        node_version = result.stdout.strip()
        print(f"Node.js version: {node_version}")
        
        # Check if version is acceptable (v22 or higher)
        version_num = node_version.replace('v', '').split('.')[0]
        if int(version_num) < 22:
            print(f"Warning: Node.js version {node_version} detected. Recommended version is v22 or higher.")
    
    except Exception as e:
        raise RuntimeError(f"Node.js validation failed: {e}")
    
    # Check Yarn version
    try:
        result = subprocess.run(
            ["yarn", "--version"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            raise RuntimeError(f"Yarn validation failed: {result.stderr.strip()}")
        
        yarn_version = result.stdout.strip()
        print(f"Yarn version: {yarn_version}")
    
    except Exception as e:
        raise RuntimeError(f"Yarn validation failed: {e}")

# --------- MAIN FLOW ----------
setup_what = input("Setup (client/server/camera): ").strip().lower()
if setup_what not in ["client", "server", "camera"]:
    raise ValueError("Invalid setup type. Choose 'client', 'server', or 'camera'.")

# Always clone fresh, remove if exists
if not os.path.exists("HSEC"):
    try:
        print("Cloning HSEC repository...")
        run("git clone https://github.com/K9Developer/HSEC.git")
    except RuntimeError as e:
        print("Failed to clone repository. Please check:")
        print("1. Internet connection")
        print("2. Git is installed and in PATH")
        print("3. Repository URL is accessible")
        raise e

if setup_what == "server":
    packages = [
        ("opencv-python", "4.8.1.78"),
        ("pycryptodomex", "3.20.0"), ("python-dotenv", "1.1.0"),
        ("qrcode", "7.4.2"), ("requests", "2.32.4"),
        ("ultralytics", "8.3.158"), ("websockets", "15.0.1"),
        ("google-auth", "2.40.3")
    ]
    install_packages(packages)
    ensure_vc_redist()
    for item in os.listdir("HSEC"):
        if item != "central_server" and item != "setup.py":
            force_delete(os.path.join("HSEC", item))
    

elif setup_what == "client":
    # Will exit and restart itself if node not present, so from here on always have node in PATH!
    ensure_node_installed()
    ensure_yarn_installed()
    validate_node_and_yarn()
    ensure_vite_installed()
    install_client_deps()
    validate_client_installation()
    for item in os.listdir("HSEC"):
        if item not in ("hsec-client", "setup.py"):
            force_delete(os.path.join("HSEC", item))
    force_delete("nodetmp")

elif setup_what == "camera":
    packages = [("pyserial", "3.5"), ("textual", "3.5.0")]
    install_packages(packages)
    for item in os.listdir("HSEC"):
        if item != "camera_module" and item != "setup.py":
            force_delete(os.path.join("HSEC", item))

print("Setup complete! Please run the application using the appropriate command for your setup.")
if setup_what == "server":
    print("Ensure you have the required certificates in HSEC/central_server/certs/ and HSEC/central_server/client_handler_server/")
    print("Run the server using: cd HSEC/central_server && python -m main")
elif setup_what == "client":
    print("Run the client using: cd HSEC/hsec-client && yarn dev")
elif setup_what == "camera":
    print("Run the camera module using: cd HSEC/camera_module/camera_interact && python -m camera_interact")