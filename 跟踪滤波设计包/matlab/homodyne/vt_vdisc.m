function v = vt_vdisc(y)
%VT_VDISC FM discrimination at the design fs / lambda.
  dp = design_params();
  v = fm_discriminator(y, dp.FS, dp.LAMBDA);
end
