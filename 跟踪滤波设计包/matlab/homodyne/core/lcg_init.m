function st = lcg_init(seed)
%LCG_INIT Portable minstd LCG state (cross-language deterministic RNG).
%   st = lcg_init(seed)
%   Park-Miller minstd: s <- mod(48271*s, 2^31-1).  48271*(2^31-2) < 2^53,
%   so the recurrence is EXACT in double precision and produces the same
%   stream in MATLAB/Octave and Python (see matlab/export_python_golden.py,
%   class PortableLCG).  numpy's default_rng (PCG64) stream cannot be
%   reproduced by MATLAB rng(seed), so golden smoke tests use this
%   generator on both sides instead.
  s = mod(floor(seed), 2147483647);
  if s == 0
    s = 1;
  end
  st = struct('s', s);
end
