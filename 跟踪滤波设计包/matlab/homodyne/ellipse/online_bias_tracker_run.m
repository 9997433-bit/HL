function [z, st] = online_bias_tracker_run(st, u, v)
%ONLINE_BIAS_TRACKER_RUN Run the online bias tracker over a full record.
%   [z, st] = online_bias_tracker_run(st, u, v)
%   Faithful port of ellipse_correction.py OnlineBiasTracker.run: processes
%   u,v in blocks of st.nb samples, correcting each block with the
%   parameters valid after that block's update.
  u = double(u(:));
  v = double(v(:));
  N = numel(u);
  z = complex(zeros(N, 1));
  for k = 1:st.nb:N
    i1 = min(k + st.nb - 1, N);
    [st, par] = online_bias_tracker_block(st, u(k:i1), v(k:i1));
    [~, ~, z(k:i1)] = heydemann_apply(u(k:i1), v(k:i1), par);
  end
end
