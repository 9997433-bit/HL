function B = het_b_loop(fn, zeta)
%HET_B_LOOP 环路单边 ENBW = pi*fn*(1+4*zeta^2)/(4*zeta).
% Port of heterodyne design_params.py::b_loop (zeta default 0.707).
  if nargin < 2 || isempty(zeta)
    P = het_params();
    zeta = P.ZETA;
  end
  B = pi * fn .* (1 + 4 * zeta ^ 2) / (4 * zeta);
end
