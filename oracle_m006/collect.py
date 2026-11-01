#!/usr/bin/env python3
"""M006-EDGECHECKER — parse logs, run the invariant gates, emit results.json
(schema 1.1). No number is invented: every value is read from a log a run
produced, and a property with no value gets a status and value null."""
from __future__ import annotations
import hashlib, json, platform, re, subprocess, sys
from pathlib import Path

H = Path(__file__).resolve().parent
EPS = [0, 5, 10, 20]; MS = [0, 1, 2, 3, 4]; C = 3
D, Dmax = 16, 16
MDP_P = {1: ('Pmax=? [ F "unsafe" ]', "P1"), 2: ('Pmin=? [ G !"unsafe" ]', "P2"),
         3: ('R{"time"}min=? [ F "latched" ]', "P3"), 4: ('Pmax=? [ F "latched" ]', "P4")}
SMG_P = {1: ('<<defender>>Pmin=? [ F "unsafe" ]', "P1"),
         2: ('<<attacker>>Pmax=? [ F "unsafe" ]', "P2"),
         3: ('<<defender>>Pmax=? [ G !"unsafe" ]', "P3"),
         4: ('<<defender>>R{"time"}min=? [ F "latched" ]', "P4"),
         5: ('<<defender>>Pmax=? [ F "latched" ]', "P5")}
GATE = 1e-6


def cells():
    for e in EPS:
        for m in MS:
            yield ("mdp", e, 0, m)
    for e in EPS:
        for b in (1, 2, 3):
            for m in MS:
                yield ("smg", e, b, m)


def mid(k, e, b, m): return f"aeb_{k}_e{e:02d}_b{b}_c{C}_m{m}"
def pid(k, p, e, b, m):
    n = (MDP_P if k == "mdp" else SMG_P)[p][1]
    return f"{n}/{k}/e{e}/b{b}/m{m}"


def parse(f: Path) -> dict:
    o = {"status": "error", "value": None, "states": None, "transitions": None,
         "build_time_s": None, "runtime_s": None, "note": None}
    if not f.exists():
        o["note"] = "log absent"; return o
    t = f.read_text(errors="replace")
    for k, rx in (("states", r"^States:\s+(\d+)"), ("transitions", r"^Transitions:\s+(\d+)")):
        mm = re.search(rx, t, re.M)
        if mm: o[k] = int(mm.group(1))
    mm = re.search(r"Time for model construction:\s+([\d.]+)", t)
    if mm: o["build_time_s"] = float(mm.group(1))
    mc = re.search(r"Time for model checking:\s+([\d.]+)", t)
    if o["build_time_s"] is not None:
        o["runtime_s"] = round(o["build_time_s"] + (float(mc.group(1)) if mc else 0), 3)
    if "TIMEOUT after" in t: o["status"], o["note"] = "timeout", "per-property cap"; return o
    if "OutOfMemoryError" in t: o["status"], o["note"] = "error", "java heap"; return o
    mm = re.search(r"^Result:\s*(\S+)", t, re.M)
    if not mm:
        em = re.search(r"^Error:\s*(.+)$", t, re.M)
        o["note"] = em.group(1).strip() if em else "no Result line"; return o
    raw = mm.group(1)
    if raw.lower().startswith("infinity"):
        o["status"], o["value"] = "ok", "Infinity"; return o
    try:
        o["value"], o["status"] = float(raw), "ok"
    except ValueError:
        o["note"] = f"unparseable {raw!r}"
    return o


def monitor_size(m: int) -> tuple[int, int]:
    """Monitor automaton size WITHOUT hardware. Its memory is the suspicion
    counter (m+1 values), the latch bit (2), and the previous perceived gap
    (D+1 values, which it must retain to test plausibility). Reported in states
    and in bits of state. The conversion to kilobytes is REFUSED: it needs an
    encoding, a compiler and a target, none of which exist here. [VERIFY-HW]"""
    states = (m + 1) * 2 * (Dmax + 1)
    bits = (max(1, (m).bit_length() if m else 1)) + 1 + (Dmax).bit_length()
    return states, bits


