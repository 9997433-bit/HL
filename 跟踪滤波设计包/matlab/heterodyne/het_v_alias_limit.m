function v = het_v_alias_limit(lam, fs)
%HET_V_ALIAS_LIMIT 采样混叠速度上限 |dphi| < pi.
% Port of heterodyne design_params.py::v_alias_limit.
  P = het_params();
  if nargin < 1 || isempty(lam)
    lam = P.LAMBDA;
  end
  if nargin < 2 || isempty(fs)
    fs = P.FS;
  end
  v = lam * fs / 4;
end
