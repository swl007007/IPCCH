# Feature-design discussion, round 1

You are the separate Claude Fable 5.1 scientific design partner explicitly requested by the user. Read-only planning; do not modify files, start tasks, run code/training, or dispatch agents. Return your proposal in text. Do not claim that user approval exists for a formula set.

Goal: converge with the primary Codex agent on a SMALL, scientifically defensible manual feature package for a perfect-weather-forecast experiment. User says the search space is too large and wants us to discuss first, then present a few proposals for their selection. This is not a model performance optimization search.

Confirmed contract:
- Existing global origin_safe_climate_idp_v1 climate_safe_history_idp baseline already has no oracle. It has new shared monthly and completed-GS climate, safe IPC history and national IDP (870 features at H0/H3/H6;654 at H12). Preserve all these inputs.
- Three arms already approved: baseline; baseline+raw oracle; baseline+raw oracle+one fixed manual feature package. H0 shares baseline, no duplicate training.
- Oracle source is shared monthly prcp_anom_month_ensmean and tmean_anom_month_ensmean. For origin O and horizon H use O+1..O+min(H,6). H3 adds6 raw columns, H6/H12 add12. H12 covers first6 months only.
- User explicitly assumes these realized weather values are 100%-accurate forecasts available at O. Preserve actual observation months separately. No other future inputs permitted.
- Manual interaction domain approved: historical climate + existing safe IPC history. IDP retained as independent feature; no hand-built oracle x IDP/conflict/price/static interactions.
- Existing XGBoost tree ensemble already learns nonlinear interactions. Fixed estimator config/seed, strict annual fitting blocks 2022-2025, identical28205 evaluation keys, no tuning, no test-score-driven feature selection. Do not revive superseded monthly refits.
- Fit label cutoff Jan(Y)-max(H,1); weight anchor Jan(Y)-H; each row uses its own origin. Four cumulative regressors. Baseline retrospective publication/standardization provenance limits remain disclosed.

Known definitions:
- Monthly prcp anomaly is monthly total minus calendar-month climatology, documented mm/month; GS prcp anomaly is daily anomaly SUM over exact GS, documented mm/GS. Different accumulation windows. Current generating code not verified; no same-scale subtraction between these quantities.
- Monthly and GS tmean anomaly are mean anomalies in degrees C. All source climatology internals remain external limitations.
- Baseline same-variable origin value P; trailing3 mean R over O-2..O with minimum2 valid months; slope6 S=(x[O]-x[O-5])/5. Latest completed GS G chosen using end <= first day of O+1, regardless of whether value is missing.
- Safe history values: overall_phase_history_1/2/3 are latest3 reported phases with source <=min(O,T-1), possibly irregularly spaced; overall_phase_history_change_1_2 and _1_3 are differences (not time-normalized rates). These are ordinal phases, not population fractions.
- Missing source values stay missing. No prediction-dependent cohort dropping.

Prior unapproved candidate26 columns (do not treat this as a target count):
4 forecast window means F and endpoint slopes D (each for prcp and tmean);6 contrasts F-P,F-R,D-S;4 products F*R and F*G;2 compounds F_prcp*F_temp and mean(max(-prcp,0)*max(temp,0));10 products of the two F values with all5 safe IPC history terms.

My initial critique for discussion:26 is arbitrary; products with ordinal phases and raw GS totals have weak interpretability; slope features from3/6 points can be noisy; signed products conflate different quadrants; adding means/slopes and interactions together means arm3's gain cannot be called the isolated interaction effect. Need a coherent bounded hypothesis, not a smaller arbitrary bag. Do not choose extra variants by scoring the2022-2025 evaluation years. We can describe arm3 as a manual-engineering package or propose a better attribution boundary, but do not silently alter the three approved arms.

Please independently evaluate and propose at most TWO packages with exact formulas and counts (prefer a much smaller default, e.g.4-8 meaningful columns if justified, not a mandatory quota). Address:
1. What scientific hypothesis distinguishes each package; what would raw-oracle XGBoost already express?
2. Is any standalone oracle summary worth adding, and how to label attribution honestly?
3. Historical monthly versus GS variables; safe IPC coupling without pretending phase scale is cardinal; whether fewer than5 history terms is warranted.
4. Missingness/window comparability/zero handling/time boundaries. No sample fitting or undocumented normalization.
5. Which prior26 terms should be rejected and why; which decisions still need user selection versus technical judgment.

You may inspect these files if necessary (cwd is repo):
.trellis/tasks/10-07-origin-safe-no-weather-oracle-baseline/prd.md
.trellis/tasks/10-07-origin-safe-no-weather-oracle-baseline/research.md
src/ipcch/climate2015_features.py
src/ipcch/origin_safe.py

Return concise but concrete scientific reasoning and exact proposal formulas. This is round1; the primary agent will challenge your proposal before user review.
