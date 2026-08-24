function y = fir_lp_same(x, fc, fs, Nt)
%FIR_LP_SAME Linear-phase FIR low-pass via FFT conv, group-delay compensated.
%   Port of core.fir_lp_same ('same' alignment removes the (Nt-1)/2-sample
%   group delay off-line; real-time hardware needs an NT_WIN/2-sample delay
%   line on the NCO phase path instead).
  x = x(:);
  h = fir_lp_kernel(fc, fs, Nt);
  nfft = 2^ceil(log2(numel(x) + Nt));
  y = ifft(fft(x, nfft) .* fft(h, nfft));
  i0 = floor((Nt - 1) / 2);
  y = y(i0+1:i0+numel(x));
  if isreal(x)
    y = real(y);
  end
end
