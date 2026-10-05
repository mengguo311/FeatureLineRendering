#!/bin/bash
set -eu
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
if ! command -v node >/dev/null 2>&1; then
  printf '需要 Node.js 20 或更高版本。安装后重新双击此文件。\n'
  read -r -p '按 Enter 关闭…' _
  exit 1
fi
printf '\nGaussian Edge Demo\n在浏览器打开下方程序打印的本机地址；保持此窗口开启。\n按 Ctrl+C 关闭服务。\n\n'
exec node server.mjs
