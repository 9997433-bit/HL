function h = np_rng_new(seed)
%NP_RNG_NEW numpy-compatible RNG: h = np_rng_new(seed) == np.random.default_rng(seed).
%   Returns an opaque handle for np_rng_randn.  Requires the compiled MEX
%   kernel homodyne_rng_mex (built automatically by ensure_kernels).
  if exist('homodyne_rng_mex', 'file') ~= 3
    ensure_kernels();
  end
  h = homodyne_rng_mex('new', seed);
end
