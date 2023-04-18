genomeNotebook
================

<!-- WARNING: THIS FILE WAS AUTOGENERATED! DO NOT EDIT! -->

## Install

    pip install genomenotebook

## How to use

Create a simple genome browser with a search bar. The sequence appears
when zooming in.

``` python
#Using the example E. coli genome data from the package
import genomenotebook as gn
import os

data_path = gn.get_example_data_dir()
genome_path = os.path.join(data_path, "MG1655_U00096.fasta")
gff_path = os.path.join(data_path, "MG1655_U00096.gff3")

g=gn.GenomeBrowser(genome_path=genome_path, gff_path=gff_path)
g.show()
```

  <div id="92453fab-390d-47f1-826e-8b1bff298816" data-root-id="p13223" style="display: contents;"></div>

    Unable to display output for mime type(s): application/javascript, application/vnd.bokehjs_exec.v0+json
