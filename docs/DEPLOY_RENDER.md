# Deploying on Render

The simulator and visualiser are deployable as two independent Render web
services. They share MongoDB for state and telemetry, and the visualiser calls
the simulator through `SIMULATOR_URL`.

## Recommended Topology

| Render Service | Root Directory | Start Command |
| --- | --- | --- |
| `battery-state-simulator` | `software/simulator` | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120` |
| `battery-state-visualiser` | `software/visualiser` | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120` |

Use one worker for both services. The simulator has a background telemetry
thread, so multiple workers can duplicate generator loops.

## Environment Variables

Set these on both services:

```text
MONGODB_URI=mongodb+srv://...
MONGODB_DB_NAME=battery_estimation_db
MONGODB_READINGS_COLLECTION=readings
MONGODB_STATE_COLLECTION=sim_state
FLASK_DEBUG=False
```

Set this only on the visualiser:

```text
SIMULATOR_URL=https://<your-simulator-service>.onrender.com
MODEL_PATH=model_rc.pkl
TELEMETRY_RESPONSE_LIMIT=150
GRAPH_SLICE_LIMIT=120
TELEMETRY_FALLBACK_LIMIT=1000
```

## Blueprint Deployment

The repository includes `render.yaml` for Render Blueprint deployment. During
deployment, Render will ask for the unsynced secret values:

- `MONGODB_URI`
- `SIMULATOR_URL`

Deploy the simulator first or fill `SIMULATOR_URL` after Render gives the
simulator its public URL.

## Manual Deployment

Create two Render Web Services from the same repository:

1. Simulator service
   - Root Directory: `software/simulator`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`

2. Visualiser service
   - Root Directory: `software/visualiser`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`
   - `SIMULATOR_URL`: public URL of the simulator service

## Notes

- Do not set `SERVERLESS=1` for the simulator on Render Web Services. The
  simulator should run its background loop in the web process.
- Use MongoDB Atlas or another reachable MongoDB instance for persistent
  telemetry. Without MongoDB, local fallback buffers work but are not persistent.
- Render filesystems are ephemeral, so retrained visualiser models should be
  saved to MongoDB model registry when persistence matters.
