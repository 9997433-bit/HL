function rc = plot_scenario_results(mat_path, out_dir)
%PLOT_SCENARIO_RESULTS Key figures from the realistic-scenario study results.
%   rc = plot_scenario_results()                    default paths (see below)
%   rc = plot_scenario_results(mat_path)            explicit results file
%   rc = plot_scenario_results(mat_path, out_dir)   explicit output folder
%
%   Reads results_realistic_scenarios.mat (written by
%   matlab/validate_realistic_scenarios.m -- schema documented in that
%   file's help text) and generates four figures, each saved as both .fig
%   and .png under OUT_DIR (default matlab/scenario_study/figs/):
%
%     fig1_homodyne_operating_map   untracked Doppler phase heatmap over the
%                                   (vibration frequency x peak velocity)
%                                   plane, auto-selected gear, guard contour
%     fig2_homodyne_band_map        which gear (SLOW/MEDIUM/FAST) the
%                                   guard-first rule picks on the same plane
%     fig3_speckle_tradeoff         QTec joint deep-fade probability vs
%                                   channel count M: theory p^M + Monte-Carlo
%     fig4_heterodyne_bathtub       per-gear trackable-velocity bathtub
%                                   v_pll_limit(f) + IF window / alias limits
%
%   Default MAT_PATH search order: <this folder>/results_realistic_scenarios.mat,
%   then <this folder>/../results_realistic_scenarios.mat.
%   Figure text is ASCII/English on purpose (GBK consoles + headless gnuplot
%   render it reliably); the Chinese walk-through lives in
%   matlab/RUN_ON_WINDOWS.md.
%
%   Works on MATLAB R2020b+ and GNU Octave >= 8, no toolboxes.  Returns
%   rc = 0 iff all four figures were written.
  here = fileparts(mfilename('fullpath'));
  if nargin < 1 || isempty(mat_path)
    cand = {fullfile(here, 'results_realistic_scenarios.mat'), ...
            fullfile(here, '..', 'results_realistic_scenarios.mat')};
    mat_path = '';
    for i = 1:numel(cand)
      if exist(cand{i}, 'file') == 2
        mat_path = cand{i};
        break
      end
    end
    if isempty(mat_path)
      error(['plot_scenario_results: results_realistic_scenarios.mat not ' ...
             'found.\nRun this first (from matlab/):  ' ...
             'validate_realistic_scenarios']);
    end
  end
  if nargin < 2 || isempty(out_dir)
    out_dir = fullfile(here, 'figs');
  end
  if ~exist(out_dir, 'dir')
    mkdir(out_dir);
  end
  R = load(mat_path);
  fprintf('plot_scenario_results: loaded %s\n', mat_path);
  if isfield(R, 'is_stub') && R.is_stub
    fprintf(['  NOTE: results were produced by the STUB validator ' ...
             '(design-formula placeholder data).\n']);
  end

  % Headless Octave (no display, e.g. CI on Linux): draw off-screen.  On
  % Windows / desktop MATLAB the figures stay visible for interactive use.
  vis = 'on';
  if exist('OCTAVE_VERSION', 'builtin') ~= 0 && ~ispc() && ...
     isempty(getenv('DISPLAY'))
    vis = 'off';
  end

  nfail = 0;

  % -- fig 1: homodyne operating map heatmap ----------------------------------
  need1 = {'map_f_hz', 'map_v_mps', 'map_phi_err_rad', 'map_phi_guard_rad'};
  if has_fields(R, need1, 'fig1_homodyne_operating_map')
    fh = figure('Visible', vis, 'Name', 'homodyne operating map');
    pcolor(R.map_f_hz, R.map_v_mps, log10(R.map_phi_err_rad));
    shading flat;
    set(gca, 'XScale', 'log', 'YScale', 'log');
    cb = colorbar();
    ylabel(cb, 'log10 phase error [rad]');
    hold on;
    contour(R.map_f_hz, R.map_v_mps, R.map_phi_err_rad, ...
            R.map_phi_guard_rad * [1 1], 'w--', 'LineWidth', 2);
    hold off;
    xlabel('vibration frequency f [Hz]');
    ylabel('peak velocity v [m/s]');
    title(sprintf('Homodyne untracked phase, auto gear (dash = %.0f rad guard)', ...
                  R.map_phi_guard_rad));
    nfail = nfail + save_both(fh, out_dir, 'fig1_homodyne_operating_map');
  else
    nfail = nfail + 1;
  end

  % -- fig 2: homodyne gear-selection map --------------------------------------
  need2 = {'map_f_hz', 'map_v_mps', 'map_band_idx', 'map_band_order'};
  if has_fields(R, need2, 'fig2_homodyne_band_map')
    fh = figure('Visible', vis, 'Name', 'homodyne band map');
    pcolor(R.map_f_hz, R.map_v_mps, R.map_band_idx);
    shading flat;
    set(gca, 'XScale', 'log', 'YScale', 'log');
    colormap(gca, [0.22 0.49 0.72; 0.99 0.75 0.29; 0.84 0.24 0.24]);
    caxis([0.5 3.5]);
    cb = colorbar();
    set(cb, 'YTick', 1:3, 'YTickLabel', R.map_band_order);
    xlabel('vibration frequency f [Hz]');
    ylabel('peak velocity v [m/s]');
    title('Homodyne gear map: guard-first selection over (f, v)');
    nfail = nfail + save_both(fh, out_dir, 'fig2_homodyne_band_map');
  else
    nfail = nfail + 1;
  end

  % -- fig 3: QTec speckle-diversity tradeoff ----------------------------------
  need3 = {'spk_M', 'spk_F', 'spk_p_theory', 'spk_p_mc'};
  if has_fields(R, need3, 'fig3_speckle_tradeoff')
    fh = figure('Visible', vis, 'Name', 'speckle diversity tradeoff');
    cols = [0.22 0.49 0.72; 0.84 0.24 0.24; 0.30 0.60 0.30];
    leg = {};
    hold on;
    for kf = 1:numel(R.spk_F)
      c = cols(1 + mod(kf - 1, size(cols, 1)), :);
      semilogy(R.spk_M, R.spk_p_theory(kf, :), '-', 'Color', c, ...
               'LineWidth', 1.5);
      leg{end + 1} = sprintf('theory (1-e^{-F})^M, F=%.3g', R.spk_F(kf)); %#ok<AGROW>
      % log scale cannot show p = 0 (finite MC saw no joint fade): drop them
      pos = isfinite(R.spk_p_mc(kf, :)) & R.spk_p_mc(kf, :) > 0;
      if any(pos)
        semilogy(R.spk_M(pos), R.spk_p_mc(kf, pos), 'o', ...
                 'Color', c, 'MarkerSize', 7, 'LineWidth', 1.5);
        leg{end + 1} = sprintf('Monte-Carlo, F=%.3g', R.spk_F(kf)); %#ok<AGROW>
      end
    end
    hold off;
    set(gca, 'YScale', 'log');
    grid on;
    xlabel('number of independent speckle channels M');
    ylabel('joint deep-fade probability');
    title('QTec diversity: joint fade prob. vs M (fade: I < F <I>)');
    legend(leg, 'Location', 'southwest');
    nfail = nfail + save_both(fh, out_dir, 'fig3_speckle_tradeoff');
  else
    nfail = nfail + 1;
  end

  % -- fig 4: heterodyne velocity bathtub ---------------------------------------
  need4 = {'bath_f_hz', 'bath_v_pll_mps', 'bath_fn_hz', 'bath_gear_order', ...
           'bath_v_if_mps', 'bath_v_alias_mps'};
  if has_fields(R, need4, 'fig4_heterodyne_bathtub')
    fh = figure('Visible', vis, 'Name', 'heterodyne bathtub');
    cols = [0.22 0.49 0.72; 0.99 0.60 0.20; 0.84 0.24 0.24];
    leg = {};
    hold on;
    for ig = 1:size(R.bath_v_pll_mps, 1)
      c = cols(1 + mod(ig - 1, size(cols, 1)), :);
      loglog(R.bath_f_hz, R.bath_v_pll_mps(ig, :), '-', 'Color', c, ...
             'LineWidth', 1.5);
      leg{end + 1} = sprintf('%s  (fn = %.3g kHz)', ...
          R.bath_gear_order{ig}, R.bath_fn_hz(ig) / 1e3); %#ok<AGROW>
    end
    fx = [min(R.bath_f_hz), max(R.bath_f_hz)];
    loglog(fx, R.bath_v_if_mps * [1 1], 'k--', 'LineWidth', 1.2);
    leg{end + 1} = 'IF hard window limit';
    loglog(fx, R.bath_v_alias_mps * [1 1], 'k:', 'LineWidth', 1.2);
    leg{end + 1} = 'sampling alias limit';
    hold off;
    set(gca, 'XScale', 'log', 'YScale', 'log');
    grid on;
    xlabel('vibration frequency f [Hz]');
    ylabel('trackable peak velocity [m/s]');
    title('Heterodyne bathtub: PLL velocity limit per gear (valley at f = fn)');
    legend(leg, 'Location', 'northwest');
    nfail = nfail + save_both(fh, out_dir, 'fig4_heterodyne_bathtub');
  else
    nfail = nfail + 1;
  end

  rc = double(nfail ~= 0);
  if rc == 0
    fprintf('plot_scenario_results: 4 figures written to %s\n', out_dir);
  else
    fprintf('plot_scenario_results: %d figure(s) FAILED or skipped\n', nfail);
  end
end


function tf = has_fields(R, names, figname)
%HAS_FIELDS True iff all NAMES are fields of R; else warn once and skip.
  miss = names(~isfield(R, names));
  tf = isempty(miss);
  if ~tf
    warning('plot_scenario_results:missingField', ...
            '%s skipped -- missing field(s): %s', figname, ...
            strjoin(miss, ', '));
  end
end


function bad = save_both(fh, out_dir, stem)
%SAVE_BOTH Write FH as <stem>.png (150 dpi) and <stem>.fig; return 0 iff ok.
  bad = 0;
  fpng = fullfile(out_dir, [stem '.png']);
  try
    print(fh, fpng, '-dpng', '-r150');
    fprintf('  wrote %s\n', fpng);
  catch err
    fprintf('  FAILED to write %s: %s\n', fpng, err.message);
    bad = 1;
  end
  ffig = fullfile(out_dir, [stem '.fig']);
  try
    savefig(fh, ffig);
    fprintf('  wrote %s\n', ffig);
  catch err
    % Octave-only environments without savefig support still get the .png.
    fprintf('  WARNING: .fig not written (%s): %s\n', ffig, err.message);
  end
end
