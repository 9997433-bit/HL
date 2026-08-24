function phi = doppler_phase(x, lam)
%DOPPLER_PHASE Optical Doppler phase of a homodyne IQ link for displacement x(t).
% Port of synth_multichannel.py::doppler_phase (lambda default = homodyne 1550 nm).
  if nargin < 2 || isempty(lam)
    P = hd_params();
    lam = P.LAMBDA;
  end
  phi = 4.0 * pi / lam * x;
end
