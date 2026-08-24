function s = arc_span_corrected(u, v, par)
%ARC_SPAN_CORRECTED Arc coverage using corrected-plane angles (independent sanity check).
%   s = arc_span_corrected(u, v, par)
%   Faithful port of ellipse_correction.py arc_span_corrected.
  [~, ~, z] = heydemann_apply(u, v, par);
  s = arc_span_angles(angle(z));
end
