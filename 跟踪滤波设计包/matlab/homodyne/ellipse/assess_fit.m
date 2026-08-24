function [ok, res] = assess_fit(par, res)
%ASSESS_FIT Full acceptance gate (doc 2.4): arc, rms, cond, epsilon, delta, A/B.
%   [ok, res] = assess_fit(par, res)
%   Faithful port of ellipse_correction.py assess_fit.  Mutations of the
%   Python res dict are returned via the second output (ok, reject_reasons,
%   msg).  NaN comparisons behave like Python (NaN > x and NaN < x are
%   both false), so held/unknown values skip their gates identically.
  E = ellipse_constants();
  reasons = {};
  allfin = true;
  for i = 1:numel(E.PAR_FIELDS)
    if ~isfield(par, E.PAR_FIELDS{i}) || ~isfinite(par.(E.PAR_FIELDS{i}))
      allfin = false;
    end
  end
  if ~allfin
    reasons{end+1} = 'non-finite parameters';
  end
  if get_num(par, 'A', 0) <= 0 || get_num(par, 'B', 0) <= 0
    reasons{end+1} = 'A or B non-positive';
  end
  A = get_num(par, 'A', NaN);
  if isfinite(A) && par.A > 0
    epsv = abs(par.B / par.A - 1.0);
    if epsv > E.EPS_MAX
      reasons{end+1} = sprintf('|epsilon|=%.3f > %g', epsv, E.EPS_MAX);
    end
  end
  if abs(get_num(par, 'delta', 0)) > E.DEL_MAX
    reasons{end+1} = sprintf('|delta|=%.1f deg > %.0f deg', ...
                             get_num(par, 'delta', 0) * 180 / pi, ...
                             E.DEL_MAX * 180 / pi);
  end
  if get_num(res, 'arc', 0) < E.ARC_MIN
    reasons{end+1} = sprintf('arc=%.3f < %.3f', get_num(res, 'arc', NaN), ...
                             E.ARC_MIN);
  end
  if get_num(res, 'rms', inf) > E.FIT_RMS_MAX
    reasons{end+1} = sprintf('rms=%.4f > %g', get_num(res, 'rms', NaN), ...
                             E.FIT_RMS_MAX);
  end
  % cond(D) blows up when algebraic residuals ~ 0 (perfect ellipse); only
  % gate on it when rms indicates a noisy/ambiguous fit (doc 2.4 intent).
  if get_num(res, 'rms', inf) > 1e-3 && ...
      get_num(res, 'design_cond', inf) > E.FIT_COND_MAX
    reasons{end+1} = sprintf('cond=%.2e > %.0e', ...
                             get_num(res, 'design_cond', NaN), ...
                             E.FIT_COND_MAX);
  end
  ok = isempty(reasons);
  res.ok = ok;
  res.reject_reasons = reasons;
  if ~ok && (~isfield(res, 'msg') || isempty(res.msg))
    res.msg = strjoin(reasons, '; ');
  end
end

function x = get_num(s, f, dflt)
  if isfield(s, f)
    x = s.(f);
  else
    x = dflt;
  end
end
