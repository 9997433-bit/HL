function ph = ve_phase_cum(z)
%VE_PHASE_CUM Unwrapped phase from complex samples via increment accumulation.
%   ph = ve_phase_cum(z)
%   Port of the phase_cum helper of the ellipse validators:
%   d = angle(z(2:end) .* conj(z(1:end-1))); ph = [0; cumsum(d)].
  z = z(:);
  d = angle(z(2:end) .* conj(z(1:end-1)));
  ph = [0; cumsum(d)];
end
