function c = vt_const()
%VT_CONST Shared constants of validate_tracking (T, N, t, VAMP, scenes).
%   Port of the module-level constants in validate_tracking.py.
  persistent cc
  if isempty(cc)
    dp = design_params();
    cc.TINY = 1e-300;
    cc.VAMP = 20e-3;
    cc.T = 5e-4;
    cc.N = fix(cc.T * dp.FS);          % Python int() truncation
    cc.t = (0:cc.N-1)' / dp.FS;
  end
  c = cc;
end
