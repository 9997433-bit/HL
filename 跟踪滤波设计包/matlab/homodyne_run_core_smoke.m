function homodyne_run_core_smoke()
%HOMODYNE_RUN_CORE_SMOKE Run the golden smoke suite and compare with Python.
%   Usage (from the package root, 跟踪滤波设计包/):
%     octave --eval "addpath('matlab'); homodyne_run_core_smoke"
%
%   1. export_golden_core          -> matlab/golden/core_smoke.mat
%   2. compare_with_python (1e-10) against matlab/golden/core_smoke_py.mat
%      (produce it first with:  python3 matlab/export_python_golden.py)
%   Errors out (non-zero exit) on any mismatch, so it can gate CI.
  homodyne_setup_path();
  export_golden_core();
  gdir = fullfile(fileparts(mfilename('fullpath')), 'golden');
  if exist(fullfile(gdir, 'core_smoke_py.mat'), 'file') || ...
      exist(fullfile(gdir, 'core_smoke_py.json'), 'file')
    compare_with_python(1e-10);
  else
    fprintf(['homodyne_run_core_smoke: Python golden not found -- run\n' ...
             '  python3 matlab/export_python_golden.py\n' ...
             'and re-run to compare.\n']);
  end
end
