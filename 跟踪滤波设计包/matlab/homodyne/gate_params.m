function gp = gate_params(name)
%GATE_PARAMS Per-gear gate/PLL time constants + common gate constants.
  dp = design_params();
  b = dp.BANDS.(name);
  gp = dp.GATE_COMMON;
  gp.tauP = b.tauP;
  gp.tauF = b.tauF;
end
