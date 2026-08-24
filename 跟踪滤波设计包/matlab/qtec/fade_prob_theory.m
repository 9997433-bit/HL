function p = fade_prob_theory(F, M)
%FADE_PROB_THEORY Joint deep-fade probability of M INDEPENDENT Rayleigh channels.
% Port of speckle_multi.py::fade_prob_theory: p = (1 - exp(-F))^M.
  if nargin < 2 || isempty(M)
    M = 1;
  end
  p = (1.0 - exp(-F)) .^ M;
end
