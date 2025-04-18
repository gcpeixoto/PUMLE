% co2lab3DPUMLE
%
% Base script to run CO2 injection simulations from 
% preset values defined in PUMLE configuration file.
%
% This script is based on MRST::co2lab-ve::synthetic3DExample.m. 
% and prepared to run the TwoPhaseWaterGasModel for modelling a
% CO2-H2O system. CO2 is injected into a brine filled 3D reservoir.
% The injection and migration times are controlled by user in the
% simulation setup. CO2 properties are taken from co2lab's tabulated 
% co2props(). Brine properties are from literature.
%
% Adaption made by Gustavo Oliveira
% TRIL Lab | CI-UFPB | Brazil

function co2lab3DPUMLE(varargin)
    % Disable warnings for a clean command line output
    warning('off', 'all');
    
    %% Expected parameter files and logging with prefix
    param_names = {'Paths', 'PreProcessing', 'Grid', 'Fluid', ...
                   'InitialConditions', 'BoundaryConditions', 'Wells', ...
                   'Schedule', 'EXECUTION', 'SimNums'};
    fprintf('[EXECUTION] Starting co2lab3DPUMLE simulation...\n');
    % fprintf('[EXECUTION] Number of input parameter files: %d\n', nargin);

    if nargin ~= numel(param_names)
        error('[EXECUTION] Usage: co2lab3DPUMLE(param1, param2, ..., paramN) with all required parameter files.');
    end

    % Load parameter files into structure PARAMS with logging and verification
    % fprintf('[EXECUTION] Loading parameter files:\n');
    PARAMS = struct();
    for s = 1:length(param_names)
        % fprintf('[EXECUTION]  Loading %s...\n', param_names{s});
        temp = load(varargin{s});
        if isempty(temp)
            error('[EXECUTION] Parameter file for %s is empty.', param_names{s});
        end
        % Log type and size of the loaded parameter structure
        % fprintf('[EXECUTION]  Parameter %s: type: %s, size: %s\n', ...
        %    param_names{s}, class(temp), mat2str(size(temp)));
        PARAMS.(param_names{s}) = temp;
    end
    % fprintf('[EXECUTION] All parameter files loaded successfully.\n');

    %% Sanity Checks on Parameters
    requiredFields.Paths             = {'PUMLE_ROOT', 'PUMLE_RESULTS'};
    requiredFields.PreProcessing     = {'case_name'};
    requiredFields.Grid              = {'file_path', 'repair_flag'}; 
    requiredFields.Fluid             = {'pres_ref', 'temp_ref', 'rho_h2o', 'XNaCl', 'srw', 'src', 'pe', 'cp_rock'};
    requiredFields.InitialConditions = {'sw_0'};
    requiredFields.BoundaryConditions = {'type'};
    requiredFields.Wells             = {'CO2_inj'};
    requiredFields.Schedule          = {'injection_timesteps', 'migration_timesteps', 'injection_time', 'migration_time'};
    requiredFields.EXECUTION         = {'mrst_root', 'octave'};
    requiredFields.SimNums           = {'sim_id'};

    % fprintf('[EXECUTION] Performing additional sanity checks on parameters...\n');
    fnames = fieldnames(requiredFields);
    for i = 1:length(fnames)
        curParam = fnames{i};
        if ~isfield(PARAMS, curParam)
            error('[EXECUTION] Missing parameter file: %s', curParam);
        end
        fieldsNeeded = requiredFields.(curParam);
        for j = 1:length(fieldsNeeded)
            if ~isfield(PARAMS.(curParam), fieldsNeeded{j})
                error('[EXECUTION] Missing field "%s" in parameter file %s', fieldsNeeded{j}, curParam);
            end
        end
    end

    simId = num2str(PARAMS.SimNums.sim_id);
    simHash = PARAMS.SimNums.sim_hash;

    % fprintf('[EXECUTION] Parameter sanity checks passed.\n');

    % Check if grid file exists
    if ~ischar(PARAMS.Grid.file_path) || exist(PARAMS.Grid.file_path, 'file') ~= 2
        error('[EXECUTION] Grid file_path "%s" does not exist or is not a valid file.', PARAMS.Grid.file_path);
    end

    %% MRST Startup and Module Loading with logging
    % fprintf('[EXECUTION] Running MRST startup...\n');
    startupFile = fullfile(PARAMS.EXECUTION.mrst_root, 'startup.m');
    if exist(startupFile, 'file') ~= 2
        error('[EXECUTION] Startup file %s not found. Check your MRST installation.', startupFile);
    end
    run(startupFile);
    % fprintf('[EXECUTION] MRST startup completed.\n');

    % fprintf('[EXECUTION] Adding modules...\n');
    mrstPath('add', 'octave', '/home/luiz/Downloads/mrst-2024b/modules/octave');
    mrstModule('add', 'co2lab', 'ad-core', 'ad-props', 'ad-blackoil', 'octave');
    mrstVerbose off;
    % fprintf('[EXECUTION] Modules added successfully.\n');

    %% Grid and Rock Model Setup with logging
    % fprintf('[EXECUTION] Reading grid file: %s\n', PARAMS.Grid.file_path);
    grdecl = readGRDECL(PARAMS.Grid.file_path);

    % Convert units to metric
    usys = getUnitSystem('METRIC');
    grdecl = convertInputUnits(grdecl, usys);

    % Handle repair flag
    if strcmpi(PARAMS.Grid.repair_flag, 'true')
        PARAMS.Grid.repair_flag = true;
    else
        PARAMS.Grid.repair_flag = false;
    end

    % Remove fault data to avoid regex issues
    if isfield(grdecl, 'FAULTS')
        grdecl = rmfield(grdecl, 'FAULTS');
    end
    if isfield(grdecl, 'faultdata')
        grdecl = rmfield(grdecl, 'faultdata');
    end

    % Process grid with fault processing disabled
    G = processGRDECL(grdecl, 'RepairZCORN', PARAMS.Grid.repair_flag, ...
                      'Verbose', false, 'processFaults', false);
    G = computeGeometry(G);
    % fprintf('[EXECUTION] Grid processed: %d cells; Cartesian dimensions:\n', G.cells.num);
    % disp(G.cartDims);

    rock = grdecl2Rock(grdecl, G.cells.indexMap);

    % Adjust rock properties and log
    rock.poro(rock.poro < min(rock.poro(rock.poro > 0))) = 1e-3;
    if isfield(rock, 'ntg')
        rock.ntg(rock.ntg < min(rock.ntg(rock.ntg > 0))) = 1e-3;
    end
    % fprintf('[EXECUTION] Rock model fields:\n');
    % disp(fieldnames(rock));

    %% Trap Analysis with logging
    % fprintf('[EXECUTION] Performing trap analysis...\n');
    [Gt, ~] = topSurfaceGrid(G);
    trapSt = trapAnalysis(Gt, false);
    trap_volume = volumesOfTraps(Gt, trapSt, unique(trapSt.traps(trapSt.traps > 0)));
    % fprintf('[EXECUTION] Trap analysis completed. Number of traps: %d\n', numel(unique(trapSt.traps(trapSt.traps > 0))));
     %% Fluid model

    %{

    ------------------------------
    REFERENCE FOR FLUID PROPERTIES
    ------------------------------

    PRESSURE (p):
        Namorado depth range: [2881.20, 3356.3] m => Average depth = h_ave = 3090.20 m
        p @h_ave: P = 0.1 [MPa] + 10 [MPa/km] x 3.902 [km] = 39.12 MPa
        p-range: [28.91, 33.46] MPa

    TEMPERATURE (T):
        T @(h_ave): T = 4 [ºC] + 23.36 [ºC/km] x 3.902 [km] = 95.15 [ºC] =
        368.30 [ºK]


    Background:


    We use information provided in Ciotta's [R1] dissertation, pp. 139-140
    to estimate density, pressure and temperature for CO2 in reservoir
    conditions. The modeling is applied to Santos Basin, but with data from
    Campos Basin and suitable for the Namorado model.

    - CO2 density: determined by (Duan, 1992) based on pressure and temperature
    - Temperature: same as (Rockett, 2010)
    
        T(h) = Tref(h0) + (h-h0) x G, where 
        
            T: temperature
            Tref: seabed temperature (~ 4 °C) => h0 = 0
            G: Campos Basin geothermal gradient (~ 23.36 ºC / km) 
            h: depth

    - Hydrostatic pressure: same as (Rockett, 2010)

        p(h) = pref(h0) + (h-h0) x P, where

            p: pressure 
            pref: reference pressure 
            P: hydrostatic pressure gradient (~ 100 bar/km = 10 MPa/km) 
            h: depth
            
    [R1]: Ciotta, M. Estudo De Possibilidades Para Armazenar CO2 em  Reservatórios Geológicos Offshore Na Bacia De Santos, 2019, University of
    São Paulo


    CO2 critical point
    ------------------ 

    - Critical temperature: 31.0 °C (304.15 K)
    - Critical pressure: 7.38 MPa (or 73.8 bar)


    Others
    ------

    1 atm = 0.101325 MPa (atmospheric pressure, if reference)
    1 bar = 10^5 Pa = 0.1 MPa ~ 0.987 atm

    %}

    %% Fluid Model Setup with logging
    % fprintf('[EXECUTION] Setting up fluid model...\n');
    P_r = PARAMS.Fluid.pres_ref;
    if ~isnumeric(P_r) || P_r <= 0
        error('[EXECUTION] Reference pressure (pres_ref) must be a positive number.');
    end
    % fprintf('[EXECUTION] Reference pressure: %.2f MPa (type: %s)\n', P_r, class(P_r));
    T_r = PARAMS.Fluid.temp_ref;
    if ~isnumeric(T_r)
        error('[EXECUTION] Reference temperature (temp_ref) must be numeric.');
    end
    % fprintf('[EXECUTION] Reference temperature: %.2f ºC\n', T_r);

    %% Brine saturation

    %{

    ---------------------------
    REFERENCE FOR BRINE DENSITY
    ---------------------------

    Brine density is computed through interpolation between pure water (H20)
    and pure sodium chloride (NaCl) densities by using mass fractions:

        \rho_w = \rho_{H20} X_{H20} + \rho_{NaCl,liquid} X_{NaCl,liquid}, where

            \rho_i: phase density for phase i [kg/m3]
            X_i: mass fraction for phase i [ ]


    Pure liquid NaCl density is obtained from correlations after (Dreisner, 2007)
    Eqs. (4) - (6):



            \rho_{NaCl,liquid} = \frac{\rho_{NaCl,liquid}^0}{1 - 0.1 \log(1 + 10P
            c_{NaCl,liquid})}, where 

                P: pressure
                \rho_{NaCl,liquid}^0}: reference density at 1 bar [kg/m3]
                c_{NaCl,liquid}: compressibility [1/bar]

    It follows that:

    \rho_{NaCl,liquid}^0} = \frac{m_0}{m_1 + m_2T + m_3T^2}
    c_{NaCl,liquid} = m_4 + m_5T,

    where 
        
                T: temperature [C]
                m_0: 58443
                m_1: 23.772
                m_2: 0.018639
                m_3: -1.9687e-6
                m_4: -1.5259e-5
                m_5: 5.5058e-8



    (Driesner, 2007): DOI: 10.1016/j.gca.2007.05.026

    Furthermore, we assume that, for pure water, 1000 [kg/m3], and for 
    Campos Basin, X_{NaCl,liquid} may vary from 1% to 20% [0.01 to 0.20].


    Note: Driesner formula is originally replicated from 
    "Tödheide K. (1980) The influence of density and temperature on
    the properties of pure molten salts. Angew. Chem. Int. Ed. Engl.
    19, 606–619."


    -----------------------------
    REFERENCE FOR BRINE VISCOSITY
    -----------------------------

    To compute the brine viscosity, we use the (Mao & Duan, 2009) model and a
    few steps.

    Mao & Duan expounded: "the viscosity of aqueous electrolyte solutions depends 
    strongly on temperature, less on salinity, and is much less dependent
    on pressure."

    The following procedure depends only on the brine saturation:

    1. Given the brine density [kg/m3] and brine mass fraction (saturation)
    [%], compute the molality (m) [mol/kg] as:

    m = \frac{ 1000 X_{NaCl} }{ M_{NaCl} (1 - X_{NaCl})}

    where M_{\text{NaCl}} is the molar mass of NaCl (58.44 g/mol).


    2. Compute the water viscosity

    \log (\mu_{H20}) = \sum_{i=1}^5 d_i T^{i-3} + \sum_{i=6}^{10} d_i \rho_{H2O} T^{i-8}

    3. Compute the relative viscosity:

    \log (\mu_r) = Am + Bm^2 + Cm^3,  \mu_r = \frac{\mu_{brine}}{\mu_{H2O},

    where 

    A = a_0 + a_1T + a_2T^2
    B = b_0 + b_1T + b_2T^2
    C = c_0 + c_1T

    where:
    
            T : temperature [K]
            a0: -0.21319213
            a1: 0.13651589e-2
            a2: -0.12191756e-5
            b0: 0.69161945e-1
            b1: −0.27292263e-3
            b2: 0.20852448e−6
            c0: −0.25988855e−2
            c1: 0.77989227e-5


    (Mao & Duan, 2009): DOI: 10.1007/s10765-009-0646-7
    %}
    gravity on;
    g = gravity;
    % fprintf('[EXECUTION] Gravity vector: '); % disp(g);

    X_NaCl = PARAMS.Fluid.XNaCl;
    X_H2O = 1 - X_NaCl;
    [m0, m1, m2, m3, m4, m5] = deal(58443, 23.772, 0.018639, -1.9687e-6, -1.5259e-5, 5.5058e-8);
    rho_NaCl_0 = m0 / (m1 + m2*T_r + m3*T_r^2);
    c_NaCl     = m4 + m5 * T_r;
    P_b        = 10 * P_r;
    rho_NaCl   = rho_NaCl_0 / (1 - 0.1 * log(1 + 10 * P_b * c_NaCl));
    rho_H2O    = PARAMS.Fluid.rho_h2o;
    rhow       = rho_H2O*X_H2O + rho_NaCl*X_NaCl;
    % fprintf('[EXECUTION] Calculated brine density: %.2f kg/m^3\n', rhow);

    t_ref = T_r + 273.15;
    NaCl_mm = 58.44/1000;
    moly = X_NaCl / (NaCl_mm*(1 - X_NaCl));
    [a0, a1, a2, b0, b1, b2, c0, c1] = deal(-0.21319213, 0.13651589e-2, -0.12191756e-5, ...
                                              0.69161945e-1, -0.27292263e-3, 0.20852448e-6, ...
                                              -0.25988855e-2, 0.77989227e-5);
    A = a0 + a1*t_ref + a2*t_ref^2;
    B = b0 + b1*t_ref + b2*t_ref^2;
    C = c0 + c1*t_ref;
    mu_rel = exp(A*moly + B*moly^2 + C*moly^3);
    mu_H2O = 0;
    d = [0.28853170e7, -0.11072577e5, -0.90834095e1, 0.30925651e-1, -0.27407100e-4, ...
         -0.19283851e7, 0.56216046e4, 0.13827250e2, -0.47609523e-1, 0.35545041e-4];
    for i = 1:5
        mu_H2O = mu_H2O + d(i) * t_ref^(i-3);
    end
    for i = 6:10
        mu_H2O = mu_H2O + d(i) * (rho_H2O/1e3) * t_ref^(i-8);
    end
    mu_H2O = exp(mu_H2O);
    % fprintf('[EXECUTION] Calculated water viscosity: %.4e\n', mu_H2O);

    co2 = CO2props();
    p_ref = P_r * mega * Pascal;
    rhoc = co2.rho(p_ref, t_ref);
    cf_co2 = co2.rhoDP(p_ref, t_ref) / rhoc;
    cf_wat = 0;
    cf_rock = PARAMS.Fluid.cp_rock / barsa;
    muw = mu_rel * mu_H2O;
    muco2 = co2.mu(p_ref, t_ref) * Pascal * second;
    % fprintf('[EXECUTION] Fluid properties computed. CO2 density: %.4e\n', rhoc);

    mrstModule('add', 'ad-props');
    fluid = initSimpleADIFluid('phases', 'WG', ...
                               'mu',  [muw, muco2], ...
                               'rho', [rhow, rhoc], ...
                               'pRef', p_ref, ...
                               'c', [cf_wat, cf_co2], ...
                               'cR', cf_rock, ...
                               'n', [2 2]);
    % fprintf('[EXECUTION] Simple ADI fluid object created.\n');

    srw = PARAMS.Fluid.srw;
    src = PARAMS.Fluid.src;
    fluid.krW = @(s) fluid.krW(max((s - srw)./(1 - srw), 0));
    fluid.krG = @(s) fluid.krG(max((s - src)./(1 - src), 0));
    pe = PARAMS.Fluid.pe * kilo * Pascal;
    pcWG = @(sw) pe * sw.^(-1/2);
    fluid.pcWG = @(sg) pcWG(max((1 - sg - srw)./(1 - srw), 1e-5));

    %% Initial State Setup with logging
    % fprintf('[EXECUTION] Setting initial state...\n');
    initState.pressure = rhow * g(3) * G.cells.centroids(:,3);
    initState.s = repmat([PARAMS.InitialConditions.sw_0, 1 - PARAMS.InitialConditions.sw_0], G.cells.num, 1);
    initState.sGmax = initState.s(:,2);
    % fprintf('[EXECUTION] Initial state: pressure size: %s, saturation size: %s\n', ...
    %   mat2str(size(initState.pressure)), mat2str(size(initState.s)));

    %% Well Selection and Placement with logging
    % fprintf('[EXECUTION] Setting up wells...\n');
    NA1A  = [38 36];
    NA2   = [21 36];
    NA3D  = [44 43];
    RJS19 = [31 27];
    origW = {NA1A, NA2, NA3D, RJS19};
    min_layer = 6;
    max_layer = 12;
    Ind = nan(prod(G.cartDims), 1);
    Ind(G.cells.indexMap) = 1:G.cells.num;
    conv = @(wc, layer) Ind(sub2ind(grdecl.cartDims, wc(1), wc(2), layer));
    cW = cell(1, length(origW));
    for i = 1:length(origW)
        aux = [];
        for k = min_layer:max_layer
            aux = [aux, conv(origW{i}, k)];  %#ok<AGROW>
        end
        cW{i} = aux;
    end
    % fprintf('[EXECUTION] CO2_inj rate: %.4e\n', PARAMS.Wells.CO2_inj);
    % fprintf('[EXECUTION] CO2_inj rate type: %s\n', class(PARAMS.Wells.CO2_inj));
    inj_rate = PARAMS.Wells.CO2_inj * meter^3 / year;
    W = [];
    W = addWell(W, G, rock, cW{1}, ...
                'refDepth', G.cells.centroids(cW{1}, 3), ...
                'type', 'rate', ...
                'val', inj_rate, ...
                'comp_i', [0 1]);

    % fprintf('[EXECUTION] Well configuration completed. Number of wells: %d\n', numel(W));

    %% Boundary Conditions Setup with logging
    % fprintf('[EXECUTION] Setting boundary conditions...\n');
    bc = [];
    vface_ind = (G.faces.normals(:,3) == 0);
    bface_ind = (prod(G.faces.neighbors, 2) == 0);
    bc_face_ix = find(vface_ind & bface_ind);
    bc_cell_ix = sum(G.faces.neighbors(bc_face_ix,:), 2);
    p_face_pressure = initState.pressure(bc_cell_ix);
    bc = addBC(bc, bc_face_ix, PARAMS.BoundaryConditions.type, p_face_pressure, 'sat', [1, 0]);
    % fprintf('[EXECUTION] Boundary conditions set for %d faces.\n', numel(bc_face_ix));

    %% Schedule Setup with logging
    % fprintf('[EXECUTION] Setting simulation schedule...\n');

    steps_injection = PARAMS.Schedule.injection_timesteps;
    steps_migration = PARAMS.Schedule.migration_timesteps;
    dT_injection = PARAMS.Schedule.injection_time * year / steps_injection;
    dT_migration = PARAMS.Schedule.migration_time * year / steps_migration;
    vec_injection = ones(steps_injection, 1) * dT_injection;
    vec_migration = ones(steps_migration, 1) * dT_migration;
    schedule.step.val = [vec_injection; vec_migration];
    schedule.step.control = [ones(steps_injection, 1); ones(steps_migration, 1)*2];
    schedule.control    = struct('W', W, 'bc', bc);
    schedule.control(2) = struct('W', W, 'bc', bc);
    schedule.control(2).W.val = 0;
    % fprintf('[EXECUTION] Schedule set with %d timesteps.\n', numel(schedule.step.val));

    %% Model Setup and Simulation with logging and error handling
    % fprintf('[EXECUTION] Initializing TwoPhaseWaterGasModel...\n');
    model = TwoPhaseWaterGasModel(G, rock, fluid, 0, 0);
    % fprintf('[EXECUTION] Model initialized.\n');

    % Extra logging: print sizes of key arrays before simulation
    % fprintf('[EXECUTION] Before simulation: initState.pressure size: %s, initState.s size: %s\n', ...
    %    mat2str(size(initState.pressure)), mat2str(size(initState.s)));

    % fprintf('[EXECUTION] Starting simulation with simulateScheduleAD...\n');
    try
        [~, states] = simulateScheduleAD(initState, model, schedule);
    catch ME
        % fprintf('[EXECUTION] Error during simulation: %s\n', ME.message);
        rethrow(ME);
    end
    % fprintf('[EXECUTION] Simulation completed successfully.\n');

    %% Visualization (optional)
    %{
    sat_end = states{end}.s(:,2);
    plume_cells = sat_end > 0.05;
    clf; plotGrid(G, 'facecolor', 'none');
    plotGrid(G, plume_cells, 'facecolor', 'red');
    view(35, 35);
    clf; plotToolbar(G, states)
    %}

    %% Save simulation data (JSON) with logging
    % JSON file name
    fname_states = fullfile(PARAMS.Paths.PUMLE_ROOT,...
        PARAMS.Paths.PUMLE_RESULTS,...
        strcat('states_',PARAMS.PreProcessing.case_name, '_', simHash, '.json'));
    
    fname_g = fullfile(PARAMS.Paths.PUMLE_ROOT,...
        PARAMS.Paths.PUMLE_RESULTS,...
        strcat('g_',PARAMS.PreProcessing.case_name, '.json'));
    
    fname_grdecl = fullfile(PARAMS.Paths.PUMLE_ROOT,...
        PARAMS.Paths.PUMLE_RESULTS,...
        strcat('grdecl_',PARAMS.PreProcessing.case_name, '_', simHash, '.json'));
    
    % Encoding
    states_encoded = jsonencode(states);
    g_encoded = jsonencode(G.cartDims);
    grdecl_encoded = jsonencode(grdecl.ACTNUM);
    % fprintf('[EXECUTION] JSON encoding completed.\n');

    % Write to file
    fid = fopen(fname_states,'w');
    % if fid == -1
    %     error('[EXECUTION] Could not open file: %s', fname_states);
    % end
    fprintf(fid,'%s', states_encoded);
    fclose(fid);

    if simId == "1"
        fid = fopen(fname_g,'w');
        % if fid == -1
        %     error('[EXECUTION] Could not open file: %s', fname_g);
        % end
        fprintf(fid,'%s', g_encoded);
        fclose(fid);
    end

    fid = fopen(fname_grdecl,'w');
    % if fid == -1
    %     error('[EXECUTION] Could not open file: %s', fname_grdecl);
    % end
    fprintf(fid,'%s', grdecl_encoded);
    fclose(fid);
    
    % fprintf('[EXECUTION] Simulation data exported to JSON');
    fprintf('[EXECUTION] Simulation completed.\n');
end
