function tf = homodyne_use_mex(name)
%HOMODYNE_USE_MEX True iff the compiled kernel NAME should be used.
%   The MEX kernels are an optional speedup: everything also runs on the
%   pure-M fallbacks (pll_core_m, np_rng_m).  Set the environment variable
%   HOMODYNE_NO_MEX=1 to force the pure-M paths even when the kernels are
%   compiled (useful for testing the fallbacks).
  tf = isempty(getenv('HOMODYNE_NO_MEX')) && exist(name, 'file') == 3;
end
