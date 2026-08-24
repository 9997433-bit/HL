function ws = expand_weights(w, block, N)
%EXPAND_WEIGHTS (M x nblk) block weights -> (M x N) per-sample (zero-order hold).
% Port of diversity_combine.py::expand_weights.
  ws = w(:, ceil((1:N) / block));
end
