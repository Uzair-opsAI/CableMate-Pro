import math
from data.lv_catalogue import lv_cables_cu

def calculate_current(power_kw, voltage_kv, pf, efficiency):
    v = voltage_kv * 1000
    return (power_kw * 1000) / (math.sqrt(3) * v * pf * efficiency)

def design_current(load_current, derating):
    return load_current / derating

def short_circuit_min_area(fault_ka, time_sec, material="Copper"):
    k = 143 if material == "Copper" else 94
    return (fault_ka * 1000 * math.sqrt(time_sec)) / k

def running_vd_percent(mv_per_am, current, length_m, voltage_kv):
    vd_volts = (mv_per_am * current * length_m) / 1000000
    return (vd_volts / (voltage_kv * 1000)) * 100

def starting_vd_percent(mv_per_am, current, length_m, voltage_kv, multiple):
    start_current = current * multiple
    vd_volts = (mv_per_am * start_current * length_m) / 1000000
    return (vd_volts / (voltage_kv * 1000)) * 100

def select_best_lv(
    power_kw,
    voltage_kv,
    pf,
    eff,
    derating,
    laying,
    length_m,
    fault_ka,
    fault_time,
    vd_run_limit,
    vd_start_limit,
    start_multiple,
    material="Copper"
):
    current = calculate_current(power_kw, voltage_kv, pf, eff)
    i_design = design_current(current, derating)
    s_min = short_circuit_min_area(fault_ka, fault_time, material)

    valid = []

    for cable in lv_cables_cu:
        amp = cable["current_air"] if laying == "Air" else cable["current_ground"]

        if amp < i_design:
            continue

        if cable["size"] < s_min:
            continue

        vd_run = running_vd_percent(
            cable["mv_per_am"], current, length_m, voltage_kv
        )

        if vd_run > vd_run_limit:
            continue

        vd_start = starting_vd_percent(
            cable["mv_per_am"], current, length_m, voltage_kv, start_multiple
        )

        if vd_start > vd_start_limit:
            continue

        valid.append({
            "size": cable["size"],
            "current": current,
            "design": i_design,
            "sc_min": s_min,
            "vd_run": vd_run,
            "vd_start": vd_start
        })

    if not valid:
        return None

    return sorted(valid, key=lambda x: x["size"])[0]
