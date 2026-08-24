function ensure_kernels()
%ENSURE_KERNELS Compile the MEX kernels in this directory if missing.
%   Kernels: homodyne_rng_mex (numpy-exact RNG; REQUIRED for validators)
%            pll_core_mex     (fast PLL loop; optional, pll_core_m fallback).
%   Octave: uses mkoctfile --mex.  MATLAB: uses mex.
  d = fileparts(mfilename('fullpath'));
  srcs = {'homodyne_rng_mex', 'pll_core_mex'};
  is_octave = exist('OCTAVE_VERSION', 'builtin') == 5;
  built = false;
  for i = 1:numel(srcs)
    if exist(fullfile(d, [srcs{i} '.' mexext()]), 'file')
      continue
    end
    fprintf('[ensure_kernels] compiling %s.c ...\n', srcs{i});
    if is_octave
      cmd = sprintf('cd "%s" && mkoctfile --mex -O2 -ffp-contract=off %s.c', ...
                    d, [srcs{i}]);
      [rc, out] = system(cmd);
      if rc ~= 0
        error('ensure_kernels: mkoctfile failed for %s:\n%s', srcs{i}, out);
      end
    else
      old = cd(d);
      c = onCleanup(@() cd(old));
      mex('-O', 'CFLAGS=$CFLAGS -ffp-contract=off', [srcs{i} '.c']);
      clear c
    end
    built = true;
  end
  if built
    rehash();
  end
end
