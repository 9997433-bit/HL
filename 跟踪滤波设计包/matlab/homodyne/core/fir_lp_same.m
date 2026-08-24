function y = fir_lp_same(x, fc, fs, Nt)
%FIR_LP_SAME Linear-phase FIR low-pass via FFT convolution, group-delay compensated.
%   y = fir_lp_same(x, fc, fs, Nt)
%   Faithful port of core.py fir_lp_same.  Off-line the (Nt-1)/2-sample
%   group delay is removed by slicing ('same' alignment).  Real-time
%   hardware must instead put an NT_WIN/2-sample delay line on the NCO
%   phase path (see validate_tracking.py header note).
%   x treated as a column vector; y is numel(x)-by-1 (real if x is real).
  x = x(:);
  h = fir_lp_kernel(fc, fs, Nt);
  nfft = 2 ^ ceil(log2(numel(x) + Nt));
  y = ifft(fft(x, nfft) .* fft(h, nfft));
  g = floor((Nt - 1) / 2);
  y = y(g+1 : g+numel(x));
  if isreal(x)
    y = real(y);
  end
end
