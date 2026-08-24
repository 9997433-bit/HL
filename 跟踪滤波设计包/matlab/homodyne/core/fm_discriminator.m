function v = fm_discriminator(z, fs, lam)
%FM_DISCRIMINATOR Differential-phase FM discriminator -> velocity (m/s).
%   v = fm_discriminator(z, fs, lam)   Faithful port of core.py.
%   z treated as a column vector; v is numel(z)-by-1, v(1) = 0.
  z = z(:);
  d = angle(z(2:end) .* conj(z(1:end-1)));
  v = [0.0; d] * fs * lam / (4 * pi);
end
