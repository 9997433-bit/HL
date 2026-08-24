function B = b_loop(fn)
%B_LOOP One-sided loop noise bandwidth of the II-type loop at design ZETA.
%   B = b_loop(fn)   Faithful port of design_params.py b_loop.
  C = homodyne_constants();
  B = C.B_LOOP_COEF * fn;
end
