#!/usr/bin/env python3

import argparse
import dataclasses
import importlib.resources
from configparser import ConfigParser
from functools import lru_cache
from itertools import chain, repeat
from subprocess import check_call


@lru_cache(maxsize=1)
def current_cibw_images():
    config = ConfigParser()
    file = importlib.resources.files('cibuildwheel.resources') / 'pinned_docker_images.cfg'
    with file.open() as fh:
        config.read_file(fh)
    return config


def echo_and_call(cmd_args, *args, **kwargs):
    print(" ".join(cmd_args))
    check_call(cmd_args, *args, **kwargs)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", required=True, choices=list(PLATFORMS))

    subparsers = parser.add_subparsers(title="image", required=True, dest="image")

    for tag, func in TAGS.items():
        subparser = subparsers.add_parser(tag)
        subparser.set_defaults(func=func)
        subparser.add_argument("--arch", required=True, choices=list(ARCHS))

    manifest_image = subparsers.add_parser("manifest")
    manifest_image.set_defaults(func=manifest)
    manifest_image.add_argument("--tag", required=True, choices=list(TAGS))

    return parser.parse_args()


def multiarch_image(platform):
    platform_version = PLATFORMS[platform].version
    return f"ghcr.io/light-curve/base-docker-images/{platform}{platform_version}"


def image_with_arch(platform, arch):
    return f"{multiarch_image(platform)}_{arch}"


def multiarch_image_with_tag(platform, tag):
    return f"{multiarch_image(platform)}:{tag}"


def image_with_arch_and_tag(platform, arch, tag):
    return f"{image_with_arch(platform, arch)}:{tag}"


def pypa_image(platform, arch):
    platform_version = PLATFORMS[platform].version
    platform_name = f'{platform}{platform_version}'
    return current_cibw_images()[arch][platform_name]


def pypa_image_tag(platform, arch):
    image = pypa_image(platform, arch)
    _base, tag = image.rsplit(':', 1)
    return tag


def build(args, *, dockerfile, tag, extra_cmd_args):
    arch_name, arch = args.arch, ARCHS[args.arch]
    image = image_with_arch_and_tag(args.platform, arch_name, tag)
    echo_and_call(
        [
            "docker",
            "buildx",
            "build",
            "--platform",
            arch.docker_platform,
            "--tag",
            image,
            "--file",
            dockerfile,
            "--push",
            ".",
        ] + extra_cmd_args
    )


def fftw(args):
    arch_name, arch = args.arch, ARCHS[args.arch]
    build(
        args,
        dockerfile="Dockerfile.fftw",
        tag="fftw",
        extra_cmd_args=[
            "--build-arg",
            f"BASE_IMAGE={pypa_image(args.platform, arch_name)}",
            "--build-arg",
            f"FFTW_SINGLE_CONF_FLAGS={arch.fftw_single_conf_flags}",
            "--build-arg",
            f"FFTW_DOCKER_CONF_FLAFS={arch.fftw_double_conf_flags}",
        ],
    )


def gsl(args):
    if args.platform != "manylinux":
        raise ValueError(f"We don't need to build gsl for anything but manylinux, you specified {args.platform} instead")
    arch_name = args.arch
    build(
        args,
        dockerfile="Dockerfile.manylinux.gsl",
        tag="gsl",
        extra_cmd_args=[
            "--build-arg",
            f"ARCH={arch_name}",
        ],
    )


def latest(args):
    arch_name = args.arch
    build(
        args,
        dockerfile=f"Dockerfile.{args.platform}",
        tag="latest",
        extra_cmd_args=[
            "--build-arg",
            f"ARCH={arch_name}",
        ]
    )


def manifest(args):
    manifest_image = multiarch_image_with_tag(args.platform, args.tag)
    arch_images = [image_with_arch_and_tag(args.platform, arch, args.tag) for arch in PLATFORMS[args.platform].archs]
    amends = list(chain.from_iterable(zip(repeat("--amend"), arch_images)))
    echo_and_call(
        [
            "docker",
            "manifest",
            "create",
            manifest_image,
        ] + amends
    )
    echo_and_call(
        [
            "docker",
            "manifest",
            "push",
            manifest_image,
        ]
    )


@dataclasses.dataclass(kw_only=True)
class Arch:
    docker_platform: str
    fftw_single_conf_flags: str = ""
    fftw_double_conf_flags: str = ""


ARCHS = {
    'aarch64': Arch(
        docker_platform="linux/arm64",
        fftw_single_conf_flags='--enable-neon',
        fftw_double_conf_flags='--enable-neon',
    ),
    'i686': Arch(
        docker_platform="linux/386",
        fftw_single_conf_flags='--enable-sse --enable-sse2',
        fftw_double_conf_flags='--enable-sse2',
    ),
    'ppc64le': Arch(
        docker_platform="linux/ppc64le",
        # --enable-vsx doesn't really help for doubles and makes things worse for floats
        fftw_single_conf_flags='--enable-altivec',
        fftw_double_conf_flags='',
    ),
    'x86_64': Arch(
        docker_platform="linux/amd64",
        fftw_single_conf_flags='--enable-sse2 --enable-avx --enable-avx2 --enable-avx512 --enable-avx-128-fma',
        fftw_double_conf_flags='--enable-sse2 --enable-avx --enable-avx2 --enable-avx512 --enable-avx-128-fma',
    ),
}


@dataclasses.dataclass(kw_only=True)
class Platform:
    version: str
    archs: list[str]


PLATFORMS = {
    'manylinux': Platform(
        version="2014",
        archs=["aarch64", "i686", "ppc64le", "x86_64"],
    ),
    'musllinux': Platform(
        version="_1_1",
        # rustup cannot install the Rust toolchain for PPC64le and MUSL
        archs=["aarch64", "i686", "x86_64"],
    ),
}


TAGS = dict(fftw=fftw, gsl=gsl, latest=latest)


def main():
    args = parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
