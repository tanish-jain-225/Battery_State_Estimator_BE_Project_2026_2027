"""Canonical shim forwarding to hardware/FPGA_Verifier/golden_model.py."""

import os
import sys

_ROOT_FPGA = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT_FPGA not in sys.path:
    sys.path.insert(0, _ROOT_FPGA)

from golden_model import *  # noqa: F401, F403, E402
from golden_model import _resolve_resource_path, main  # noqa: F401, E402

if __name__ == "__main__":
    main()
