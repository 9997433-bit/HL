function r = joint_fade_fraction(h, F)
%JOINT_FADE_FRACTION Fraction of samples where ALL channels' intensity < F*<I_k>.
% Port of speckle_multi.py::joint_fade_fraction.  h: (M x N) complex
% (a vector is treated as a single channel).
  if isvector(h)
    h = h(:).';
  end
  I = abs(h) .^ 2;
  thr = F * mean(I, 2);
  r = mean(all(I < thr, 1));
end
