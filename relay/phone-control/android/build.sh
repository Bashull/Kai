#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
umask 077
APP="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FACTORY="${KAI_FACTORY_ROOT:-/data/data/com.termux/files/home/KAI_RUNTIME_LAB/KAI_TERMUX_FACTORY_STAGE02_20261012}"
SDK="$FACTORY/toolchain/android-sdk/platforms/android-36/android.jar"
R8="$FACTORY/toolchain/sources/r8-9.5.23.jar"
OUT="$APP/build"
test -f "$SDK"
test -f "$R8"
if [[ -e "$OUT" ]]; then
  echo 'Build output exists; preserve or review it before rebuilding.' >&2
  exit 3
fi
mkdir -p "$OUT/compiled" "$OUT/gen" "$OUT/classes" "$OUT/dex" "$OUT/private"
chmod 700 "$OUT/private"
aapt2 compile -o "$OUT/compiled" "$APP/res/values/strings.xml"
ANDROID_DATA=/data aapt2 link -o "$OUT/resources.apk" -I "$SDK" \
  --manifest "$APP/AndroidManifest.xml" --java "$OUT/gen" \
  --min-sdk-version 26 --target-sdk-version 36 "$OUT/compiled/"*.flat
javac --release 8 -Xlint:-options -cp "$SDK" -d "$OUT/classes" \
  "$OUT/gen/com/kai/controlprobe/R.java" "$APP/src/com/kai/controlprobe/ProbeActivity.java"
mapfile -d '' classes < <(find "$OUT/classes" -type f -name '*.class' -print0)
java -cp "$R8" com.android.tools.r8.D8 --min-api 26 --lib "$SDK" --output "$OUT/dex" "${classes[@]}"
cp "$OUT/resources.apk" "$OUT/unsigned.apk"
(cd "$OUT/dex"; zip -q "$OUT/unsigned.apk" classes.dex)
zipalign -f -p 4 "$OUT/unsigned.apk" "$OUT/aligned.apk"
python - "$OUT/private/signing-password" <<'PY'
import os,sys,secrets
fd=os.open(sys.argv[1],os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,'w') as f:f.write(secrets.token_hex(32))
PY
keytool -genkeypair -keystore "$OUT/private/control-lab.p12" -storetype PKCS12 \
  -storepass:file "$OUT/private/signing-password" -keypass:file "$OUT/private/signing-password" \
  -alias kaicontrol -dname 'CN=KAI Control Lab,OU=Local Test,O=KAI' \
  -validity 365 -keyalg RSA -keysize 2048 -noprompt > "$OUT/key-generation.log" 2>&1
chmod 600 "$OUT/private/"*
apksigner sign --ks "$OUT/private/control-lab.p12" \
  --ks-pass "file:$OUT/private/signing-password" \
  --ks-key-alias kaicontrol --out "$OUT/KAI_Control_Lab_0.1.0.apk" "$OUT/aligned.apk"
apksigner verify --verbose "$OUT/KAI_Control_Lab_0.1.0.apk" > "$OUT/signature.txt"
zipalign -c 4 "$OUT/KAI_Control_Lab_0.1.0.apk"
ANDROID_DATA=/data aapt dump permissions "$OUT/KAI_Control_Lab_0.1.0.apk" > "$OUT/permissions.txt"
if grep -q 'uses-permission:' "$OUT/permissions.txt"; then
  echo 'Unexpected permission' >&2; exit 4
fi
ANDROID_DATA=/data aapt dump badging "$OUT/KAI_Control_Lab_0.1.0.apk" > "$OUT/badging.txt"
grep -q "package: name='com.kai.controlprobe'" "$OUT/badging.txt"
unzip -t "$OUT/KAI_Control_Lab_0.1.0.apk" > "$OUT/zip-integrity.txt"
sha256sum "$OUT/KAI_Control_Lab_0.1.0.apk"
echo 'CONTROL_LAB_BUILD_PASS'
