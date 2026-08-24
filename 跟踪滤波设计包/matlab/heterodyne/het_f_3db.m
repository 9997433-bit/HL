function f = het_f_3db(fn, zeta)
%HET_F_3DB -3 dB closed-loop frequency of the II-type loop (= 测量带宽, 纯 NCO).
% Port of heterodyne design_params.py::f_3db.
  if nargin < 2 || isempty(zeta)
    P = het_params();
    zeta = P.ZETA;
  end
  b = 2 + 4 * zeta ^ 2;
  f = sqrt((b + sqrt(b * b + 4)) / 2) * fn;
end
