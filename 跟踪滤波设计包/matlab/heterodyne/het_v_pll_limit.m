function v = het_v_pll_limit(f, fn, lam, zeta, e_crit)
%HET_V_PLL_LIMIT 纯 PLL 浴缸边界: 可跟踪正弦速度幅值 (谷底精确在 f = fn).
% Port of heterodyne design_params.py::v_pll_limit (e_crit default pi).
  P = het_params();
  if nargin < 3 || isempty(lam)
    lam = P.LAMBDA;
  end
  if nargin < 4 || isempty(zeta)
    zeta = P.ZETA;
  end
  if nargin < 5 || isempty(e_crit)
    e_crit = pi;
  end
  v = e_crit * lam * f / 2 ./ het_loop_error_mag(f, fn, zeta);
end
