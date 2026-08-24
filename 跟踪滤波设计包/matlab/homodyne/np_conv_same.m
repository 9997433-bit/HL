function y = np_conv_same(x, k)
%NP_CONV_SAME Convolution with numpy's mode='same' alignment.
%   numpy takes elements (len(k)-1)//2 .. (len(k)-1)//2 + len(x) - 1 of the
%   full convolution (MATLAB's conv(...,'same') differs for even-length k).
  x = x(:);
  k = k(:);
  yf = conv(x, k);
  i0 = floor((numel(k) - 1) / 2);
  y = yf(i0+1:i0+numel(x));
end
