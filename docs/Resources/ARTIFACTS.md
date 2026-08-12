[← Back to README](../../README.md)

# Artifact Policy

This document outlines the versioning, maintenance and generation guidelines for the dataset and model weights stored within this repository. To ensure reviewers and evaluators can immediately run the visualization and edge diagnostic demonstrations, a pre-compiled set of model parameters is tracked.

---

## Artifact Generation & Deployment Flow

The diagram below details how source datasets feed into the training scripts to produce the serialized model assets and embedded C headers:

```mermaid
flowchart TD
    subgraph Raw Datasets
        Data_Class["original_ev_battery_dataset_multiclass.csv"]
    end

    subgraph Offline Training Pipelines
        Train_Class["train_classifier.py"]
        Train_Est["train_estimator.py"]
        Train_Soft["train_rc.py"]
    end

    subgraph Generated Assets & Code Artifacts
        Header_Class["esn_classifier_weights.h<br>(CSR format, C header)"]
        Header_Est["esn_estimator_weights.h<br>(C header)"]
        Pickle_Model["model_rc.pkl<br>(Python pickle)"]
    end

    subgraph Runtime Engines
        MCU_Firmware["main.c<br>(Embedded diagnostic firmware)"]
        Visualiser["app.py (Visualiser)<br>(Comparative dashboard)"]
    end

    Data_Class --> Train_Class
    Train_Class --> Header_Class
    Train_Est --> Header_Est
    Train_Soft --> Pickle_Model

    Header_Class --> MCU_Firmware
    Pickle_Model --> Visualiser
```

---

## Tracked Repository Artifacts

The table below catalogs all model parameters, datasets and generated headers tracked in Git:

| File path | Format | Typical Size | Role | Source / Generator | Versioning Policy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| [`hardware/STM_Verifier/original_ev_battery_dataset_multiclass.csv`](../hardware/STM_Verifier/original_ev_battery_dataset_multiclass.csv) | CSV | ~360 KB | Training and validation data for thermal state classification. | Synthesized battery sensor logs. | Immutable. Only updated on structural schema shifts. |
| [`software/visualiser/model_rc.pkl`](../software/visualiser/model_rc.pkl) | PKL | ~140 KB | Local fallback model for the visualiser ESN estimator (used when MongoDB is offline). | Trained via [`train_rc.py`](../software/visualiser/training/train_rc.py). | Regenerated upon tuning model hyperparameters. |
| [`hardware/STM_Verifier/esn_classifier_weights.h`](../hardware/STM_Verifier/esn_classifier_weights.h) | H (C Header) | ~13 KB | Generated sparse classifier weights consumed by [`main.c`](../hardware/STM_Verifier/main.c). | Exported via [`train_classifier.py`](../hardware/STM_Verifier/train_classifier.py). | Re-exported whenever the classifier ESN is retrained. |
| [`hardware/STM_Verifier/esn_estimator_weights.h`](../hardware/STM_Verifier/esn_estimator_weights.h) | H (C Header) | ~5.8 MB | Generated estimator weights for embedded testing. | Exported via [`train_estimator.py`](../hardware/STM_Verifier/train_estimator.py). | Updated on observer pipeline refinements. |

---

## 🚫 What NOT to Commit

> [!CAUTION]
> The root `.gitignore` file enforces exclusion rules. Do not bypass it to commit:
> - Local configuration scripts or `.env` files.
> - Raw local database dumps, temporary runtime logs, or telemetry playback caches.
> - Local python virtual environments (`venv`, `.venv`) and compiler outputs (`.o`, `.elf`, `.hex`, `.exe`).
> - Temp python caches (`__pycache__`, `.pytest_cache`).

---

## 🔁 Updating Artifacts

When submitting a pull request that updates any tracked model or dataset, the submitter must document the following in the commit message or PR description:

1. **Training Command**: The exact python execution script and arguments used.
2. **Dataset Version**: The source files and dataset timestamps used.
3. **Metrics Log**: The validation criteria met (e.g., classification accuracy percentage, estimator RMSE bounds).
4. **Justification**: A brief rationale explaining why the pre-trained weights need updating in Git instead of running dynamic local training.
