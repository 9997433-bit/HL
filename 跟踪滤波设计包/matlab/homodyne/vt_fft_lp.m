function y = vt_fft_lp(x, fc, Nt)
%VT_FFT_LP Linear-phase FIR low-pass, 'same' alignment (validate_tracking.fft_lp).
%   Thin wrapper over fir_lp_same -- the SAME design function used by
%   residual_mode, so the validated window is the product window.
  dp = design_params();
  y = fir_lp_same(x, fc, dp.FS, Nt);
end
