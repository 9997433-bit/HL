function E = ellipse_constants()
%ELLIPSE_CONSTANTS Module constants of ellipse_correction.py.
%   E = ellipse_constants()
%   ARC_MIN      below this 98% coverage the fit is declared invalid
%   FIT_RMS_MAX, FIT_COND_MAX, EPS_MAX (|B/A - 1|), DEL_MAX
%   PAR_FIELDS   {'p','q','A','B','delta'}
  E.ARC_MIN = pi / 2;
  E.FIT_RMS_MAX = 0.05;
  E.FIT_COND_MAX = 1e6;
  E.EPS_MAX = 0.20;
  E.DEL_MAX = 15.0 * pi / 180;
  E.PAR_FIELDS = {'p', 'q', 'A', 'B', 'delta'};
end
