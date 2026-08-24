function y = fir_lp(x, fc, fs, Nt)
%FIR_LP Direct 'same'-mode FIR low-pass (utility; NOT the residual window path).
%   y = fir_lp(x, fc, fs, Nt)   Faithful port of core.py fir_lp.
%   Nt defaults to 257 and is forced odd.  Column-vector convention.
  if nargin < 4
    Nt = 257;
  end
  if mod(Nt, 2) == 0
    Nt = Nt + 1;
  end
  h = fir_lp_kernel(fc, fs, Nt);
  y = conv(x(:), h, 'same');
end
