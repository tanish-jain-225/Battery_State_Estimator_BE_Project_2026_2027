# Legacy material (October 2026), kept only for reference

Superseded on 8 Nov 2026. Do not use these for new work.

* `packs/pack_B0018_roomtemp` and `packs/fold_B000x`: trained on the three or four 24 °C reference cells only,
  with post-load rest data inside each window. They are poor outside room temperature (SOC MAE about 0.7 on the
  4 °C cell B0047) and do not match the published results. They still load and run bit-exactly on the chip.
* `make_pack.py`, `make_pack_fold.py`: older pack builders that need the original research repository
  (`repo_fixed/`, `ip/mem/`), which is not part of this package. Use `../train_pack.py` instead.

The RTL regression vectors in `test_data/sim_c115` and `test_data/sim_b47` were generated with the room-temperature
pack. They test the hardware (bit-exactness), not model accuracy, so they remain valid.
