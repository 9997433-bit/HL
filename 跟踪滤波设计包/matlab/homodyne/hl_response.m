function H = hl_response(f, fs, fn, zeta)
%HL_RESPONSE Exact discrete closed-loop phase response of this update ordering.
%   Port of core.hl_response.
  th = 2 * pi * fn / fs;
  Kp = 2 * zeta * th;
  Ki = th * th;
  q = exp(1i * 2 * pi * f / fs) - 1;
  H = (Ki + (Ki + Kp) * q) ./ (q.^2 + (Ki + Kp) * q + Ki);
  H(f == 0) = 1.0;
end
