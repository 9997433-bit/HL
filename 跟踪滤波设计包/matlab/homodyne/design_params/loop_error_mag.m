function m = loop_error_mag(f, fn, zeta)
%LOOP_ERROR_MAG |1 - H_L| of the II-type loop at frequency f (continuous approx.).
%   m = loop_error_mag(f, fn, zeta)   Faithful port of design_params.py.
%   zeta defaults to ZETA (1.2).  f may be scalar or vector.
  if nargin < 3 || isempty(zeta)
    C = homodyne_constants();
    zeta = C.ZETA;
  end
  x = f ./ fn;
  m = x .* x ./ sqrt((1 - x .* x) .^ 2 + (2 * zeta * x) .^ 2);
end
