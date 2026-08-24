function c = ve_const()
%VE_CONST Shared constants of the ellipse-correction validators.
%   Port of the module-level constants in validate_ellipse_dynamic.py that
%   the switching / no-large-vib validators import (FS, LAMBDA, EPS_HW,
%   DEL_HW, GI, GQ, P_OFF0, Q_OFF, P_DRIFT, FRINGE_RATE).
  persistent cc
  if isempty(cc)
    cc.LAMBDA = 1550e-9;
    cc.FS = 2.5e6;
    cc.T_TRIM = 0.05;
    cc.EPS_HW = -0.10;
    cc.DEL_HW = 4.5 * pi / 180;
    cc.GI = 1.0;
    cc.GQ = 1.0 + cc.EPS_HW;
    cc.P_OFF0 = 0.06;
    cc.Q_OFF = -0.05;
    cc.P_DRIFT = 0.008;
    cc.FRINGE_RATE = 1.2;
  end
  c = cc;
end
