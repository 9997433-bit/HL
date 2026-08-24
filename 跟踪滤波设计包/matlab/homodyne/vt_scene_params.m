function p = vt_scene_params(f0)
%VT_SCENE_PARAMS Per-test-frequency burst/welch parameters (SCENES dict).
  if f0 == 100e3
    p = struct('ncyc', 20, 't0', 0.02e-3, 'L', 8192, 'band', 60e3);
  elseif f0 == 1e6
    p = struct('ncyc', 50, 't0', 0.05e-3, 'L', 4096, 'band', 150e3);
  elseif f0 == 3e6
    p = struct('ncyc', 60, 't0', 0.05e-3, 'L', 4096, 'band', 150e3);
  else
    error('vt_scene_params: no scene for f0=%g', f0);
  end
end
