from custom_components.dmx_monitor.device_inventory import DeviceInventory
from custom_components.dmx_monitor.device_fingerprints import fingerprint_mdns
from custom_components.dmx_monitor.discovery_pipeline import DiscoveryPipeline


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

def test_arp_then_mdns_on_same_ip_merges_not_duplicates(tmp_path):
    """Audit-confirmed: 'IP dupliquées entre ARP et DNS-SD'.

    ARP's own fallback ids are interface-qualified
    ("candidate:<ip>:<iface>", see runtime/setup.py), while
    DiscoveryPipeline.mdns_result()'s fallback is plain "candidate:<ip>"
    with no serial/mac -- so before the promotion gate in upsert() was
    loosened to try find_by_ip() for any IP (not just ones also carrying
    a serial/mac), an mDNS hit for an address ARP had already recorded
    could never merge into it and always created a second, separate
    inventory record for the same physical device.
    """
    inv = DeviceInventory(str(tmp_path / "overrides.json"))
    pipeline = DiscoveryPipeline(inv)

    arp_dev = inv.upsert(
        ip="10.4.1.50", mac=None, protocols={"IPv4/ARP"},
        sources={"arp_cache"}, confidence="candidate", confidence_score=0.65,
        interface="enp10s0", unique_id="candidate:10.4.1.50:enp10s0",
    )
    mdns_dev = pipeline.mdns_result("10.4.1.50", "_http._tcp.local.", "GigaCore16i", {})

    assert len(inv.devices) == 1, "ARP and mDNS results for the same IP must merge into one record"
    assert mdns_dev is arp_dev
    assert arp_dev.hostname == "GigaCore16i", "the mDNS hit should still enrich the merged record"


def test_mdns_vendor_enrichment_reuses_pipeline_record(tmp_path):
    inv=DeviceInventory(str(tmp_path/'overrides.json'))
    pipeline=DiscoveryPipeline(inv)
    dev=pipeline.mdns_result('10.0.0.20', '_http._tcp.local.', 'GigaCore 16i', {})
    enriched=inv.upsert(ip='10.0.0.20', hostname='gigacore.local', manufacturer='Luminex',
                        category='network_switch', unique_id=dev.unique_id)
    assert enriched is dev
    assert len(inv.devices) == 1


def test_mdns_with_neither_ip_nor_name_creates_no_phantom_row(tmp_path):
    """Audit-confirmed: 'une ligne vide affichée comme si elle existait'.

    With neither an IP nor a name, the only thing left to key a record on
    is the bare service_type -- not device-specific, so every
    unidentified mDNS announcement of that service type from any device
    used to collapse into one shared, ever-refreshed, effectively blank
    inventory row. mdns_result() must decline to create a record rather
    than fabricate one from non-device-specific evidence.
    """
    inv = DeviceInventory(str(tmp_path / "overrides.json"))
    pipeline = DiscoveryPipeline(inv)

    result = pipeline.mdns_result(None, "_http._tcp.local.", "", {})

    assert result is None
    assert len(inv.devices) == 0, "no inventory row should be created from unattributable evidence"

