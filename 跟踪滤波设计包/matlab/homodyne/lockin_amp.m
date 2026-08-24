function a = lockin_amp(v, t, f0, win)
%LOCKIN_AMP Lock-in amplitude of v at f0 over the logical window win.
%   Port of core.lockin_amp.
  k = exp(-1i * 2 * pi * f0 * t(:));
  v = v(:);
  seg = v(win) - mean(v(win));
  a = 2 * abs(mean(seg .* k(win)));
end
