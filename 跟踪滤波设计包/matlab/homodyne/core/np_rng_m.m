function out = np_rng_m(cmd, a1, a2)
%NP_RNG_M Pure-M numpy default_rng: bit-exact PCG64 + ziggurat standard normal.
%   Fallback twin of the MEX kernel homodyne_rng_mex -- same stream, no
%   compiler needed (see np_rng_new, which picks the backend).
%
%     id = np_rng_m('new', seed)     new generator (seed: non-neg int < 2^53)
%     x  = np_rng_m('randn', id, n)  next n standard normals (n x 1 column)
%     np_rng_m('reset')              discard all generator states
%
%   Reproduces bit for bit numpy.random.default_rng(seed).standard_normal:
%   SeedSequence entropy mixing -> PCG64 (128-bit LCG, XSL-RR output) ->
%   256-layer ziggurat (numpy random_standard_normal), transcribed from
%   NumPy v2.4.4 (BSD-3-Clause); ziggurat tables are parsed at first use
%   from ziggurat_constants.h in this directory.
%
%   128-bit arithmetic uses 8 base-2^16 limbs held in doubles (all products
%   and carries stay < 2^53, hence exact).  The LCG is advanced a block at
%   a time via s_i = A^i*s0 + (sum_{j<i} A^j)*inc mod 2^128 with the
%   constant matrices A^i precomputed, so draws are vectorized; only the
%   rare ziggurat rejections (~1.2%) run scalar code.
  persistent Z REG
  if isempty(Z)
    Z = init_tables_();
  end
  if isempty(REG)
    REG = struct('state', zeros(0, 8), 'inc', zeros(0, 8));
  end

  switch cmd
    case 'reset'
      REG = struct('state', zeros(0, 8), 'inc', zeros(0, 8));
      out = [];

    case 'new'
      seed = a1;
      if ~isscalar(seed) || seed < 0 || seed ~= floor(seed) || seed > 2^53
        error('np_rng_m:seed', 'seed must be a non-negative integer < 2^53');
      end
      [st, inc] = pcg_seed_(seed, Z);
      REG.state(end + 1, :) = st;
      REG.inc(end + 1, :) = inc;
      out = size(REG.state, 1);

    case 'randn'
      id = a1;
      n = a2;
      if ~isscalar(id) || id < 1 || id ~= floor(id) || id > size(REG.state, 1)
        error('np_rng_m:handle', 'invalid rng handle');
      end
      if n < 0 || n ~= floor(n)
        error('np_rng_m:n', 'n must be a non-negative integer');
      end
      out = zeros(n, 1);
      if n == 0
        return
      end
      [out, REG.state(id, :)] = draw_(REG.state(id, :), REG.inc(id, :), n, Z);

    otherwise
      error('np_rng_m:cmd', 'unknown command "%s"', cmd);
  end
end


% ===== normal draws ========================================================
function [x, s] = draw_(s, inc, n, Z)
%DRAW_ n standard normals starting from PCG state s; returns the new state.
  x = zeros(n, 1);
  filled = 0;
  [buf, S] = gen_block_(s, inc, Z);
  [idx, xv, acc] = zigg_fields_(buf, Z);
  pos = 1;
  B = numel(buf);
  while filled < n
    if pos > B
      s = S(B, :);
      [buf, S] = gen_block_(s, inc, Z);
      [idx, xv, acc] = zigg_fields_(buf, Z);
      pos = 1;
    end
    if acc(pos)
      j = find(~acc(pos:B), 1);            % end of the accepted run
      if isempty(j)
        stop_ = B;
      else
        stop_ = pos + j - 2;
      end
      ncopy = min(stop_ - pos + 1, n - filled);
      x(filled+1 : filled+ncopy) = xv(pos : pos+ncopy-1);
      filled = filled + ncopy;
      pos = pos + ncopy;
    else
      [val, pos, buf, S, idx, xv, acc, s] = ...
          slow_draw_(pos, buf, S, idx, xv, acc, s, inc, Z);
      filled = filled + 1;
      x(filled) = val;
    end
  end
  s = S(pos - 1, :);                       % state at the last consumed draw
