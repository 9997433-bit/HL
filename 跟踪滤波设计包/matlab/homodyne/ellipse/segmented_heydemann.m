function [t_c, pars, oks, arcs] = segmented_heydemann(u, v, fs, seg_len, ...
                                                      gate_tol, max_pts)
%SEGMENTED_HEYDEMANN Per-segment amplitude-gated Heydemann with parameter freeze.
%   [t_c, pars, oks, arcs] = segmented_heydemann(u, v, fs, seg_len,
%                                                gate_tol, max_pts)
%   Faithful port of ellipse_correction.py segmented_heydemann.  Defaults:
%   seg_len=0.25, gate_tol=0.05, max_pts=8000.
%
%   Segment k is fitted from its own samples (gated on radius w.r.t. the
%   previous segment's parameters); if the fit is invalid (arc < pi/2, gate
%   kept too few points, degenerate conic) the previous parameters are held.
%
%   Returns:
%     t_c   K-by-1 segment-centre times (s)
%     pars  K-by-1 cell array of parameter structs (held values filled in)
%     oks   K-by-1 logical, true where the segment produced a fresh valid fit
%     arcs  K-by-1 robust 98% coverage arc of each attempted fit (rad)
  if nargin < 4 || isempty(seg_len),  seg_len = 0.25;  end
  if nargin < 5 || isempty(gate_tol), gate_tol = 0.05; end
  if nargin < 6 || isempty(max_pts),  max_pts = 8000;  end
  u = double(u(:));
  v = double(v(:));
  N = numel(u);
  ns = max(64, round(seg_len * fs));
  K = max(1, floor(N / ns));
  t_c = zeros(K, 1);
  pars = cell(K, 1);
  oks = false(K, 1);
  arcs = nan(K, 1);
  prev = [];
  for k = 1:K
    i0 = (k - 1) * ns;                    % 0-based sample offsets as Python
    if k == K
      i1 = N;
    else
      i1 = k * ns;
    end
    uu = u(i0+1 : i1);
    vv = v(i0+1 : i1);
    t_c(k) = 0.5 * (i0 + i1) / fs;
    if isempty(prev)
      % bootstrap: ungated fit for rough parameters (annulus-biased),
      % then two gated refit passes to wash the bias out
      [uus, vvs] = subsample_uv(uu, vv, max_pts);
      [cand, res] = heydemann_fit(uus, vvs);
      for it = 1:2
        if ~res.ok
          break
        end
        [par1, res1] = fit_arc_gated(uu, vv, cand, gate_tol, max_pts);
        if res1.ok
          cand = par1;
          res = res1;
        end
      end
      if ~res.ok
        cand = [];
      end
    else
      [par1, res] = fit_arc_gated(uu, vv, prev, gate_tol, max_pts);
      if res.ok
        cand = par1;
      else
        cand = [];
      end
    end
    if isfield(res, 'arc')
      arcs(k) = res.arc;
    end
    if ~isempty(cand)
      prev = cand;
      oks(k) = true;
    end
    if ~isempty(prev)
      pars{k} = prev;
    end
  end

  first = find(~cellfun(@isempty, pars), 1);
  if isempty(first)
    error('segmented_heydemann:nofit', ...
          ['segmented_heydemann: no segment produced a valid ellipse fit ' ...
           '(drift arc coverage insufficient?)']);
  end
  if first > 1
    warning('segmented_heydemann:backfill', ...
            'segmented_heydemann: first %d segment(s) back-filled from segment %d', ...
            first - 1, first - 1);
    for k = 1:first-1
      pars{k} = pars{first};
    end
  end
end
