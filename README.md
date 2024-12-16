
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/fomightez/genomenotebook-binder/main?urlpath=%2Flab%2Ftree%2Fnbs%2F00_Examples.ipynb)

This fork of [David Bikard's genomenotebook repo](https://github.com/dbikard/genomenotebook) is only meant to see if can use in Jupyter sessions served via MyBinder.org, so no sign in or Google account needed.

------------

# GenomeNotebook (1.0.0)

> A genome browser in your Jupyter notebook

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
g=gn.GenomeBrowser(gff_path=gff_path, fasta_path=fasta_path, init_pos=10000, bounds=(0,100000))
g.show()
```

## Documentation

<https://dbikard.github.io/genomenotebook/>

## Contributing to GenomeNotebook

GenomeNotebook is developed using the nbdev framework, which makes it
easy to develop Python packages with Jupyter Notebooks.

### Setting up a Fork

#### 1. Fork the Repository

1.  Navigate to the [GenomeNotebook GitHub
    repository](https://github.com/dbikard/genomenotebook.git).

2.  Click the “Fork” button in the top-right corner to create your own
    copy of the repository.

#### 2. Clone Your Fork

Clone your forked repository to your local machine by running the
following command in your terminal:
`bash git clone https://github.com/<your-username>/genomenotebook.git`

Navigate to the cloned directory: `bash cd genomenotebook`

#### 3. Set Up Upstream Remote

To keep your fork updated with the original repository:

Add the upstream repository:
`bash git remote add upstream https://github.com/dbikard/genomenotebook.git`

Verify the remotes: `bash git remote -v`

You should see origin pointing to your fork and upstream pointing to the
original repository.

### Setting Up the Development Environment

1.  Create a virtual environment and activate it

``` bash
conda create -n gn python=3.11
conda activate gn
```

2.  Install Required Tools

It is a good idea to read the nbdev [Getting Started
Guide](https://nbdev.fast.ai/getting_started.html) and [End-To-End
Walkthrough](https://nbdev.fast.ai/tutorials/tutorial.html)

``` bash
pip install jupyterlab
pip install nbdev
nbdev_install_quarto
pip install jupyterlab-quarto
nbdev_install_hooks
```

3.  Install dependecies and genomenotebook in editable mode

``` bash
pip install -e '.[dev]'
```

### Making Changes

1.  Sync with Upstream Repository Before making changes, ensure your
    fork is up-to-date:

``` bash
git fetch upstream
git checkout main
git merge upstream/main
```

2.  Create a New Branch

``` bash
git checkout -b <feature-branch>
```

Replace <feature-branch> with a descriptive name for your branch.

3.  Make and Test Changes

Open the Jupyter Notebooks in the repository to make your changes.
Changes should be made to notebooks in the `nbs/` folder only. The
package `.py` files are automatically generated from the notebooks.

Run the following command to rebuild the Python package, documentation
and run the tests:

``` bash
nbdev_prepare
```

4.  When ready you can create a pull request.
