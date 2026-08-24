function [P, f] = welch_psd(x, fs, L)
%WELCH_PSD Hann-window Welch PSD, 50%% overlap, one-sided doubling as in core.py.
%   [P, f] = welch_psd(x, fs, L)   Faithful port of core.py welch_psd.
%   L defaults to 1024.  P and f are column vectors of length floor(L/2)+1.
  if nargin < 3
    L = 1024;
  end
  x = x(:);
  L = min(L, numel(x));
  win = 0.5 - 0.5 * cos(2 * pi * (0:L-1).' / (L - 1));
  U = sum(win .^ 2);
  P = zeros(L, 1);
  K = 0;
  hop = floor(L / 2);
  for i0 = 0:hop:(numel(x) - L)
    P = P + abs(fft(x(i0+1 : i0+L) .* win)) .^ 2 / (fs * U);
    K = K + 1;
  end
  P = P / max(K, 1);
  P = P(1 : floor(L / 2) + 1);
  P(2:end-1) = P(2:end-1) * 2;
  f = (0 : floor(L / 2)).' * fs / L;
end
