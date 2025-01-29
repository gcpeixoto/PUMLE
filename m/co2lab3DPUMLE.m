%% co2lab3DPUMLE
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

%% Loading structs of input parameters from path

sections = {'Paths','PreProcessing', 'Grid', 'Fluid', ...
    'InitialConditions', 'BoundaryConditions', 'Wells', ...
    'Schedule', 'MATLAB'};

% auxiliary 
aux = @(base) load(fullfile('./',strcat(base,'ParamsPUMLE','.mat')));

 
for s = 1:length(sections), PARAMS.(sections{s}) = aux(sections{s}); end

fprintf('[MATLAB] PUMLE''s .mat files loaded for simulation.\n')


%% General Settings
% Run MRST startup (for command line)
run(fullfile(PARAMS.MATLAB.mrst_root,'startup.m'));

% Load modules
mrstModule add co2lab ad-core ad-props ad-blackoil;
mrstVerbose off

% Case name
case_name = PARAMS.PreProcessing.case_name;

%% Grid and rock models

grdecl = readGRDECL(PARAMS.Grid.file_path);

% SI
usys = getUnitSystem('METRIC');
grdecl = convertInputUnits(grdecl, usys);

% Convert to logical
if strcmp(PARAMS.Grid.repair_flag,'true') || strcmp(PARAMS.Grid.repair_flag,'True')
    PARAMS.Grid.repair_flag = true;
else
    PARAMS.Grid.repair_flag = false;
end

G = processGRDECL(grdecl,'RepairZCORN', PARAMS.Grid.repair_flag);
G = computeGeometry(G);

rock = grdecl2Rock(grdecl, G.cells.indexMap);

% prevents zero poreVolume by setting a residual in cells below the least
% nonzero value
rock.poro(rock.poro < min(rock.poro(rock.poro > 0)) ) = 1e-3;
rock.ntg(rock.ntg < min(rock.ntg(rock.ntg > 0)) ) = 1e-3;

%% Trap Analysis

[Gt,Gaux] = topSurfaceGrid(G);

trapSt = trapAnalysis(Gt,false);
trap_volume = volumesOfTraps(Gt,trapSt,unique(trapSt.traps(trapSt.traps>0)));


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

P_r = PARAMS.Fluid.pres_ref; % reference pressure [MPa]
T_r = PARAMS.Fluid.temp_ref; % reference temperature [º C]

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

% mass fractions for H2O-NaCl binary mixture (brine)
X_NaCl = PARAMS.Fluid.XNaCl;
X_H2O = 1 - X_NaCl; % 


% === Driesner correlation for brine density

% coefficients
[m0, m1, m2, m3, m4, m5] = deal(58443, 23.772, 0.018639, -1.9687e-6, -1.5259e-5, 5.5058e-8);

% formula 
rho_NaCl_0 = m0 / (m1 + m2*T_r + m3*T_r^2);
c_NaCl     = m4 + m5 * T_r;

P_b        = 10*P_r; % pressure [bar];  MPa to bar : 1 MPa = 10 bar
rho_NaCl   = rho_NaCl_0 / ( 1 - 0.1*log(1 + 10*P_b * c_NaCl) ); % salt density
rho_H2O    = PARAMS.Fluid.rho_h2o; % water density [kg/m3]; reference: 1000

rhow       = rho_H2O*X_H2O + rho_NaCl*X_NaCl; % brine density


% ==== Mao & Duan correlation 

t_ref = T_r + 273.15; % reference temperature, in Kelvin

% NaCl molar mass [kg/mol] = [58.44 g/mol / 1e3]
NaCl_mm = 58.44/1000; 

% NaCl molality [mol/kg]
moly = X_NaCl / ( NaCl_mm*(1 - X_NaCl) );


% Coeffiecients
[a0, a1, a2, ...
 b0, b1, b2, ...
 c0, c1] = deal(-0.21319213, 0.13651589e-2, -0.12191756e-5, ... 
     0.69161945e-1, -0.27292263e-3, 0.20852448e-6, ... 
     -0.25988855e-2, 0.77989227e-5);


