function v = fm_discriminator(z, fs, lam)
%FM_DISCRIMINATOR Differential-phase FM discriminator -> velocity [m/s].
% Port of core.py::fm_discriminator.  Column in/out.
  z = z(:);
  d = angle(z(2:end) .* conj(z(1:end - 1)));
  v = [0; d] * fs * lam / (4 * pi);
end
