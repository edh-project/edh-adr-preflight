#!/usr/bin/env bash
set -u
work="$RUNNER_TEMP/r10-runtime"
mkdir -p "$work" || exit 1
cd "$work" || exit 1
fetch() {
  curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' --retry 2 --max-time 900 "$1" -o "$2" &&
  printf '%s  %s\n' "$3" "$2" | sha256sum -c -
}
release=https://github.com/ggml-org/llama.cpp/releases/download/b12646
if [ "${R10_ACCEL:-cpu}" = cuda ]; then
  nvidia-smi || exit 1
  fetch "$release/llama-b12646-bin-ubuntu-cuda-12.8-x64.tar.gz" runtime.tar.gz 3626bc8507d1af6888b612010843c29bde30c96c34f3bf173ad833e21d34282c || exit 1
  fetch "$release/cudart-llama-b12646-bin-ubuntu-cuda-12.8-x64.tar.gz" cuda.tar.gz 33a3c3ed42063766783f190b15d334ccdacc48af2defad959275c656c6253d76 || exit 1
  tar -xzf cuda.tar.gz || exit 1
  layers=99
else
  fetch "$release/llama-b12646-bin-ubuntu-x64.tar.gz" runtime.tar.gz 4f430ba722c4d13954981fe845768ebb84a9b712bc6da0cca23f36b05ab77738 || exit 1
  layers=0
fi
tar -xzf runtime.tar.gz || exit 1
fetch 'https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/resolve/e87f176479d0855a907a41277aca2f8ee7a09523/Qwen3.5-4B-UD-Q5_K_XL.gguf' model.gguf b4c36a8e14a80c21bcab5a067ce342b2e70e28f60b4aa95ad12203fa17b87426 || exit 1
server=$(find "$work" -type f -name llama-server -print -quit)
test -n "$server" || exit 1
export LD_LIBRARY_PATH="$(dirname "$server"):$work:${LD_LIBRARY_PATH:-}"
"$server" --version || exit 1
"$server" -m "$work/model.gguf" --alias qwen4b --host 127.0.0.1 --port 8092 -c 8192 -np 1 -ngl "$layers" > "$work/server.log" 2>&1 &
pid=$!
trap 'kill "$pid" 2>/dev/null || true' EXIT
ready=false
for i in $(seq 1 120); do
  if curl --noproxy '*' -fsS --max-time 2 http://127.0.0.1:8092/health >/dev/null 2>&1; then ready=true; break; fi
  kill -0 "$pid" 2>/dev/null || break
  sleep 2
done
if [ "$ready" != true ]; then tail -50 "$work/server.log"; exit 1; fi
cd "$GITHUB_WORKSPACE" || exit 1
python3 experiments/r10/runner.py --output reports/r10 --suite "$R10_SUITE" --repeats "$R10_REPEATS"
rc=$?
printf 'Inference exit status: %s\n' "$rc"
exit "$rc"
