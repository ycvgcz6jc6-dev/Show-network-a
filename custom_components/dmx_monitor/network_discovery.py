"""Passive local neighbor discovery helpers.

No packets are emitted. The Linux ARP cache is read when available and merged
with mDNS/protocol observations by the runtime discovery pipeline.
"""
from __future__ import annotations
from pathlib import Path

def arp_neighbors(path: str = "/proc/net/arp") -> list[dict]:
    p = Path(path)
    try:
        lines = p.read_text().splitlines()
    except OSError:
        return []
    rows = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 6:
            continue
        ip, _hw_type, flags, mac, _mask, device = parts[:6]
        if mac == "00:00:00:00:00:00":
            continue
        try:
            complete = bool(int(flags, 16) & 0x2)
        except ValueError:
            complete = False
        rows.append({"ip": ip, "mac": mac.lower(), "interface": device, "complete": complete, "source": "arp_cache"})
    return rows

def ipv4_interfaces() -> list[dict]:
    """Return active non-loopback IPv4 interfaces using Linux ioctl only."""
    import socket, struct, fcntl, ipaddress
    out=[]
    for _idx,name in socket.if_nameindex():
        if name == 'lo':
            continue
        sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        try:
            req=struct.pack('256s',name[:15].encode())
            addr=socket.inet_ntoa(fcntl.ioctl(sock.fileno(),0x8915,req)[20:24])
            mask=socket.inet_ntoa(fcntl.ioctl(sock.fileno(),0x891b,req)[20:24])
            net=ipaddress.ip_network(f'{addr}/{mask}',strict=False)
            if not ipaddress.ip_address(addr).is_loopback:
                out.append({'interface':name,'address':addr,'netmask':mask,'network':str(net)})
        except OSError:
            pass
        finally:
            sock.close()
    return out


def warm_neighbor_cache(interfaces: list[dict], max_hosts_per_interface: int = 254) -> dict:
    """Emit one harmless UDP datagram per local IPv4 host to populate ARP/neighbor cache.

    This is only used by the explicit inventory scan path. It does not alter
    protocol listeners and never sends DMX/show-control payloads.
    """
    import socket, ipaddress
    result={'interfaces':[], 'targets':0, 'skipped':[]}
    for item in interfaces:
        try: net=ipaddress.ip_network(item['network'],strict=False)
        except Exception:
            continue
        hosts=list(net.hosts())
        if len(hosts)>max_hosts_per_interface:
            result['skipped'].append({'interface':item['interface'],'network':str(net),'reason':'subnet_too_large'})
            continue
        sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        try:
            sock.bind((item['address'],0))
            for host in hosts:
                if str(host)==item['address']: continue
                try: sock.sendto(b'',(str(host),9)); result['targets']+=1
                except OSError: pass
        finally: sock.close()
        result['interfaces'].append(item)
    return result
