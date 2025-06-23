import os
import sys
import subprocess
import urllib.request
import shutil
import time

ENCRYPTED_ENV = b'\x95r\x92\x91\x9fT\xc3&\xcc\xda\xe8\x10\x12\xe6\xe4\x86\x8f\xd5\x14\n=b\x16\xbf\xa0\x7f\xc6sb\xdb\x9d\x9b'
ENCRYPTED_SERVICE_KEY = b'\xb9\x88Mb\xd8\x07T\xb7|\xa9\xf1+\xd8\xc6\xf2\x8duj)\xec\x86=\x9d\x92\x9d\xda\xb6\x9fC\xcag9M8\xdf\x15F\x85x\xda"\xb5\x1b\xab\x8cj\t\xd9s\xa5\x17\x85\x96C\x94\x89\xca(T\x8feU\xf7\x9a9R\x1eZ\x00\x9a\x0c\xcd&\xfb=\xb7\x1b\x1b%\xb8J\xa0\xc9\xf3\xb8KV<\xf4\x075ls\xc6\x8b\xee\xacy\xa4\xe7X\xe1t\xbc\xdd\x92\x12Wl\xf9\xe7s\x9f\n\xe4{\xd7$\xab\xa8\xdb\x99&\xd7\x85\x88\xde\x88\x0f<C\x8beC\x1fo\xea\xaa\xdd*\x96Rw\xfb5\xe3e[\xd9\xf6\xfe\xc7NX\xa5oG\x08\xcd\x01\x7f(\xac\n\xb1-\xc4\xf2p\xca\xc9\xd0\xa2\x94\xf6\x8b\x05\x85\xaf\x19\x02\xdf\xdeB\xf4\xed\x83\xde\xabV\xd9\x8fS\x87\x0c{X\x94\xf3\x9d\t\xb8\x9a\x90P\x81\xda+\xa9& ~\xc1\x91\xe5\x06w\xd9\xf2%\x02\x92\xc7\xf0Bh\xd3<\xd4M\xd8pTUfNeA#B\xc3`+\x08(\xc0"B|!sI\x80T\x00Rw\xd8E\xa2\xdc\xe80v\xa5(w\xea%\xea\xfc\xabD\xe45{\x04\xe7\xe5`\xe8P\x83\x887\xb1\x9f\xf2\xc2\xb7\x7f\x84;yMv\xe7<mN\x9c\x83\xb6\xb9\xaf\x89\xe4\\\xb3\x06Hzp%Z\xa4\x16-\x0e\xdb1\xa1\xd4\x14\xfd\xc5\xb6W\xe7\xc4\xb0\x1a\xd0\xd4F:\xcd\x96\x9a\x88\x8b\xd6G\x00mj\x8d\xb1t\xd7\xa6\xf8\x17?\x9f\xc1\xe8\xee\xaf\x8fW\xc3(\xf3\x14\x07\xba5\xea\x99\xb487\x8d\x1cU6\x81\xb1\x13\x98\x1eC\xb2\xe0\xbe\x99\xfc\x18\xc6q\x07U7\x0b\xe1\xa0G\x9bk\xc7J\x88\x06\nU\xae\xdeC\x85}\xaf\x05^]\x98\xad\xbb\xab\xf8\xfb\xcb\xa5\xfdl/W\xf1\x9c\x0f\xe9fiX\x9aa7\xcc\xb5\x1b\x8a\x1b\x02S\xcc\xc6s\xd3ja\xdf\xb6@g\x03:\x9b|\x8b\xcfm\xc4\xac\xf4\xaf\x9c\xabs\xed\x84\x88zz3\xb7\xb9y8Q\xe8%\x10(\x90\xa8\x87=0\xcd\x9f!2{\x9co\xce\xae\x03qX\xe2\xc8\xe4|\xfe\xe8\x95\xd2\x15\xc9\xff\xd9l+yw\x03\x13\x19\x95\x8c,9rS\xf6\xa4*ln\x99D\r\xc4\xbf\xc0\xd2H\xaaY=4\xdbgzA}1\xd2\xe80\xceZ#q\xebz\x11\xc1\xdf\xdd\xf4\xab\xcdX\x0e\xd11\x7f\x875(N6\x06\xf5*\xb5"\x0e\xb0nv.W^\xe3\x00\xaaf\xe1\xa7 E\x9f\x1a"N\xf62\xb4E\xf7^\xafyB\xb25\xeb\xd0\xbb\xa1\x9c\xde\t\xd9\x8b[p\xe8L\xdf\x9f\xe6\rQ\xc7<\xf8T\x19&q|\xf4\xac\xa4\x1aInp[\xaf&7\xea\x91\xad\xb1U+>j\x1eXS\x89?\xd7=T\xc8z\xc2\x05(\x80#\xc8\x0f*\xc1H7\xd2\xa6Ze\xd0\xcbbN2\x9e\xaa\x95\xd8\xb8\xf6\x8bi\xd7\x8b\x1a\xe2>X\x8e\x81\xb6\xf1\x0f\xfc\xb7k\xd8\xd4hj\xd7dF\xb9\x11\xd4\x8e \xa4\xa8d\x04j\x94a0\xcd\xc7\x90\xcf<\x07\xf1`&?\x98s\xc4\x81~\xcd\xc1\xbf\x1fJRKP\x8c\xb7\xb9\xad\xcb\x8dr)~\xb59\xbd\xa9\xb6X\xa1\n\xdfw\xbc`\xa2}\x05\x97\xafK[Z<0Z\xe9\x82\x18{\xa0\xb7\xa8\x00\x0c\x04\xe9t\xc2\xfb\xdf\x08\xae\xdc\x7f\x97\xde?\xd1\x08F!g=\xcdK\x96\xe1\xa4ls\xa4z\x10X*,\xbd\x96\xa2x\xa8/\x06U\x9a\x013\xf0\x13\x8e\x89$\xa3\x8a\x07|L\xf6t\x7f\x8b_\xdd\x0b\xd7\xec\x8f\xcb\x97\x9f-\x9c\x8a\xa2\x1b\x1e\xc6`\xc8\xfa#qA\xd0\xdc\xba\xc5\\]\x84\x08\xac\x11o\x90sW;Qo\xda\x81\x83J \x90\x04!7-\xbar_\xc0\x8cQm\ro\x02\x81AU\x1d\x9d\xef\xb8\xe5D{\x1d\xd5 /m\x14\xac\xeeP|\x80\xf0!_\xd8\x03\xee\xee\xb3vL\x0cnG3\x97~\x08\xb8\xe3\x82X\x1a\x9f\t\n\xed\x93\xacJ+WK4\x0b\x82\xfd\xc9`\xc4=\xc4mb+\xbduHKSU\xe7\xc9!^s\x93\x88r(w\x87\rG\\$\xc5\x95\xc33\x11\xa5S\xc2\xddH\xb7\xe7\xed;\xd8hs\xb2\xc5\x12$\xf5t\xcbd\xb4\xde\x9d\xd7j1vz(\xe6(\xee-\x17r\xf8Q\xeaK\x1cmD\xc3>4"w\xe6\xab\xcfrtw`@\xe8\x0ci\xd8\x081\x87\x96\x96\xfc\xcb\xb8i{\xc0\xf9h\xbf\x95\xd8]1\xf7M?\x82?\xf5t/\x8fM\x8a\xc2]\x08a0<\xbep\x9dF\xfb;\'J\xadhN\x85\xec\x02\x02m\x1a>\xee/`\xffK\x1d\xd6\xaa\xf8U9\x04\xd0l\xa1\x8e5\xb3D\x01f\x11\x99#\xcf\xf9j\xcc\xc7\xaa\xf69XK\xa2\x831Ei\x91\x15\x81Z\x1b\xe1\xca\x1c!\'\x98\x10\x99.#\x1b1\x0f\xd6\x18\x01m\xbf\x1b\xadO\xab\xd5\x8f\x00.8\x91\xa0} 0\xc4\x11\x90\xb2\xd8\x97\xb9\x11\xe2\xc5\xf7\x04\xd2\xd4OdS\xb7(r\x8bg\x98B\xb47\xba\xe1\xcd\xea\xc1Y\xed\xe0\xbaA\xf07\xe2L\x85\xa2\ngkz\x04N\xda\xa2s\n5\x83&\x82^y\xbfD\x9e\x07 \x85\xdd\xe3\x81\xab\x02\xbf\xe58\x85\xd3a\xdc\xdb\xbd\xc2P\xff3\x0e\xb1 Jx\xfa\x96\x05\x07\x0b\x05\xba\xa5\x16>\x90\xbc\x05\xb6\xc1qK\x93\x93\x81\x9c\xf9C\x13\x1c\xcdS\xe90\xb2\xc0\xfd\xc0\x14\x19\xfe\x9d\xa6g)p(\x0b;\x89\x0c\xca\x12e4\x17\xed\xb2\xb6\xa4&G\xd3\x08\xff\xcb\xb7r\xafS\xe2\x16\xf5>\xfb\xea\xb0z\\\xe9\x05\xee:{\x05/\x7f*e\xb4[\x92\xbf&G&L\np\x11D2\x98\x0e\xd6\xc1\\SEa[\xcd\xb4\xdc\x18y|J\x96U\x85K\xe5ta\x80)o\x97(DN\xf3\x85\xa1\xaf0_X\xf13\x89\x1b\xba\xcf\x8d\xfe\x02\xf3\xae$\xe7\xd5\xb8_\x9c\xc6\xc6\x8d\xf4\xf5\xf5\xb2\x7f\xa6gY\x89J\t\xa1\xe1?\xfd\x92\r\xdf\xcaZ\xc3\x03\x83\x82$\xd3\x01\x80\x14\x0c9#?@\x1e\x11;\x10&l\x8b\xbf5\xf8{\x0b^\xac\xc4\xbf\x1a\xd5\xf5\x99\x1a\xa1\xcf\xe7\xe7\x089|\x7fqH\xd5\xfc\xf0+#\x7fS\xb9G\xa6\x94\x83,\xcez\x03h\x99\xf3\xa1\xc0\x17\x91N\x14<\xdf\x93\xe8\x0f\x142\'\x04\xc0b\xdbQ\xb5\xd7U\xa8\xcc\xcfGR\xf0dYzm\x99\xc2\xb1D\xb6\xb2\xdcF\xda/\x08\xe0GD\x17cI%F\x822-\n\xafx\xf5\x82z\xee\xd0\xb9V\xc24\x8b\x87\'\xe5\xad\xfe}\xcd:D\x94rH\xee\x9b\x99\x1d\xf6[\xd5\xfaQ\xde\xfdiNR\xb5\xb9\x15\xd5\xe4#N\xce\x08\x13\xadoqt\x0c#\x14[\xd8\xabZ\xb9\xf4\xf2x\x88\x8c\xa6N0z\xd4\xe8\x8a\x06\xf4\x9a{O\x04$?_\xb0\xb2\xe6\xc0\xd6\x8f\xa9\xab\n7\x88\xae\xcd~/\x8f\x18?\xae\x80%\x15\xd2\xb9\xd8\xd7\xe3ax\x85}m\x8e4\xe0\xc5)^\xd1o\x1b\x06\x84\xd0\xc8S\x8d\xec\xd5\xdc\xfbv.\xfe\x99X\xa1\xcc\xd7046l\x88\x1a\x98\x8ay\xbb\xc9R\xeb\xce\xc4\xfd1\xa2\x1c{\x14+\xd0\x14~\x86\xb4\xeai\xa7\xee?\xf8\xfa\xbf)\xe8Lg\xb0;\xf7\x11\xf8"V|8\xa9-\x99\x0c\r\xd6\x88a\xfb\xdf\xbc\xc1#u\xe2\xb5\xd9\xb7\xd8\xb0:2\x96}\x06\x12O9)\x12\x95\x80\x87\x8a\x8bb)\xda\xa6\xd3xd\t\xc1\x8c\xad9c\x88F\x11#=\xf0\x89\xa1\x0b\xff|\xfa\x9f\x7f\xc8\x99\x1d`\xbd\xfeWC4b\xc9\xb9FR+*TFY\x03G`\x1bct\x81W\x94\xe5\x81(\xb4\xb8\x99\xbe\xe6E6?\xbe\xe8\xefL\xa6@M\x07\xa6e\xd2\xd25F\xa9\xd2\x9e\xaa=*\x94B\xf8\x1c5P\xed(\x90\x00\xd5\x0b!\xba\xfa#\x02N\x88\x02\x07\x80\x93\xb5\x82\xf6s\xd6<\xea\xcc\xa8\r\x151K\xcb\t\t;\x87\x86\xba0\xa6a\xd02\xc7u\xc7\x074f\xd4\x91\xe6\xe3}\xc9n9;\x01O\xeb\x06\x84\xca\xe3\x7f\x03\xe9\xf49\xe0\xd7\x83\x81\x1e\x96\xf0\x91\xa3_C\xa5S\xad\xf2\x15\xb7pQ\xe2\xc0\xd9\xd6\x10\xd2\xdcA\xba@sr\xd5O:>\xe3k\x9de53;\xe5\x98\xa8\xd0t\x11\xf3T\xe5\x03\xffL\xdf=\xd5\xef\xa3\xa8\xd7\x16\xbe\xd1\xe4\xa2\xcc\xea\xa2~\x85\xd9\x86\x877\xa9Y\xa8\x0e\xa4\r\x01\x8b;\xbb\xaf\x9f\xa8\xff\x06\xf6yF\xa4 \xdd\xc8\xc6\x85\xc2(D^h\xd9j\xbc\xfdm[\x80.}\xaa,\xae\xfd/\xa4\x00e\xba\xc6\xe9=\xe2\xe93\x9a\xa0g\xfc\xe3,\xd8\xe2&\xef\xff\x13\x96JJ\xe1\xd4\xfc\x1a:\xfa4\n8\xc12\xfc@\x89\n\xe8\x13\xa9\xea\xacz\nZ\xb1\xd9|Y\x00\x94\x0c\x17\xcf\xdc\xd5\x16\x10\xd9!\xe06\xe9Z\x9a\xec\xc5\xd6~\xff\xba\x1b_c%\xf1j\x93\x9f\xd8t\x05\x16\x19F\xb2\x05\xd5\x99b\t\x12\xbcC]\xc1\x8a\xfb$\x9b\x92J\x07\r\xc9`\xba\xc7\x95\xd2}\xa9\xee6\x05\x94\x8e\x13i(*o\x1e\x9f\x07\x03\xcd\xfeTp\xa4\xdf\xb8Wc\\\xc9\x97\x02\xc9\xf6j\n9\x81~\x1b\xbb%>\xd66\x17\xa3\x17\xfd\x91\xean\xfa=\xfd\xf4v\xe5\xca?a\x05\xcfy\x01\xeaEw\xff\x957N\x06\x0f\xc6J1\xe5\x00\x01\x0f{?<Z\xf4\x14p>K3\x97\xc9\xed:\xfa\x93\x06\x0c\x9d\x04\xb9\xb7,\x10(O\xf9\xe0\x1b\xa0\x80\xee\x9cy\x9e\xa3\xe7\x9e\x14d\x87\xbf\xf0C\xba\xe8\xc1@a\xb8\xce\xa6\x1a \xd9\xbe5\xcew\x1e{\xe3\xe5cf\x82\xf8\x8d\x1f(9\x16\xd4\xdc\x1a\xc6\x9a\x01a3\xd2\xee\xa6\xcaj\x89\xa8V\xb8rS\xb5Q\xc6\xcf\xb1)\x08\x00\x91y\xe2\x81\x991\xa3!\x1e\xfe\xc0\xe8\xe2\x0c/\x00\xbe\x0c\x84\xfd\xb6\x7f\x1ds\x84\x9c\x08'
try:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import unpad
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "pycryptodomex"])
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import unpad

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
    print("Downloading Microsoft Visual C++ Redistributable...")
    urllib.request.urlretrieve(url, out)
    print("Installing Microsoft Visual C++ Redistributable (silent)...")
    # Silent install: /quiet /install
    ret = subprocess.run([out, "/quiet", "/install"], shell=True)
    if ret.returncode == 0:
        print("VC++ Redistributable installed successfully.")
    else:
        print("VC++ Redistributable installer returned error code", ret.returncode)
    try:
        os.remove(out)
    except Exception:
        pass

