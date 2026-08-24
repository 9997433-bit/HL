function C = estimate_C(z, fs, Nhat, tauP)
%ESTIMATE_C Re-computed carrier power estimate C(t) = max(IIR(|z|^2, tauP) - Nhat, 0).
% Port of diversity_combine.py::estimate_C -- mirrors the P/C estimator
% inside pll_carrier_regen (same tauP one-pole IIR, zero initial state).
  a = exp(-1.0 / (fs * tauP));
  P = iir1_lowpass(abs(z(:)) .^ 2, a);
  C = max(P - Nhat, 0.0);
end
