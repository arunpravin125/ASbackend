import swisseph as swe
import pandas as pd
import datetime
import pytz
import os
import sys

# Add root to sys.path
backend_root = os.path.dirname(os.path.abspath(__file__))
if backend_root not in sys.path:
    sys.path.append(backend_root)

from kp_core.kp_engine import KPEngine, PlanetNameUtils, ZODIAC_SIGNS, PLANET_NAMES, SIGN_LORDS, PLANET_SHORT_NAMES
from kp_core.timeline_generator import TimelineGenerator
from kp_core.analysis_engine import AnalysisEngine
import math

def score_to_ab_percent(score):
    """
    Convert a timeline score to A/B percentage strings and a strength tier.
    A = Asc, B = Desc to match the reference image.
    """
    try:
        score_val = float(score)
    except Exception:
        score_val = 0.0

    magnitude = abs(score_val)
    if magnitude >= 1.0:
        tier = "very_high"
        major_pct = 90
    elif magnitude >= 0.7:
        tier = "high"
        major_pct = 80
    elif magnitude >= 0.4:
        tier = "medium"
        major_pct = 70
    elif magnitude >= 0.2:
        tier = "low"
        major_pct = 60
    else:
        tier = "balanced"
        major_pct = 50

    if score_val > 0:
        a_pct = major_pct
        b_pct = 100 - major_pct
    elif score_val < 0:
        a_pct = 100 - major_pct
        b_pct = major_pct
    else:
        a_pct = 50
        b_pct = 50

    # Match the reference style for very high confidence
    a_str = "90++" if (tier == "very_high" and a_pct >= 90) else f"{a_pct}%"
    b_str = "90++" if (tier == "very_high" and b_pct >= 90) else f"{b_pct}%"

    return a_str, b_str, tier

def build_reference_style_timeline(simplified_df, match_start_utc, duration_hours, target_tz):
    """
    Groups the 3-minute intervals into meaningful 12-15 minute blocks 
    to match the reference image format.
    """
    if simplified_df is None or simplified_df.empty:
        return pd.DataFrame()
        
    df = simplified_df.copy()

    # Normalize incoming schema because source timeline columns can vary.
    normalized_cols = {str(col).strip().lower().replace("_", " "): col for col in df.columns}

    def _first_present(*aliases):
        for alias in aliases:
            key = alias.strip().lower().replace("_", " ")
            if key in normalized_cols:
                return normalized_cols[key]
        return None

    start_time_col = _first_present('Start Time', 'Start', 'Time', 'datetime_utc')
    indicator_col = _first_present('Indicator', 'Verdict', 'Label')
    score_col = _first_present('Score', 'Final_Score', 'Base_Score', 'total_score')

    if start_time_col is None:
        return pd.DataFrame()

    # Ensure Start Time is datetime
    df[start_time_col] = pd.to_datetime(df[start_time_col], errors='coerce')
    df = df.dropna(subset=[start_time_col])
    if df.empty:
        return pd.DataFrame()
    
    # Localize/Convert to target TZ
    if isinstance(target_tz, str):
        target_tz = pytz.timezone(target_tz)
    
    match_start = pd.to_datetime(match_start_utc)
    if match_start.tzinfo is None:
        match_start = pytz.UTC.localize(match_start)
    
    # We want to group by ~15 minute blocks
    # But often the reference image has irregular blocks based on transitions.
    # Logic: Group consecutive rows that have the same Indicator label.
    
    blocks = []
    current_block = None
    
    for idx, row in df.iterrows():
        label = row[indicator_col] if indicator_col in row else None
        # Safely obtain a score value from available columns
        score_val = row[score_col] if score_col in row else 0
        try:
            score_val = float(score_val)
        except Exception:
            score_val = 0.0

        if current_block is None:
            current_block = {
                'Indicator': label,
                'Start': row[start_time_col],
                'End': row[start_time_col],
                'Total_Score': score_val,
                'Count': 1
            }
        elif label == current_block['Indicator']:
            current_block['End'] = row[start_time_col]
            current_block['Total_Score'] += score_val
            current_block['Count'] += 1
        else:
            # Shift. Close current block.
            blocks.append(current_block)
            current_block = {
                'Indicator': label,
                'Start': row[start_time_col],
                'End': row[start_time_col],
                'Total_Score': score_val,
                'Count': 1
            }
    
    if current_block:
        blocks.append(current_block)
        
    # Format blocks for display
    ref_rows = []
    for b in blocks:
        avg_score = b['Total_Score'] / b['Count']
        a_pct, b_pct, tier = score_to_ab_percent(avg_score)
        
        # Format times
        s_local = b['Start'].astimezone(target_tz)
        e_local = b['End'].astimezone(target_tz)
        
        # Add buffer to end time of the last interval (3 mins)
        e_local_plus = e_local + datetime.timedelta(minutes=3)
        
        time_range = f"{s_local.strftime('%H:%M')}-{e_local_plus.strftime('%H:%M')}"
        
        ref_rows.append({
            'Time Range': time_range,
            'A': a_pct,
            'B': b_pct,
            'Verdict': b['Indicator'],
            'Duration': f"{int((e_local_plus - s_local).total_seconds() / 60)}m"
        })
        
    return pd.DataFrame(ref_rows)

