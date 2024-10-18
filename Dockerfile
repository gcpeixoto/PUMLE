# Usar a imagem oficial do Octave como base
FROM matpower/octave:latest
# Instalar Python e suas dependências
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    python3 \
    python3-pip \
    libblas-dev \
    liblapack-dev \
    libhdf5-dev \
    && apt-get clean

WORKDIR /app

ADD requirements.txt /app/requirements.txt
RUN pip3 install -r requirements.txt

# Baixar e instalar o MRST
RUN wget https://www.sintef.no/globalassets/project/mrst/mrst-2024a.zip -O mrst.zip && \
    unzip mrst.zip && \
    mv mrst-2024a mrst && \
    rm mrst.zip && \
    cd mrst && \
    octave --eval "startup"  # Executar o comando diretamente no Octave para inicializar o MRST


# Adicionar o Miniconda ao PATH
ENV PATH="/opt/miniconda/bin:${PATH}"

RUN mkdir src
# Copiar o script Python e o script Octave para o contêiner
COPY m/co2lab3DPUMLE.m /app/mrst/co2lab3DPUMLE.m
COPY src/ /app/src/
COPY setup.ini /app/setup.ini
COPY benchmark/ /app/mrst/benchmark


# Comando padrão para rodar o script Python

ENTRYPOINT ["tail", "-f", "/dev/null"]

# CMD ["python3", "src/main.py"]
