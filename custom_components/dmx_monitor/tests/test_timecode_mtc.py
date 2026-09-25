from custom_components.dmx_monitor.timecode import TimecodeMonitor
from custom_components.dmx_monitor.midi import MIDIMessage
from time import monotonic

def test_mtc_requires_all_eight_quarter_frames_and_decodes():
    m=TimecodeMonitor()
    # 01:02:03:04 at 25 fps. Pieces: frame lo/hi, sec lo/hi, min lo/hi, hour lo, hour-hi+rate.
    vals=[4,0,3,0,2,0,1,2]  # rate bits 01 => 25fps, hour high bit 0
    for i,v in enumerate(vals[:-1]):
        assert m.observe_mtc(MIDIMessage('quarter_frame',None,(i,v),'MIDI A',monotonic())) is False
    assert m.snapshot()['status']=='waiting'
    assert m.observe_mtc(MIDIMessage('quarter_frame',None,(7,vals[7]),'MIDI A',monotonic())) is True
    s=m.snapshot()
    assert s['text']=='01:02:03:04'
    assert s['fps']==25.0
    assert s['transport']=='MIDI Time Code (MTC quarter-frame)'
    assert s['source']=='MIDI A'
    assert s['locked'] is True
