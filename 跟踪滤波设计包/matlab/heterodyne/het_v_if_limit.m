function v = het_v_if_limit(lam, f_dev_max)
%HET_V_IF_LIMIT IF 硬频偏窗口速度上限 (与 ENBW 无关).
% Port of heterodyne design_params.py::v_if_limit.
  P = het_params();
  if nargin < 1 || isempty(lam)
    lam = P.LAMBDA;
  end
  if nargin < 2 || isempty(f_dev_max)
    f_dev_max = P.F_DEV_MAX;
  end
  v = lam * f_dev_max / 2;
end
