function [par, res] = fit_arc_gated(u, v, prev_par, gate_tol, max_pts, min_pts)
%FIT_ARC_GATED Amplitude-gated Heydemann fit (document M1: stable-amplitude arc only).
%   [par, res] = fit_arc_gated(u, v, prev_par, gate_tol, max_pts, min_pts)
%   Faithful port of ellipse_correction.py fit_arc_gated.  Defaults:
%   gate_tol=0.05, max_pts=8000, min_pts=100.
%
%   Points are circularised with the PREVIOUS parameters prev_par; gating
%   |rho/median - 1| <= gate_tol keeps exactly the stable-return-amplitude
%   points at every angle (annulus rejection).  The gate is relaxed once
%   (2x) if it keeps too few points.  A pre-fit arc check with the trusted
%   prev_par blocks noise-inflated self-reported arcs on short arcs.
  E = ellipse_constants();
  if nargin < 4 || isempty(gate_tol), gate_tol = 0.05; end
  if nargin < 5 || isempty(max_pts),  max_pts = 8000;  end
  if nargin < 6 || isempty(min_pts),  min_pts = 100;   end
  u = double(u(:));
  v = double(v(:));
  [us, vs] = subsample_uv(u, v, max_pts);
  [~, ~, zc] = heydemann_apply(us, vs, prev_par);
  rho = abs(zc);
  med = max(median(rho), eps);
  keep = abs(rho / med - 1.0) <= gate_tol;
  if sum(keep) < max(min_pts, floor(0.05 * numel(us)))
    keep = abs(rho / med - 1.0) <= 2 * gate_tol;
  end
  if sum(keep) < min_pts
    par = nan_par();
    res = struct('ok', false, 'arc', NaN, ...
                 'msg', 'amplitude gate kept too few points');
    return
  end
  % Pre-fit arc with trusted prev_par (not candidate fit) -- blocks noise-
  % inflated self-reported arc on short arcs (audit: arc_before < ARC_MIN
  % => reject).
  arc_before = arc_span_corrected(us(keep), vs(keep), prev_par);
  if arc_before < E.ARC_MIN
    par = nan_par();
    res = struct('ok', false, 'arc', arc_before, ...
                 'msg', sprintf('pre-fit arc %.3f < %.3f (prev_par coverage)', ...
                                arc_before, E.ARC_MIN));
    return
  end
  [par, res] = heydemann_fit(us(keep), vs(keep));
end

function par = nan_par()
  par = struct('p', NaN, 'q', NaN, 'A', NaN, 'B', NaN, 'delta', NaN);
end
