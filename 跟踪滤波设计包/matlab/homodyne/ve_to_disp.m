function x = ve_to_disp(ph)
%VE_TO_DISP Optical phase (rad) -> displacement (m) at lambda = 1550 nm.
%   Port of the to_disp helper of the ellipse validators:
%   x = ph * lambda / (4*pi).
  c = ve_const();
  x = ph * (c.LAMBDA / (4 * pi));
end
