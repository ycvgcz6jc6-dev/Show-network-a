from custom_components.dmx_monitor.core.profile_loader import LazyCatalog, warm_catalogs


def test_warm_catalogs_loads_lazy_catalog_once():
    calls = []
    catalog = LazyCatalog(lambda: calls.append("loaded") or ("profile",))

    warm_catalogs(catalog)
    warm_catalogs(catalog)

    assert tuple(catalog) == ("profile",)
    assert calls == ["loaded"]


def test_warm_catalogs_accepts_legacy_materialized_values():
    warm_catalogs(("legacy",), {"legacy": True})
