// 色差の計算を照合するテスト
//   node tests/test.js            # 不一致があれば終了コード 1
//   python tests/make_reference.py  # 参照値 tests/reference.json を作り直す（colour-science が必要）
// 計算部分は index.html の /*MATH-START*/ ～ /*MATH-END*/ を切り出して実行する
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const m = html.match(/\/\*MATH-START\*\/([\s\S]*?)\/\*MATH-END\*\//);
if (!m) { console.error('index.html に MATH-START / MATH-END の目印が見つかりません'); process.exit(1); }
const ctx = {};
vm.createContext(ctx);
vm.runInContext(m[1] + '\n;Object.assign(this,{cie76,cie94,cmc,ciede2000,deltaE,flopIndex,midPoint,P94});', ctx);
const { cie76, cie94, cmc, ciede2000, deltaE, flopIndex, midPoint, P94 } = ctx;

const K1 = { kL: 1, kC: 1, kH: 1 };
const fails = [];
const counts = {};
const check = (group, ok, msg) => {
  counts[group] = (counts[group] || 0) + 1;
  if (!ok) fails.push(`[${group}] ${msg}`);
};

// ---------- 1. CIEDE2000：Sharma らの公式テストデータ 34 組 ----------
// 公表値は小数 4 桁なので、丸めの幅（±0.00005）以内なら一致とする。基準と試料を入れ替えても同じ値になることも確かめる
const sharma = require('./sharma.js');
sharma.forEach(([a, b, exp], i) => {
  for (const [r, s, dir] of [[a, b, '1→2'], [b, a, '2→1']]) {
    const v = ciede2000(r, s, K1).dE;
    check('Sharma', Math.abs(v - exp) <= 5e-5 + 1e-12, `${i + 1} 組目 ${dir}: ${v.toFixed(6)}（公表値 ${exp.toFixed(4)}）`);
  }
});

// ---------- 2. colour-science との照合（乱数 300 組 × 7 式） ----------
const ref = JSON.parse(fs.readFileSync(path.join(__dirname, 'reference.json'), 'utf8'));
const calc = {
  de76:         (r, s) => cie76(r, s).dE,
  de94_graphic: (r, s) => cie94(r, s, P94.graphic).dE,
  de94_textile: (r, s) => cie94(r, s, P94.textile).dE,
  cmc_2_1:      (r, s) => cmc(r, s, { l: 2, c: 1 }).dE,
  cmc_1_1:      (r, s) => cmc(r, s, { l: 1, c: 1 }).dE,
  de00:         (r, s) => ciede2000(r, s, K1).dE,
  de00_kL2:     (r, s) => ciede2000(r, s, { kL: 2, kC: 1, kH: 1 }).dE,
};
const maxDiff = {};
for (const [key, f] of Object.entries(calc)) {
  const exp = ref.dE[key];
  if (!exp) { check('colour', false, `参照値に ${key} がありません`); continue; }
  let worst = 0;
  ref.pairs.forEach(([r, s], i) => {
    const d = Math.abs(f(r, s) - exp[i]);
    worst = Math.max(worst, d);
    check('colour', d <= 1e-9, `${key} ${i + 1} 組目: 差 ${d.toExponential(2)}`);
  });
  maxDiff[key] = worst;
}

// ---------- 3. フロップインデックス（手計算の値） ----------
// FI = 2.69 × (118.2 − 30.5)^1.11 / 58.1^0.86 = 11.73
check('FI', flopIndex(118.2, 58.1, 30.5).toFixed(2) === '11.73', `FI = ${flopIndex(118.2, 58.1, 30.5)}`);
check('FI', Number.isNaN(flopIndex(118.2, 0, 30.5)), 'L*45° = 0 のときは NaN');
check('FI', flopIndex(30.5, 58.1, 118.2) < 0, 'L*15° < L*110° のときは負');

// ---------- 4. 中間色：指定した比になっているか（乱数 500 組 × 4 式 × 比 3 種） ----------
let seed = 12345;
const rand = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 2 ** 32; };
const lab = () => [rand() * 100, rand() * 200 - 100, rand() * 200 - 100];
const opt = { p94: 'graphic', cmc: { l: 2, c: 1 }, k: K1 };
// CMC は色相角 164°・345° で T が、L* = 16 で SL が不連続に変わるため、比がその点で飛び、指定の比ちょうどの点が
// ないことがある。そのときは二分法が飛びの位置に収束するので、前後の比が指定の比をはさんでいれば正しく求まったとみなす
const ratio = (A, B, s, f) => {
  const M = A.map((v, k) => v + s * (B[k] - v));
  const dA = deltaE(f, M, A, opt).dE, dB = deltaE(f, M, B, opt).dE;
  return dA / (dA + dB);
};
let midWorst = 0, midJump = 0;
for (let i = 0; i < 500; i++) {
  const A = lab(), B = lab();
  for (const f of ['de76', 'de94', 'cmc', 'de00']) {
    for (const t of [0.25, 0.5, 0.75]) {
      const { s } = midPoint(A, B, t, f, opt);
      const d = Math.abs(ratio(A, B, s, f) - t);
      let ok = d <= 1e-9;
      if (!ok && f === 'cmc') {
        const lo = ratio(A, B, s - 1e-9, f), hi = ratio(A, B, s + 1e-9, f);
        if (lo <= t && t <= hi) { ok = true; midJump++; }
      }
      if (d <= 1e-9) midWorst = Math.max(midWorst, d);
      check('中間色', ok, `${f} t=${t} ${i + 1} 組目: 比の差 ${d.toExponential(2)}`);
    }
  }
}

// ---------- 結果 ----------
console.log(Object.entries(counts).map(([k, v]) => `${k}:${v}`).join('  '));
console.log(`colour-science（${ref.generator}）との最大差: ` +
  Object.entries(maxDiff).map(([k, v]) => `${k} ${v.toExponential(1)}`).join(', '));
console.log(`中間色の比の最大差: ${midWorst.toExponential(1)}（CMC の不連続点に当たったもの ${midJump} 件を除く）`);
const total = Object.values(counts).reduce((a, b) => a + b, 0);
if (fails.length) {
  console.error(`${fails.length} / ${total} 件が不一致`);
  fails.slice(0, 20).forEach(f => console.error('  ' + f));
  process.exit(1);
}
console.log(`全 ${total} 件一致`);
