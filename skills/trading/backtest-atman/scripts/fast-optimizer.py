#!/usr/bin/env python3
"""
ATMAN-v04 FAST OPTIMIZER — Pattern A only
Grid search over TP, BE, SL, trailing, hours, DOW filters.
Precomputes all indicators and swing levels ONCE before the grid loop.

Usage:
    cd /c/Users/Administrator/Desktop/FxPro
    "/c/Program Files/Python312/python.exe" scripts/fast-optimizer.py

Output: results/atman_optimization_results.json (1,440-2,880 configs)
Duration: 3-10 minutes (vs 42+ minutes for naive version)

Architecture:
  Phase 1 (once): load + indicators + regimes + swing levels
  Phase 2 (per config): one pass over bars, no indicator recalc
  
CONFIG (edit before run):
  TP_VALS = [300, 400, 500, 555, 650]
  BE_VALS = [0.30, 0.40, 0.50, 0.60]
  SL_VALS = [150, 185, 220, 250]
  TRAIL_VALS = [0, 20, 30]
  HOURS_VALS = [(8,20), (10,20), (12,20), (13,20), (13,19), (7,20)]
  DOW_VALS = [None, "not_mon"]
"""
import json, time
from pathlib import Path
import pandas as pd
import numpy as np

WORKDIR = Path(r"C:\Users\Administrator\Desktop\FxPro")
DATA_FILE = WORKDIR / "data" / "XAUUSD_H1_2019_2025.csv"
OUT_DIR = WORKDIR / "results"
BACKTEST_START = "2025-01-01"

LOT = 0.01
POINT = 0.01
SPREAD_FILTER_MAX = 150
SWING_LOOKBACK_H4 = 50
PULLBACK_MAX_PTS = 1500

# === GRID PARAMS (edit these) ===
TP_VALS = [300, 400, 500, 555, 650]
BE_VALS = [0.30, 0.40, 0.50, 0.60]
SL_VALS = [150, 185, 220, 250]
TRAIL_VALS = [0, 20, 30]
HOURS_VALS = [(8,20), (10,20), (12,20), (13,20), (13,19), (7,20)]
DOW_VALS = [None, "not_mon"]


def load_and_prep():
    df = pd.read_csv(DATA_FILE, parse_dates=["time"])
    df = df.sort_values("time").reset_index(drop=True)
    df["hour"] = df["time"].dt.hour
    df["dow"] = df["time"].dt.dayofweek
    df["spread"] = df["spread"].clip(lower=20)
    start = pd.Timestamp(BACKTEST_START)
    df = df[df["time"] >= start].reset_index(drop=True)
    print(f"[LOAD] {len(df)} bars")

    n = len(df)
    high, low, close = df["high"].values, df["low"].values, df["close"].values

    # ATR
    tr = np.zeros(n)
    tr[1:] = np.maximum(high[1:]-low[1:], np.maximum(np.abs(high[1:]-close[:-1]), np.abs(low[1:]-close[:-1])))
    df["atr14"] = pd.Series(tr).rolling(14, min_periods=14).mean()

    # ADX
    up_move = np.diff(high); down_move = np.diff(low)
    plus_dm = np.where((up_move>down_move)&(up_move>0), up_move, 0)
    minus_dm = np.where((down_move>up_move)&(down_move>0), down_move, 0)
    atr14_v = df["atr14"].values
    pdi=np.zeros(n); ndi=np.zeros(n)
    for i in range(1,n):
        if atr14_v[i]>0: pdi[i]=100*plus_dm[i-1]/atr14_v[i]; ndi[i]=100*minus_dm[i-1]/atr14_v[i]
    pdi_ema = pd.Series(pdi).ewm(span=14, min_periods=14).mean()
    ndi_ema = pd.Series(ndi).ewm(span=14, min_periods=14).mean()
    dx = 100*np.abs(pdi_ema-ndi_ema)/(pdi_ema+ndi_ema+1e-10)
    df["adx"] = dx.ewm(span=14, min_periods=14).mean()

    # ER
    change = np.zeros(n); noise = np.zeros(n)
    for i in range(10, n):
        change[i]=abs(close[i]-close[i-10])
        noise[i]=np.sum(np.abs(np.diff(close[i-10:i+1])))
    er_arr = np.full(n, np.nan)
    mask=noise>0
    er_arr[mask]=change[mask]/noise[mask]
    df["er"] = er_arr

    df["vol_ratio"] = df["atr14"] / pd.Series(tr).rolling(50, min_periods=50).mean()

    # Regime
    df["regime"] = "UNKNOWN"
    for i in range(50, n):
        row=df.iloc[i]
        if pd.isna(row["adx"]) or pd.isna(row["er"]): continue
        if row["vol_ratio"]>1.8: df.at[i,"regime"]="VOLATILE"
        elif row["adx"]>25 and row["er"]>0.4: df.at[i,"regime"]="TRENDING"
        elif row["adx"]<20 and row["er"]<0.3: df.at[i,"regime"]="RANGING"
        else: df.at[i,"regime"]="TRANSITIONING"

    # H4 swings (ONE TIME — precomputed per bar)
    df_h4 = df.copy()
    df_h4["g4"] = df_h4.index // 4
    h4 = df_h4.groupby("g4").agg({"time":"first","high":"max","low":"min"}).reset_index(drop=True)
    swings_h = []; swings_l = []
    for i in range(1,len(h4)-1):
        if h4.iloc[i]["high"]>h4.iloc[i-1]["high"] and h4.iloc[i]["high"]>h4.iloc[i+1]["high"]:
            swings_h.append(i)
        if h4.iloc[i]["low"]<h4.iloc[i-1]["low"] and h4.iloc[i]["low"]<h4.iloc[i+1]["low"]:
            swings_l.append(i)

    df["swing_high"] = np.nan
    df["swing_low"] = np.nan
    current_sh = None; sh_idx = -1000
    for i in range(100, n):
        h4_idx = i // 4
        if current_sh is not None and sh_idx < h4_idx - SWING_LOOKBACK_H4: current_sh = None
        for sh in swings_h:
            if sh <= h4_idx and (current_sh is None or sh > sh_idx):
                if sh >= h4_idx - SWING_LOOKBACK_H4:
                    current_sh = h4.iloc[sh]["high"]; sh_idx = sh
        if current_sh is not None: df.at[i, "swing_high"] = current_sh

    current_sl = None; sl_idx = -1000
    for i in range(100, n):
        h4_idx = i // 4
        if current_sl is not None and sl_idx < h4_idx - SWING_LOOKBACK_H4: current_sl = None
        for sl in swings_l:
            if sl <= h4_idx and (current_sl is None or sl > sl_idx):
                if sl >= h4_idx - SWING_LOOKBACK_H4:
                    current_sl = h4.iloc[sl]["low"]; sl_idx = sl
        if current_sl is not None: df.at[i, "swing_low"] = current_sl

    print(f"[PREP] {df['regime'].value_counts().to_dict()}")
    return df


