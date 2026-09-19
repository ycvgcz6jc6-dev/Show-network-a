#!/usr/bin/env python3
"""Static acceptance checks for Show Network frontend/backend wiring.
Conservative: checks literal routes/services/cards. Dynamic runtime data still needs HA testing.
"""
from pathlib import Path
import re, sys, yaml
root=Path(__file__).resolve().parents[1]
js=(root/'custom_components/dmx_monitor/static/show-network.js').read_text()
services=yaml.safe_load((root/'custom_components/dmx_monitor/services.yaml').read_text()) or {}
errors=[]
# Module navigation: every literal data-go and module card target must exist in _modules.
mods=set(re.findall(r"\['([a-z0-9_]+)','[^']+','[^']*','(?:reseau|protocoles|equipements|controles|homeassistant|diagnostic|securite)'\]",js))
for target in set(re.findall(r"data-go=[\"']([a-z0-9_]+)[\"']",js)):
    if target and target not in mods: errors.append(f'navigation target missing module: {target}')
# Literal service calls must be declared in services.yaml.
svc=set(re.findall(r"(?:_call|\.callService\(\s*['\"]dmx_monitor['\"]\s*,|this\.call\()\s*['\"]([a-zA-Z0-9_]+)['\"]",js))
# Also service names passed through common call(...) helper.
svc.update(re.findall(r"\bcall\(\s*['\"]([a-zA-Z0-9_]+)['\"]\s*,",js))
missing=sorted(x for x in svc if x not in services and x not in {'switch'})
if missing: errors.append('services missing: '+', '.join(missing))
# A declared service is not enough: every literal UI service must also have a
# concrete hass.services.async_register(DOMAIN, "...") backend registration.
py='\n'.join(p.read_text(errors='ignore') for p in (root/'custom_components/dmx_monitor').rglob('*.py'))
registered=set(re.findall(r"async_register\(\s*DOMAIN\s*,\s*['\"]([a-zA-Z0-9_]+)['\"]",py))
missing_backend=sorted(x for x in svc if x not in registered and x not in {'switch'})
if missing_backend: errors.append('UI services without literal backend registration: '+', '.join(missing_backend))
# Every defined Lovelace card must also occur in registration/config code.
defs=set(re.findall(r"snDefine\(['\"]([^'\"]+)['\"]",js))
cards={x for x in defs if x.endswith('-card')}
for c in sorted(cards):
    if js.count(c)<2: errors.append(f'card defined but not registered/referenced: {c}')
# Every static panel mounted by tag name must exist.
map_chunks=re.findall(r"\bmap=\{(.+?)\};\s*if\(map\[key\]\)",js,re.S)
if map_chunks:
    mounted=set(re.findall(r"['\"]([a-z0-9-]+(?:panel|inventory|fingerprint))['\"]",map_chunks[0]))
    for tag in sorted(mounted-defs): errors.append(f'mounted custom element not defined: {tag}')
# Fixed view buttons must point to a render branch.
fixed=set(re.findall(r"_setView\(['\"]([a-z]+)['\"]\)",js))
valid={'pro','classic','archive','timeline','modules'}
for v in sorted(fixed-valid): errors.append(f'fixed view has no render branch: {v}')
print(f'modules={len(mods)} services_literal={len(svc)} cards={len(cards)} custom_elements={len(defs)} fixed_views={sorted(fixed)}')
if errors:
    print('FAIL')
    for e in errors: print(' -',e)
    sys.exit(1)
print('PASS: no dead literal navigation/service/card/panel references found')
