function [Kp, Ki] = loop_gains(fn, fs, zeta)
%LOOP_GAINS PLL proportional/integral gains for natural frequency fn.
  dp = design_params();
  if nargin < 2 || isempty(fs), fs = dp.FS; end
  if nargin < 3 || isempty(zeta), zeta = dp.ZETA; end
  th = 2 * pi * fn / fs;
  Kp = 2 * zeta * th;
  Ki = th * th;
end
