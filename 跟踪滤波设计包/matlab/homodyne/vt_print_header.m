function vt_print_header(title)
%VT_PRINT_HEADER Section header like validate_tracking.print_header.
  fprintf('\n%s\n', repmat('=', 1, 86));
  fprintf('%s\n', title);
  fprintf('%s\n', repmat('=', 1, 86));
end