end


function [idx, xv, acc] = zigg_fields_(buf, Z)
%ZIGG_FIELDS_ Vectorized ziggurat fast path fields for a block of uint64s.
  idx = double(bitand(buf, uint64(255)));
  r8 = bitshift(buf, -8);
  sgn = double(bitand(r8, uint64(1)));
  rabs = double(bitand(bitshift(r8, -1), uint64(4503599627370495)));  % 2^52-1
  xv = (rabs .* Z.wi(idx + 1)) .* (1 - 2 * sgn);
  acc = rabs < Z.ki(idx + 1);
end


function [val, pos, buf, S, idx, xv, acc, s] = ...
    slow_draw_(pos, buf, S, idx, xv, acc, s, inc, Z)
%SLOW_DRAW_ Scalar ziggurat rejection loop (numpy random_standard_normal).
%   Consumes uint64s from the block buffer starting at pos, regenerating
%   blocks as needed; the first consumed value is the one the vectorized
%   pass rejected.
  B = numel(buf);
  while true
    [pos, buf, S, idx, xv, acc, s] = ensure_(pos, buf, S, idx, xv, acc, s, inc, Z);
    r = buf(pos);
    i0 = idx(pos);
    xx = xv(pos);
    ok = acc(pos);
    rabs_u = bitand(bitshift(r, -9), uint64(4503599627370495));
    pos = pos + 1;
    if ok
      val = xx;
      return
    end
    if i0 == 0
      while true
        [pos, buf, S, idx, xv, acc, s] = ensure_(pos, buf, S, idx, xv, acc, s, inc, Z);
        u1 = double(bitshift(buf(pos), -11)) * (1.0 / 9007199254740992.0);
        pos = pos + 1;
        [pos, buf, S, idx, xv, acc, s] = ensure_(pos, buf, S, idx, xv, acc, s, inc, Z);
        u2 = double(bitshift(buf(pos), -11)) * (1.0 / 9007199254740992.0);
        pos = pos + 1;
        xt = -Z.nor_inv_r * log1p(-u1);
        yt = -log1p(-u2);
        if yt + yt > xt * xt
          if bitand(bitshift(rabs_u, -8), uint64(1)) == 1
            val = -(Z.nor_r + xt);
          else
            val = Z.nor_r + xt;
          end
          return
        end
      end
    else
      [pos, buf, S, idx, xv, acc, s] = ensure_(pos, buf, S, idx, xv, acc, s, inc, Z);
      u = double(bitshift(buf(pos), -11)) * (1.0 / 9007199254740992.0);
      pos = pos + 1;
      if ((Z.fi(i0) - Z.fi(i0 + 1)) * u + Z.fi(i0 + 1)) < exp(-0.5 * xx * xx)
        val = xx;
        return
      end
    end
  end
end


function [pos, buf, S, idx, xv, acc, s] = ...
    ensure_(pos, buf, S, idx, xv, acc, s, inc, Z)
%ENSURE_ Regenerate the block buffer when it is exhausted.
  if pos > numel(buf)
    s = S(end, :);
    [buf, S] = gen_block_(s, inc, Z);
    [idx, xv, acc] = zigg_fields_(buf, Z);
    pos = 1;
  end
end


% ===== PCG64 (vectorized block advance) ====================================
function [buf, S] = gen_block_(s, inc, Z)
%GEN_BLOCK_ Next Z.B outputs of the PCG64 XSL-RR stream from state s.
%   S(i,:) is the 128-bit LCG state (base-2^16 limbs) after producing
%   buf(i); buf is a Z.B x 1 uint64 column.
  V = mul_blk_(Z.Api, s);                  % A^i * s0        (mod 2^128)
  W = mul_blk_(Z.Ti, inc);                 % (sum A^j) * inc (mod 2^128)
  S = V + W;                               % limb sums < 2^17: carry below
  carry = zeros(Z.B, 1);
  for k = 1:8
    t = S(:, k) + carry;
    S(:, k) = mod(t, 65536);
    carry = floor(t / 65536);
  end
  lo = uint64(S(:, 1)) + bitshift(uint64(S(:, 2)), 16) + ...
       bitshift(uint64(S(:, 3)), 32) + bitshift(uint64(S(:, 4)), 48);
  hi = uint64(S(:, 5)) + bitshift(uint64(S(:, 6)), 16) + ...
       bitshift(uint64(S(:, 7)), 32) + bitshift(uint64(S(:, 8)), 48);
  xo = bitxor(hi, lo);
  rot = floor(S(:, 8) / 1024);             % top 6 bits of the 128-bit state
  buf = bitor(bitshift(xo, -rot), bitshift(xo, 64 - rot));
