from ipykernel.kernelapp import IPKernelApp
import sys

from .kernel import FortranKernel


def main():
    kwargs = sys.argv
    for kwarg in kwargs[:]:
        if kwarg.startswith('--std='):
            # TODO: Handle this properly. Currently this is hard-coded in
            # the kernel.
            assert kwarg == '--std=f2008'
            kwargs.remove(kwarg)
    IPKernelApp.launch_instance(kernel_class=FortranKernel)
