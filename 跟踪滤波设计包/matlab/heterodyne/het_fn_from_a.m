function fn = het_fn_from_a(a, lam, e_crit)
%HET_FN_FROM_A fn 使得正弦加速度 a 处的稳态峰值相位误差 = e_crit (低频渐近).
% Port of heterodyne design_params.py::fn_from_a.
  P = het_params();
  if nargin < 2 || isempty(lam)
    lam = P.LAMBDA;
  end
  if nargin < 3 || isempty(e_crit)
    e_crit = 1.0;
  end
  fn = sqrt(a / (e_crit * pi * lam));
end
