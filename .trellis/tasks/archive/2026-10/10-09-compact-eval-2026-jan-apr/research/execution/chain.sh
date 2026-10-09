#!/bin/bash
# Sequential authorized actions; stop on the first nonzero action return code.
cd "/mnt/c/Users/swl00/IFPRI Dropbox/Weilun Shi/Google fund/Analysis/2.source_code/Step5_Geo_RF_trial/IPCCH"
E=.trellis/tasks/10-09-compact-eval-2026-jan-apr/research/execution
export PATH=/tmp/ipcch-windows-git-bin:$PATH PYTHONPATH=src
pin() { { echo "pinned_utc $(date -u +%FT%TZ)"; git rev-parse HEAD; sha256sum scripts/modeling/run_compact_eval_2026_extension.py tests/unit/test_compact_eval_2026_extension.py scripts/modeling/run_somalia_local_compact_test.py configs/forecasting_hyperparameters.json configs/forecasting_hyperparameters_p3.json; } > "$1"; }
for step in "global approve-training" "SOM approve-training" "global report" "SOM report" "global verify" "SOM verify"; do
  set -- $step; scope=$1; action=$2; tag="${action}_${scope}"
  pin $E/${tag}_pins_before.txt
  /usr/bin/time -v /home/swl007007/.venvs/ipcch-geo/bin/python scripts/modeling/run_compact_eval_2026_extension.py --scope $scope --$action > $E/${tag}_stdout.json 2> $E/${tag}.log &
  pid=$!; echo "$pid $tag" >> $E/pids.txt; wait $pid; rc=$?
  pin $E/${tag}_pins_after.txt
  echo "$(date -u +%FT%TZ) $tag rc=$rc" >> $E/action_returncodes.txt
  if [ $rc -ne 0 ]; then echo "STOPPED after $tag" >> $E/action_returncodes.txt; exit $rc; fi
done
echo "ALL DONE" >> $E/action_returncodes.txt
