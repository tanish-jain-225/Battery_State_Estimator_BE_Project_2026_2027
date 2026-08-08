import csv
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
golden_path = os.path.join(BASE_DIR, 'golden.csv')
vivado_path = os.path.join(BASE_DIR, 'vivado_esn_results.csv')

def load(path, key_pass='pass', key_neuron='neuron'):
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found at {path}")
    with open(path, newline='') as f:
        r = csv.DictReader(f)
        return {(int(row[key_pass]), int(row[key_neuron])): row for row in r}

golden = load(golden_path)
vivado = load(vivado_path, key_pass='passbuf', key_neuron='neuron')

stages = ['mac', 'bias', 'sum', 'tanh_in', 'tanh_out']

keys = sorted(golden.keys())
missing_in_vivado = [k for k in keys if k not in vivado]
extra_in_vivado = [k for k in vivado.keys() if k not in golden]

print(f"golden.csv rows: {len(golden)}")
print(f"vivado_esn_results.csv rows: {len(vivado)}")
print(f"missing in vivado: {len(missing_in_vivado)}")
print(f"extra in vivado (no golden counterpart): {len(extra_in_vivado)}")
print()

stopped_at = None
for stage in stages:
    mismatches = []
    for k in keys:
        if k not in vivado:
            continue
        g = golden[k][stage].strip().lower()
        v = vivado[k][stage].strip().lower()
        if g != v:
            mismatches.append((k, g, v))

    total = sum(1 for k in keys if k in vivado)
    ok = total - len(mismatches)
    print(f"[{stage:8s}] {ok}/{total} match", end='')
    if mismatches:
        print(f"  -- FIRST MISMATCH: pass={mismatches[0][0][0]} neuron={mismatches[0][0][1]}  golden={mismatches[0][1]}  vivado={mismatches[0][2]}")
        print(f"             {len(mismatches)} total mismatches in this stage")
        # show first 5
        for k, g, v in mismatches[:5]:
            print(f"             pass={k[0]} neuron={k[1]}: golden={g} vivado={v}")
        if stopped_at is None:
            stopped_at = stage
    else:
        print("  -- ALL MATCH")
    print()

print("="*60)
if stopped_at:
    print(f"First stage with divergence: {stopped_at.upper()}")
else:
    print("All stages match bit-exactly across all 200 rows.")
