function [x, st] = lcg_randn(st, n)
%LCG_RANDN n standard normal draws from the portable minstd LCG stream.
%   [x, st] = lcg_randn(st, n)  -> x is an n-by-1 column vector.
%   Each normal consumes exactly two uniforms via Box-Muller (cos branch
%   only, no spare caching) so the draw sequence is trivially identical to
%   the Python PortableLCG.standard_normal implementation.
  M = 2147483647;
  A = 48271;
  s = st.s;
  x = zeros(n, 1);
  for i = 1:n
    s = mod(A * s, M);
    u1 = s / M;
    s = mod(A * s, M);
    u2 = s / M;
    x(i) = sqrt(-2 * log(u1)) * cos(2 * pi * u2);
  end
  st.s = s;
end
