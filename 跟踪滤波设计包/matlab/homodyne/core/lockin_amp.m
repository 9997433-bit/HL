function a = lockin_amp(v, t, f0, win)
%LOCKIN_AMP Lock-in amplitude of tone f0 within window win (logical mask or indices).
%   a = lockin_amp(v, t, f0, win)   Faithful port of core.py lockin_amp.
  v = v(:);
  t = t(:);
  k = exp(-1i * 2 * pi * f0 * t);
  seg = v(win) - mean(v(win));
  a = 2 * abs(mean(seg .* k(win)));
end
