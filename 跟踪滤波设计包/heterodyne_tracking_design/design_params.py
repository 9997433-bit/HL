"""外差电IQ (Polytec类) 三档跟踪滤波参数 -- HeNe 632.8 nm 默认 (1550 nm 传 lam 即可).

与零差方案 (homodyne_tracking_design) 的设计哲学差异
--------------------------------------------------
  零差: 载波停在 0 Hz, 测量带宽由公共残差窗 B_win 决定, 换档只改载波环动态,
        三档在 3 MHz 处幅值误差都能 <5% (残差窗兜底).
  外差: 纯 NCO 架构 (OFV-3001 手册附录 D.2: 跟踪滤波器输出 = 再生载波,
        解码在下游另一级, **没有零差那样的残差窗**)。
        解码器看到的相位 = phi_hat = H_L * phi, 因此换档 SAME KNOB 同时决定:
          - 测量带宽   f_3dB = 2.0582*fn, 渐近 -20 dB/dec
          - 跟踪动态   a_design = pi*lambda*fn^2 (e_crit=1 设计线),
                       a_slip ~= pi*a_design    (e_crit=pi 卷绕线)
        高于 f_3dB 的谱线可用已知 |H_L(f)| 做频响校正恢复幅值刻度, 但谱线附近
        的噪声被同一 |H_L| 衰减 -- 校正不改变谱线 SNR, 只恢复标定。

[自研] 三步 fn 推导规则 (对齐 polytec_tracking_filter_sim.m 的 mode_params,
非原厂公式; PSV-500 手册只给规格数字):
  1) a_design(FAST) = 2*pi*f_acc*v_range,  f_acc = min(acq_bw, f_acc_cap)
     必须设 cap: "满量程幅值 x MHz 频率" 的加速度物理上不存在
  2) MEDIUM = FAST/10, SLOW = FAST/100 (a_design 比例) -> fn 每档 /sqrt(10)
  3) fn = sqrt(a_design/(pi*lambda))   (即 e_crit=1 设计线)

四层带宽 (noise_bandwidths.m 教义, 禁止 fs == 噪声带宽):
  fs          采样率: 只决定混叠与 |dphi|<pi 极限,  v_alias = lambda*fs/4
  B_frontend  前端复基带双边 ENBW: 决定 CNR 与噪声总功率 (积分意义)
  f_dev_max   IF 可用频偏硬边缘:  v_if = lambda*f_dev_max/2  (与 ENBW 不同参数!)
  B_loop      环路单边 ENBW = pi*fn*(1+4*zeta^2)/(4*zeta) = 3.3319*fn (zeta=.707)

CNR->相位灵敏度增益      = 10*log10(B_frontend / B_loop)
相对 OFF 的相位底噪改善  = 10*log10((B_frontend/2) / B_loop)   (差 3.01 dB)

纯 PLL 动态边界 (浴缸形, 从环路推导, 不是画出来的):
  v_max(f) = e_crit * lambda*f/2 / |1-H_L(f)|,
  |1-H_L| = x^2/sqrt((1-x^2)^2+4*zeta^2*x^2),  x = f/fn
  谷底精确在 f = fn, 谷值 = e_crit*lambda*fn/sqrt(2)  (zeta=0.707)
  整机可用边界 = min(v_max(f), lambda*f_dev_max/2, lambda*fs/4)
"""
import math

# ---------------------------------------------------------------- 物理/系统
LAMBDA = 632.8e-9          # HeNe 默认 (与 polytec_tracking_filter_sim.m 一致)
LAMBDA_ALT = 1550e-9       # 1550 nm 亦支持: 所有函数均可显式传 lam
FS = 50e6                  # 采样率 (只决定混叠, 非噪声带宽)
B_FRONTEND = 19e6          # 前端复基带双边 ENBW
F_DEV_MAX = 9.5e6          # IF 可用频偏硬边缘 (与 ENBW 是两个参数)
ZETA = 0.707

# [自研] fn 推导规则输入
ACQ_BW = 1e6               # 采集带宽 (Hz)
F_ACC_CAP = 1e5            # f_acc 上限: 满量程加速度设计点封顶频率

ORDER = ('SLOW', 'MEDIUM', 'FAST')
A_RATIO = {'SLOW': 0.01, 'MEDIUM': 0.10, 'FAST': 1.00}   # a_design 比例

B_LOOP_COEF = math.pi * (1 + 4 * ZETA ** 2) / (4 * ZETA)  # 3.3319 (zeta=.707)
_b = 2 + 4 * ZETA ** 2
F3DB_COEF = math.sqrt((_b + math.sqrt(_b * _b + 4)) / 2)  # 2.0582

V_RANGE_DEFAULT = 1.0      # 演示统一取中间量程 (对齐 .m 第 1 节)

# 旧代码硬编码档位 (polytec sim 已判定自相矛盾) -- H3 的固定 fn 对照组
FIXED_FN_LEGACY = {'SLOW': 40e3, 'MEDIUM': 126e3, 'FAST': 400e3}

PHI_GUARD = 1.0            # rad, 选档跟踪误差守卫 (e_crit=1 设计线)


