function y = ve_movmean(x, n)
%VE_MOVMEAN Centered moving average with shrinking edge windows, O(N).
%   y = ve_movmean(x, n)
%   Port of the movmean helper shared by the ellipse validators
%   (validate_ellipse_small_disp.py / validate_ellipse_dynamic.py).  The two
%   Python variants differ only for n < 2 (h = max(1, n//2) vs h = n//2),
%   which no validator uses; this port takes h = max(1, floor(n/2)).
  x = double(x(:));
  n = floor(n);
  h = max(1, floor(n / 2));
  N = numel(x);
  c = [0; cumsum(x)];
  i = (0:N-1)';
  lo = max(i - h, 0);
  hi = min(i + h + 1, N);
  y = (c(hi + 1) - c(lo + 1)) ./ (hi - lo);
end
