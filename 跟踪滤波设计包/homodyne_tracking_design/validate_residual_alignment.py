#!/usr/bin/env python3
"""审查项 #4: core.residual_mode (产品路径) vs gear_filter (验证路径) 一致性断言.

背景: 原 core.residual_mode 的残差测量窗是一阶 IIR (iir1_lowpass), 而
validate_tracking.py 验证的是 1025-tap 线性相位 FIR 窗 -- 验证 PASS 不覆盖
产品路径, 且 residual_mode 是死代码 (无人调用).  现 residual_mode 已改为与
gear_filter 复用同一 FIR 设计函数 (core.fir_lp_kernel, Hann 窗加窗 sinc,
NT_WIN=1025 taps), 本脚本对两条路径做端到端一致性断言:

  SLOW/MEDIUM/FAST 三档 x 100 kHz / 1 MHz / 3 MHz 三频, 分别在
    (a) 近无噪 burst, gate='always'  (validate_tracking 规则 R1 的幅值转移)
    (b) 含噪 CNR=3 dB, gate='auto'   (同一噪声实现喂给两条路径)
  比较 lock-in 幅度误差 (%), 断言 |err_gear - err_core| < 1 个百分点.

群时延说明: 两条路径均以 'same' 对齐补偿 (Nt-1)/2 采样 FIR 群时延;
实时硬件需在 NCO 相位路径加 NT_WIN/2 采样延迟线 (见 core.fir_lp_same 注释).
250 MS/s 全速率单级 1025 taps 硬件不可行, 需多级降采样等效实现
(见 design_params.NT_WIN 注释); 本脚本与 validate_tracking 一样直接跑
全速率参考滤波器.
"""
import time
import numpy as np

from core import residual_mode, complex_bandlimited_noise
from design_params import (
  FS, B_FRONTEND, ZETA, B_WIN, NT_WIN, TAU_G, BANDS, ORDER, gate_params,
)
from validate_tracking import (
  N, gear_filter, make_scene, clean_z, amp_err_pct, vdisc,
)

TOL_PP = 1.0                     # 断言容差: 幅度误差差异 < 1 个百分点
FREQS = (100e3, 1e6, 3e6)


def core_path(z, band, Nhat, gate):
  """core.residual_mode with the gear's parameter set (product path)."""
  y, phi, st, dg = residual_mode(
      z, FS, BANDS[band]['fn'], Nhat, B_WIN,
      zeta=ZETA, tauG=TAU_G, Nt_win=NT_WIN, gate=gate, **gate_params(band))
  return y


def main():
  t0 = time.time()
  print('残差窗一致性验证 (审查项 #4): core.residual_mode vs '
        'validate_tracking.gear_filter')
  print(f'  fs={FS/1e6:.0f}MS/s, B_win={B_WIN/1e6:.0f}MHz, '
        f'NT_WIN={NT_WIN} taps, 容差 |Δerr| < {TOL_PP:.0f}pp')

  fails = []
  for tag, gate, cnr_db in (('near-noiseless / gate=always', 'always', None),
                            ('CNR=3dB noisy / gate=auto', 'auto', 3.0)):
    print(f'\n  [{tag}]')
    print(f"    {'gear':<7} {'f0':>7} | {'err gear_filter':>15} "
          f"{'err residual_mode':>17} | {'|diff| pp':>9}")
    for band in ORDER:
      for f0 in FREQS:
        sc = make_scene(f0)
        if gate == 'always':
          z, Nhat = clean_z(sc), 1e-10
        else:
          s2 = 10 ** (-cnr_db / 10)
          rng = np.random.default_rng(40_000 + int(f0 / 1e3))
          z = (np.exp(1j * sc['ph'])
               + complex_bandlimited_noise(N, FS, B_FRONTEND, s2, rng))
          Nhat = s2
        yg, _, _, _, _ = gear_filter(z, band, Nhat, gate=gate)
        yc = core_path(z, band, Nhat, gate)
        eg = amp_err_pct(vdisc(yg), sc)
        ec = amp_err_pct(vdisc(yc), sc)
        d = abs(eg - ec)
        ok = d < TOL_PP
        if not ok:
          fails.append((tag, band, f0, eg, ec, d))
        print(f"    {band:<7} {f0/1e3:5.0f}k | {eg:+14.3f}% {ec:+16.3f}% "
              f"| {d:9.4f}{'' if ok else '   <-- FAIL'}")

  print('\n' + '=' * 70)
  n_cases = 2 * len(ORDER) * len(FREQS)
  if fails:
    print(f'FAIL: {len(fails)}/{n_cases} 组合差异 >= {TOL_PP:.0f}pp')
  else:
    print(f'PASS: 全部 {n_cases} 组合 (三档 x 三频 x 无噪/含噪) '
          f'幅度误差差异 < {TOL_PP:.0f}pp -- 验证路径 = 产品路径')
  print(f'[elapsed {time.time()-t0:.1f} s]')
  return 1 if fails else 0


if __name__ == '__main__':
  raise SystemExit(main())
