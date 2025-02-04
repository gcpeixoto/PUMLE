g++ simulation/simulation.cpp -o simulation/simulationCompiled.out -fopenmp
echo "Simulation compiled"
export OMP_NUM_THREADS=4
./simulation/simulationCompiled.out
echo "Simulation executed"