A = a0 + a1*t_ref + a2*t_ref^2;
B = b0 + b1*t_ref + b2*t_ref^2;
C = c0 + c1*t_ref;

% relative viscosity correlation
mu_rel = exp( A*moly + B*moly^2 + C*moly^3 );

% water viscosity
mu_H2O = 0; 

% coefficients
d = [ 0.28853170e7, -0.11072577e5, -0.90834095e1, 0.30925651e-1, -0.27407100e-4, ...
      -0.19283851e7, 0.56216046e4, 0.13827250e2, -0.47609523e-1, 0.35545041e-4 ];

% summing
for i = 1:5;  mu_H2O = mu_H2O + d(i) * t_ref^(i-3);               end
for i = 6:10; mu_H2O = mu_H2O + d(i) * rho_H2O/1e3 * t_ref^(i-8); end % divided by 1e3 to convert to g/cm3

% correlation
mu_H2O = exp(mu_H2O);


% === Further parameters
co2     = CO2props(); % sampled tables of co2 fluid properties (MRST)
p_ref   = P_r * mega * Pascal; % reference pressure
rhoc    = co2.rho(p_ref, t_ref); % co2 density at ref. press/temp
cf_co2  = co2.rhoDP(p_ref, t_ref) / rhoc; % co2 compressibility
cf_wat  = 0; % brine compressibility (zero)
cf_rock = PARAMS.Fluid.cp_rock / barsa; % rock compressibility
muw     = mu_rel*mu_H2O; % brine viscosity; ref. 8e-4 
muco2   = co2.mu(p_ref, t_ref) * Pascal * second; % co2 viscosity

mrstModule add ad-props; % The module where initSimpleADIFluid is found

% Use function 'initSimpleADIFluid' to make a simple fluid object
fluid = initSimpleADIFluid('phases', 'WG'           , ...
                           'mu'  , [muw, muco2]     , ...
                           'rho' , [rhow, rhoc]     , ...
                           'pRef', p_ref            , ...
                           'c'   , [cf_wat, cf_co2] , ... 
                           'cR'  , cf_rock          , ...                           
                           'n'   , [2 2]);

% Change relperm curves
srw = PARAMS.Fluid.srw;
src = PARAMS.Fluid.src;
fluid.krW = @(s) fluid.krW(max((s-srw)./(1-srw), 0));
fluid.krG = @(s) fluid.krG(max((s-src)./(1-src), 0));

% Add capillary pressure curve
pe = PARAMS.Fluid.pe * kilo * Pascal;
pcWG = @(sw) pe * sw.^(-1/2);
fluid.pcWG = @(sg) pcWG(max((1-sg-srw)./(1-srw), 1e-5)); %@@


%% Initial state

initState.pressure = rhow * g(3) * G.cells.centroids(:,3); % initial pressure
initState.s = repmat([PARAMS.InitialConditions.sw_0, 1 - PARAMS.InitialConditions.sw_0],...
    G.cells.num, 1); % initial saturations
initState.sGmax = initState.s(:,2); % initial max. gas saturation (hysteresis)


%% Well selection

% Original UNISIM-I surface well coordinates
NA1A  = [38 36];
NA2   = [21 36];
NA3D  = [44 43];
RJS19 = [31 27];

origW = {NA1A,NA2,NA3D,RJS19};

% Perforation layering
min_layer = 6;
max_layer = 12;

% reverse mapping
Ind = nan(prod(G.cartDims),1);
Ind(G.cells.indexMap) = 1:G.cells.num;

% convert cartesian well coordinates to cell index in the current grid
conv = @(wc,layer) Ind(sub2ind(grdecl.cartDims,wc(1),wc(2),layer));

cW = cell(1,length(origW));

for i = 1:length(origW)
    aux = [];
    for k = min_layer:max_layer
        aux = [aux, conv(origW{i},k)];
    end
    cW{i} = aux;
end


%% Well placement

