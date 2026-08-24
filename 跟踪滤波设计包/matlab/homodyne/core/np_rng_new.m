function h = np_rng_new(seed)
%NP_RNG_NEW numpy-compatible RNG: h = np_rng_new(seed) == np.random.default_rng(seed).
%   Returns a draw handle: h(n) yields the next n standard normals of the
%   stream, bit-identical to numpy Generator.standard_normal (PCG64 +
%   256-layer ziggurat).  Pass h anywhere a Python rng argument is expected
%   (np_rng_randn, complex_bandlimited_noise, make_speckle, ...).
%
%   Backend: the compiled MEX kernel homodyne_rng_mex when available (built
%   on demand by ensure_kernels; fast), otherwise the pure-M twin np_rng_m
%   (slower, bit-identical) -- so the validators run without any compiler.
  if exist('homodyne_rng_mex', 'file') ~= 3 && isempty(getenv('HOMODYNE_NO_MEX'))
    ensure_kernels();
  end
  if homodyne_use_mex('homodyne_rng_mex')
    hh = homodyne_rng_mex('new', seed);
    h = @(n) homodyne_rng_mex('randn', hh, n);
  else
    hh = np_rng_m('new', seed);
    h = @(n) np_rng_m('randn', hh, n);
  end
end
