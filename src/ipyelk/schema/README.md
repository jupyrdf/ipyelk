# elk schema

`elkschema.json` can be re-generated in this directory with:

```bash
jlpm schema
```

`elk-catalog.json` lists the layout options, algorithms and categories of the bundled
`elkjs`. Re-generate it after an `elkjs` upgrade with:

```bash
pixi run build-py-elk-catalog
```
