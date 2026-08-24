function e = vt_amp_err_pct(v_est, sc)
%VT_AMP_ERR_PCT Lock-in amplitude error (%) vs the true burst velocity.
  c = vt_const();
  a = lockin_amp(v_est, c.t, sc.f0, sc.Wm);
  a0 = lockin_amp(sc.v, c.t, sc.f0, sc.Wm);
  e = 100 * (a / a0 - 1);
end
