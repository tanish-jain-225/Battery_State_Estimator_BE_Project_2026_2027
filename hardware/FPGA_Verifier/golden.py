import csv
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
verification_path = os.path.join(BASE_DIR, 'verification.csv')
golden_path = os.path.join(BASE_DIR, 'golden.csv')

def to_hex_signed(val, nbits):
    mask = (1 << nbits) - 1
    ndigits = -(-nbits // 4)  # ceiling division: 18 bits -> 5 hex digits
    return format(val & mask, 'x').zfill(ndigits)

rows_out = []
if not os.path.exists(verification_path):
    raise FileNotFoundError(f"Verification CSV not found at {verification_path}")

with open(verification_path, newline='') as f:
    r = csv.DictReader(f)
    for row in r:
        p = int(row['Pass'])
        if p not in (1, 2):
            continue  # Pass 3 has no Vivado counterpart (tb only ran 2 passes)
        passbuf = p - 1  # Pass 1 -> passbuf 0, Pass 2 -> passbuf 1

        neuron = int(row['Neuron'])

        mac_hex = row['MAC_hex'].strip().lower().zfill(4)
        bias_hex = row['Bias_hex'].strip().lower().zfill(4)

        sum_raw = int(row['NeuronSum_raw'])
        sum_hex = to_hex_signed(sum_raw, 18)

        tanh_in_real = float(row['TanhInput'])
        tanh_in_raw = round(tanh_in_real * 1024)
        tanh_in_hex = to_hex_signed(tanh_in_raw, 16)

        x_next_raw = int(row['x_next_raw'])
        tanh_out_hex = to_hex_signed(x_next_raw, 16)

        rows_out.append({
            'pass': passbuf,
            'neuron': neuron,
            'mac': mac_hex,
            'bias': bias_hex,
            'sum': sum_hex,
            'tanh_in': tanh_in_hex,
            'tanh_out': tanh_out_hex,
        })

rows_out.sort(key=lambda r: (r['pass'], r['neuron']))

with open(golden_path, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['pass','neuron','mac','bias','sum','tanh_in','tanh_out'])
    w.writeheader()
    w.writerows(rows_out)

print(f"Wrote {len(rows_out)} rows to {golden_path}")
