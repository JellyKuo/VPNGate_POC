import subprocess
import requests
import os
import tempfile
import platform
import base64
import time

__openvpn_proc__ = None

class VPNGateServer:
    def __init__(self, server_str):
        # Decode server CSV string
        # Columns:
        #   0: Host Name
        #   1: IP
        #   2: Score
        #   3: Ping
        #   4: Speed
        #   5: Country Name
        #   6: Country Code
        #   7: VPN Sessions
        #   8: Uptime
        #   9: Total Users
        #   10: Total Traffic
        #   11: Log Type
        #   12: Operator
        #   13: Message
        #   14: OVPN Config Base64

        self.server_str = server_str
        cells = server_str.split(',')
        self.host_name = cells[0]
        self.ip = cells[1]
        self.score = cells[2]
        self.ping = cells[3]
        self.speed = cells[4]
        self.country_name = cells[5]
        self.country_code = cells[6]
        self.vpn_sessions = cells[7]
        self.uptime = cells[8]
        self.total_users = cells[9]
        self.total_traffic = cells[10]
        self.log_type = cells[11]
        self.operator = cells[12]
        self.message = cells[13]
        self.ovpn_config_b64 = cells[14]


def get_vpn_list():
    url = 'http://www.vpngate.net/api/iphone/'
    # Get server list from the API
    response = requests.get(url).text
    # Remove the first line and last line (*vpn_servers*) as well as titles and new lines
    response = response.split('\n')[2:-2]
    return [VPNGateServer(server_str) for server_str in response]

# Globally static OpenVPN process (Should use a better method to do this)


def connect_vpn(server: VPNGateServer):
    if platform.system() == "Windows":
        openvpn_path = "C:\\Program Files\\OpenVPN\\bin\\openvpn.exe"
    else:
        openvpn_path = "/usr/bin/openvpn"

    # 0. Check if OpenVPN executable exists
    if not os.path.exists(openvpn_path):
        raise FileNotFoundError(f"OpenVPN not found in {openvpn_path}")

    # 0.1. Check if OpenVPN is running
    global __openvpn_proc__
    if __openvpn_proc__ is not None:
        raise Exception("OpenVPN is already running")
    
    # 1. Log the current IP for connection verification
    current_ip = get_ip()

    # 1. Write the config file
    ovpn_config_bytes = base64.b64decode(server.ovpn_config_b64)
    auth_file = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
    # Generate authentication file
    auth_file.writelines([b"vpn\n", b"vpn"])
    auth_file.close()
    ovpn_file = tempfile.NamedTemporaryFile(prefix="vpngate_", suffix=".ovpn", delete=False)
    ovpn_file.write(ovpn_config_bytes)
    ovpn_file.close()
    
    # 2. Start OpenVPN
    retries = 0
    max_retries = 5
    while retries < max_retries:
        proc = subprocess.Popen([openvpn_path, '--config', ovpn_file.name, '--auth-user-pass', auth_file.name])
        # 3. Wait for the connection to be established
        #   OpenVPN process quits (Poll is not None)
        #   VPN connection is established (Current IP is different from the one before)
        #   Timeout reached (wait_counter reached max_wait)
        max_wait = 10
        wait_counter = 0
        while proc.poll() is None and get_ip() == current_ip and wait_counter < max_wait:
            time.sleep(1)
            wait_counter += 1
        # 4. Handling errors
        if proc.poll() is not None or get_ip() != current_ip or wait_counter >= max_wait:
            retries+=1
            print(f"VPN connection error, waiting 3 seconds to retry... {retries}/{max_retries}")
            time.sleep(3)
            continue # Retry
        print("VPN connection established!")
        # 5. Setup global OpenVPN process
        __openvpn_proc__ = proc
        break # Do not retry

def get_ip():
    return requests.get('http://ifconfig.me').text