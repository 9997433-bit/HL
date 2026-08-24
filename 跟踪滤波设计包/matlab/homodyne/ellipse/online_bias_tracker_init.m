function st = online_bias_tracker_init(gd_par, fs, blk_s, rho_jump, arc_min)
%ONLINE_BIAS_TRACKER_INIT State for the online p,q bias tracker (arc-gated).
%   st = online_bias_tracker_init(gd_par, fs, blk_s, rho_jump, arc_min)
%   Faithful port of ellipse_correction.py OnlineBiasTracker.__init__
%   (struct-based instead of a class, for Octave compatibility).
%   Defaults: blk_s=0.1, rho_jump=0.20, arc_min=pi/2.
%
%   Frozen g,delta (A,B,delta); update p,q only when block-mean arc is
%   sufficient.  Block-mean IIR of raw u,v is WRONG at a fixed working
%   point because mean(u) ~ p + A*cos(psi), not p.  Instead accumulate
%   block means and fit the circle centre only when the corrected-plane
%   arc exceeds ARC_MIN.  On rho jump (surface/distance switch) clear the
%   buffer and hold p,q.
%
%   Use with online_bias_tracker_block / online_bias_tracker_run.
  E = ellipse_constants();
  if nargin < 3 || isempty(blk_s),    blk_s = 0.1;        end
  if nargin < 4 || isempty(rho_jump), rho_jump = 0.20;    end
  if nargin < 5 || isempty(arc_min),  arc_min = E.ARC_MIN; end
  st = struct();
  st.gd = struct('A', double(gd_par.A), 'B', double(gd_par.B), ...
                 'delta', double(gd_par.delta));
  if isfield(gd_par, 'p'), st.p = double(gd_par.p); else st.p = 0.0; end
  if isfield(gd_par, 'q'), st.q = double(gd_par.q); else st.q = 0.0; end
  st.nb = max(64, floor(blk_s * fs));
  st.rho_jump = rho_jump;
  st.arc_min = arc_min;
  st.buf_u = zeros(0, 1);
  st.buf_v = zeros(0, 1);
  st.rho_ref = 1.0;
end
