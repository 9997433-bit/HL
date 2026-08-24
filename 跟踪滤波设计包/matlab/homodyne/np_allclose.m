function ok = np_allclose(a, b, rtol, atol)
%NP_ALLCLOSE numpy.allclose semantics: all(|a-b| <= atol + rtol*|b|).
  if nargin < 3 || isempty(rtol), rtol = 1e-5; end
  if nargin < 4 || isempty(atol), atol = 1e-8; end
  a = a(:);
  b = b(:);
  ok = all(abs(a - b) <= atol + rtol * abs(b));
end