def decrypt_aes(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
    return decrypted

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
    run(f"where {cmd}", check=False)
    return shutil.which(cmd) is not None

def run(cmd, cwd=None, check=True):
    print(f"> {cmd}")
    result = subprocess.run(
        ["cmd.exe", "/c", cmd],
        cwd=cwd,
        shell=False
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}")
    return result.returncode

def install_packages(packages, max_retries=3):
    for package, version in packages:
        attempt = 1
        while attempt <= max_retries:
            try:
                print(f"Installing {package}=={version} (attempt {attempt}/{max_retries})")
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", f"{package}=={version}", "--force-reinstall", "--user"],
                    stdout=sys.stdout, stderr=sys.stderr
                )
                if result.returncode == 0:
                    print(f"{package}=={version} installed successfully.")
                    break
                else:
                    print(f"pip install failed with code {result.returncode}")
            except Exception as e:
                print(f"Error installing {package}: {e}")
            if attempt == max_retries:
                raise RuntimeError(f"Failed to install {package}=={version} after {max_retries} attempts.")
            print(f"Retrying {package}...")
            time.sleep(2)
            attempt += 1

def ensure_node_installed():
    if is_command_available("node"):
        print("Node.js is already installed.")
        return False
    print("Node.js not found. Downloading and installing Node.js v22.16.0...")
    os.makedirs("nodetmp", exist_ok=True)
    msi_path = "nodetmp/nodejs.msi"
    urllib.request.urlretrieve("https://nodejs.org/dist/v22.16.0/node-v22.16.0-x64.msi", msi_path)
    while not os.path.exists(msi_path): time.sleep(1)
    run(f"cd nodetmp && msiexec /i nodejs.msi /qn /norestart")
    print("\n[INFO] Node.js installed successfully.")

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

