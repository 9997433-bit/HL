function a = het_a_from_fn(fn, lam, e_crit)
%HET_A_FROM_FN Inverse of het_fn_from_a.
% Port of heterodyne design_params.py::a_from_fn.
  P = het_params();
  if nargin < 2 || isempty(lam)
    lam = P.LAMBDA;
  end
  if nargin < 3 || isempty(e_crit)
    e_crit = 1.0;
  end
  a = e_crit * pi * lam * fn .^ 2;
end
