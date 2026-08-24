function q = np_unwrap(p)
%NP_UNWRAP 1-D phase unwrap, identical to numpy.unwrap (default period 2*pi).
  p = p(:);
  dd = diff(p);
  ddmod = mod(dd + pi, 2 * pi) - pi;
  ddmod((ddmod == -pi) & (dd > 0)) = pi;
  ph_correct = ddmod - dd;
  ph_correct(abs(dd) < pi) = 0;
  q = p + [0; cumsum(ph_correct)];
end
