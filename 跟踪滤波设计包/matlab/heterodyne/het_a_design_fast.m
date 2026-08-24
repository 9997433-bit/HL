function a = het_a_design_fast(v_range, acq_bw, f_acc_cap)
%HET_A_DESIGN_FAST [自研] 规则第 1 步: FAST 档设计加速度.
% Port of heterodyne design_params.py::a_design_fast.
  P = het_params();
  if nargin < 2 || isempty(acq_bw)
    acq_bw = P.ACQ_BW;
  end
  if nargin < 3 || isempty(f_acc_cap)
    f_acc_cap = P.F_ACC_CAP;
  end
  a = 2 * pi * min(acq_bw, f_acc_cap) * v_range;
end
