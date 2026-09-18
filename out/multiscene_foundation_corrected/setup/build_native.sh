#!/usr/bin/env bash
set -eu
# Run at repository root, in a fresh reproduction checkout. Never overwrite the
# live archived shared objects while another process could have them mapped.
for name in area_layers surface fast_query; do
    test ! -e "out/multiscene_foundation_corrected/setup/${name}.so"
done
g++ -O3 -std=c++17 -shared -fPIC -fopenmp src/corrected_layers.cpp -o out/multiscene_foundation_corrected/setup/area_layers.so
g++ -O3 -std=c++17 -shared -fPIC src/corrected_surface.cpp -o out/multiscene_foundation_corrected/setup/surface.so
g++ -O3 -std=c++17 -shared -fPIC -fopenmp src/corrected_query.cpp -o out/multiscene_foundation_corrected/setup/fast_query.so
# fast_query.so is exercised only by its synthetic regression test. The
# scientific runner deliberately retains the inherited native query binary.