end


function P = mul_blk_(M, v)
%MUL_BLK_ Row-wise 128-bit multiply (mod 2^128) of limb matrix M by limb row v.
%   Exact: limb products summed per output limb stay < 2^36 in doubles.
  T8 = zeros(8, 8);
  for i = 1:8
    T8(i, i:8) = v(1:9 - i);
  end
  P = M * T8;
  carry = zeros(size(M, 1), 1);
  for k = 1:8
    t = P(:, k) + carry;
    P(:, k) = mod(t, 65536);
    carry = floor(t / 65536);
  end
end


% ===== seeding (SeedSequence + PCG64 init) =================================
function [st, inc] = pcg_seed_(seed, Z)
%PCG_SEED_ numpy SeedSequence(seed) -> PCG64 seeding (limb representation).
  w = seedseq_generate_(seed);             % 8 x uint32 words (as doubles)
  % out[i] = w(2i-1) | w(2i)<<32; initstate = out1<<64 | out2, initseq = out3<<64 | out4
  u64limbs = @(low, high) [mod(low, 65536), floor(low / 65536), ...
                           mod(high, 65536), floor(high / 65536)];
  initstate = [u64limbs(w(3), w(4)), u64limbs(w(1), w(2))];
  initseq   = [u64limbs(w(7), w(8)), u64limbs(w(5), w(6))];
  % inc = (initseq << 1) | 1  (mod 2^128)
  inc = zeros(1, 8);
  c = 0;
  for k = 1:8
    t = initseq(k) * 2 + c;
    inc(k) = mod(t, 65536);
    c = floor(t / 65536);
  end
  inc(1) = inc(1) + 1;                     % bit 0 (inc(1) was even)
  % state = 0; step; state += initstate; step
  st = zeros(1, 8);
  st = step_(st, inc, Z);                  % = inc
  st = add128_(st, initstate);
  st = step_(st, inc, Z);
end


function s = step_(s, inc, Z)
  s = add128_(mul128_(s, Z.A), inc);
end


function c = mul128_(a, b)
%MUL128_ Scalar 128-bit multiply mod 2^128 on base-2^16 limb rows (exact).
  f = conv(a, b);                          % 15 limbs of partial sums < 2^36
  c = zeros(1, 8);
  carry = 0;
  for k = 1:8
    t = f(k) + carry;
    c(k) = mod(t, 65536);
    carry = floor(t / 65536);
  end
end


function c = add128_(a, b)
  c = zeros(1, 8);
  carry = 0;
  for k = 1:8
    t = a(k) + b(k) + carry;
    c(k) = mod(t, 65536);
    carry = floor(t / 65536);
  end
end


function w = seedseq_generate_(entropy)
%SEEDSEQ_GENERATE_ numpy SeedSequence(entropy).generate_state(4, uint64)
%   returned as 8 uint32 words (doubles); entropy < 2^64 non-negative int.
  INIT_A = 1135663077;   MULT_A = 2468251765;   % 0x43b0d7e5, 0x931e8875
  INIT_B = 2337405405;   MULT_B = 1492356589;   % 0x8b51f9dd, 0x58f38ded
  MIX_L  = 3389127133;   MIX_R  = 1232336661;   % 0xca01f9dd, 0x4973f715
  two32 = 4294967296;

  ent = [mod(entropy, two32), floor(entropy / two32)];
  if ent(2) > 0
    nent = 2;
  else
    nent = 1;
  end

  hc = INIT_A;
  pool = zeros(1, 4);
  for i = 1:4
    if i <= nent
      v = ent(i);
    else
      v = 0;
    end
    [pool(i), hc] = hashmix_(v, hc, MULT_A);
  end
  for i_src = 1:4
    for i_dst = 1:4
      if i_src ~= i_dst
        [hv, hc] = hashmix_(pool(i_src), hc, MULT_A);
        m = mod(mul32_(MIX_L, pool(i_dst)) - mul32_(MIX_R, hv), two32);
        pool(i_dst) = bitxor(m, floor(m / 65536));
      end
    end
  end

  hb = INIT_B;
  w = zeros(1, 8);
  for i = 1:8
    v = pool(mod(i - 1, 4) + 1);
    v = bitxor(v, hb);
    hb = mul32_(hb, MULT_B);
    v = mul32_(v, hb);
    w(i) = bitxor(v, floor(v / 65536));
  end
