# PERSEUS Alert Rules

from SatisfiableSet import TypedConditionSet, TypedValueSet
from enum import Enum
import logging
import yaml


class Priority(Enum):
    max = 4
    high = 3
    medium = 2
    low = 1
    none = 0

class PERSEUSAlert(object):

    def __init__(self, rule, v, source):
        self._msg = rule._msg
        self.priority = rule.priority
        self.source = source
        self.v = v

    @property
    def msg(self):
        # logging.debug(self.v.as_dict())
        m = "{priority}.ALERT".format(priority=self.priority.name.upper())
        if self.source:
            m = "{0} | Room: {source}".format(m, source=self.source)
        if self._msg:
            s = self._msg.format(BP=-1, BP_dt=-1, **self.v.as_dict())
            m = "{0} | {1}".format(m, s)
        return m


class PERSEUSRule(object):

    def __init__(self, priority='high', conditions={}, msg=None):
        # logging.debug(conditions)
        self.conditions = TypedConditionSet(conditions)
        self.priority = Priority[priority]
        self._msg = msg

    def SatisfiedBy(self, v):
        if self.conditions.satisfied_by(v):
            return True


def TestRules(rules, v, source=None):
    for rule in rules:
        if rule.SatisfiedBy(v):
            return PERSEUSAlert(rule, v, source)


def ParseRules(config):
    rules = []
    for rule in config:
        rules.append(PERSEUSRule(rule['priority'], rule['conditions'], rule['message']))
    return rules


def test_alert_rules():

    r = PERSEUSRule('high', {'x': ['EQ', 1, 2, 3]}, "x: {x}")
    v = TypedValueSet({'x': 3})

    alert = TestRules([r], v)
    if alert:
        logging.debug(alert.msg)

    with open("config.yaml", 'rU') as f:
        topology, rule_config, zones = yaml.load_all(f)

    rules = ParseRules(rule_config)

    v = TypedValueSet({'source': 'NOM_ECG_CARD_BEAT_RATE',
                       'alarm':  'NOM_EVT_ECG_V_TACHY',
                       'bpm':    120 })

    alert = TestRules(rules, v, 'monitor0')
    if alert:
        logging.debug(alert.msg)

    v2 = TypedValueSet({'source': 'NOM_ECG_V_P_C_CNT',
                        'alarm' : 'NOM_EVT_ECG_V_TACHY',
                        'bpm':    120,
                        'spo2':   70 })

    alert = TestRules(rules, v2, 'monitor1')
    if alert:
        logging.debug(alert.msg)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    test_alert_rules()