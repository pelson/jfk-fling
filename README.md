# Jupyter Fortran Kernel

Inspired by the incredible power of the C++ interpreter [Cling](https://github.com/root-project/cling)
and its associated [Jupyter](https://jupyter.org/) kernel [xeus-cling](https://github.com/QuantStack/xeus-cling),
``jfk-fling`` is a [prototype](#Limitations) kernel that facilitates iterative and investigatory computing
using modern Fortran.


## Materials designed for the jfk-fling kernel

The purpose of the jfk-fling kernel is to speed up the learning of modern Fortran.
A number of resources have been made available that build upon the jfk-fling kernel,
some of which are listed below:

 * [Introduction to jfk-fling]()
 * [Fortran 90 with jfk-fling]()
 * [Object-oriented programming with jfk-fling]()
 * ...


*Please submit a pull request to add a link to any other jfk-fling notebook material.*


## License

This code is released under the MIT license, with copyright held by the individual contributors.
See the list of contributors at https://github.com/pelson/jfk-fling/graphs/contributors.

## A note on maintenance

This prototype was developed in support of learning modern Fortran, and it has been invaluable for that purpose.
I am releasing this work in the hope that it can be useful to others who want to learn, or indeed develop learning
resources for, modern Fortran.

As such, I do not intend to develop this kernel on an ongoing basis - anybody who wishes to do so may either
fork the repository, or request merge access to this repository.


## Limitations

 * Whilst it may appear that cells are being executed iteratively, each cell is in fact an entirely independent execution environment.
   For example, suppose you have a long-running execution cell followed by a simple cell to print the results, it will result in the long-running
   code being executed twice.

 * In order to interpret the code we use [fparser](https://github.com/stfc/fparser). Any limitations
   of parsing within fparser are therefore inherited, as well as some additional constraints on the source form.


## Inspiration

 * [Cling](https://github.com/root-project/cling)
 * [fparser](https://github.com/stfc/fparser)
 * [Jupyter](https://jupyter.org/)
 * [jupyter-fortran-kernel](https://github.com/ZedThree/jupyter-fortran-kernel) &
   [jupyter-c-kernel](https://github.com/brendan-rius/jupyter-c-kernel) - the design of this kernel was significantly influenced by these implementations.
 * [xeus-cling](https://github.com/QuantStack/xeus-cling)
