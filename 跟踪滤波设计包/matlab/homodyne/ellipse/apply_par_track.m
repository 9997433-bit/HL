function z = apply_par_track(u, v, trk)
%APPLY_PAR_TRACK heydemann_apply with time-varying (per-sample) parameters.
%   z = apply_par_track(u, v, trk)
%   Faithful port of ellipse_correction.py apply_par_track.  trk is a
%   struct of per-sample vectors (see interp_par_track).
  u = double(u(:));
  v = double(v(:));
  Ic = (u - trk.p(:)) ./ trk.A(:);
  Qc = ((v - trk.q(:)) ./ trk.B(:) - Ic .* sin(trk.delta(:))) ...
       ./ cos(trk.delta(:));
  z = Ic + 1i * Qc;
end