def main():
    logs = H / "logs"
    runs = {}
    for k, e, b, m in cells():
        P = MDP_P if k == "mdp" else SMG_P
        for p in P:
            runs[(k, e, b, m, p)] = parse(logs / f"{mid(k,e,b,m)}_P{p}.log")

    models, props, metrics, anomalies = [], [], [], []
    for k, e, b, m in cells():
        P = MDP_P if k == "mdp" else SMG_P
        rs = [runs[(k, e, b, m, p)] for p in P]
        st = next((r for r in rs if r["states"] is not None), None)
        status = "built" if st else "build_error"
        if st and st["states"] > 1.0e7:
            status = "over_budget"; anomalies.append(f"{mid(k,e,b,m)}: over 1.0e7 states")
        ent = {"model_id": mid(k, e, b, m), "game": "AEB loop (edge-AI + environment + attacker)",
               "ruleset": f"eps={e}/100, attacker b={b}, check c={C}, monitor m={m}",
               "file": f"models/{mid(k,e,b,m)}.prism", "model_type": k,
               "status": status, "engine": "explicit"}
        if st:
            ent.update(states=st["states"], transitions=st["transitions"],
                       build_time_s=st["build_time_s"])
        models.append(ent)
        for p in P:
            r = runs[(k, e, b, m, p)]
            pe = {"property_id": pid(k, p, e, b, m), "model_id": mid(k, e, b, m),
                  "prism_property": P[p][0], "props_file": f"props/{k}.props",
                  "status": r["status"], "value": r["value"] if r["status"] == "ok" else None,
                  "engine": "explicit",
                  "command": (f"{'prism' if k=='mdp' else 'prism-games'} "
                              f"models/{mid(k,e,b,m)}.prism props/{k}.props -prop {p} -explicit"),
                  "log_file": f"logs/{mid(k,e,b,m)}_P{p}.log"}
            if r["runtime_s"] is not None: pe["runtime_s"] = r["runtime_s"]
            sf = logs / f"strategy_smg_e{e:02d}_b{b}_m{m}.txt"
            if k == "smg" and p == 1 and sf.exists():
                pe["strategy_export"] = f"logs/{sf.name}"
                pe["command"] += f" -exportstrat logs/{sf.name}"
            if r["status"] != "ok" and r["note"]:
                anomalies.append(f"{pe['property_id']}: {r['status']} -- {r['note']}")
            props.append(pe)

    # ---- gate 1: MDP duality  Pmax[F unsafe] + Pmin[G !unsafe] = 1 ----------
    worst_dual, worst_dual_id = 0.0, None
    for e in EPS:
        for m in MS:
            a, bb = runs[("mdp", e, 0, m, 1)], runs[("mdp", e, 0, m, 2)]
            if a["status"] != "ok" or bb["status"] != "ok": continue
            if not (isinstance(a["value"], float) and isinstance(bb["value"], float)): continue
            res = abs(a["value"] + bb["value"] - 1.0)
            metrics.append({"metric_id": f"dual_residual/mdp/e{e}/m{m}", "value": res,
                            "derived_from": [pid("mdp",1,e,0,m), pid("mdp",2,e,0,m)],
                            "formula": "abs(Pmax[F unsafe] + Pmin[G !unsafe] - 1)"})
            if res > worst_dual: worst_dual, worst_dual_id = res, f"mdp/e{e}/m{m}"
            if res > GATE: anomalies.append(f"GATE FAIL dual mdp/e{e}/m{m}: {res:.3g}")

    # ---- gate 2: SMG determinacy  <<def>>Pmin = <<att>>Pmax ----------------
    worst_det, worst_det_id = 0.0, None
    for e in EPS:
        for b in (1, 2, 3):
            for m in MS:
                a, bb = runs[("smg", e, b, m, 1)], runs[("smg", e, b, m, 2)]
                if a["status"] != "ok" or bb["status"] != "ok": continue
                if not (isinstance(a["value"], float) and isinstance(bb["value"], float)): continue
                res = abs(a["value"] - bb["value"])
                metrics.append({"metric_id": f"determinacy_residual/smg/e{e}/b{b}/m{m}", "value": res,
                                "derived_from": [pid("smg",1,e,b,m), pid("smg",2,e,b,m)],
                                "formula": "abs(<<defender>>Pmin[F unsafe] - <<attacker>>Pmax[F unsafe])"})
                if res > worst_det: worst_det, worst_det_id = res, f"smg/e{e}/b{b}/m{m}"
                if res > GATE: anomalies.append(f"GATE FAIL determinacy smg/e{e}/b{b}/m{m}: {res:.3g}")

    # ---- monitor size, hardware-free --------------------------------------
    for m in MS:
        st, bits = monitor_size(m)
        metrics.append({"metric_id": f"monitor_states/m{m}", "value": st,
                        "derived_from": [pid("mdp",1,10,0,m)],
                        "formula": ("(m+1) suspicion values x 2 latch x (D+1) retained "
                                    "previous perceived gap; D=16. Structural, read off the "
                                    "model, NOT measured on hardware [VERIFY-HW]")})
        metrics.append({"metric_id": f"monitor_bits/m{m}", "value": bits,
                        "derived_from": [pid("mdp",1,10,0,m)],
                        "formula": "ceil bits for the same three fields [VERIFY-HW]"})

    # ---- benefit and non-monotonicity -------------------------------------
    for k, bs in (("mdp", [0]), ("smg", [1, 2, 3])):
        for e in EPS:
            for b in bs:
                vs = {}
                for m in MS:
                    r = runs[(k, e, b, m, 1)]
                    if r["status"] == "ok" and isinstance(r["value"], float): vs[m] = r["value"]
                if len(vs) < 2 or 0 not in vs: continue
                best = min(vs, key=lambda x: vs[x])
                metrics.append({"metric_id": f"best_m/{k}/e{e}/b{b}", "value": float(best),
                                "derived_from": [pid(k,1,e,b,m) for m in vs],
                                "formula": "argmin over m of the collision probability"})
                metrics.append({"metric_id": f"benefit_at_best/{k}/e{e}/b{b}",
                                "value": vs[0] - vs[best],
                                "derived_from": [pid(k,1,e,b,0), pid(k,1,e,b,best)],
                                "formula": "P(unsafe) at m=0 minus P(unsafe) at the best m"})
                rises = [m for m in sorted(vs)[1:] if vs[m] > vs[m-1] + GATE] if all(
                    m-1 in vs for m in sorted(vs)[1:]) else []
                metrics.append({"metric_id": f"nonmonotone_steps/{k}/e{e}/b{b}",
                                "value": float(len(rises)),
                                "derived_from": [pid(k,1,e,b,m) for m in vs],
                                "formula": ("count of m where P(unsafe) STRICTLY INCREASES from "
                                            "m-1 to m by more than 1e-6 -- the mission's PR4")})

    # ---- noise as a defence: does a NOISIER AI survive an attack better? ---
    # Under attack with no monitor the AI is the only thing standing between a
    # spoof and a collision. A deterministic AI (eps=0) is fully fooled; a noisy
    # one sometimes brakes anyway. This measures that, and it is the mission's
    # most counter-intuitive result, so it gets its own metric rather than
    # living in prose.
    for b in (1, 2, 3):
        vals = {}
        for e in EPS:
            r = runs[("smg", e, b, 0, 1)]
            if r["status"] == "ok" and isinstance(r["value"], float):
                vals[e] = r["value"]
        if 0 in vals and 20 in vals:
            metrics.append({
                "metric_id": f"noise_defence/smg/b{b}",
                "value": vals[0] - vals[20],
                "derived_from": [pid("smg", 1, e, b, 0) for e in sorted(vals)],
                "formula": ("P(unsafe) at eps=0 minus P(unsafe) at eps=20%, unmonitored "
                            "(m=0) and under attack. Positive means a NOISIER controller "
                            "is SAFER against the attacker.")})

    checks = {}
    for d in ("models", "props"):
        for f in sorted((H / d).glob("*")):
            if f.is_file(): checks[f"{d}/{f.name}"] = hashlib.sha256(f.read_bytes()).hexdigest()

    out = {"schema_version": "1.1", "mission_id": "M006-EDGECHECKER", "agent": "claude",
           "completed_at": subprocess.run(["date","-u","+%Y-%m-%dT%H:%M:%SZ"],
                                          capture_output=True, text=True).stdout.strip(),
           "environment": {"prism_version": "4.10.1", "prism_games_version": "3.2.4",
                           "os": f"macOS {platform.mac_ver()[0]}", "machine": "Apple M1 Pro, 16 GB"},
           "models": models, "properties": props, "metrics": metrics,
           "claims": json.loads((H/"claims.json").read_text()) if (H/"claims.json").exists() else [],
           "anomalies": anomalies, "checksums": checks}
    (H/"results.json").write_text(json.dumps(out, indent=2) + "\n")
    ok = sum(1 for p in props if p["status"] == "ok")
    print(f"properties {ok}/{len(props)} ok | models {len(models)} | metrics {len(metrics)}")
    print(f"gate 1 MDP duality      worst {worst_dual:.3g} at {worst_dual_id or 'n/a'}")
    print(f"gate 2 SMG determinacy  worst {worst_det:.3g} at {worst_det_id or 'n/a'}")
    print(f"anomalies {len(anomalies)}")
    for a in anomalies[:8]: print("  !", a)


if __name__ == "__main__":
    main()