# --------- MAIN FLOW ----------
setup_what = input("Setup (client/server/camera): ").strip().lower()
if setup_what not in ["client", "server", "camera"]:
    raise ValueError("Invalid setup type. Choose 'client', 'server', or 'camera'.")

# Always clone fresh, remove if exists
if not os.path.exists("HSEC"):
    run("git clone https://github.com/K9Developer/HSEC.git")

if setup_what == "server":
    password1 = input("Enter the password for the server (ENV): ").strip()
    password2 = input("Enter the password for the server (SERVICE): ").strip()
    if len(password1) != 16 or len(password2) != 16:
        raise ValueError("Both passwords must be exactly 16 characters long.")

    decrypted_env = decrypt_aes(ENCRYPTED_ENV, password1.encode(), password1.encode()[:16])
    decrypted_service_key = decrypt_aes(ENCRYPTED_SERVICE_KEY, password2.encode(), password2.encode()[:16])

    with open(r"HSEC\central_server\package\client_handler_server\.env", "wb") as f: f.write(decrypted_env)
    if not os.path.exists(r"HSEC\central_server\certs"): 
        os.makedirs(r"HSEC\central_server\certs")
    with open(r"HSEC\central_server\certs\serviceAccountKey.json", "wb") as f: f.write(decrypted_service_key)

    packages = [
        ("numpy", "2.0.2"), ("opencv-python", "4.8.1.78"),
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
    ensure_vite_installed()
    install_client_deps()
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
    print("Run the server using: cd HSEC/central_server && python -m main")
elif setup_what == "client":
    print("Run the client using: cd HSEC/hsec-client && yarn dev")
elif setup_what == "camera":
    print("Run the camera module using: cd HSEC/camera_module/camera_interact && python -m camera_interact")