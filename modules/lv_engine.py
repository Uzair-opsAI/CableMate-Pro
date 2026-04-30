import math
from data.lv_catalogue import lv_cu_xlpe_1c, lv_cu_xlpe_3c

# -------------------------------------------------
# BASIC CALCULATIONS
# -------------------------------------------------

def calculate_current(power_kw, voltage_kv, pf, efficiency):

    voltage_v = voltage_kv * 1000

    # AUTO DETECT PHASE
    if voltage_v <= 230:
        # SINGLE PHASE
        return (power_kw * 1000) / (voltage_v * pf)

    else:
        # THREE PHASE
        return (power_kw * 1000) / (math.sqrt(3) * voltage_v * pf * efficiency)


def design_current(load_current, derating):
    return load_current / derating


def short_circuit_min_area(fault_ka, time_sec, material="Cu"):
    k = 143 if material == "Cu" else 94
    return (fault_ka * 1000 * math.sqrt(time_sec)) / k


def voltage_drop_percent(mv_per_am, current, length_m, voltage_kv):
    vd_volts = (mv_per_am * current * length_m) / 1000
    return (vd_volts / (voltage_kv * 1000)) * 100


def starting_vd_percent(mv_per_am, current, length_m, voltage_kv, multiple):
    start_current = current * multiple
    vd_volts = (mv_per_am * start_current * length_m) / 1000
    return (vd_volts / (voltage_kv * 1000)) * 100


# -------------------------------------------------
# DATASET SELECTOR
# -------------------------------------------------

def get_dataset(core_type, material="Cu", insulation="XLPE"):

    # Normalize material names from UI
    material = material.strip().lower()

    if material in ["copper", "cu"]:
        material = "Cu"
    elif material in ["aluminium", "aluminum", "al"]:
        material = "Al"

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
    
        for runs in [1, 2, 3, 4]:
    
            # Ampacity (total)
            amp_single = cable["current_air"] if laying == "Air" else cable["current_ground"]
            amp = amp_single * runs
    
            if amp < i_design:
                continue
    
            # Short Circuit (total conductor area)
            total_area = cable["size"] * runs
            if total_area < s_min:
                continue
    
            # Running Voltage Drop (divided by runs)
            vd_run = voltage_drop_percent(
                cable["mv_per_am"], current, length_m, voltage_kv
            ) / runs
    
            if vd_run > vd_run_limit:
                continue
    
            # Starting Voltage Drop
            if start_multiple > 1:
                vd_start = starting_vd_percent(
                    cable["mv_per_am"], current, length_m, voltage_kv, start_multiple
                ) / runs
    
                if vd_start > vd_start_limit:
                    continue
            else:
                vd_start = 0
    
            # Cost approximation (engineering decision basis)
            cost = runs * cable["size"]
    
            valid.append({
                "size": cable["size"],
                "runs": runs,
                "current": current,
                "design": i_design,
                "sc_min": s_min,
                "vd_run": vd_run,
                "vd_start": vd_start,
                "ampacity": amp,
                "cores": cable["cores"],
                "cost": cost
            })
    if not valid:
        return None

    # Smallest valid cable
    return sorted(valid, key=lambda x: (x["size"], x["runs"]))[0]
