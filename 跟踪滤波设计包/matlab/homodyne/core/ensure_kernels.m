function ok = ensure_kernels()
%ENSURE_KERNELS Try to compile the optional MEX kernels in this directory.
%   ok = ensure_kernels()
%   Kernels: homodyne_rng_mex (numpy-exact RNG) and pll_core_mex (fast PLL
%   scalar loop).  Both are OPTIONAL speedups: when a kernel is missing and
%   cannot be compiled, the pure-M twins (np_rng_m, pll_core_m) are used
%   instead and produce bit-identical results, so every validator runs on
%   any platform without a compiler.  Returns true iff both kernels are
%   available afterwards.
%
%   Octave: uses mkoctfile --mex.  MATLAB: uses mex (on Windows this needs
%   a GCC-compatible compiler, e.g. the MinGW-w64 add-on; MSVC lacks the
%   __uint128_t type used by homodyne_rng_mex.c).
%   Set HOMODYNE_NO_MEX=1 to skip compilation and force the pure-M paths.
  persistent attempted
  if isempty(attempted)
    attempted = false;
  end
  d = fileparts(mfilename('fullpath'));
  srcs = {'homodyne_rng_mex', 'pll_core_mex'};
  if ~isempty(getenv('HOMODYNE_NO_MEX'))
    ok = false;
    return
  end
  is_octave = exist('OCTAVE_VERSION', 'builtin') == 5;
  built = false;
  ok = true;
  for i = 1:numel(srcs)
    if exist(fullfile(d, [srcs{i} '.' mexext()]), 'file')
      continue
    end
    if attempted
      ok = false;
      continue
    end
    fprintf('[ensure_kernels] compiling %s.c ...\n', srcs{i});
    try
      if is_octave
        cmd = sprintf('cd "%s" && mkoctfile --mex -O2 -ffp-contract=off %s.c 2>&1', ...
                      d, [srcs{i}]);
        [rc, out] = system(cmd);
        if rc ~= 0
          error('mkoctfile failed:\n%s', out);
        end
      else
        old = cd(d);
        c = onCleanup(@() cd(old));
        mex('-O', 'CFLAGS=$CFLAGS -ffp-contract=off', [srcs{i} '.c']);
        clear c
      end
      built = true;
    catch err
      warning('ensure_kernels:build', ...
              ['could not compile %s (%s); falling back to the pure-M ' ...
               'implementation (slower, same results)'], srcs{i}, err.message);
      attempted = true;
      ok = false;
    end
  end
  if built
    rehash();
  end
end
