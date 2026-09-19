from custom_components.dmx_monitor.power_manager import PowerButton

def test_power_button_state_is_explicitly_commanded_not_feedback():
    assert PowerButton('p','Power').public()['state_evidence']=='commanded_dmx_output_not_physical_feedback'
