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
    insulation="XLPE",
    debug=False 
):
    debug_logs = []
    dataset = get_dataset(core_type, material, insulation)
    if not dataset:
        return None

    current = calculate_current(power_kw, voltage_kv, pf, eff)
    i_design = design_current(current, derating)
    s_min = short_circuit_min_area(fault_ka, fault_time, material)

    valid = []
    for cable in dataset:
    
        for runs in [1, 2, 3, 4]:
    
            if debug:
                debug_logs.append(f"Trying: {runs}R × {cable['cores']} × {cable['size']} mm²")
        
            # -------------------------------------------------
            # AMPACITY CHECK
            # -------------------------------------------------
            amp_single = cable["current_air"] if laying == "Air" else cable["current_ground"]
            amp = amp_single * runs
        
            if debug:
                debug_logs.append(f"  Ampacity: {amp:.1f} A | Required: {i_design:.1f} A")
        
            if amp < i_design:
                if debug:
                    debug_logs.append("  ❌ FAIL AMPACITY\n")
                continue
        
            # -------------------------------------------------
            # SHORT CIRCUIT CHECK (LV LOGIC)
            # -------------------------------------------------
            apply_sc = True
        
            # Ignore SC for motors (protected circuits)
            if start_multiple > 3:
                apply_sc = False
        
            # Ignore SC for very small loads
            elif power_kw <= 5:
                apply_sc = False
        
            if apply_sc:
                total_area = cable["size"] * runs
        
                if debug:
                    debug_logs.append(f"  SC Area: {total_area} | Required: {s_min:.1f}")
        
                if total_area < s_min:
                    if debug:
                        debug_logs.append("  ❌ FAIL SHORT CIRCUIT\n")
                    continue
        
            # -------------------------------------------------
            # RUNNING VOLTAGE DROP
            # -------------------------------------------------
            vd_run = voltage_drop_percent(
                cable["mv_per_am"], current, length_m, voltage_kv
            ) / runs
        
            if debug:
                debug_logs.append(f"  VD Run: {vd_run:.2f}% | Limit: {vd_run_limit}%")
        
            if vd_run > vd_run_limit:
                if debug:
                    debug_logs.append("  ❌ FAIL RUN VD\n")
                continue
        
            # -------------------------------------------------
            # STARTING VOLTAGE DROP
            # -------------------------------------------------
            if start_multiple > 1:
                vd_start = starting_vd_percent(
                    cable["mv_per_am"], current, length_m, voltage_kv, start_multiple
                ) / runs
        
                if debug:
                    debug_logs.append(f"  VD Start: {vd_start:.2f}% | Limit: {vd_start_limit}%")
        
                if vd_start > vd_start_limit:
                    if debug:
                        debug_logs.append("  ❌ FAIL START VD\n")
                    continue
            else:
                vd_start = 0
        
            # -------------------------------------------------
            # PASSED ALL CHECKS
            # -------------------------------------------------
            if debug:
                debug_logs.append("  ✅ PASSED ALL CHECKS\n")
        
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
        
    # -------------------------------------------------
    # FINAL SELECTION
    # -------------------------------------------------
    if not valid:
        if debug:
            return None, debug_logs
        return None
    
    # Select optimal cable (engineering priority)
    best = sorted(valid, key=lambda x: (x["cost"], x["runs"]))[0]
    
    if debug:
        return best, debug_logs
    else:
        return best
