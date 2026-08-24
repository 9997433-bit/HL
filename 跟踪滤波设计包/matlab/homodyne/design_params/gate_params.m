function g = gate_params(name)
%GATE_PARAMS Per-band gate parameter struct (tauP, tauF + GATE_COMMON).
%   g = gate_params(name)   Faithful port of design_params.py gate_params.
  C = homodyne_constants();
  b = C.BANDS.(name);
  g = C.GATE_COMMON;
  g.tauP = b.tauP;
  g.tauF = b.tauF;
end
