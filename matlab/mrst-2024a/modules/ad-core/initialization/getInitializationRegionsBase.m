function region = getInitializationRegionsBase(model, rho, contacts, varargin)
%Undocumented Utility Function

%{
Copyright 2009-2024 SINTEF Digital, Mathematics & Cybernetics.

This file is part of The MATLAB Reservoir Simulation Toolbox (MRST).

MRST is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

MRST is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with MRST.  If not, see <http://www.gnu.org/licenses/>.
%}

    nph = sum(model.getActivePhases());
    
    assert(numel(contacts) == nph-1);

    region = struct('datum_pressure',  1*atm, ...
                    'datum_depth',     0, ...
                    'reference_index', model.water+1, ...
                    'cells',           (1:model.G.cells.num)', ...
                    'rho',             {rho}, ...
                    'contacts',        contacts, ...
                    'saturation_region', 1, ...
                    'pvt_region',      1, ...
                    'pc_sign',         ones(1, nph), ...
                    'pc_functions',    {{}}, ...
                    'pc_scale',        ones(1, nph), ...
                    'contacts_pc',     zeros(1, nph-1), ...
                    's_max',           ones(1, nph), ...
                    's_min',           zeros(1, nph) ...
                );
    region = merge_options(region, varargin{:});
    assert(isscalar(region.datum_depth));
    assert(isscalar(region.datum_pressure));
    assert(numel(region.contacts_pc) == numel(contacts));
end