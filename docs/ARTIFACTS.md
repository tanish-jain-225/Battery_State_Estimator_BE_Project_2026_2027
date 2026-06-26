# Artifact Policy

The repository intentionally contains a small set of data and model artifacts so
reviewers can run the demo without first retraining everything.

## Tracked Artifacts

- `hardware/original_ev_battery_dataset_multiclass.csv`
  - Used by the hardware-side ESN classifier training/export path.
- `software/visualiser/model_rc.pkl`
  - Local fallback model for the dashboard ESN estimator when MongoDB model
    registry data is unavailable.
- `hardware/esn_classifier_weights.h`
  - Generated C header consumed by `hardware/main.c`.
- `hardware/esn_estimator_weights.h`
  - Generated estimator weights for embedded experiments.

## Generated Locally

Do not commit local caches, `.env` files, compiled binaries, Python bytecode,
temporary logs, or scratch outputs. The root `.gitignore` covers these paths.

## Updating Artifacts

When updating a model or dataset, include:

- training command or script used,
- source dataset version,
- validation metrics,
- reason the artifact needs to be stored in Git instead of regenerated.