def _sssl_wicket_strength(sssl_short, engine):
    """Fallback implementation of wicket strength check."""
    try:
        # Get 8th house lord (natural significator of wickets/falling)
        cusps_df = engine.get_all_cusps_df()
        eight_lord = cusps_df.loc[8]['sign_lord'] if 8 in cusps_df.index else None
        twelve_lord = cusps_df.loc[12]['sign_lord'] if 12 in cusps_df.index else None
        
        # If SSSL is 8th or 12th lord, it's strong for wickets
        if sssl_short in [eight_lord, twelve_lord]:
            return 0.8
        
        # Ketu is also a general significator of wickets
        if sssl_short in ['Ke', 'Ketu']:
            return 0.7
            
        return 0.1
    except:
        return 0.1

def _planet_longitude_at_time(dt_utc, planet_short_or_full):
    planet_full = PlanetNameUtils.to_full_name(planet_short_or_full)
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, 
                    dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600)
    
    if planet_full == 'Rahu':
        pos, _ = swe.calc_ut(jd, swe.MEAN_NODE, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
        return pos[0]
    elif planet_full == 'Ketu':
        pos, _ = swe.calc_ut(jd, swe.MEAN_NODE, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
        return (pos[0] + 180) % 360
    
    # Map back to swe IDs
    SWE_PLANETS = {v: k for k, v in PLANET_NAMES.items() if k != 'Asc'}
    p_id = SWE_PLANETS.get(planet_full)
    if p_id is not None:
        pos, _ = swe.calc_ut(jd, p_id, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
        return pos[0]
    return None

def _sign_from_longitude(lon):
    if lon is None: return None
    return ZODIAC_SIGNS[int(lon // 30)]

def _sign_lord(sign):
    return SIGN_LORDS.get(sign)

def _angular_diff(a, b):
    diff = abs(a - b) % 360
    return min(diff, 360 - diff)

def _is_conjunct(lon_a, lon_b, orb=6.0):
    if lon_a is None or lon_b is None: return False
    return _angular_diff(lon_a, lon_b) <= orb

def _has_aspect(planet_full, lon_a, lon_b, orb=6.0):
    if lon_a is None or lon_b is None: return False
    
    _ASPECT_DEGREES = {
        'Sun': [180], 'Moon': [180], 'Mercury': [180], 'Venus': [180],
        'Mars': [90, 180, 210], 'Jupiter': [120, 180, 240], 'Saturn': [60, 180, 270],
        'Rahu': [180], 'Ketu': [180]
    }
    
    aspects = _ASPECT_DEGREES.get(planet_full, [180])
    for deg in aspects:
        if _angular_diff(_angular_diff(lon_a, lon_b), deg) <= orb:
            return True
    return False

def _cusps_at_time(dt_utc, lat, lon):
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, 
                    dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600)
    ayanamsa = swe.get_ayanamsa_ut(jd)
    cusps, _ = swe.houses(jd, lat, lon, b'P')
    return [(c - ayanamsa) % 360 for c in cusps]

def _find_house_from_cusps(longitude, cusps):
    for i in range(11):
        if cusps[i] <= cusps[i+1]:
            if cusps[i] <= longitude < cusps[i+1]:
                return i + 1
        else: # Cusp 12 wrap-around
            if longitude >= cusps[i] or longitude < cusps[i+1]:
                return i + 1
    return 12

def _is_connected_to_lord(planet_short, lord_short, dt_utc, engine, target_houses=None):
    if not planet_short or not lord_short:
        return False

    planet_full = PlanetNameUtils.to_full_name(planet_short)
    lord_full = PlanetNameUtils.to_full_name(lord_short)

    planet_lon = _planet_longitude_at_time(dt_utc, planet_short)
    lord_lon = _planet_longitude_at_time(dt_utc, lord_short)
    if planet_lon is None or lord_lon is None:
        return False

    # In star (nakshatra) of lord
    planet_nl, _, _, _ = engine._get_lordships(planet_lon)
    in_star = planet_nl == lord_short

    # Conjunction or aspect
    conjunct = _is_conjunct(planet_lon, lord_lon, orb=6.0)
    aspect = _has_aspect(planet_full, planet_lon, lord_lon, orb=6.0) or _has_aspect(lord_full, lord_lon, planet_lon, orb=6.0)

    # In target houses
    in_target_house = False
    if target_houses:
        cusps_now = _cusps_at_time(dt_utc, engine.lat, engine.lon)
        planet_house = _find_house_from_cusps(planet_lon, cusps_now)
        in_target_house = planet_house in target_houses

    # Mutual exchange (sign lords swap)
    planet_sign = _sign_from_longitude(planet_lon)
    lord_sign = _sign_from_longitude(lord_lon)
    exchange = False
    if planet_sign and lord_sign:
        exchange = _sign_lord(planet_sign) == lord_full and _sign_lord(lord_sign) == planet_full

    return in_star or conjunct or aspect or in_target_house or exchange

def map_to_image_labels(row, team_a, team_b):
    verdict = str(row.get('Verdict', ''))
    score = row.get('Score', 0)
    nl_score = row.get('NL_Score', None)
    sl_score = row.get('SL_Score', None)
    ssl_score = row.get('SSL_Score', None)

    try:
        score = float(score)
    except:
        score = 0

    def _safe_float(val):
        try: return float(val)
        except: return None

    nl_score = _safe_float(nl_score)
    sl_score = _safe_float(sl_score)
    ssl_score = _safe_float(ssl_score)

    is_asc = score > 0
    is_desc = score < 0
    abs_score = abs(score)

    aligned_layers = 0
    for layer_score in [nl_score, sl_score, ssl_score]:
        if layer_score is None or layer_score == 0:
            continue
        if is_asc and layer_score > 0: aligned_layers += 1
        if is_desc and layer_score < 0: aligned_layers += 1

    if aligned_layers >= 2 and abs_score >= 0.95:
        return "BOTH SL ASC (NOTE IT)" if is_asc else "BOTH SL DSC (NOTE IT)"

    if abs_score >= 0.75 and sl_score is not None:
        if is_asc and sl_score > 0: return "SL ASC ADV"
        if is_desc and sl_score < 0: return "SL DSC ADV"

    if abs_score >= 0.85:
        return "SL ASC" if is_asc else "SL DSC"
    if abs_score >= 0.35:
        label = "ASC" if is_asc else "DSC"
        if aligned_layers >= 2 and abs_score <= 0.45: return f"{label} (NOTE IT)"
        return label
    if abs_score >= 0.15:
        label = "CAN BE ASC" if is_asc else "LOOKS DSC"
        if aligned_layers >= 2: return f"{label} (NOTE IT)"
        return label
    return "MIX"

def generate_lagna_based_timeline(engine, analysis_engine, start_utc, duration_hours, target_tz, team_a, team_b,
                                  sssl_adjustment_map=None, sssl_adjustment_strength=0.0,
                                  combined_adjustment_map=None, combined_adjustment_strength=0.0):
    asc_gen = TimelineGenerator(engine, 'Ascendant')
    detailed = asc_gen.generate_detailed_timeline_df(start_utc, duration_hours)
    lagna_sssl_df = detailed['sssl_timeline']
    moon_gen = TimelineGenerator(engine, 'Moon')
    
    rows = []
    last_label = None
    last_time = None
    
    for idx, l_row in lagna_sssl_df.iterrows():
        t = l_row['Start Time']
        # Ensure timestamp is timezone-aware (use UTC as default)
        try:
            if getattr(t, 'tzinfo', None) is None:
                t = pytz.UTC.localize(pd.to_datetime(t))
        except Exception:
            t = pd.to_datetime(t)
            if getattr(t, 'tzinfo', None) is None:
                t = pytz.UTC.localize(t)
        m_details = moon_gen._get_body_details_at_time(t)
        m_nl, m_sl, m_ssl, m_sssl = m_details['nl'], m_details['sl'], m_details['ssl'], m_details['sssl']
        
        l_lon = l_row.get('longitude') or engine.get_cusp_longitude_at_time(t, 1)
        lagna_sign = ZODIAC_SIGNS[int(l_lon // 30)]
        
        nl_score = analysis_engine.calculate_planet_score(PlanetNameUtils.to_full_name(m_nl))
        sl_score = analysis_engine.calculate_planet_score(PlanetNameUtils.to_full_name(m_sl))
        ssl_score = analysis_engine.calculate_planet_score(PlanetNameUtils.to_full_name(m_ssl))
        
        ssl_score_adj = analysis_engine._calculate_lagna_based_moon_ssl_adjustment(m_ssl, lagna_sign, ssl_score, 'ascendant')
        base_score = analysis_engine._calculate_ssl_hierarchical_score(ssl_score_adj, sl_score, nl_score)

        final_score = base_score
        if combined_adjustment_map and combined_adjustment_strength:
            key = f"{m_sssl}|{lagna_sign}"
            comb_dir = combined_adjustment_map.get(key)
            if comb_dir in (-1, 1): final_score += (comb_dir * float(combined_adjustment_strength))
        if sssl_adjustment_map and sssl_adjustment_strength:
            sssl_dir = sssl_adjustment_map.get(m_sssl)
            if sssl_dir in (-1, 1): final_score += (sssl_dir * float(sssl_adjustment_strength))
        
        dummy_row = {'Score': final_score, 'NL_Score': nl_score, 'SL_Score': sl_score, 'SSL_Score': ssl_score_adj}
        label = map_to_image_labels(dummy_row, team_a, team_b)
        m_ssl_name = PlanetNameUtils.to_full_name(m_ssl)
        favors = team_a if final_score > 0 else team_b
        if idx == 0: note = f"Match Start: Lagna in {lagna_sign} (Favors {favors})"
        else:
            if label != last_label:
                if "SL" in label: note = f"Peak Momentum: {favors} strongest phase"
                elif label in ["ASC", "DSC"]: note = f"Momentum Shift: {favors} builds pressure"
                else: note = f"Lagna in {lagna_sign} | Moon SSSL: {m_ssl_name}"
            else: note = f"Sustained {favors} advantage"

        include = (label != last_label) or (last_time and (t - last_time).total_seconds() > 180)
        if include:
            if t.tzinfo is None: t = pytz.UTC.localize(t)
            ist = t.astimezone(pytz.timezone('Asia/Kolkata')).strftime('%I:%M:%S %p')
            loc_tz = target_tz if not isinstance(target_tz, str) else pytz.timezone(target_tz)
            loc = t.astimezone(loc_tz).strftime('%I:%M:%S %p')
            rows.append({
                'Time (IST)': ist, 'Time (Local)': loc, 'Start Time': t.isoformat(),
                'Indicator': label, 'Technical Note (Moon SSSL / Lagna)': note,
                'Moon_SSSL': m_sssl, 'Moon_SL': m_sl, 'Moon_SSL': m_ssl, 'Lagna_Sign': lagna_sign,
                'NL_Score': nl_score, 'SL_Score': sl_score, 'SSL_Score': ssl_score_adj,
                'Base_Score': base_score, 'Final_Score': final_score,
                'wicket_strength': _sssl_wicket_strength(m_sssl, engine)
            })
            last_label = label; last_time = t
    return pd.DataFrame(rows)

# --- Wicket Event Assignment by Batting/Bowling and Dominance ---
def assign_wicket_events_by_rules(timeline_df, match_start_utc, match_duration_hours):
    """
    Assigns wicket events per user rules:
    - First half: A bats, B bowls. Second half: B bats, A bowls.
    - Dominance: A% > B% means A dominant, B% > A% means B dominant.
    - Only one event per segment: 'A takes wicket', 'A loses wicket', 'B takes wicket', 'B loses wicket', or 'No wicket event'.
    """
    if timeline_df is None or timeline_df.empty:
        return timeline_df
    df = timeline_df.copy()
    
    # Compute match midpoint
    try:
        match_start = pd.to_datetime(match_start_utc)
        if match_start.tzinfo is None:
            match_start = pytz.UTC.localize(match_start)
        match_mid = match_start + pd.Timedelta(hours=match_duration_hours / 2)
    except Exception:
        match_start = None
        match_mid = None

    n = len(df)
    for i, row in df.iterrows():
        # Determine batting/bowling by half using Start Time if available
        seg_time = None
        if match_start is not None:
            if 'Start Time' in row:
                seg_time = pd.to_datetime(row['Start Time'], errors='coerce')
                if seg_time.tzinfo is None:
                    seg_time = pytz.UTC.localize(seg_time)
            
            if seg_time is None or pd.isna(seg_time):
                # Fallback to index-based split
                seg_time = match_start + pd.Timedelta(minutes=i * (match_duration_hours * 60 / n))

        if seg_time is not None and match_mid is not None:
            first_half = seg_time < match_mid
        else:
            first_half = i < n // 2

        # A is Ascendant (Team A), B is Descendant (Team B)
        if first_half:
            batting = 'A'
            bowling = 'B'
        else:
            batting = 'B'
            bowling = 'A'

        # Dominance based on percentage scores
        try:
            a_val = str(row.get('A', '0')).replace('%', '').replace('+', '')
            a_pct = float(a_val) if a_val else 0.0
        except Exception:
            a_pct = 0.0
            
        try:
            b_val = str(row.get('B', '0')).replace('%', '').replace('+', '')
            b_pct = float(b_val) if b_val else 0.0
        except Exception:
            b_pct = 0.0

        if a_pct > b_pct:
            dominant = 'A'
        elif b_pct > a_pct:
            dominant = 'B'
        else:
            dominant = None

        # Apply wicket rules
        wicket_event = 'No wicket event'
        if dominant:
            if batting == 'A' and dominant == 'B':
                wicket_event = 'A loses wicket'
            elif bowling == 'A' and dominant == 'A':
                wicket_event = 'A takes wicket'
            elif batting == 'B' and dominant == 'A':
                wicket_event = 'B loses wicket'
            elif bowling == 'B' and dominant == 'B':
                wicket_event = 'B takes wicket'

        df.at[i, 'Wicket_Event'] = wicket_event

    return df
