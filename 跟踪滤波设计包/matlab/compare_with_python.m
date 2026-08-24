function ok = compare_with_python(rtol)
%COMPARE_WITH_PYTHON Compare MATLAB golden vs Python golden (rtol=1e-10).
%   ok = compare_with_python(rtol)
%   Loads matlab/golden/core_smoke.mat (written by export_golden_core) and
%   matlab/golden/core_smoke_py.mat (written by matlab/export_python_golden.py
%   via scipy.io.savemat; falls back to core_smoke_py.json + jsondecode when
%   scipy was unavailable) and checks every field to a field-relative
%   tolerance:  max|a-b| / max(max|a|, tiny) <= rtol.
%
%   Raises an error (non-zero octave exit) if any field mismatches, if the
%   Python golden is missing, or if fields/sizes disagree.
  if nargin < 1 || isempty(rtol)
    rtol = 1e-10;
  end
  gdir = fullfile(fileparts(mfilename('fullpath')), 'golden');
  fm = fullfile(gdir, 'core_smoke.mat');
  if ~exist(fm, 'file')
    error('compare_with_python:missing', ...
          'run export_golden_core first (missing %s)', fm);
  end
  M = load(fm);

  fp_mat = fullfile(gdir, 'core_smoke_py.mat');
  fp_json = fullfile(gdir, 'core_smoke_py.json');
  if exist(fp_mat, 'file')
    P = load(fp_mat);
    src = fp_mat;
  elseif exist(fp_json, 'file')
    P = jsondecode(fileread(fp_json));
    src = fp_json;
  else
    error('compare_with_python:missing', ...
          ['Python golden not found; run  python3 matlab/export_python_golden.py' ...
           '  first (looked for %s and %s)'], fp_mat, fp_json);
  end

  fns = fieldnames(M);
  nfail = 0;
  worst_rel = 0;
  worst_field = '';
  fprintf('compare_with_python: %d fields, rtol=%.1e (python golden: %s)\n', ...
          numel(fns), rtol, src);
  for i = 1:numel(fns)
    f = fns{i};
    if ~isfield(P, f)
      fprintf('  FAIL %-18s missing in Python golden\n', f);
      nfail = nfail + 1;
      continue
    end
    a = double(M.(f)(:));
    b = double(P.(f)(:));
    if numel(a) ~= numel(b)
      fprintf('  FAIL %-18s size mismatch (%d vs %d)\n', f, numel(a), numel(b));
      nfail = nfail + 1;
      continue
    end
    scale = max(max(abs(a)), 1e-300);
    maxabs = max(abs(a - b));
    if isempty(maxabs)
      maxabs = 0;
    end
    rel = maxabs / scale;
    if rel > worst_rel
      worst_rel = rel;
      worst_field = f;
    end
    if rel > rtol || any(isnan(a) ~= isnan(b))
      fprintf('  FAIL %-18s max|d|=%.3e rel=%.3e\n', f, maxabs, rel);
      nfail = nfail + 1;
    end
  end
  ok = (nfail == 0);
  if ok
    fprintf(['compare_with_python: PASS -- all %d fields match ' ...
             '(worst rel err %.3e in %s)\n'], numel(fns), worst_rel, worst_field);
  else
    error('compare_with_python:mismatch', ...
          '%d field(s) exceeded rtol=%.1e (worst rel err %.3e in %s)', ...
          nfail, rtol, worst_rel, worst_field);
  end
end
