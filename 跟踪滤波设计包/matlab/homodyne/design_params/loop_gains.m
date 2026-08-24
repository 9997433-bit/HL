function [Kp, Ki] = loop_gains(fn, fs, zeta)
%LOOP_GAINS II-type loop gains for natural frequency fn.
%   [Kp, Ki] = loop_gains(fn, fs, zeta)   Faithful port of design_params.py.
%   fs defaults to FS (250e6), zeta to ZETA (1.2).
  C = homodyne_constants();
  if nargin < 2 || isempty(fs)
    fs = C.FS;
  end
  if nargin < 3 || isempty(zeta)
    zeta = C.ZETA;
  end
  th = 2 * pi * fn / fs;
  Kp = 2 * zeta * th;
  Ki = th * th;
end
