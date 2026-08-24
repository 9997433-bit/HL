function x = np_rng_randn(h, n)
%NP_RNG_RANDN Draw n standard normals from RNG handle h (numpy bit-exact).
%   Equivalent to rng.standard_normal(n) on the matching numpy Generator;
%   the handle's stream advances, so consecutive calls continue the stream.
  x = homodyne_rng_mex('randn', h, n);
end
