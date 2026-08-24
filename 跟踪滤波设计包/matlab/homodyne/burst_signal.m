function [x, v, env] = burst_signal(t, f0, vamp, ncyc, t0)
%BURST_SIGNAL Hann-enveloped burst: displacement and EXACT velocity.
%   Port of core.burst_signal (includes the d(env)/dt term).
  X0 = vamp / (2 * pi * f0);
  Tb = ncyc / f0;
  w = 2 * pi * f0;
  u = (t - t0) / Tb;
  inb = (u >= 0) & (u <= 1);
  env = zeros(size(t));
  env(inb) = 0.5 * (1 - cos(2 * pi * u(inb)));
  edot = zeros(size(t));
  edot(inb) = (pi / Tb) * sin(2 * pi * u(inb));
  ph = w * (t - t0);
  x = X0 * sin(ph) .* env;
  v = X0 * w * cos(ph) .* env + X0 * sin(ph) .* edot;
end
