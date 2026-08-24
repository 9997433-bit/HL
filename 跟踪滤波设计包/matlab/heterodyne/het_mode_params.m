function out = het_mode_params(v_range, acq_bw, f_acc_cap, lam, zeta, B_frontend)
%HET_MODE_PARAMS 三档参数表: fn(mode, v_range, acq_bw) -- 外差档位同时定测量带宽与动态.
% Port of heterodyne design_params.py::mode_params.  Returns a struct with
% fields SLOW / MEDIUM / FAST, each a struct of the derived quantities.
  P = het_params();
  if nargin < 1 || isempty(v_range)
    v_range = P.V_RANGE_DEFAULT;
  end
  if nargin < 2 || isempty(acq_bw)
    acq_bw = P.ACQ_BW;
  end
  if nargin < 3 || isempty(f_acc_cap)
    f_acc_cap = P.F_ACC_CAP;
  end
  if nargin < 4 || isempty(lam)
    lam = P.LAMBDA;
  end
  if nargin < 5 || isempty(zeta)
    zeta = P.ZETA;
  end
  if nargin < 6 || isempty(B_frontend)
    B_frontend = P.B_FRONTEND;
  end
  aF = het_a_design_fast(v_range, acq_bw, f_acc_cap);
  for i = 1:numel(P.ORDER)
    name = P.ORDER{i};
    a = aF * P.A_RATIO.(name);
    fn = het_fn_from_a(a, lam);
    B = het_b_loop(fn, zeta);
    out.(name) = struct( ...
        'name', name, 'v_range', v_range, 'fn', fn, ...
        'a_design', a, ...                          % e_crit=1 设计线
        'a_slip', pi * a, ...                       % e_crit=pi 卷绕线
        'f_3db', het_f_3db(fn, zeta), ...           % = 测量带宽 (纯 NCO!)
        'B_loop', B, ...
        'gain_db', 10 * log10(B_frontend / B), ...
        'noise_red_db', 10 * log10((B_frontend / 2) / B), ...
        'valley_v', pi * lam * fn / sqrt(2));       % 浴缸谷值 (e=pi)
  end
end