def simulate_fast(df, tp, be, sl, trail, h_start, h_end, dow_f):
    n = len(df); trades = []; in_trade = None

    for i in range(200, n):
        row = df.iloc[i]
        if row["regime"]!="TRENDING": continue
        h = row["hour"]
        if h<h_start or h>h_end: continue
        if dow_f=="not_mon" and row["dow"]==0: continue
        if row["spread"]>SPREAD_FILTER_MAX: continue

        if in_trade:
            r = mgmt(df, i, in_trade, tp, be, sl, trail)
            if r: trades.append(r); in_trade = None
            continue

        close = row["close"]
        sh = row.get("swing_high")
        sl_val = row.get("swing_low")
        sig = None

        if not pd.isna(sh) and close>sh:
            dist = (close-sh)/POINT
            if 0<dist<=PULLBACK_MAX_PTS:
                sig = ("BUY", close, close-sl*POINT, close+tp*POINT, dist)
        if not sig and not pd.isna(sl_val) and close<sl_val:
            dist = (sl_val-close)/POINT
            if 0<dist<=PULLBACK_MAX_PTS:
                sig = ("SELL", close, close+sl*POINT, close-tp*POINT, dist)

        if sig:
            in_trade = {
                "dir":sig[0],"entry":sig[1],"sl":sig[2],"tp":sig[3],
                "dist_pts":sig[4],"spread":row["spread"],"hour":h,"dow":row["dow"],
                "time":row["time"],"be_set":False,"max_favor":0,"trail_sl":sig[2],
            }

    if in_trade:
        r = mgmt(df, n-1, in_trade, tp, be, sl, trail, force=True)
        if r: trades.append(r)
    return trades


def mgmt(df, i, ot, tp, be, sl, trail, force=False):
    row = df.iloc[i]; high, low, close = row["high"], row["low"], row["close"]
    entry = ot["entry"]; dir_ = ot["dir"]; sp = ot.get("spread", 20)
    be_trigger = tp * be

    fav = (high-entry)/POINT if dir_=="BUY" else (entry-low)/POINT
    ot["max_favor"] = max(ot["max_favor"], fav)

    if not ot["be_set"] and ot["max_favor"] >= be_trigger:
        ot["be_set"] = True
        ot["sl"] = entry + sp*POINT*0.3 if dir_=="BUY" else entry - sp*POINT*0.3

    if trail>0 and ot["be_set"]:
        ns = close - trail*POINT if dir_=="BUY" else close + trail*POINT
        if (dir_=="BUY" and ns>ot["trail_sl"]) or (dir_=="SELL" and ns<ot["trail_sl"]):
            ot["trail_sl"] = ns
            ot["sl"] = max(ot["sl"], ns) if dir_=="BUY" else min(ot["sl"], ns)

    if dir_=="BUY" and high>=ot["tp"]: return mk_t(ot, row["time"], ot["tp"], "TP", tp-sp)
    if dir_=="SELL" and low<=ot["tp"]: return mk_t(ot, row["time"], ot["tp"], "TP", tp-sp)
    if dir_=="BUY" and low<=ot["sl"]: return mk_t(ot, row["time"], ot["sl"], "BE" if ot["be_set"] else "SL", (ot["sl"]-entry)/POINT-sp)
    if dir_=="SELL" and high>=ot["sl"]: return mk_t(ot, row["time"], ot["sl"], "BE" if ot["be_set"] else "SL", (entry-ot["sl"])/POINT-sp)
    if force:
        pts = (close-entry)/POINT * (-1 if dir_=="SELL" else 1) - sp
        return mk_t(ot, row["time"], close, "TIME", pts)
    return None

