# Minimal Fortran kernel for Jupyter

Shamelessly hacked together from [jupyter-c-kernel](https://github.com/brendan-rius/jupyter-c-kernel)

## Manual installation

 * Make sure you have the following requirements installed:
  * gfortran
  * jupyter
  * python 3
  * pip

### Step-by-step:
 * `git clone git@github.com:ZedThree/jupyter-fortran-kernel.git`
 * `pip install -e --user jupyter-fortran-kernel`
 * `cd jupyter-fortran-kernel`
 * `jupyter-kernelspec install fortran_spec/`
 * `jupyter-notebook`. Enjoy!

## Example of notebook

[Example of notebook](example-notebook.ipynb "Example of notebook")

## Contributing

Create branches named `issue-X` where `X` is the no of the issue.
Rebase instead of merge.

## License

[MIT](LICENSE.txt)
