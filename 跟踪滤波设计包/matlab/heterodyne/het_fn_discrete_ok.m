function ok = het_fn_discrete_ok(fn, fs)
%HET_FN_DISCRETE_OK 离散环稳定性约束 fn <= fs/50.
% Port of heterodyne design_params.py::fn_discrete_ok.
  if nargin < 2 || isempty(fs)
    P = het_params();
    fs = P.FS;
  end
  ok = fn <= fs / 50;
end
