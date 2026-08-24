function compare_validate()
%COMPARE_VALIDATE Compare Python vs MATLAB golden metrics of the validators.
%   Loads golden/validate_<name>_py.mat (written by export_validate_golden.py)
%   and golden/validate_<name>_mat.mat (written by the validate_*.m ports)
%   for tracking / off_mode / zeta_sweep / residual_alignment /
%   app_30ms_100khz, and reports the max relative error per metric group.
%
%   Tolerances:
%     det   (deterministic select_band grids, guard limits, phi_err tables):
%           1e-6 relative
%     noisy (simulation statistics -- SNR gains, amp errors, lock fractions):
%           1% relative
%   A few threshold-quantized metrics (event counts, first-crossing times)
%   get a documented ABSOLUTE tolerance instead, because a 1e-13 FP
%   difference can move a threshold crossing by a whole count/sample
%   (see OVERRIDES below); their max rel err is still reported.
%
%   Check outcomes (checks_ok vectors) must match EXACTLY.
%
%   Run:  cd matlab && octave --eval compare_validate
%   Raises an error (nonzero exit code) if any pair disagrees.
  sd = fileparts(mfilename('fullpath'));
  gdir = fullfile(sd, 'golden');
  names = {'tracking', 'off_mode', 'zeta_sweep', 'residual_alignment', ...
           'app_30ms_100khz'};
  TOL_DET = 1e-6;
  TOL_NOISY = 1e-2;
  % name:field -> absolute tolerance (units: us for times, counts for events,
  % cycles for the fade phase gap)
  OVR_KEYS = {'zeta_sweep:z2_tr', 'zeta_sweep:z2_ts', ...
              'app_30ms_100khz:a7_rel_med', 'app_30ms_100khz:a7_gap_med', ...
              'app_30ms_100khz:a2_np_med', 'app_30ms_100khz:a6_np_med', ...
              'app_30ms_100khz:a8_np_pct'};
  OVR_ABS = [0.5, 0.5, 0.5, 5.0, 4.0, 4.0, 8.0];

  nbad = 0;
  for i = 1:numel(names)
    name = names{i};
    fpy = fullfile(gdir, sprintf('validate_%s_py.mat', name));
    fmat = fullfile(gdir, sprintf('validate_%s_mat.mat', name));
    fprintf('\n=== validate_%s ===\n', name);
    if ~exist(fpy, 'file') || ~exist(fmat, 'file')
      fprintf('  [MISSING] py: %d, mat: %d\n', ...
              exist(fpy, 'file') > 0, exist(fmat, 'file') > 0);
      nbad = nbad + 1;
      continue
    end
    py = load(fpy);
    mt = load(fmat);

    % ---- check outcomes must match exactly ----
    okpy = double(py.checks_ok(:));
    okmt = double(mt.checks_ok(:));
    same = numel(okpy) == numel(okmt) && all(okpy == okmt);
    fprintf('  checks: py %d/%d, mat %d/%d -> %s\n', ...
            sum(okpy), numel(okpy), sum(okmt), numel(okmt), ...
            pf_(same));
    nbad = nbad + ~same;

    % ---- metric groups ----
    groups = {'det', TOL_DET; 'noisy', TOL_NOISY};
    for ig = 1:2
      grp = groups{ig, 1};
      tol = groups{ig, 2};
      if ~isfield(mt, grp)
        continue
      end
      if ~isfield(py, grp)
        fprintf('  [FAIL] group %s missing on the Python side\n', grp);
        nbad = nbad + 1;
        continue
      end
      gm = mt.(grp);
      gp = py.(grp);
      fns = fieldnames(gm);
      for j = 1:numel(fns)
        fn = fns{j};
        if ~isfield(gp, fn)
          fprintf('  [FAIL] %s.%s missing on the Python side\n', grp, fn);
          nbad = nbad + 1;
          continue
        end
        atol = 0;
        key = sprintf('%s:%s', name, fn);
        kk = find(strcmp(OVR_KEYS, key), 1);
        if ~isempty(kk), atol = OVR_ABS(kk); end
        [rmax, ok, note] = cmp_(gm.(fn), gp.(fn), tol, atol);
        if atol > 0, extra = sprintf('  (abs tol %g)', atol); else, extra = ''; end
        fprintf('  [%s] %s %-22s max rel err %.3e%s%s\n', ...
                pf_(ok), grp, fn, rmax, note, extra);
        nbad = nbad + ~ok;
      end
    end
  end

  fprintf('\n');
  if nbad > 0
    fprintf('COMPARE FAILED: %d mismatching item(s)\n', nbad);
    error('compare_validate: FAILED');
  end
  fprintf(['COMPARE PASSED: all golden pairs agree (det <= %.0e rel, ' ...
           'noisy <= %.0f%% rel)\n'], TOL_DET, 100 * TOL_NOISY);
end


function s = pf_(ok)
  if ok, s = 'OK  '; else, s = 'FAIL'; end
end


function [rmax, ok, note] = cmp_(a, b, tol, atol)
%CMP_ Max relative error of a (MATLAB) vs b (Python reference).
%   Elements are compared as |a-b| / max(|b|, 1e-12); elements with
%   |a-b| <= atol are accepted regardless (threshold-quantized metrics).
%   Inf/Inf with equal sign and NaN/NaN count as equal.
  note = '';
  a = double(a(:));
  b = double(b(:));
  if numel(a) ~= numel(b)
    rmax = Inf;
    ok = false;
    note = sprintf('  size mismatch (%d vs %d)', numel(a), numel(b));
    return
  end
  both_nan = isnan(a) & isnan(b);
  both_inf = isinf(a) & isinf(b) & (sign(a) == sign(b));
  drop = both_nan | both_inf;
  a(drop) = 0;
  b(drop) = 0;
  if any(isnan(a) | isnan(b) | isinf(a) | isinf(b))
    rmax = Inf;
    ok = false;
    note = '  NaN/Inf mismatch';
    return
  end
  d = abs(a - b);
  rel = d ./ max(abs(b), 1e-12);
  rmax = max([0; rel]);
  ok = all(rel <= tol | d <= atol);
end
