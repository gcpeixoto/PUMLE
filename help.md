## Useful shell commands for environment creation 

- Create environment from YAML

```bash
conda env create --name PUMLE --file environment.yml
```

- Create environment from YAML by passing `prefix` as argument (otherwise, chenge inside `environment.yml`)

```bash
conda env create --name PUMLE --file environment.yml --prefix path/where/install
```

- To recreate the requirements after any additions

```bash
conda env export > environment.yml
```

## Useful VSCode TODO-Tree extension tags

```
TODO, FIXME, BUG
```