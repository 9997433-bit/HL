function m = het_loop_gain_mag(f, fn, zeta)
%HET_LOOP_GAIN_MAG |H_L(f)| 连续近似 (纯 NCO 输出的谱线幅值传递).
% Port of heterodyne design_params.py::loop_gain_mag.
  if nargin < 3 || isempty(zeta)
    P = het_params();
    zeta = P.ZETA;
  end
  x = f ./ fn;
  m = sqrt((1 + (2 * zeta * x) .^ 2) ./ ((1 - x .* x) .^ 2 + (2 * zeta * x) .^ 2));
end
