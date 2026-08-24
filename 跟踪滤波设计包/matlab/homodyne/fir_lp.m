function y = fir_lp(x, fc, fs, Nt)
%FIR_LP Direct-convolution FIR low-pass, 'same' alignment (numpy convention).
%   Port of core.fir_lp.
  if nargin < 4 || isempty(Nt), Nt = 257; end
  if mod(Nt, 2) == 0
    Nt = Nt + 1;
  end
  h = fir_lp_kernel(fc, fs, Nt);
  y = np_conv_same(x(:), h);
end
