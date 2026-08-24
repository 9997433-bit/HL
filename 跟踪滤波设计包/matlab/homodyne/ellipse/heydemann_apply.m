function [Ic, Qc, z] = heydemann_apply(u, v, par)
%HEYDEMANN_APPLY Ellipse -> unit circle inverse transform.
%   [Ic, Qc, z] = heydemann_apply(u, v, par)
%   Faithful port of ellipse_correction.py heydemann_apply:
%     Ic = (u - p)/A
%     Qc = ((v - q)/B - Ic*sin(delta))/cos(delta)
%     z  = Ic + 1i*Qc
%   u, v treated as column vectors; par is a struct with p,q,A,B,delta.
  E = ellipse_constants();
  u = double(u(:));
  v = double(v(:));
  for i = 1:numel(E.PAR_FIELDS)
    if ~isfield(par, E.PAR_FIELDS{i})
      error('heydemann_apply:par', ...
            'heydemann_apply: par must contain p,q,A,B,delta');
    end
  end
  pv = [par.p, par.q, par.A, par.B, par.delta];
  if numel(u) ~= numel(v) || ~all(isfinite(pv)) || ...
      par.A <= 0 || par.B <= 0 || abs(cos(par.delta)) < 1e-6
    error('heydemann_apply:inputs', ...
          'heydemann_apply: invalid inputs or delta ~ +/-90 deg');
  end
  Ic = (u - par.p) / par.A;
  Qc = ((v - par.q) / par.B - Ic * sin(par.delta)) / cos(par.delta);
  z = Ic + 1i * Qc;
end
