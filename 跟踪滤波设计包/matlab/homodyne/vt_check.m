function e = vt_check(cid, label, ok, detail)
%VT_CHECK Print a [PASS]/[FAIL] line and return the check record.
  ok = logical(ok);
  if ok, tag = 'PASS'; else, tag = 'FAIL'; end
  fprintf('  [%s] %s  %s  (%s)\n', tag, cid, label, detail);
  e = struct('cid', cid, 'label', label, 'ok', ok, 'detail', detail);
end
