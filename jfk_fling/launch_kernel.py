from ipykernel.kernelapp import IPKernelApp

from .kernel import FortranKernel


def main():
    IPKernelApp.launch_instance(kernel_class=FortranKernel)
