import vpngate
import time
def main():
    vpn_list = vpngate.get_vpn_list()
    for vpn in vpn_list:
        print(f"Will attempt connect to {vpn.ip}")
        vpngate.connect_vpn(vpn)
        print(f"Connected to VPN {vpn.ip}, current IP: {vpngate.get_ip()}")
        time.sleep(3)
        print(f"Disconnecting from VPN")
        vpngate.disconnect_vpn()
        time.sleep(1)

if __name__ == '__main__':
    main()