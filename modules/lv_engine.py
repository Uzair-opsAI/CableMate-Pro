from data.lv_catalogue import lv_cables_cu
import math

def calculate_current(power_kw, voltage, pf, efficiency):
    return (power_kw * 1000) / (math.sqrt(3) * voltage * 1000 * pf * efficiency)


def apply_derating(current, derating):
    return current / derating


def voltage_drop(mv_per_am, current, length):
    # mV/A/m × A × m = mV
    # convert mV to V
    return (mv_per_am * current * length) / 1000000

def select_cable(current, laying_type):
    for cable in lv_cables_cu:
        if laying_type == "Air":
            if cable["current_air"] >= current:
                return cable
        else:
            if cable["current_ground"] >= current:
                return cable
    return None
