# About PUMLE

![Beta Status](https://img.shields.io/badge/status-beta-brightgreen)

PUMLE (as a quibble for "plume") is a project under the [CO2SS Project](https://co2ssproject.com) by [TRIL Lab](http://www.tril.ci.ufpb.br) / CCS Team intended to:

- produce data related to plume migration from numerical simulations outputed by MRST software;
- feed (physics-informed) machine learning experiments;
- build a ingestion/consumption data engineering pipeline for geological carbon storage applications in Brazilian reservoirs;

## Process overview

This flowchart summarizes PUMLE's purpose:

```mermaid
flowchart TD
    n1(("Start")) --> n2("fa:fa-file Input simulation parameters")
    n2 --> n3["fa:fa-file-lines Process 'setup.ini'"]
    n3 --> n4["fa:fa-file-export Export Matlab structs"]
    n4 --> n5["fa:fa-file-import Load structs into m-file"]
    n5 --> n6["fa:fa-gear Run Matlab simulation"]
    n6 --> n7["fa:fa-database Store simulation results"]
    n7 --> n8{"API"}
    n8 -- CSE --> n9["fa:fa-arrow-up-right-dots Forward modeling"]
    n8 -- ML --> n10["fa:fa-brain Machine learning"]
    n9 --> n11["fa:fa-list-check Data quality assessment"]
    n10 --> n11
    n11 --> n12{"Consistency?"}
    n12 -- Not OK --> n2
    n12 -- OK --> n13(("End"))
    style n1 stroke:#00C853
    style n2 stroke:#2962FF
    style n3 stroke:#2962FF
    style n4 stroke:#2962FF
    style n5 stroke:#2962FF
    style n6 stroke:#2962FF
    style n7 stroke:#2962FF
    style n8 stroke:#FF6D00
    style n9 stroke:#2962FF
    style n10 stroke:#2962FF
    style n11 stroke:#2962FF
    style n12 stroke:#FF6D00
    style n13 stroke:#D50000
```

## Developers

- Gustavo Oliveira
- Luiz Fernando Santos
- Samuel Mendes

## Remarks

- Modify prefix in `environment.yml`.

## Setup

Run the coomands below to create and activate the environment.


```sh
conda env create -f environment.yml -n pumle-env
conda activate pumle-env
``` 

