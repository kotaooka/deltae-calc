# colour-science で色差の参照値を作り、tests/reference.json に書き出す
#   pip install colour-science
#   python tests/make_reference.py
# 乱数の種は固定なので、同じ版の colour-science なら毎回同じ値になる
from pathlib import Path
import json
import numpy as np
import colour

N = 300
rng = np.random.default_rng(20261012)

# 基準 r：L* 0〜100、a*・b* −100〜100
r = np.column_stack([rng.uniform(0, 100, N), rng.uniform(-100, 100, N), rng.uniform(-100, 100, N)])
# 試料 s：実務に近い小さい差（前半）と、大きい差（後半）を混ぜる
scale = np.where(np.arange(N) < N // 2, 3.0, 30.0)[:, None]
s = r + rng.normal(0, 1, (N, 3)) * scale
s[:, 0] = np.clip(s[:, 0], 0, 100)

D = colour.difference
cases = {
    # キーは tests/test.js の呼び出しと対応させる
    'de76':          D.delta_E_CIE1976(r, s),
    'de94_graphic':  D.delta_E_CIE1994(r, s, textiles=False),
    'de94_textile':  D.delta_E_CIE1994(r, s, textiles=True),
    'cmc_2_1':       D.delta_E_CMC(r, s, l=2, c=1),
    'cmc_1_1':       D.delta_E_CMC(r, s, l=1, c=1),
    'de00':          D.delta_E_CIE2000(r, s),
    'de00_kL2':      D.delta_E_CIE2000(r, s, textiles=True),
}

out = {
    'generator': f'colour-science {colour.__version__}',
    'pairs': [[a.tolist(), b.tolist()] for a, b in zip(r, s)],
    'dE': {k: np.asarray(v).tolist() for k, v in cases.items()},
}
path = Path(__file__).resolve().parent / 'reference.json'
path.write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8', newline='\n')
print(f'{path.name} を書き出しました（{out["generator"]}、{N} 組 × {len(cases)} 式）')
