function B = b_loop(fn)
%B_LOOP Closed-loop noise bandwidth of the II-type loop at design zeta.
  dp = design_params();
  B = dp.B_LOOP_COEF * fn;
end
