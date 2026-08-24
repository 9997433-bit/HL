function y = fir_lp(x, fc, fs, Nt)
%FIR_LP Hann-windowed-sinc FIR low-pass, direct convolution, 'same' output.
% Port of core.py::fir_lp (identical maths in the heterodyne core, which
% builds the kernel inline).  Column in/out.
  if nargin < 4
    Nt = 257;
  end
  if mod(Nt, 2) == 0
    Nt = Nt + 1;
  end
  x = x(:);
  h = fir_lp_kernel(fc, fs, Nt);
  yf = conv(x, h);
  d = floor((Nt - 1) / 2);
  y = yf(d + 1:d + numel(x));
end
