function [us, vs] = subsample_uv(u, v, max_pts)
%SUBSAMPLE_UV Uniform-stride subsample keeping at most ~max_pts points.
%   [us, vs] = subsample_uv(u, v, max_pts)
%   Faithful port of ellipse_correction.py _subsample.
  u = u(:);
  v = v(:);
  step = max(1, floor(numel(u) / floor(max_pts)));
  us = u(1:step:end);
  vs = v(1:step:end);
end
