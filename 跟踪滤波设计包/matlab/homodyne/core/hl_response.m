function H = hl_response(f, fs, fn, zeta)
%HL_RESPONSE Exact discrete closed-loop phase response of this update ordering.
%   H = hl_response(f, fs, fn, zeta)   Faithful port of core.py hl_response.
%   f may be scalar or vector; H has the same shape, H(f==0) = 1.
  th = 2 * pi * fn / fs;
  Kp = 2 * zeta * th;
  Ki = th * th;
  q = exp(1i * 2 * pi * f / fs) - 1;
  H = (Ki + (Ki + Kp) * q) ./ (q .^ 2 + (Ki + Kp) * q + Ki);
  H(f == 0) = 1.0;
end