def mk_t(ot, et, ep, reason, pts):
    return {"dir":ot["dir"],"entry":ot["entry"],"exit_price":ep,"exit_reason":reason,
            "pnl_pts":round(pts,1),"pnl_usd":round(pts*LOT,2),"spread":ot.get("spread",20),
            "hour":ot.get("hour",""),"dow":ot.get("dow",""),
            "time":str(ot["time"])[:16],"exit_time":str(et)[:16],
            "max_favor":round(ot.get("max_favor",0),0)}

def calc_m(trades):
    if not trades: return {"n":0}
    n=len(trades); wins=[t for t in trades if t["pnl_usd"]>0]; losses=[t for t in trades if t["pnl_usd"]<=0]
    nw,nl=len(wins),len(losses); wr=nw/n; aw=sum(t["pnl_usd"] for t in wins)/nw if nw else 0
    al=sum(t["pnl_usd"] for t in losses)/nl if nl else 0; total=sum(t["pnl_usd"] for t in trades)
    pf=abs(sum(t["pnl_usd"] for t in wins)/(sum(abs(t["pnl_usd"]) for t in losses)+1e-10))
    eq=[1550]; [eq.append(eq[-1]+t["pnl_usd"]) for t in trades]
    p=eq[0]; dd=0
    for e in eq[1:]:
        if e>p: p=e
        dd=max(dd,p-e)
    ret=np.diff(eq)/np.array(eq[:-1]); ret=ret[ret!=0]
    sharpe=np.mean(ret)/(np.std(ret)+1e-10)*np.sqrt(365*24) if len(ret)>1 else 0
    neg=ret[ret<0]
    sortino=np.mean(ret)/(np.std(neg)+1e-10)*np.sqrt(365*24) if len(neg)>0 else 0
    return {"n":n,"wr":round(wr,4),"total":round(total,2),"pf":round(pf,4),
            "dd":round(dd,2),"dd_pct":round(dd/1550*100,1),"sharpe":round(sharpe,4),
            "sortino":round(sortino,4),"calmar":round(total/dd,2) if dd>0 else 0,
            "avg_win":round(aw,2),"avg_loss":round(al,2)}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    df = load_and_prep()

    t = len(TP_VALS)*len(BE_VALS)*len(SL_VALS)*len(TRAIL_VALS)*len(HOURS_VALS)*len(DOW_VALS)
    print(f"[GRID] {t} configs"); results = []; done=0

    for tp, be, sl, trail, (hs,he), dw in [(tp,be,sl,trail,(hs,he),dw) 
        for tp in TP_VALS for be in BE_VALS for sl in SL_VALS
        for trail in TRAIL_VALS for (hs,he) in HOURS_VALS for dw in DOW_VALS]:
        trades = simulate_fast(df, tp, be, sl, trail, hs, he, dw)
        m = calc_m(trades)
        m["cfg"] = {"tp":tp,"be":be,"sl":sl,"trail":trail,"hours":f"{hs}-{he}","dow":dw}
        results.append(m); done+=1
        if done%300==0:
            bp = max(r["pf"] for r in results if r["n"]>=15)
            print(f"  {done}/{t} best PF={bp:.3f} ({time.time()-t0:.0f}s)")

    results.sort(key=lambda r: (r["pf"] if r["n"]>=15 else 0), reverse=True)
    top15 = [r for r in results if r["n"]>=15][:15]
    print("\nTOP 15:"); [print(f"  #{i+1}: PF={r['pf']:.3f} WR={r['wr']*100:.0f}% ${r['total']:.0f} DD=${r['dd']:.0f} n={r['n']} cfg={r['cfg']}") for i,r in enumerate(top15)]
    if top15:
        c=top15[0]["cfg"]; print(f"\n🥇 BEST: TP={c['tp']} BE={c['be']:.2f} SL={c['sl']} Trail={c['trail']} Hours={c['hours']} DOW={c['dow']}")

    with open(OUT_DIR/"atman_optimization_results.json","w") as f:
        json.dump([r for r in results if r["n"]>=10], f, indent=2, default=str)
    print(f"[JSON] Saved ({time.time()-t0:.0f}s)")

if __name__=="__main__":
    main()
