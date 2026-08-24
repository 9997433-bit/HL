function [st, par] = online_bias_tracker_block(st, u, v)
%ONLINE_BIAS_TRACKER_BLOCK One block update of the online p,q bias tracker.
%   [st, par] = online_bias_tracker_block(st, u, v)
%   Faithful port of ellipse_correction.py OnlineBiasTracker.process_block
%   (+ the private _try_center).  Returns the updated state and the current
%   parameter struct p,q,A,B,delta.
  u = double(u(:));
  v = double(v(:));
  [~, ~, z] = heydemann_apply(u, v, obt_par(st));
  rho = median(abs(z));
  if st.rho_ref > 0 && abs(rho / st.rho_ref - 1.0) > st.rho_jump
    st.buf_u = zeros(0, 1);
    st.buf_v = zeros(0, 1);
  end
  st.rho_ref = 0.9 * st.rho_ref + 0.1 * max(rho, 1e-9);
  st.buf_u(end+1, 1) = mean(u);
  st.buf_v(end+1, 1) = mean(v);
  if numel(st.buf_u) > 120
    st.buf_u(1) = [];
    st.buf_v(1) = [];
  end
  st = try_center(st);
  par = obt_par(st);
end

function par = obt_par(st)
  par = struct('p', st.p, 'q', st.q, 'A', st.gd.A, 'B', st.gd.B, ...
               'delta', st.gd.delta);
end

function st = try_center(st)
  if numel(st.buf_u) < 12
    return
  end
  us = st.buf_u;
  vs = st.buf_v;
  if arc_span_corrected(us, vs, obt_par(st)) < st.arc_min
    return
  end
  % Scale factory A,B by current |z|: heydemann_apply with frozen A,B gives
  % |z| ~ R/R_cal, so A_eff = A*rho recovers the true interference radius.
  % Without this, weak-return segments subtract a factory-sized vector and
  % drive amplitude error -> 100% (audit residual after item 1).
  [~, ~, z] = heydemann_apply(us, vs, obt_par(st));
  rho_med = max(median(abs(z)), 1e-9);
  Ae = st.gd.A * rho_med;
  Be = st.gd.B * rho_med;
  ang = angle(z);
  c = mean((us - Ae * cos(ang)) + 1i * (vs - Be * sin(ang + st.gd.delta)));
  st.p = 0.8 * st.p + 0.2 * real(c);
  st.q = 0.8 * st.q + 0.2 * imag(c);
end
