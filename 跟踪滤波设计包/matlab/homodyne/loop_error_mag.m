function m = loop_error_mag(f, fn, zeta)
%LOOP_ERROR_MAG |1 - H_L| of the II-type loop at frequency f (continuous approx).
  if nargin < 3 || isempty(zeta)
    dp = design_params();
    zeta = dp.ZETA;
  end
  x = f ./ fn;
  m = x .* x ./ sqrt((1 - x .* x).^2 + (2 * zeta * x).^2);
end
