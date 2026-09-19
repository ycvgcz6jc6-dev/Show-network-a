from custom_components.dmx_monitor.device_inventory import DeviceInventory
from custom_components.dmx_monitor.device_fingerprints import fingerprint_mdns


def test_same_ip_on_two_interfaces_does_not_cross_merge(tmp_path):
    inv=DeviceInventory(str(tmp_path/'overrides.json'))
    a=inv.upsert(ip='10.2.1.50', interface='enp1s0', unique_id='candidate:10.2.1.50:enp1s0')
    b=inv.upsert(ip='10.2.1.50', interface='enp2s0', unique_id='candidate:10.2.1.50:enp2s0')
    assert inv.find_by_ip('10.2.1.50', interface='enp1s0') is a
    assert inv.find_by_ip('10.2.1.50', interface='enp2s0') is b
    assert inv.find_by_ip('10.2.1.50', interface='enp3s0') is None
    assert inv.find_by_ip('10.2.1.50') is None


def test_unscoped_mdns_candidate_can_be_promoted_by_mac_on_known_interface(tmp_path):
    inv=DeviceInventory(str(tmp_path/'overrides.json'))
    old=inv.upsert(ip='10.2.1.60', hostname='device.local', unique_id='mdns:10.2.1.60')
    promoted=inv.upsert(ip='10.2.1.60', mac='00:11:22:33:44:55', interface='enp2s0')
    assert promoted is old
    assert promoted.unique_id == 'mac:001122334455'
    assert promoted.interface == 'enp2s0'


def test_lldp_exact_hostname_does_not_match_custom_display_name(tmp_path):
    inv=DeviceInventory(str(tmp_path/'overrides.json'))
    d=inv.upsert(ip='10.0.0.5', hostname='real-host.local', unique_id='candidate:10.0.0.5')
    inv.set_override(d.unique_id, name='StageBox')
    assert inv.find_by_hostname_exact('StageBox') is None
    assert inv.find_by_hostname_exact('real-host.local.') is d


def test_apple_model_only_from_explicit_txt_model():
    generic=fingerprint_mdns('_airplay._tcp.local.', 'Mac mini de Regie', {})
    assert generic.vendor == 'Apple'
    assert generic.model is None
    explicit=fingerprint_mdns('_device-info._tcp.local.', 'Regie', {'model':'Macmini9,1'})
    assert explicit.vendor == 'Apple'
    assert explicit.model == 'Macmini9,1'

from custom_components.dmx_monitor.discovery_pipeline import DiscoveryPipeline

def test_mdns_vendor_enrichment_reuses_pipeline_record(tmp_path):
    inv=DeviceInventory(str(tmp_path/'overrides.json'))
    pipeline=DiscoveryPipeline(inv)
    dev=pipeline.mdns_result('10.0.0.20', '_http._tcp.local.', 'GigaCore 16i', {})
    enriched=inv.upsert(ip='10.0.0.20', hostname='gigacore.local', manufacturer='Luminex',
                        category='network_switch', unique_id=dev.unique_id)
    assert enriched is dev
    assert len(inv.devices) == 1
