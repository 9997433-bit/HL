function s = band_specs(name, B_frontend, cnr_db)
%BAND_SPECS Full spec struct for one gear (port of design_params.band_specs).
  dp = design_params();
  if nargin < 2 || isempty(B_frontend), B_frontend = dp.B_FRONTEND; end
  if nargin < 3 || isempty(cnr_db), cnr_db = 3.0; end
  b = dp.BANDS.(name);
  fn = b.fn;
  [Kp, Ki] = loop_gains(fn);
  B = b_loop(fn);
  cnr = 10^(cnr_db / 10);
  s = struct('name', name, 'fn', fn, 'zeta', dp.ZETA, 'Kp', Kp, 'Ki', Ki, ...
             'f_target_max', b.f_target_max, 'B_loop', B, ...
             'f_3db', dp.F3DB_COEF * fn, ...
             'a_design', pi * dp.LAMBDA * fn^2, ...
             'B_win', dp.B_WIN, ...
             'ceiling_db', 10 * log10((B_frontend / 2) / B), ...
             'sigma_phi_at_cnr', sqrt(B / (cnr * B_frontend)));
  gp = gate_params(name);
  fns = fieldnames(gp);
  for i = 1:numel(fns)
    s.(fns{i}) = gp.(fns{i});
  end
end
