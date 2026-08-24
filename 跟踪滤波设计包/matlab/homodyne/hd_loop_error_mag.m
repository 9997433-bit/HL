function m = hd_loop_error_mag(f, fn, zeta)
%HD_LOOP_ERROR_MAG |1 - H_L| of the II-type loop (continuous approx., homodyne zeta).
% Port of design_params.py::loop_error_mag.
  if nargin < 3
    P = hd_params();
    zeta = P.ZETA;
  end
  x = f ./ fn;
  m = x .* x ./ sqrt((1 - x .* x) .^ 2 + (2 * zeta * x) .^ 2);
end
