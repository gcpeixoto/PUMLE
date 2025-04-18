#!/bin/bash

# Exit on error
set -e

THREADS=${1:-4}

# Create data_lake directory if it doesn't exist
mkdir -p data_lake/staging

# Compile simulation code
echo "Compiling simulation code..."
cd simulation
g++ simulation.cpp -o simulationCompiled.out -fopenmp
cd ..

echo "Simulation compiled successfully"

# Set OpenMP threads
export OMP_NUM_THREADS=${THREADS}
echo "OMP_NUM_THREADS set to ${OMP_NUM_THREADS}"

# Run simulation
echo "Starting simulation..."
./simulation/simulationCompiled.out ${THREADS}
if [ $? -ne 0 ]; then
    echo "Simulation failed"
    exit 1
fi

echo "Simulation completed successfully"