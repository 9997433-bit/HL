function s = arc_span_angles(ang)
%ARC_SPAN_ANGLES Robust 98% coverage arc from angles (rad), wrap-safe.
%   s = arc_span_angles(ang)
%   Faithful port of ellipse_correction.py _arc_span_angles.
  ang = sort(mod(ang(:), 2 * pi));
  nang = numel(ang);
  if nang < 2
    s = 0.0;
    return
  end
  mcover = max(2, ceil(0.98 * nang));
  ang2 = [ang; ang + 2 * pi];
  idx = (1:nang).';
  s = min(ang2(idx + mcover - 1) - ang2(idx));
end
