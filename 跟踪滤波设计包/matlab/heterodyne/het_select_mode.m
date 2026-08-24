function name = het_select_mode(f_target, v_peak, v_range, lam)
%HET_SELECT_MODE 外差选档: 档位同时决定测量带宽与动态 (f_3dB 是硬约束).
% Port of heterodyne design_params.py::select_mode.
%   1. 最窄的 f_3dB >= f_target 的档; 三档都覆盖不了则只能 FAST + 频响校正.
%   2. 跟踪误差守卫: phi_err <= PHI_GUARD, 超了就升档.
% v_peak = [] skips the guard.
  P = het_params();
  if nargin < 2
    v_peak = [];
  end
  if nargin < 3 || isempty(v_range)
    v_range = P.V_RANGE_DEFAULT;
  end
  if nargin < 4 || isempty(lam)
    lam = P.LAMBDA;
  end
  modes = het_mode_params(v_range, [], [], lam);
  idx = numel(P.ORDER);
  for i = 1:numel(P.ORDER)
    if f_target <= modes.(P.ORDER{i}).f_3db
      idx = i;
      break;
    end
  end
  if ~isempty(v_peak)
    while idx < numel(P.ORDER) && ...
        het_tracking_error_rad(f_target, v_peak, ...
                               modes.(P.ORDER{idx}).fn, lam) > P.PHI_GUARD
      idx = idx + 1;
    end
  end
  name = P.ORDER{idx};
end
