#!/usr/bin/env python3
"""Audit fixes for ellipse correction (review items 1-3)."""
import math
import numpy as np
from ellipse_correction import heydemann_fit, assess_fit, ARC_MIN

rng = np.random.default_rng(0)
lines = ['椭圆校正审查回归测试', '=' * 40]

# 1) Random noise must NOT pass
u = rng.standard_normal(500)
v = rng.standard_normal(500)
_, res = heydemann_fit(u, v)
ok_noise = res['ok']
lines.append(f'1. 纯高斯噪声 ok={ok_noise} (应为 False)  rms={res["rms"]:.3f}')

# 2) Short arc with high rms should fail
psi = np.linspace(0, 1.2, 80)
u_short = np.cos(psi) + 0.35
v_short = 0.9 * np.sin(psi + 0.08) + 0.30
par_short, res_short = heydemann_fit(u_short, v_short)
ctr_err = math.hypot(par_short['p'], par_short['q'])
lines.append(f'2. 短弧 ok={res_short["ok"]} (应为 False)  中心误差={ctr_err:.3f}  rms={res_short["rms"]:.3f}')

# 3) Good full circle should pass
phi = np.linspace(0, 2 * math.pi, 400, endpoint=False)
u = np.cos(phi) + 0.06
v = 0.88 * np.sin(phi + math.radians(4.5)) - 0.05
par, res = heydemann_fit(u, v)
lines.append(f'3. 整圆 ok={res["ok"]} (应为 True)  eps={par["B"]/par["A"]-1:+.3f}  rms={res["rms"]:.4f}')

pass_all = (not ok_noise) and (not res_short['ok']) and res['ok']
lines.append(f'\n{"PASS" if pass_all else "FAIL"}')
text = '\n'.join(lines)
print(text)
with open('/opt/cursor/artifacts/results_ellipse_audit.txt', 'w') as f:
    f.write(text)
