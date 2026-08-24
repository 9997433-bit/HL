function homodyne_setup_path()
%HOMODYNE_SETUP_PATH Add the homodyne MATLAB/Octave port subfolders to the path.
%   Layout: matlab/homodyne/core, matlab/homodyne/design_params,
%           matlab/homodyne/ellipse  (plain folders + addpath, no +package,
%           for maximum Octave compatibility).
  d = fileparts(mfilename('fullpath'));
  addpath(fullfile(d, 'homodyne', 'core'));
  addpath(fullfile(d, 'homodyne', 'design_params'));
  addpath(fullfile(d, 'homodyne', 'ellipse'));
end
