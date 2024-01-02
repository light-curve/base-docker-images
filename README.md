# Base Docker images used by [`light-curve`](https://github.com/light-curve/) packages

## `./python-linux`

Multi-architecture images
[`manylinux2014`](https://github.com/light-curve/base-docker-images/pkgs/container/base-docker-images%2Fmanylinux2014)
and [`musllinux`](https://github.com/light-curve/base-docker-images/pkgs/container/base-docker-images%2Fmusllinux_1_1)
based on the official [manylinux/musllinux](https://github.com/pypa/manylinux) PyPA images for `aarch64`, `ppc64le`, and `x86_64` platforms.
We use these images to build binary wheels of [`light-curve-python`](https://github.com/light-curve/light-curve-python) package.
We add Rust toolchain, FFTW (compiled with platform-specific flags for SIMD) and GSL.