# ---------------------------------------------------------------- 推导函数
def a_design_fast(v_range, acq_bw=ACQ_BW, f_acc_cap=F_ACC_CAP):
    """[自研] 规则第 1 步: FAST 档设计加速度."""
    return 2 * math.pi * min(acq_bw, f_acc_cap) * v_range


def fn_from_a(a, lam=LAMBDA, e_crit=1.0):
    """fn 使得正弦加速度 a 处的稳态峰值相位误差 = e_crit (低频渐近)."""
    return math.sqrt(a / (e_crit * math.pi * lam))


def a_from_fn(fn, lam=LAMBDA, e_crit=1.0):
    return e_crit * math.pi * lam * fn ** 2


def b_loop(fn, zeta=ZETA):
    return math.pi * fn * (1 + 4 * zeta ** 2) / (4 * zeta)


def f_3db(fn, zeta=ZETA):
    b = 2 + 4 * zeta ** 2
    return math.sqrt((b + math.sqrt(b * b + 4)) / 2) * fn


def mode_params(v_range=V_RANGE_DEFAULT, acq_bw=ACQ_BW, f_acc_cap=F_ACC_CAP,
                lam=LAMBDA, zeta=ZETA, B_frontend=B_FRONTEND):
    """三档参数表: fn(mode, v_range, acq_bw) -- 外差档位同时定测量带宽与动态."""
    aF = a_design_fast(v_range, acq_bw, f_acc_cap)
    out = {}
    for name in ORDER:
        a = aF * A_RATIO[name]
        fn = fn_from_a(a, lam)
        B = b_loop(fn, zeta)
        out[name] = dict(
            name=name, v_range=v_range, fn=fn,
            a_design=a,                       # e_crit=1 设计线
            a_slip=math.pi * a,               # e_crit=pi 卷绕线
            f_3db=f_3db(fn, zeta),            # = 测量带宽 (纯 NCO!)
            B_loop=B,
            gain_db=10 * math.log10(B_frontend / B),
            noise_red_db=10 * math.log10((B_frontend / 2) / B),
            valley_v=math.pi * lam * fn / math.sqrt(2),   # 浴缸谷值 (e=pi)
        )
    return out


def loop_error_mag(f, fn, zeta=ZETA):
    """|1 - H_L(f)| 连续二阶 II 型环近似."""
    x = f / fn
    return x * x / math.sqrt((1 - x * x) ** 2 + (2 * zeta * x) ** 2)


def loop_gain_mag(f, fn, zeta=ZETA):
    """|H_L(f)| 连续近似 (纯 NCO 输出的谱线幅值传递 = 频响校正因子的倒数)."""
    x = f / fn
    return math.sqrt((1 + (2 * zeta * x) ** 2) /
                     ((1 - x * x) ** 2 + (2 * zeta * x) ** 2))


def v_pll_limit(f, fn, lam=LAMBDA, zeta=ZETA, e_crit=math.pi):
    """纯 PLL 浴缸边界: 可跟踪正弦速度幅值 (谷底精确在 f = fn)."""
    return e_crit * lam * f / 2 / loop_error_mag(f, fn, zeta)


def v_if_limit(lam=LAMBDA, f_dev_max=F_DEV_MAX):
    """IF 硬频偏窗口速度上限 (与 ENBW 无关)."""
    return lam * f_dev_max / 2


def v_alias_limit(lam=LAMBDA, fs=FS):
    """采样混叠速度上限 |dphi| < pi."""
    return lam * fs / 4


def fn_discrete_ok(fn, fs=FS):
    """离散环稳定性约束 fn <= fs/50 (theta = 2*pi*fn/fs 必须远小于 1)."""
    return fn <= fs / 50


def tracking_error_rad(f_v, v_peak, fn, lam=LAMBDA, zeta=ZETA):
    """正弦运动 v_peak@f_v 的未跟踪多普勒相位 (rad)."""
    return loop_error_mag(f_v, fn, zeta) * 2 * v_peak / (lam * f_v)


def select_mode(f_target, v_peak=None, v_range=V_RANGE_DEFAULT, lam=LAMBDA):
    """外差选档: 档位同时决定测量带宽与动态 (与零差频率优先不同的地方是
    测量带宽约束是硬的 -- 没有残差窗兜底).

    1. 最窄的 f_3dB >= f_target 的档 (最低档 = 最大门限扩展);
       若三档都覆盖不了 (f_target > f_3dB(FAST)), 只能选 FAST + 频响校正。
    2. 跟踪误差守卫: |1-H_L(f_target)|*(2*v_peak/(lam*f_target)) <= PHI_GUARD,
       超了就升档。
    """
    modes = mode_params(v_range, lam=lam)
    idx = next((i for i, n in enumerate(ORDER)
                if f_target <= modes[n]['f_3db']), len(ORDER) - 1)
    if v_peak is not None:
        while idx < len(ORDER) - 1 and tracking_error_rad(
                f_target, v_peak, modes[ORDER[idx]]['fn'], lam) > PHI_GUARD:
            idx += 1
    return ORDER[idx]
