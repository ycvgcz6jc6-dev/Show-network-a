from custom_components.dmx_monitor.rules import DmxCondition,DmxRule,DmxRuleEvaluator,RuleSet

def test_rule_any_hysteresis_and_transition():
    r=DmxRule('r',1,DmxCondition((1,2),'any',100,50),enabled=True)
    e=DmxRuleEvaluator(r)
    assert not e.evaluate(bytes([99,0]),0).active
    assert e.evaluate(bytes([100,0]),1).active
    assert e.evaluate(bytes([60,0]),2).active
    assert not e.evaluate(bytes([50,0]),3).active

def test_rule_all_and_x_of_y():
    assert DmxRuleEvaluator(DmxRule('a',1,DmxCondition((1,2),'all',10))).evaluate(bytes([10,9]),0).target is False
    assert DmxRuleEvaluator(DmxRule('x',1,DmxCondition((1,2,3),'x_of_y',10,x=2))).evaluate(bytes([10,10,0]),0).target is True

def test_rule_test_is_non_mutating():
    rs=RuleSet(); r=DmxRule('r',1,DmxCondition((1,),threshold_on=10),enabled=True); rs.add(r)
    rs.test(r,bytes([255]),0)
    assert rs._evaluators['r'].state is False