end


function [v, hc] = hashmix_(v, hc, MULT_A)
  v = bitxor(v, hc);
  hc = mul32_(hc, MULT_A);
  v = mul32_(v, hc);
  v = bitxor(v, floor(v / 65536));
end


function c = mul32_(a, b)
%MUL32_ Exact multiply mod 2^32 of two uint32 values held in doubles.
  a0 = mod(a, 65536);
  a1 = floor(a / 65536);
  c = mod(a0 * b + mod(a1 * b, 65536) * 65536, 4294967296);
end


% ===== constant tables =====================================================
function Z = init_tables_()
%INIT_TABLES_ Ziggurat tables (parsed from ziggurat_constants.h) + PCG64
%   block-advance constants A^i and T_i = sum_{j<i} A^j for i = 1..B.
  d = fileparts(mfilename('fullpath'));
  txt = fileread(fullfile(d, 'ziggurat_constants.h'));

  Z.ki = parse_hex_array_(txt, 'ki_double');           % < 2^53: exact doubles
  Z.wi = parse_dbl_array_(txt, 'wi_double');
  Z.fi = parse_dbl_array_(txt, 'fi_double');
  if numel(Z.ki) ~= 256 || numel(Z.wi) ~= 256 || numel(Z.fi) ~= 256
    error('np_rng_m:tables', 'failed to parse ziggurat_constants.h');
  end
  Z.nor_r = parse_scalar_(txt, 'ziggurat_nor_r');
  Z.nor_inv_r = parse_scalar_(txt, 'ziggurat_nor_inv_r');

  % PCG64 multiplier (2549297995355413924 << 64) | 4865540595714422341, i.e.
  % 0x2360ed051fc65da44385df649fccf645, as base-2^16 limbs (the 64-bit
  % halves are NOT exactly representable as doubles, so limbs are literal):
  Z.A = [63045, 40908, 57188, 17285, 23972, 8134, 60677, 9056];

  Z.B = 4096;
  Z.Api = zeros(Z.B, 8);                   % A^i
  Z.Ti = zeros(Z.B, 8);                    % 1 + A + ... + A^(i-1)
  api = Z.A;
  ti = [1, zeros(1, 7)];
  for i = 1:Z.B
    Z.Api(i, :) = api;
    Z.Ti(i, :) = ti;
    if i < Z.B
      ti = add128_(ti, api);
      api = mul128_(api, Z.A);
    end
  end
end


function a = parse_hex_array_(txt, name)
  seg = regexp(txt, [name '\[\]\s*=\s*\{([^}]*)\}'], 'tokens', 'once');
  toks = regexp(seg{1}, '0[xX]([0-9A-Fa-f]+)ULL', 'tokens');
  a = zeros(numel(toks), 1);
  for i = 1:numel(toks)
    a(i) = hex2dec(toks{i}{1});
  end
end


function a = parse_dbl_array_(txt, name)
  seg = regexp(txt, [name '\[\]\s*=\s*\{([^}]*)\}'], 'tokens', 'once');
  a = sscanf(strrep(seg{1}, ',', ' '), '%f');
  a = a(:);
end


function v = parse_scalar_(txt, name)
  tok = regexp(txt, [name '\s*=\s*([0-9.eE+-]+)\s*;'], 'tokens', 'once');
  v = str2double(tok{1});
end
