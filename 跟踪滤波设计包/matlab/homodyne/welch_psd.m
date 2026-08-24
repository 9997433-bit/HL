function [P, f] = welch_psd(x, fs, L)
%WELCH_PSD One-sided Welch PSD, Hann window, 50% overlap.
% Port of core.py::welch_psd.  Returns columns P (L/2+1) and f.
  if nargin < 3
    L = 1024;
  end
  x = x(:);
  L = min(L, numel(x));
  win = 0.5 - 0.5 * cos(2 * pi * (0:L - 1)' / (L - 1));
  U = sum(win .^ 2);
  P = zeros(L, 1);
  K = 0;
  step = floor(L / 2);
  for i = 0:step:(numel(x) - L)
    P = P + abs(fft(x(i + 1:i + L) .* win)) .^ 2 / (fs * U);
    K = K + 1;
  end
  P = P / max(K, 1);
  P = P(1:floor(L / 2) + 1);
  P(2:end - 1) = P(2:end - 1) * 2;
  f = (0:floor(L / 2))' * fs / L;
end
