THREADS=${1:-4}

g++ simulation/simulation.cpp -o simulation/simulationCompiled.out -fopenmp
echo "Simulation compiled"

export OMP_NUM_THREADS=${THREADS}
echo "OMP_NUM_THREADS set to ${OMP_NUM_THREADS}"

./simulation/simulationCompiled.out
if [ $? -ne 0 ]; then
  echo "Simulation failed"
  exit 1
fi
echo "Simulation executed"