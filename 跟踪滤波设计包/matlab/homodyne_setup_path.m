function homodyne_setup_path()
%HOMODYNE_SETUP_PATH Add the homodyne MATLAB/Octave port folders to the path.
%   Layout (plain folders + addpath, no +package, for maximum Octave
%   compatibility):
%     matlab/homodyne                validator-only helpers (hd_*, np_*,
%                                    set_rng, vt_*, ve_*, ellipse validators)
%     matlab/homodyne/core           canonical DSP core (PLL, signals,
%                                    filters, numpy-exact RNG + MEX kernels)
%     matlab/homodyne/design_params  canonical design-parameter functions
%     matlab/homodyne/ellipse        ellipse / Heydemann correction port
%   Each implementation exists exactly once; the canonical folders are
%   added LAST so they take path precedence (addpath prepends).
  d = fileparts(mfilename('fullpath'));
  addpath(fullfile(d, 'homodyne'));
  addpath(fullfile(d, 'homodyne', 'core'));
  addpath(fullfile(d, 'homodyne', 'design_params'));
  addpath(fullfile(d, 'homodyne', 'ellipse'));
end
