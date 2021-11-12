import vpngate
def main():
    vpn_list = vpngate.get_vpn_list()
    for vpn in vpn_list:
        print(f"Will attempt connect to {vpn.ip}")
        vpngate.connect_vpn(vpn)

if __name__ == '__main__':
    main()