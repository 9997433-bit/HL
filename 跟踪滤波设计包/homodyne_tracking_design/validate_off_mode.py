#!/usr/bin/env python3
"""OFF 模式 (tracking_mode='off') 产品封装冒烟回归.

OFF 不是第四档, 是跟踪旁路: 无 PLL、无残差窗, 输出 angle(z) / FM 鉴频
(core.off_mode) -- 即 V1/V3 对照中的 OFF 参考列.  与 gate_policy='always'
严格区分: 后者只旁路掉落门, PLL 仍在跟踪 (gate-off != OFF).

断言 (轻量 smoke, 全部 PASS 退出码 0):
  O1  API 路由: cfg_for_frequency(tracking_mode='off') -> band=None;
      core.tracking_filter 走旁路, phi == angle(z) 逐样本一致, |y| == 1,
      state is None (此模式不存在门控).
  O2  旁路保真: 近无噪 100 kHz burst, OFF 输出的 FM 鉴频与直接鉴频 raw z
      一致 (单位模归一化不改变鉴频), 且 lock-in 幅值误差 < 0.5 %.
  O3  gate-off != OFF: 弱光 CNR=3 dB, SLOW 档 gate_policy='always' 相对
      OFF 的 quiet-window 速度 ASD 改善 > 10 dB (PLL 仍在跟踪并提供门限
      扩展); OFF 增益恒为 0 dB (输出 == 输入相位, 定义使然).
  O4  PLL 路径一致: tracking_filter(cfg pll) 与 residual_mode 直接调用
      逐样本一致 (gate auto / always 各一次) -- 新入口未改变已验证路径.
  O5  参数守卫: 非法 tracking_mode / 非法 gate_policy (含把 'off' 误当
      门控值) / pll 模式缺 Nhat, 均抛 ValueError.
"""
import math
import time
import numpy as np

from core import (
  tracking_filter, residual_mode, complex_bandlimited_noise,
)
from design_params import (
  FS, B_FRONTEND, ZETA, B_WIN, BANDS, gate_params, cfg_for_frequency,
)
from validate_tracking import N, make_scene, clean_z, amp_err_pct, vdisc, asd_at

LINES = []
CHECKS = []


def out(s=''):
  print(s)
  LINES.append(s)


def check(cid, label, ok, detail):
  CHECKS.append(ok)
  out(f"  [{'PASS' if ok else 'FAIL'}] {cid}  {label}  ({detail})")
  return ok


def main():
  t0 = time.time()
  out('OFF 模式产品封装冒烟回归 (tracking_mode in {pll, off})')
  out(f'  fs={FS/1e6:.0f}MS/s; OFF = 跟踪旁路: 输出 angle(z)/FM 鉴频, '
      '无 PLL 无残差窗; gate-off (gate_policy=always) 仍是 PLL 模式')

  sc = make_scene(100e3)
  zc = clean_z(sc)

  # ---- O1: routing / bypass identity -------------------------------------
  cfg_off = cfg_for_frequency(100e3, tracking_mode='off')
  y, phi, st, dg = tracking_filter(zc, FS, cfg_off)
  ok1 = (cfg_off['tracking_mode'] == 'off' and cfg_off['band'] is None
         and st is None and dg.get('mode') == 'off'
         and np.array_equal(phi, np.angle(zc))
         and np.allclose(np.abs(y), 1.0, atol=1e-12))
  check('O1', "cfg(tracking_mode='off') 路由到旁路: band=None, "
        'phi==angle(z), |y|=1, state=None', ok1,
        f"band={cfg_off['band']}, mode={dg.get('mode')}")

  # ---- O2: bypass fidelity (near-noiseless) -------------------------------
  v_off = vdisc(y)
  e = amp_err_pct(v_off, sc)
  same = bool(np.allclose(v_off, vdisc(zc), atol=1e-6))
  check('O2', 'OFF 旁路保真: FM 鉴频与 raw z 一致, 近无噪幅值误差 < 0.5 %',
        same and abs(e) < 0.5, f'ampErr {e:+.3f}%, v_off==v_raw: {same}')

  # ---- O3: gate-off != OFF (weak light, SLOW @100 kHz) --------------------
  s2 = 10 ** (-3.0 / 10)                      # CNR = 3 dB
  cfg_gof = cfg_for_frequency(100e3, gate_policy='always')
  gains = []
  off_is_raw = True
  for s in range(2):
    rng = np.random.default_rng(50_000 + s)
    z = np.exp(1j * sc['ph']) + complex_bandlimited_noise(N, FS, B_FRONTEND,
                                                          s2, rng)
    y_off, _, _, _ = tracking_filter(z, FS, cfg_off)
    off_is_raw &= bool(np.allclose(vdisc(y_off), vdisc(z), atol=1e-6))
    y_pll, _, _, _ = tracking_filter(z, FS, cfg_gof, Nhat=s2)
    gains.append(20 * math.log10(asd_at(vdisc(y_off), sc)
                                 / asd_at(vdisc(y_pll), sc)))
  g = float(np.median(gains))
  check('O3', "gate-off != OFF: gate_policy='always' 仍在跟踪 "
        '(弱光 ASD 改善 > 10 dB), OFF 恒 0 dB (输出==输入)',
        g > 10.0 and off_is_raw and cfg_gof['tracking_mode'] == 'pll'
        and cfg_gof['gate'] == 'always',
        f'PLL(SLOW, gate=always) vs OFF: {g:+.1f} dB @100kHz CNR=3dB '
        f'(2 seeds); OFF==raw: {off_is_raw}')

  # ---- O4: pll path of tracking_filter == residual_mode -------------------
  rng = np.random.default_rng(50_000)
  z = np.exp(1j * sc['ph']) + complex_bandlimited_noise(N, FS, B_FRONTEND,
                                                        s2, rng)
  ok4 = True
  for gate in ('auto', 'always'):
    cfg = cfg_for_frequency(100e3, gate_policy=gate)
    ya, pa, sa, _ = tracking_filter(z, FS, cfg, Nhat=s2)
    yb, pb, sb, _ = residual_mode(z, FS, BANDS['SLOW']['fn'], s2, B_WIN,
                                  zeta=ZETA, gate=gate, **gate_params('SLOW'))
    ok4 &= (np.array_equal(ya, yb) and np.array_equal(pa, pb)
            and np.array_equal(sa, sb))
  check('O4', 'PLL 路径一致: tracking_filter == residual_mode 逐样本 '
        '(gate auto/always)', ok4, 'y/phi/state 全部 array_equal')

  # ---- O5: parameter guards ------------------------------------------------
  def raises(fn):
    try:
      fn()
      return False
    except ValueError:
      return True

  ok5 = (raises(lambda: cfg_for_frequency(1e5, tracking_mode='bogus'))
         and raises(lambda: cfg_for_frequency(1e5, gate_policy='off'))
         and raises(lambda: tracking_filter(zc, FS, cfg_for_frequency(1e5))))
  check('O5', '参数守卫: 非法 tracking_mode / gate_policy=off 误用 / '
        'pll 缺 Nhat 均 ValueError', ok5, '3/3 raised')

  allok = all(CHECKS)
  out('')
  out(('ALL CHECKS PASSED' if allok else 'SOME CHECKS FAILED')
      + f'  ({sum(CHECKS)}/{len(CHECKS)})')
  out(f'[elapsed {time.time()-t0:.1f} s]')
  from _artifact_io import write_results
  write_results('results_off_mode.txt', '\n'.join(LINES) + '\n')
  return 0 if allok else 1


if __name__ == '__main__':
  raise SystemExit(main())
