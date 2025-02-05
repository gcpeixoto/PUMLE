THREADS=${1:-4}

g++ simulation/simulation.cpp -o simulation/simulationCompiled.out -fopenmp
echo "Simulation compiled"

export OMP_NUM_THREADS=${THREADS}
echo "OMP_NUM_THREADS set to ${OMP_NUM_THREADS}"

./simulation/simulationCompiled.out
echo "Simulation executed"