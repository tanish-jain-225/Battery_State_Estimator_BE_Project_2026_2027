import sys
import os

# Ensure root directory is at the front of sys.path for fully-qualified imports
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Add subdirectories at the end of sys.path so fully-qualified software.* and hardware.* take precedence
for sub in [
    os.path.join(ROOT_DIR, "software", "visualiser"),
    os.path.join(ROOT_DIR, "software", "visualiser", "training"),
    os.path.join(ROOT_DIR, "hardware", "FPGA_Verifier"),
    os.path.join(ROOT_DIR, "hardware", "STM_Verifier"),
]:
    if sub not in sys.path:
        sys.path.append(sub)

# Enable testing mode flag for Flask apps and background workers
os.environ["TESTING"] = "1"

# Set non-blocking testing default for MongoDB so offline/sandboxed test suites execute instantly
if "MONGODB_URI" not in os.environ:
    os.environ["MONGODB_URI"] = "mongodb://localhost:27017/?serverSelectionTimeoutMS=20"
