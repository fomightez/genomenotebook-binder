# GenomeNotebook


<!-- WARNING: THIS FILE WAS AUTOGENERATED! DO NOT EDIT! -->

## Install

``` bash
pip install genomenotebook
```

#### Upgrade

New versions of genomenotebook are released on a regular basis. Make
sure to upgrade your installation to enjoy all the features.

``` bash
pip install genomenotebook --upgrade
```

## How to use

Create a simple genome browser with a search bar. The sequence appears
when zooming in.

Tracks can be added to visualize your favorite genomics data. See
[Examples](https://dbikard.github.io/genomenotebook/examples.html) for
more !!!!

``` python
import genomenotebook as gn
```

``` python
g=gn.GenomeBrowser(gff_path=gff_path, fasta_path=fasta_path, init_pos=10000)
g.show()
```

## Documentation

<https://dbikard.github.io/genomenotebook/>
