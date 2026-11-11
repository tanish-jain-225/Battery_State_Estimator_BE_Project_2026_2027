"""Canonical shim forwarding to hardware/FPGA_Verifier/compare_results.py."""

import os
import sys

_ROOT_FPGA = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT_FPGA not in sys.path:
    sys.path.insert(0, _ROOT_FPGA)

from compare_results import *  # noqa: F401, F403, E402
from compare_results import main  # noqa: E402

if __name__ == "__main__":
    main()
