function v = fm_discriminator(z, fs, lam)
%FM_DISCRIMINATOR Velocity from differential phase (port of core.fm_discriminator).
  z = z(:);
  d = angle(z(2:end) .* conj(z(1:end-1)));
  v = [0; d] * fs * lam / (4 * pi);
end
