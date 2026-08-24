function res = diversity_combine(z, fs, varargin)
%DIVERSITY_COMBINE Full P1 pipeline: M independent demodulators + weighted velocity sum.
% Port of diversity_combine.py::diversity_combine.
%
%   res = diversity_combine(z, fs, 'name', value, ...)
%
% z      (M x N) complex IQ observations (a vector = single channel)
% Options (defaults match Python): 'band' 'FAST', 'Nhat' (scalar or M x 1,
% mandatory), 'gate' 'auto', 'use_residual' true, 'alpha' 2.0, 'rel_x' 0.05,
% 'block_s' 2e-6, 'chans' {} (pre-computed channel_demod cell array to reuse,
% letting a caller sweep alpha/rel_x/block_s without re-running the PLLs).
%
% Returns a struct with the combined velocity v (1 x N), block weights w,
% per-sample weights ws, dark (HOLD) blocks, dark_frac, block, chans.
  o = struct('band', 'FAST', 'Nhat', [], 'gate', 'auto', ...
             'use_residual', true, 'alpha', 2.0, 'rel_x', 0.05, ...
             'block_s', 2e-6, 'chans', {{}});
  for k = 1:2:numel(varargin)
    if strcmp(varargin{k}, 'chans')
      o.chans = varargin{k + 1};
    else
      o.(varargin{k}) = varargin{k + 1};
    end
  end
  if isvector(z)
    z = z(:).';
  end
  [M, N] = size(z);
  Nh = o.Nhat(:);
  if isscalar(Nh)
    Nh = repmat(Nh, M, 1);
  end
  chans = o.chans;
  if isempty(chans)
    chans = cell(1, M);
    for k = 1:M
      chans{k} = channel_demod(z(k, :), fs, o.band, Nh(k), ...
                               o.gate, o.use_residual);
    end
  end
  C = zeros(M, N);
  st = zeros(M, N);
  gs = zeros(M, N);
  vch = zeros(M, N);
  for k = 1:M
    C(k, :) = chans{k}.C.';
    st(k, :) = chans{k}.state.';
    gs(k, :) = (chans{k}.gs .* ones(N, 1)).';   % broadcast scalar gs if needed
    vch(k, :) = chans{k}.v.';
  end
  block = max(1, round(o.block_s * fs));
  [w, dark] = block_weights(C, st, gs, Nh, block, o.alpha, o.rel_x);
  ws = expand_weights(w, block, N);
  v = sum(ws .* vch, 1);
  res = struct('v', v, 'w', w, 'ws', ws, 'dark', dark, ...
               'dark_frac', mean(dark), 'block', block, 'chans', {chans});
end
