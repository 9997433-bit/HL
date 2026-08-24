function a = vt_asd_at(v, sc)
%VT_ASD_AT Velocity ASD near f0, quiet window only (rule R2).
  c = vt_const();
  dp = design_params();
  v = v(:);
  [P, f] = welch_psd(v(sc.Wq), dp.FS, sc.L);
  m = abs(f - sc.f0) < sc.band;
  a = max(sqrt(median(P(m))), c.TINY);
end
