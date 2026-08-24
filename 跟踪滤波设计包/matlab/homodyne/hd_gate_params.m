function g = hd_gate_params(name)
%HD_GATE_PARAMS Gate/loop time-constant set for one homodyne gear.
% Port of design_params.py::gate_params -- band tauP/tauF merged with
% GATE_COMMON.  Returned as a struct.
  P = hd_params();
  b = P.BANDS.(name);
  g = P.GATE_COMMON;
  g.tauP = b.tauP;
  g.tauF = b.tauF;
end
