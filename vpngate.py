import subprocess
import requests
import os
import tempfile
import platform
import base64
import time
import signal
import sys

# Globally static OpenVPN process (Should use a better method to do this like class encapsulation)
# It's a POC please don't kill me
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


def connect_vpn(server: VPNGateServer):
    global __openvpn_proc__

    if platform.system() == "Windows":
        openvpn_path = "C:\\Program Files\\OpenVPN\\bin\\openvpn.exe"
    else:
        openvpn_path = "/usr/bin/openvpn"

    # 0.0. Check if OpenVPN executable exists
    if not os.path.exists(openvpn_path):
        raise FileNotFoundError(f"OpenVPN not found in {openvpn_path}")

    # 0.1. Check if OpenVPN is running
    if __openvpn_proc__ is not None:
        raise Exception(
            "An existing OpenVPN connection is connected, call disconnect first")

    # 1. Log the current IP for connection verification
    current_ip = get_ip()
    if current_ip is None:
        raise Exception("Could not get current IP.")

    # 2.1. Write the config file
    ovpn_config_bytes = base64.b64decode(server.ovpn_config_b64)
    auth_file = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
    # 2.2 Generate authentication file
    auth_file.writelines([b"vpn\n", b"vpn"])
    auth_file.close()
    ovpn_file = tempfile.NamedTemporaryFile(
        prefix="vpngate_", suffix=".ovpn", delete=False)
    ovpn_file.write(ovpn_config_bytes)
    ovpn_file.close()

    # 3. Start OpenVPN
    retries = 0
    max_retries = 5
    while retries < max_retries:
        proc = subprocess.Popen(
            [openvpn_path, '--config', ovpn_file.name, '--auth-user-pass', auth_file.name], stdin=subprocess.PIPE, shell=False)
        start_time = time.time()
        max_wait_time = 30  # Waits for 30 seconds and assume timeout
        while proc.poll() is None:
            # Process not terminated, check for network connectivity
            ip = get_ip()
            if ip is not None and ip != current_ip:
                # IP has changed, VPN connection is established
                print("VPN connection established!")
                __openvpn_proc__ = proc
                return
            # IP has not changed or is unavailable, VPN connection is not established
            # Check for timeout and wait a second for next check
            if time.time() - start_time >= max_wait_time:
                # Wait time expired, kill the process
                print("VPN connection timed out, killing process...")
                proc.kill()
                break
            time.sleep(1)

        # Process terminated, something went wrong
        retries += 1
        print(f"VPN connection failed, retrying... {retries}/{max_retries}")


def disconnect_vpn():
    global __openvpn_proc__
    if __openvpn_proc__ is not None:
        __openvpn_proc__.terminate()
        __openvpn_proc__ = None
    else:
        raise Exception("No VPN connection is connected")


def is_vpn_connected():
    global __openvpn_proc__
    return __openvpn_proc__ is not None


def get_ip():
    try:
        return requests.get('http://ifconfig.me', timeout=3).text
    except:
        return None


def __sigint_ignore_preexec_fn__():
    # Ignore SIGINT signal
    signal.signal(signal.SIGINT, signal.SIG_IGN)
