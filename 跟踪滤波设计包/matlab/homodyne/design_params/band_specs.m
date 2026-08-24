function s = band_specs(name, B_frontend, cnr_db)
%BAND_SPECS Full numeric spec struct for one gear.
%   s = band_specs(name, B_frontend, cnr_db)
%   Faithful port of design_params.py band_specs.  B_frontend defaults to
%   B_FRONTEND (40e6), cnr_db to 3.0.
  C = homodyne_constants();
  if nargin < 2 || isempty(B_frontend)
    B_frontend = C.B_FRONTEND;
  end
  if nargin < 3 || isempty(cnr_db)
    cnr_db = 3.0;
  end
  b = C.BANDS.(name);
  fn = b.fn;
  [Kp, Ki] = loop_gains(fn);
  B = b_loop(fn);
  cnr = 10 ^ (cnr_db / 10);
  s = struct( ...
    'name', name, 'fn', fn, 'zeta', C.ZETA, 'Kp', Kp, 'Ki', Ki, ...
    'f_target_max', b.f_target_max, ...
    'B_loop', B, ...
    'f_3db', C.F3DB_COEF * fn, ...
    'a_design', pi * C.LAMBDA * fn ^ 2, ...
    'B_win', C.B_WIN, ...
    'ceiling_db', 10 * log10((B_frontend / 2) / B), ...
    'sigma_phi_at_cnr', sqrt(B / (cnr * B_frontend)));
  g = gate_params(name);
  gf = fieldnames(g);
  for i = 1:numel(gf)
    s.(gf{i}) = g.(gf{i});
  end
end
