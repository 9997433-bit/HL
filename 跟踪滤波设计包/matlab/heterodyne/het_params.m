function P = het_params()
%HET_PARAMS 外差电IQ (Polytec类) 三档跟踪滤波参数 -- HeNe 632.8 nm 默认.
% Port of heterodyne_tracking_design/design_params.py (module constants).
%
% 与零差方案的设计哲学差异: 外差是纯 NCO 架构 (无残差窗), 换档 SAME KNOB 同时
% 决定测量带宽 f_3dB = 2.0582*fn 与跟踪动态 a_design = pi*lambda*fn^2.
% 四层带宽: fs (混叠) / B_frontend (ENBW) / f_dev_max (IF 硬窗) / B_loop.
  P.LAMBDA = 632.8e-9;       % HeNe 默认
  P.LAMBDA_ALT = 1550e-9;    % 1550 nm 亦支持 (所有函数均可显式传 lam)
  P.FS = 50e6;               % 采样率 (只决定混叠, 非噪声带宽)
  P.B_FRONTEND = 19e6;       % 前端复基带双边 ENBW
  P.F_DEV_MAX = 9.5e6;       % IF 可用频偏硬边缘 (与 ENBW 是两个参数)
  P.ZETA = 0.707;

  % [自研] fn 推导规则输入
  P.ACQ_BW = 1e6;            % 采集带宽 (Hz)
  P.F_ACC_CAP = 1e5;         % f_acc 上限: 满量程加速度设计点封顶频率

  P.ORDER = {'SLOW', 'MEDIUM', 'FAST'};
  P.A_RATIO = struct('SLOW', 0.01, 'MEDIUM', 0.10, 'FAST', 1.00);

  P.B_LOOP_COEF = pi * (1 + 4 * P.ZETA ^ 2) / (4 * P.ZETA);   % 3.3319
  b = 2 + 4 * P.ZETA ^ 2;
  P.F3DB_COEF = sqrt((b + sqrt(b * b + 4)) / 2);              % 2.0582

  P.V_RANGE_DEFAULT = 1.0;   % 演示统一取中间量程

  % 旧代码硬编码档位 (polytec sim 已判定自相矛盾) -- H3 的固定 fn 对照组
  P.FIXED_FN_LEGACY = struct('SLOW', 40e3, 'MEDIUM', 126e3, 'FAST', 400e3);

  P.PHI_GUARD = 1.0;         % rad, 选档跟踪误差守卫 (e_crit=1 设计线)
end
