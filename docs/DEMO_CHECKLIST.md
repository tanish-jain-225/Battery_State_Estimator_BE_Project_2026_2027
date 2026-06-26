# Demo Checklist

Use this checklist before a review, viva, project exhibition, or pull request.

## Pre-Run

- Install all requirements: `python -m pip install -r requirements.txt`
- Confirm `.env` files contain only local values and are not committed.
- Train Software RC: `python software/visualiser/training/train_rc.py`
- Train Hardware Classifier: `python hardware/train_classifier.py`
- Train Hardware Estimator: `python hardware/train_estimator.py`
- Confirm MongoDB is running if persistent telemetry is required.
- Run `python -m unittest discover -s software/visualiser/tests`.
- Run the C simulator through `hardware/run_c_simulator.bat` or
  `hardware/run_c_simulator.sh`.

## Live Demo
- Start `software/simulator/app.py`: `python software/simulator/app.py`
- Start `software/visualiser/app.py`: `python software/visualiser/app.py`
- Open `http://localhost:5000`
- Open `http://localhost:8000`
- Start telemetry playback from the simulator/dashboard.
- Show SOC and SOH tracking against ground truth.
- Toggle thermal runaway, sensor dropout, and micro-short faults.
- Show how EKF, ESN, and diagnostics respond.
- Run the C classifier simulator and point out Normal/Warning/Critical output.

## Review Talking Points

- Why a 2-RC ECM is used for battery dynamics.
- Why EKF is a strong physics-based baseline.
- Why ESNs are suitable for low-cost recurrent inference.
- How CSR compression reduces embedded computation.
- How Q12/Q15 fixed-point math lowers MCU runtime cost.
- What still needs HIL validation before safety-critical use.
