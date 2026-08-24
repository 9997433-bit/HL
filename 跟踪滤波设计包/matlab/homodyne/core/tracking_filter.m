function [y, phi, state, diag] = tracking_filter(z, fs, cfg, Nhat)
%TRACKING_FILTER Product entry point, driven by cfg_for_frequency structs.
%   [y, phi, state, diag] = tracking_filter(z, fs, cfg, Nhat)
%   Faithful port of core.py tracking_filter.
%
%   cfg.tracking_mode == 'off': tracking bypass (off_mode); Nhat unused.
%   cfg.tracking_mode == 'fixed_lp': no PLL, output is the common fixed
%       measurement window LP(z) built from cfg.B_win / cfg.NT_win.
%   cfg.tracking_mode == 'pll' (or absent, for legacy cfg structs):
%       gear PLL + common residual window (residual_mode); Nhat is the
%       mandatory dark-calibrated noise floor.
  if isfield(cfg, 'tracking_mode')
    mode = cfg.tracking_mode;
  else
    mode = 'pll';
  end
  if strcmp(mode, 'off')
    [y, phi, state, diag] = off_mode(z);
    return
  end
  if strcmp(mode, 'fixed_lp')
    [y, phi, state, diag] = fixed_lp_mode(z, fs, cfg.B_win, cfg.NT_win);
    return
  end
  if nargin < 4 || isempty(Nhat)
    error('tracking_filter:Nhat', ...
          "tracking_mode='pll' requires the dark-calibrated noise floor Nhat");
  end
  pll_cfg_keys = {'tauP', 'tauF', 'snr_on', 'snr_off', 'reacq', 'gate', ...
                  'rel_on', 'rel_off', 'tauRef'};
  opts = struct();
  for i = 1:numel(pll_cfg_keys)
    if isfield(cfg, pll_cfg_keys{i})
      opts.(pll_cfg_keys{i}) = cfg.(pll_cfg_keys{i});
    end
  end
  if isfield(cfg, 'zeta')
    opts.zeta = cfg.zeta;
  else
    opts.zeta = 1.2;
  end
  [y, phi, state, diag] = residual_mode(z, fs, cfg.fn, Nhat, cfg.B_win, opts);
end
