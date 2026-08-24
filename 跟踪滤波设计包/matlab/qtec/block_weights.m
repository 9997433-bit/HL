function [w, dark] = block_weights(C, state, gs, Nhat, block, alpha, rel_x)
%BLOCK_WEIGHTS Block-wise combining weights with cross-channel gate and HOLD flywheel.
% Port of diversity_combine.py::block_weights.
% C, state, gs : (M x N);  Nhat : (M x 1) per-channel noise power.
% Returns w (M x nblk) normalised weights and dark (1 x nblk) logical --
% blocks where every channel was gated out (weights held from the previous
% block: the all-dark HOLD flywheel).
  if nargin < 6 || isempty(alpha)
    alpha = 1.0;
  end
  if nargin < 7 || isempty(rel_x)
    rel_x = 0.05;
  end
  [M, N] = size(C);
  Nhat = Nhat(:);
  nblk = ceil(N / block);
  w = zeros(M, nblk);
  dark = false(1, nblk);
  w_prev = ones(M, 1) / M;              % cold-start: equal weights
  for b = 1:nblk
    s = (b - 1) * block + 1:min(b * block, N);
    snr = mean(C(:, s), 2) ./ Nhat;
    lockf = mean(state(:, s) == 2, 2);
    gsf = mean(gs(:, s), 2);
    base = snr .* lockf .* gsf;
    if isinf(alpha)
      q = zeros(M, 1);
      if max(base) > 0.0
        [~, imax] = max(base);
        q(imax) = 1.0;
      end
    else
      q = snr .^ alpha .* lockf .* gsf;
      qmax = max(q);
      if qmax > 0.0
        q(q < rel_x * qmax) = 0.0;
      end
    end
    tot = sum(q);
    if tot <= 0.0
      w(:, b) = w_prev;                 % all-dark HOLD flywheel
      dark(b) = true;
    else
      w(:, b) = q / tot;
      w_prev = w(:, b);
    end
  end
end
