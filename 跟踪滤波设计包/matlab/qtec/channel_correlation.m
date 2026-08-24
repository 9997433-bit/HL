function C = channel_correlation(h)
%CHANNEL_CORRELATION Empirical pairwise complex field correlation matrix (M x M).
% Port of speckle_multi.py::channel_correlation:
%   C[j,k] = <h_j h_k*> / sqrt(<|h_j|^2><|h_k|^2>).
  if isvector(h)
    h = h(:).';
  end
  G = h * h' / size(h, 2);
  d = sqrt(real(diag(G)));
  C = G ./ (d * d');
end
