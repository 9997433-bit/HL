function [y, phi, state, diag] = tracking_filter(z, fs, cfg, Nhat)
%TRACKING_FILTER Product entry point, driven by cfg_for_frequency structs.
%   Port of core.tracking_filter.  Nhat = [] (or omitted) mirrors Python
%   None; tracking_mode='pll' then raises an error (Python ValueError).
  if nargin < 4, Nhat = []; end
  mode = 'pll';
  if isfield(cfg, 'tracking_mode'), mode = cfg.tracking_mode; end
  if strcmp(mode, 'off')
    [y, phi, state, diag] = off_mode(z);
    return
  end
  if strcmp(mode, 'fixed_lp')
    [y, phi, state, diag] = fixed_lp_mode(z, fs, cfg.B_win, cfg.NT_win);
    return
  end
  if isempty(Nhat)
    error('homodyne:ValueError', ...
          "tracking_mode='pll' requires the dark-calibrated noise floor Nhat");
  end
  opts = struct('zeta', 1.2);
  if isfield(cfg, 'zeta'), opts.zeta = cfg.zeta; end
  keys = {'tauP', 'tauF', 'snr_on', 'snr_off', 'reacq', 'gate', ...
          'rel_on', 'rel_off', 'tauRef'};
  for i = 1:numel(keys)
    if isfield(cfg, keys{i})
      opts.(keys{i}) = cfg.(keys{i});
    end
  end
  [y, phi, state, diag] = residual_mode(z, fs, cfg.fn, Nhat, cfg.B_win, opts);
end
