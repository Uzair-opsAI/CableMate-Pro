import math
from data.lv_catalogue import lv_cu_xlpe_1c, lv_cu_xlpe_3c


# -------------------------------------------------
# BASIC CALCULATIONS
# -------------------------------------------------

def calculate_current(power_kw, voltage_kv, pf, efficiency):
    voltage_v = voltage_kv * 1000
    return (power_kw * 1000) / (math.sqrt(3) * voltage_v * pf * efficiency)


def design_current(load_current, derating):
    return load_current / derating


def short_circuit_min_area(fault_ka, time_sec, material="Cu"):
    k = 143 if material == "Cu" else 94
    return (fault_ka * 1000 * math.sqrt(time_sec)) / k


def voltage_drop_percent(mv_per_am, current, length_m, voltage_kv):
    vd_volts = (mv_per_am * current * length_m) / 1000000
    return (vd_volts / (voltage_kv * 1000)) * 100


def starting_vd_percent(mv_per_am, current, length_m, voltage_kv, multiple):
    start_current = current * multiple
    vd_volts = (mv_per_am * start_current * length_m) / 1000000
    return (vd_volts / (voltage_kv * 1000)) * 100


# -------------------------------------------------
# DATASET SELECTOR
# -------------------------------------------------

def get_dataset(core_type, material="Cu", insulation="XLPE"):

    if material == "Cu" and insulation == "XLPE":

        if core_type == "Single Core":
            return lv_cu_xlpe_1c

        elif core_type == "3 Core":
            return lv_cu_xlpe_3c

    return []


# -------------------------------------------------
# MAIN LV ENGINE
# -------------------------------------------------

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
    core_type,
    material="Cu",
    insulation="XLPE"
):

    dataset = get_dataset(core_type, material, insulation)

    if not dataset:
        return None

    current = calculate_current(power_kw, voltage_kv, pf, eff)
    i_design = design_current(current, derating)
    s_min = short_circuit_min_area(fault_ka, fault_time, material)

    valid = []

    for cable in dataset:

        amp = cable["current_air"] if laying == "Air" else cable["current_ground"]

        # Check 1: Ampacity
        if amp < i_design:
            continue

        # Check 2: Short Circuit
        if cable["size"] < s_min:
            continue

        # Check 3: Running VD
        vd_run = voltage_drop_percent(
            cable["mv_per_am"], current, length_m, voltage_kv
        )

        if vd_run > vd_run_limit:
            continue

        # Check 4: Starting VD
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
            "vd_start": vd_start,
            "ampacity": amp,
            "cores": cable["cores"]
        })

    if not valid:
        return None

    # Smallest valid cable
    return sorted(valid, key=lambda x: x["size"])[0]
