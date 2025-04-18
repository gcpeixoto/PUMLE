# Use Ubuntu as base image
FROM ubuntu:22.04

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    unzip \
    octave \
    octave-control \
    octave-image \
    octave-io \
    octave-optim \
    octave-signal \
    octave-statistics \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Set up Python environment
WORKDIR /app
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Install MRST
WORKDIR /opt
RUN wget https://www.sintef.no/globalassets/project/mrst/mrst-2024b.zip && \
    unzip mrst-2024b.zip && \
    rm mrst-2024b.zip

# Set environment variables
ENV MRST_ROOT=/opt/mrst-2024b
ENV OCTAVE_PATH=$MRST_ROOT/mrst-2024b/modules/octave:$OCTAVE_PATH

# Copy application code
WORKDIR /app
COPY . .


# Set default command
CMD ["python3", "main.py"] 