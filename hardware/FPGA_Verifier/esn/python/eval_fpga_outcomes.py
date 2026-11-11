"""Canonical shim forwarding to hardware/FPGA_Verifier/eval_fpga_outcomes.py."""

import os
import sys

_ROOT_FPGA = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT_FPGA not in sys.path:
    sys.path.insert(0, _ROOT_FPGA)

from eval_fpga_outcomes import *  # noqa: F401, F403, E402
from eval_fpga_outcomes import evaluate_fpga_outcomes  # noqa: E402

if __name__ == "__main__":
    evaluate_fpga_outcomes()
