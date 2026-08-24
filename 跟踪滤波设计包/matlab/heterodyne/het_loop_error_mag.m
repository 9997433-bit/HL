function m = het_loop_error_mag(f, fn, zeta)
%HET_LOOP_ERROR_MAG |1 - H_L(f)| 连续二阶 II 型环近似 (外差 zeta 默认 0.707).
% Port of heterodyne design_params.py::loop_error_mag.
  if nargin < 3 || isempty(zeta)
    P = het_params();
    zeta = P.ZETA;
  end
  x = f ./ fn;
  m = x .* x ./ sqrt((1 - x .* x) .^ 2 + (2 * zeta * x) .^ 2);
end