% Calculate the injection rate
inj_rate = PARAMS.Wells.CO2_inj * meter^3 / year;

% Start with empty set of wells
W = [];

% Add wells
W = addWell(W, G, rock, cW{1}, ...
            'refDepth', G.cells.centroids(cW{1}, 3), ... % BHP reference depth
            'type', 'rate', ...  % inject at constant rate
            'val', inj_rate, ... % volumetric injection rate
            'comp_i', [0 1]);    % inject CO2, not water


%plotGrid(G, 'facecolor', 'none', 'edgealpha', 0.1);
%plotGrid(G, cW{1}, 'facecolor', 'red');

%% Boundary conditions

% Start with an empty set of boundary faces
bc = [];

% identify all vertical faces
vface_ind = (G.faces.normals(:,3) == 0);

% identify all boundary faces (having only one cell neighbor
bface_ind = (prod(G.faces.neighbors, 2) == 0);

% identify all lateral boundary faces
bc_face_ix = find(vface_ind & bface_ind);

% identify cells neighbouring lateral boundary baces
bc_cell_ix = sum(G.faces.neighbors(bc_face_ix,:), 2);

% lateral boundary face pressure equals pressure of corresponding cell
p_face_pressure = initState.pressure(bc_cell_ix); 

% Add hydrostatic pressure conditions to open boundary faces
bc = addBC(bc, bc_face_ix, PARAMS.BoundaryConditions.type, ...
    p_face_pressure, 'sat', [1, 0]);


%% Schedule

% Setting up two copies of the well and boundary specifications. 
% Modifying the well in the second copy to have a zero flow rate.
schedule.control    = struct('W', W, 'bc', bc);
schedule.control(2) = struct('W', W, 'bc', bc);
schedule.control(2).W.val = 0;

% dT = rampupTimesteps(PARAMS.Schedule.injection_time * year, ...
%     PARAMS.Schedule.injection_timestep_rampup * year);  % injection with increasing timestep size
% 
% schedule.step.val = [dT; ... 
%                     repmat(PARAMS.Schedule.migration_time * year, ...
%                     PARAMS.Schedule.migration_timestep, 1)]; % post injection
% 
% % Specifying which control to use for each timestep.
% schedule.step.control = [ones(numel(dT), 1); ones(PARAMS.Schedule.migration_timestep,1)*2];

% Sets uniform time steps for injection and post-injection
steps_injection = PARAMS.Schedule.injection_timesteps;
steps_migration = PARAMS.Schedule.migration_timesteps;


dT_injection = PARAMS.Schedule.injection_time * year / ... 
               steps_injection;
               
dT_migration = PARAMS.Schedule.migration_time * year / ... 
               steps_migration;

vec_injection = ones(steps_injection, 1) * dT_injection;
vec_migration = ones(steps_migration, 1) * dT_migration;

schedule.step.val = [vec_injection; vec_migration];
schedule.step.control = [ones(steps_injection, 1); ones(steps_migration, 1)*2];


%% Model
model = TwoPhaseWaterGasModel(G, rock, fluid, 0, 0);

%% Simulate

[wellSol, states] = simulateScheduleAD(initState, model, schedule);

%% Visualization

%{ 

% Plot plume at end of simulation
sat_end = states{end}.s(:,2);  % co2 saturation at end state

% Plot cells with CO2 saturation more than 0.05
plume_cells = sat_end > 0.05;

clf; plotGrid(G, 'facecolor', 'none');  % plot outline of simulation grid
plotGrid(G, plume_cells, 'facecolor', 'red'); % plot cells with CO2 in red
view(35, 35);

% Inspect results interactively using plotToolbar

clf;
plotToolbar(G,states)

%}

%% Save simulation data

% save wellSols to disk
save(fullfile(PARAMS.Paths.PUMLE_ROOT,...
            PARAMS.Paths.PUMLE_RESULTS,...
            strcat('states_',PARAMS.PreProcessing.case_name,'.mat')),'-v7.3');

fprintf('[MATLAB] Simulation completed.\n')
