function [par, res] = heydemann_fit(u, v)
%HEYDEMANN_FIT Constrained direct algebraic ellipse fit + closed-form parameters.
%   [par, res] = heydemann_fit(u, v)
%   Faithful port of ellipse_correction.py heydemann_fit (Halir-Flusser
%   constrained direct ellipse LS + closed-form p,q,A,B,delta, 98% robust
%   arc-coverage validity check).
%
%   Model:  u = A*cos(phi) + p,   v = B*sin(phi + delta) + q
%   Fit:    a*u^2 + b*u*v + c*v^2 + d*u + e*v + f = 0, 4ac - b^2 > 0 enforced.
%
%   Returns:
%     par  struct p,q,A,B,delta  (delta in rad; NaN on failure)
%     res  struct ok, theta (1x6 raw conic coeffs), rms, algebraic_rms,
%          arc (98% robust coverage, rad), arc_all, design_cond, method,
%          msg, reject_reasons
  u = double(u(:));
  v = double(v(:));
  if numel(u) ~= numel(v) || numel(u) < 6 || ...
      ~all(isfinite(u)) || ~all(isfinite(v))
    error('heydemann_fit:inputs', ...
          'heydemann_fit: u, v must be equal-length finite real vectors with >= 6 points');
  end

  % centre + common scale preconditioning (large DC bias -> ill-posed conic)
  mu = [mean(u); mean(v)];
  sc = max([std(u, 1), std(v, 1), eps]);   % std(.,1): population std as numpy
  un = (u - mu(1)) / sc;
  vn = (v - mu(2)) / sc;
  D1 = [un .* un, un .* vn, vn .* vn];
  D2 = [un, vn, ones(numel(un), 1)];
  D = [D1, D2];

  res = struct('ok', false, 'theta', nan(1, 6), 'rms', NaN, ...
               'algebraic_rms', NaN, 'arc', NaN, 'arc_all', NaN, ...
               'design_cond', cond(D), ...
               'method', 'direct-ellipse-LS', 'msg', '', ...
               'reject_reasons', {{}});
  par = nan_par();

  if rank(D) < 5
    res.msg = 'rank-deficient design matrix (arc/diversity too small)';
    return
  end

  S1 = D1' * D1;
  S2 = D1' * D2;
  S3 = D2' * D2;
  if 1.0 / cond(S3) < 1e-14
    res.msg = 'linear-part scatter matrix ill-conditioned';
    return
  end
  T = -(S3 \ S2');
  C1 = [0.0, 0.0, 2.0; 0.0, -1.0, 0.0; 2.0, 0.0, 0.0];
  [E, ~] = eig(C1 \ (S1 + S2 * T));

  best = [];
  best_cost = inf;
  for k = 1:size(E, 2)
    q3 = E(:, k);
    if max(abs(imag(q3))) > 1e-8 * max(1.0, max(abs(real(q3))))
      continue
    end
    q3 = real(q3);
    if 4 * q3(1) * q3(3) - q3(2) ^ 2 <= 0
      continue
    end
    ck = [q3; T * q3];
    cost = norm(D * ck) / max(norm(ck), eps);
    if cost < best_cost
      best = ck;
      best_cost = cost;
    end
  end
  if isempty(best)
    res.msg = 'constrained fit produced no real ellipse';
    return
  end

  a = best(1); b = best(2); c = best(3);
  d = best(4); e = best(5); f = best(6);
  Q = [a, b / 2; b / 2, c];
  if all(eig(Q) < 0)
    best = -best;
    a = best(1); b = best(2); c = best(3);
    d = best(4); e = best(5); f = best(6);
    Q = -Q;
  end
  if any(eig(Q) <= 0) || 1.0 / cond(Q) < 1e-14
    res.msg = 'quadratic form not a positive-definite ellipse';
    return
  end
  ctr = -0.5 * (Q \ [d; e]);
  K = ctr' * Q * ctr - f;
  if ~isfinite(K) || K <= 0
    res.msg = 'ellipse scale K non-positive';
    return
  end

  best = best / K;                        % centred equation normalised to 1
  a = best(1); b = best(2); c = best(3);
  sd = min(max(-b / (2 * sqrt(a * c)), -1 + 1e-12), 1 - 1e-12);
  delta = asin(sd);
  A_n = sqrt(1.0 / (a * cos(delta) ^ 2));
  B_n = sqrt(1.0 / (c * cos(delta) ^ 2));

  par = struct('p', mu(1) + sc * ctr(1), 'q', mu(2) + sc * ctr(2), ...
               'A', sc * A_n, 'B', sc * B_n, 'delta', delta);

  % raw-coordinate conic coefficients (diagnostics / reproducibility)
  a = best(1); b = best(2); c = best(3);
  d = best(4); e = best(5); f = best(6);
  raw = [a / sc ^ 2, b / sc ^ 2, c / sc ^ 2, ...
         d / sc - 2 * a * mu(1) / sc ^ 2 - b * mu(2) / sc ^ 2, ...
         e / sc - b * mu(1) / sc ^ 2 - 2 * c * mu(2) / sc ^ 2, ...
         f - d * mu(1) / sc - e * mu(2) / sc ...
         + a * mu(1) ^ 2 / sc ^ 2 + b * mu(1) * mu(2) / sc ^ 2 ...
         + c * mu(2) ^ 2 / sc ^ 2];

  Ic = (u - par.p) / par.A;
  Qc = ((v - par.q) / par.B - Ic * sin(par.delta)) / cos(par.delta);
  rho = hypot(Ic, Qc);
  ang = sort(mod(atan2(Qc, Ic), 2 * pi));
  gaps = diff([ang; ang(1) + 2 * pi]);
  nang = numel(ang);
  mcover = max(2, ceil(0.98 * nang));
  ang2 = [ang; ang + 2 * pi];
  idx = (1:nang).';
  span98 = ang2(idx + mcover - 1) - ang2(idx);

  res.theta = raw;
  res.rms = sqrt(mean((rho - 1.0) .^ 2));
  res.algebraic_rms = sqrt(mean((D * best) .^ 2));
  res.arc_all = 2 * pi - max(gaps);       % wrap-safe coverage
  res.arc = min(span98);                  % robust to outliers
  [~, res] = assess_fit(par, res);
end

function par = nan_par()
  par = struct('p', NaN, 'q', NaN, 'A', NaN, 'B', NaN, 'delta', NaN);
end
