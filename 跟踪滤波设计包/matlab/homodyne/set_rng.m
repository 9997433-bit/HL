function set_rng(seed)
%SET_RNG Seed Octave/MATLAB global RNG streams (rand + randn) deterministically.
% The Python sources use np.random.default_rng(seed) (PCG64), which cannot be
% reproduced bit-for-bit here; validators only need per-seed reproducibility
% of their OWN draws, which this provides (golden comparisons instead export
% the Python-generated arrays and bypass the RNG entirely).
  rand('twister', seed);
  randn('state', seed);
end
