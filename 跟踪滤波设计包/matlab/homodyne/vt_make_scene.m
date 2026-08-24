function sc = vt_make_scene(f0, vamp)
%VT_MAKE_SCENE Burst scene + measurement/quiet windows (validate_tracking).
  c = vt_const();
  dp = design_params();
  if nargin < 2 || isempty(vamp), vamp = c.VAMP; end
  p = vt_scene_params(f0);
  [x, v, ~] = burst_signal(c.t, f0, vamp, p.ncyc, p.t0);
  Tb = p.ncyc / f0;
  Wm = (c.t > p.t0) & (c.t < p.t0 + Tb);
  Wq = (c.t > p.t0 + Tb + 0.04e-3) & (c.t < 0.48e-3);
  sc = struct('f0', f0, 'vamp', vamp, 'x', x, 'v', v, ...
              'ph', 4 * pi / dp.LAMBDA * x, 'Wm', Wm, 'Wq', Wq, ...
              'L', p.L, 'band', p.band);
end
