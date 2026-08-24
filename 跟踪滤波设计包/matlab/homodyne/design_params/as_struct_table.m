function T = as_struct_table()
%AS_STRUCT_TABLE Code-ready parameter table (band name -> band_specs struct).
%   T = as_struct_table()   Faithful port of design_params.py as_struct_table.
  C = homodyne_constants();
  T = struct();
  for i = 1:numel(C.ORDER)
    T.(C.ORDER{i}) = band_specs(C.ORDER{i});
  end
end
