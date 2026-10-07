# IPCCH forecasting comparison language

Terms used in the origin-safe global forecast and perfect-weather comparison.

## Forecast timing

**Target month (T)**: The month whose reported food-security outcome is predicted.

**Row origin (O)**: The information cutoff for one prediction, H months before its target month: O=T−H.
_Avoid_: Using the annual fitting origin as every row's origin.

**Annual fitting origin**: The information cutoff used to fit the model for one target-year block; it can precede the row origins of later predictions in that year.

**Safe historical report**: A reported outcome available under the experiment's reporting-month cutoff. It may be stale and is not necessarily the actual state at the prediction origin.

**Origin-safe availability proxy**: A retrospective rule that uses source observation/reporting months to bound historical inputs. It does not establish their actual publication vintages or absence of later revisions.

## Comparison configurations

**Oracle-free reference**: The existing global configuration retaining shared monthly climate, completed growing-season climate, safe IPC history, national IDP and its other established inputs, without post-origin weather oracle terms.
_Avoid_: Claiming this configuration was chronologically the first experiment.

**Perfect-weather oracle**: Realized future weather treated counterfactually as a 100%-accurate forecast available at the row origin. Its actual observation month and assumed availability month are different concepts.
_Avoid_: Historical forecast-vintage evidence; a theoretical upper bound on forecast performance.

**B6 manual package**: Six fixed transformations of weather and safe history: future means, equal-weight past/future means and latest-safe-IPC3+ gated future means, each for precipitation and temperature.
_Avoid_: Calling all six terms interactions, or attributing the package's entire increment to IPC interaction alone.

## Regional evaluation

**Southern African region**: Areas assigned to region3 by the project's established area-to-region mapping.
_Avoid_: Substituting SADC, UN M49 or South Africa the country.

**Local evaluation of global predictions**: Scoring the regional subset of predictions produced by globally fitted models.
_Avoid_: Local model; regional retraining.

**Country-stratified whole-area paired bootstrap**: Resampling areas within each observed country, carrying every selected-period observation of each area together and sharing multiplicities across compared predictions. It conditions on the fitted models and observed country strata.

**Undefined metric**: A metric without a value under the frozen evaluation definition, such as F2 when no true positives are present under the current global convention.
_Avoid_: Automatically substituting zero.

**Conditional bootstrap interval**: A percentile interval formed only from paired resamples in which both compared metrics are defined. It describes that conditional resampling distribution, and its invalid-draw proportion is part of the result.
_Avoid_: Presenting it as an interval computed from all requested draws.
