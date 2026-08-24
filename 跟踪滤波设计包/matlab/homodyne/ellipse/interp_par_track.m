function trk = interp_par_track(t, t_c, pars)
%INTERP_PAR_TRACK Sample-wise linear interpolation of segment parameters (edge-hold).
%   trk = interp_par_track(t, t_c, pars)
%   Faithful port of ellipse_correction.py interp_par_track (np.interp
%   clamps outside the abscissa range; emulated here by clamping t).
%   pars is a cell array of parameter structs; trk is a struct of column
%   vectors with fields p,q,A,B,delta.
  E = ellipse_constants();
  t = double(t(:));
  t_c = double(t_c(:));
  trk = struct();
  for i = 1:numel(E.PAR_FIELDS)
    f = E.PAR_FIELDS{i};
    y = cellfun(@(pk) pk.(f), pars(:));
    if numel(t_c) == 1
      trk.(f) = repmat(y(1), size(t));
    else
      tcl = min(max(t, t_c(1)), t_c(end));
      trk.(f) = interp1(t_c, y, tcl, 'linear');
    end
  end
end
