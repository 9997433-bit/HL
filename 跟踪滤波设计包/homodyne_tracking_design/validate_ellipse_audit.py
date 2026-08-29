#!/usr/bin/env python3
"""Audit fixes for ellipse correction (review items 1-3)."""
import math
import sys

import numpy as np

from _artifact_io import write_results
from ellipse_correction import heydemann_fit, fit_arc_gated, ARC_MIN

rng = np.random.default_rng(0)
lines = ['椭圆校正审查回归测试', '=' * 40]

# 1) Random noise must NOT pass
u = rng.standard_normal(500)
v = rng.standard_normal(500)
_, res = heydemann_fit(u, v)
ok_noise = res['ok']
lines.append(f'1. 纯高斯噪声 ok={ok_noise} (应为 False)  rms={res["rms"]:.3f}')

# 2) Short arc (noiseless) should fail
psi = np.linspace(0, 1.2, 80)
u_short = np.cos(psi) + 0.35
v_short = 0.9 * np.sin(psi + 0.08) + 0.30
par_short, res_short = heydemann_fit(u_short, v_short)
ctr_err = math.hypot(par_short['p'], par_short['q'])
lines.append(f'2. 无噪短弧 ok={res_short["ok"]} (应为 False)  中心误差={ctr_err:.3f}  rms={res_short["rms"]:.3f}')

# 3) Noisy short arc via fit_arc_gated must fail (pre-fit arc gate)
prev = dict(p=0.35, q=0.30, A=1.0, B=0.9, delta=math.radians(4.58))
psi3 = np.linspace(0, 1.2, 300)
u3 = np.cos(psi3) + prev['p'] + 0.002 * rng.standard_normal(300)
v3 = 0.9 * np.sin(psi3 + prev['delta']) + prev['q'] + 0.002 * rng.standard_normal(300)
_, res_noisy = fit_arc_gated(u3, v3, prev, gate_tol=0.15)
lines.append(f'3. 带噪短弧 fit_arc_gated ok={res_noisy["ok"]} (应为 False)  '
             f'msg={res_noisy.get("msg", "")[:60]}')

# 4) Good full circle should pass
phi = np.linspace(0, 2 * math.pi, 400, endpoint=False)
u = np.cos(phi) + 0.06
v = 0.88 * np.sin(phi + math.radians(4.5)) - 0.05
par, res = heydemann_fit(u, v)
lines.append(f'4. 整圆 ok={res["ok"]} (应为 True)  eps={par["B"]/par["A"]-1:+.3f}  rms={res["rms"]:.4f}')

pass_all = ((not ok_noise) and (not res_short['ok']) and (not res_noisy['ok'])
            and res['ok'])
lines.append(f'\n{"PASS" if pass_all else "FAIL"}')
text = '\n'.join(lines)
print(text)
write_results('results_ellipse_audit.txt', text)
sys.exit(0 if pass_all else 1)
