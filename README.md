# Jupyter Fortran Kernel

Inspired by the incredible power of the C++ REPL [Cling](https://github.com/root-project/cling)
and its assosiated [Jupyter](https://jupyter.org/) kernel [xeus-cling](https://github.com/QuantStack/xeus-cling),
``jfk-fling`` is a [prototype](#Limitations) kernel that facilitates iterative and investigatory computing
using modern Fotran.


## Limitations

 * Whilst it may appear that cells are being executed iteratively, each cell is in fact an entirely independent execution environment.
   For example, suppose you have a long-running execution cell followed by a simple cell to print the results, it will result in the long-running
   code being executed twice.

 * In order to interpret the code we use [fparser](https://github.com/stfc/fparser)


## Inspiration

 * [Cling](https://github.com/root-project/cling)
 * [fparser](https://github.com/stfc/fparser)
 * [Jupyter](https://jupyter.org/)
 * [jupyter-fortran-kernel](https://github.com/ZedThree/jupyter-fortran-kernel) &
   [jupyter-c-kernel](https://github.com/brendan-rius/jupyter-c-kernel) - the design of this kernel was significantly influenced by these implementations.
 * [xeus-cling](https://github.com/QuantStack/xeus-cling)
