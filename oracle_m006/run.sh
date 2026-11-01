#!/bin/bash
# M006-EDGECHECKER -- reproduces every number in results.json from a clean shell.
#   ./run.sh          regenerate models, run every property, write logs/, collect
#   ./run.sh collect  rebuild results.json from existing logs/ (no engine needed)
#
# ENGINE: -explicit throughout, as the mission instructs (the PI reports hybrid
# hung previously). Note that PRISM-games switches to explicit for every SMG
# regardless, so the flag binds only the MDP arm.
# Per-property cap 30 min, enforced by a perl fork/alarm wrapper (macOS has no
# timeout(1)). State budget 1.0e7 -- not approached; see NOTES.md.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE"
PRISM="${PRISM:-prism}"
PG="${PRISM_GAMES:-prism-games}"
PY="${PYTHON:-python3}"
CAP=${CAP:-1800}
mkdir -p models props logs

cap() { local s=$1; shift
  perl -e 'my $s=shift; my $pid=fork(); if($pid==0){exec @ARGV or exit 127;}
    $SIG{ALRM}=sub{kill "TERM",$pid; sleep 2; kill "KILL",$pid; exit 124;};
    alarm $s; waitpid($pid,0); my $rc=$?>>8; alarm 0; exit $rc;' "$s" "$@"; }

if [ "${1:-run}" != "collect" ]; then
  echo "== M2: regenerating models from the written spec =="
  $PY gen_edge.py models

  echo "== M4: sweep =="
  for f in models/*.prism; do
    m=$(basename "$f" .prism)
    case "$m" in aeb_mdp_*) BIN="$PRISM"; PROPS=props/mdp.props; N=4;;
                 *)         BIN="$PG";    PROPS=props/smg.props; N=5;; esac
    for p in $(seq 1 $N); do
      cap "$CAP" "$BIN" "$f" "$PROPS" -prop "$p" -explicit > "logs/${m}_P${p}.log" 2>&1
      rc=$?; [ $rc -eq 124 ] && echo "TIMEOUT after ${CAP}s" >> "logs/${m}_P${p}.log"
    done
    echo "  $m done"
  done

  echo "== M4: strategy export at the equalising cells =="
  for m in 1 2; do
    f=models/aeb_smg_e10_b2_c3_m${m}.prism
    cap "$CAP" "$PG" "$f" props/smg.props -prop 1 -explicit \
        -exportstrat "logs/strategy_smg_e10_b2_m${m}.txt" \
        > "logs/strategy_smg_e10_b2_m${m}.log" 2>&1
  done
fi

echo "== M5: collect =="
$PY collect.py
