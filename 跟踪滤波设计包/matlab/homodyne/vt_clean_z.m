function z = vt_clean_z(sc, seed)
%VT_CLEAN_Z Near-noiseless complex baseband (validate_tracking.clean_z).
  c = vt_const();
  dp = design_params();
  if nargin < 2 || isempty(seed), seed = 777; end
  rh = np_rng_new(seed);
  z = exp(1i * sc.ph) + complex_bandlimited_noise(c.N, dp.FS, 20e6, 1e-10, rh);
end
