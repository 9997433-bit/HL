function [m, lo, hi] = vt_stats(a)
%VT_STATS median, p10, p90 with numpy-matching ceil-index percentiles.
  a = a(:);
  a = a(isfinite(a));
  if isempty(a)
    m = NaN; lo = NaN; hi = NaN;
    return
  end
  s = sort(a);
  m = median(s);
  n = numel(s);
  q = @(p) s(max(1, min(n, ceil(p / 100 * n))));
  lo = q(10);
  hi = q(90);
end
