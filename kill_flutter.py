#!/usr/bin/env python3
# K!ll Fl!utter - Flutter SSL Pinning Bypass Tool
# By: f3rb
# Supports: Android (APK) + iOS (IPA)
# For authorized penetration testing only

import struct, re, sys, os, zipfile, subprocess, argparse, plistlib, socket, shutil, json, hashlib


# ─────────────────────────────────────────────
#  BOX HELPERS (keeps all boxes perfectly aligned)
# ─────────────────────────────────────────────

BOX_WIDTH = 54  # visible characters between the ║ borders

C_CYAN   = "\033[96m"
C_YELLOW = "\033[93m"
C_GREEN  = "\033[92m"
C_RED    = "\033[91m"
C_GREY   = "\033[90m"
C_PURPLE = "\033[95m"
C_RESET  = "\033[0m"


def box_top():
    return C_CYAN + "╔" + "═" * BOX_WIDTH + "╗" + C_RESET


def box_bottom():
    return C_CYAN + "╚" + "═" * BOX_WIDTH + "╝" + C_RESET


def box_line(text, color=""):
    """text is the raw visible text (no ANSI). Pads to BOX_WIDTH and adds borders."""
    padded = text.ljust(BOX_WIDTH)
    return f"{C_CYAN}║{C_RESET}{color}{padded}{C_RESET}{C_CYAN}║{C_RESET}"


# ─────────────────────────────────────────────
#  BANNER & HELP
# ─────────────────────────────────────────────

def print_banner():
    print(C_CYAN + """
██╗  ██╗██╗██╗     ██╗     
██║ ██╔╝██║██║     ██║     
█████╔╝ ██║██║     ██║     
██╔═██╗ ██║██║     ██║     
██║  ██╗██║███████╗███████╗
╚═╝  ╚═╝╚═╝╚══════╝╚══════╝""" + C_PURPLE + """
███████╗██╗     ██╗   ██╗████████╗████████╗███████╗██████╗ 
██╔════╝██║     ██║   ██║╚══██╔══╝╚══██╔══╝██╔════╝██╔══██╗
█████╗  ██║     ██║   ██║   ██║      ██║   █████╗  ██████╔╝
██╔══╝  ██║     ██║   ██║   ██║      ██║   ██╔══╝  ██╔══██╗
██║     ███████╗╚██████╔╝   ██║      ██║   ███████╗██║  ██║
╚═╝     ╚══════╝ ╚═════╝    ╚═╝      ╚═╝   ╚══════╝╚═╝  ╚═╝""" + C_RESET)

    print(box_top())
    print(box_line("  K!ll Fl!utter  —  Flutter SSL Pinning Bypass", C_YELLOW))
    print(box_line("  By: f3rb                              v2.1.0", C_GREEN))
    print(box_line("  Android (APK) + iOS (IPA) Support", C_PURPLE))
    print(box_line("  For authorized penetration testing only", C_PURPLE))
    print(box_bottom())
    print("")


def print_help():
    print_banner()
    print("""
\033[93mUSAGE:\033[0m
  python3 kill_flutter.py <path_to_apk_or_ipa> [options]

\033[93mOPTIONS:\033[0m
  \033[92m-h, --help\033[0m          Show this help message
  \033[92m-i, --ip\033[0m            Your machine IP (auto-detected if omitted)
  \033[92m-p, --port\033[0m          Burp Suite port (default: 8080)
  \033[92m-o, --output\033[0m        Output directory for generated files
  \033[92m--platform\033[0m          Force platform: android or ios (auto-detected from extension)
  \033[92m--package\033[0m           Explicit package/bundle id (skips detection + interactive prompt)
  \033[92m--no-scan\033[0m           Skip the protection/RASP pre-scan
  \033[92m--from-device\033[0m       Pull the app (all splits) from a device by package name (Android)
  \033[92m--serial\033[0m            adb / Frida device serial (for --from-device and --run)
  \033[92m--run\033[0m               Spawn the app via Frida and verify the bypass actually loaded
  \033[92m--run-timeout\033[0m       Seconds to wait for the hook with --run (default 15)
  \033[92m--no-cache\033[0m          Ignore the offset cache and always rescan
  \033[92m--refresh-cache\033[0m     Rescan and overwrite the cached offset for this binary

\033[93mNOTES:\033[0m
  \033[90m- Offsets are cached by libflutter.so SHA-256 in ~/.kill_flutter/ (instant re-runs).\033[0m
  \033[90m- The generated script also unpins Java-layer TLS (OkHttp/TrustManager) for\033[0m
  \033[90m  hybrid apps; toggle ENABLE_TLS_UNPIN in the script to disable.\033[0m

\033[93mINPUT TYPES (Android):\033[0m
  a single .apk, a folder of split APKs, an .xapk/.apks/.apkm bundle,
  or --from-device to pull straight off a connected phone.

\033[93mEXAMPLES:\033[0m
  \033[90m# Android APK\033[0m
  python3 kill_flutter.py app.apk -i 192.168.1.10 -p 8080

  \033[90m# iOS IPA\033[0m
  python3 kill_flutter.py app.ipa -i 192.168.1.10 -p 8080

  \033[90m# Force platform\033[0m
  python3 kill_flutter.py app.apk --platform android -i 192.168.1.10

  \033[90m# Auto-detect your machine IP (omit -i) + auto protection/RASP scan\033[0m
  python3 kill_flutter.py app.apk

  \033[90m# Explicit package/bundle id (skips detection + interactive prompt; good for scripts/CI)\033[0m
  python3 kill_flutter.py app.apk --package com.example.app
  python3 kill_flutter.py app.ipa --bundle-id com.example.app

  \033[90m# Skip the protection/RASP pre-scan\033[0m
  python3 kill_flutter.py app.apk --no-scan

  \033[90m# Fully non-interactive run (explicit id, explicit IP)\033[0m
  python3 kill_flutter.py app.apk --package com.example.app -i 192.168.1.10 -p 8080

  \033[90m# Pull the app straight off a connected phone (no manual adb pull)\033[0m
  python3 kill_flutter.py --from-device com.example.app

  \033[90m# Folder of split APKs, or an .xapk/.apks bundle\033[0m
  python3 kill_flutter.py ./app_splits/
  python3 kill_flutter.py app.xapk

  \033[90m# Generate AND auto-verify the bypass on-device (spawns via Frida)\033[0m
  python3 kill_flutter.py --from-device com.example.app --run

  \033[90m# Pick a specific device when several are attached\033[0m
  python3 kill_flutter.py --from-device com.example.app --serial RZ8R32PFELT --run

\033[93mWORKFLOW:\033[0m
  \033[96m1.\033[0m Auto-detects platform from file extension
  \033[96m2.\033[0m Auto-detects your host IP (unless -i is given)
  \033[96m3.\033[0m Scans the app for known protections / RASP (PAIRIP, Talsec, RootBeer, ...)
  \033[96m4.\033[0m Resolves package/bundle id (--package > aapt > aapt2 > manifest parser)
  \033[96m5.\033[0m Extracts Flutter engine binary (libflutter.so / Flutter framework)
  \033[96m6.\033[0m Scans for ssl_client/ssl_server string anchors
  \033[96m7.\033[0m Parses ELF (Android) or Mach-O (iOS) segments
  \033[96m8.\033[0m Finds ADRP+ADD instruction pairs referencing both strings
  \033[96m9.\033[0m Walks back to function prologue to get exact hook offset
  \033[96m10.\033[0m Generates ready-to-use Frida script (SSL + root/anti-Frida bypass)
  \033[96m11.\033[0m Verifies the on-device frida-server, then prints copy-paste commands

\033[93mREQUIREMENTS:\033[0m
  \033[92m- Python 3\033[0m
  \033[92m- Frida\033[0m             pip install frida-tools
  \033[92m- aapt\033[0m              OPTIONAL (Android) — falls back to aapt2, then a
                      built-in binary-manifest parser if aapt is absent
  \033[92m- Rooted Android / Jailbroken iOS device\033[0m
  \033[92m- Burp Suite\033[0m        invisible proxy on all interfaces

\033[93mBURP SETUP:\033[0m
  \033[96m-\033[0m Proxy → Listeners → Bind to 0.0.0.0:8080
  \033[96m-\033[0m Request handling → Enable invisible proxying
  \033[96m-\033[0m Intercept → OFF

\033[93mANDROID — REVERT IPTABLES:\033[0m
  adb shell su -c "iptables -t nat -D OUTPUT -p tcp --dport 443 -j DNAT --to-destination <IP>:8080"
  adb shell su -c "iptables -t nat -D OUTPUT -p tcp --dport 80  -j DNAT --to-destination <IP>:8080"
  \033[90m# Or simply: adb reboot\033[0m

\033[93miOS — REVERT IPTABLES (via SSH):\033[0m
  ssh root@<device-ip> "iptables -t nat -D OUTPUT -p tcp --dport 443 -j DNAT --to-destination <IP>:8080"
  ssh root@<device-ip> "iptables -t nat -D OUTPUT -p tcp --dport 80  -j DNAT --to-destination <IP>:8080"
  \033[90m# Or simply reboot the device\033[0m
""")


# ─────────────────────────────────────────────
#  PLATFORM DETECTION
# ─────────────────────────────────────────────

def detect_platform(file_path, forced=None):
    if forced:
        return forced.lower()
    if os.path.isdir(file_path):
        return 'android'  # a folder of split APKs
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ('.apk', '.xapk', '.apks', '.apkm'):
        return 'android'
    elif ext == '.ipa':
        return 'ios'
    else:
        print("\033[93m[!] Cannot detect platform from input. Use --platform android or --platform ios\033[0m")
        sys.exit(1)


# ─────────────────────────────────────────────
#  ANDROID — PACKAGE NAME
# ─────────────────────────────────────────────

def get_package_name_android(apk_path):
    """Resolve the package name with a graceful fallback chain so the tool does
    NOT hard-depend on aapt: aapt -> aapt2 -> binary-AndroidManifest parser.
    Added by CaptainHacX: the aapt2 + binary-manifest fallbacks."""
    # 1) aapt (if present)
    try:
        result = subprocess.run(['aapt', 'dump', 'badging', apk_path],
                                capture_output=True, text=True, timeout=30)
        for line in result.stdout.splitlines():
            if line.startswith("package:"):
                for part in line.split():
                    if part.startswith("name="):
                        return part.split("'")[1]
    except FileNotFoundError:
        pass  # aapt not installed; fall through
    except Exception as e:
        print(f"\033[93m[!] aapt failed: {e}\033[0m")

    # 2) aapt2 (ships in newer build-tools)
    try:
        result = subprocess.run(['aapt2', 'dump', 'packagename', apk_path],
                                capture_output=True, text=True, timeout=30)
        name = result.stdout.strip()
        if result.returncode == 0 and name:
            return name.splitlines()[0].strip()
    except FileNotFoundError:
        pass
    except Exception:
        pass

    # 3) Parse the binary AndroidManifest.xml directly (no external tools)
    pkg = _parse_package_from_axml(apk_path)
    if pkg:
        print(f"\033[96m[*]\033[0m Package resolved from AndroidManifest.xml (aapt not required)")
        return pkg

    return None


def _parse_package_from_axml(apk_path):
    """Extract the `package` attribute of <manifest> from an APK's binary
    AndroidManifest.xml without aapt. Fully defensive: returns None on any error.
    Added by CaptainHacX."""
    try:
        with zipfile.ZipFile(apk_path, 'r') as z:
            axml = z.read('AndroidManifest.xml')
    except Exception:
        return None

    try:
        n = len(axml)
        if n < 8 or struct.unpack_from('<H', axml, 0)[0] != 0x0003:  # RES_XML_TYPE
            return None

        # ---- string pool (first chunk after the 8-byte file header) ----
        sp = 8
        if struct.unpack_from('<H', axml, sp)[0] != 0x0001:  # RES_STRING_POOL_TYPE
            return None
        sp_size       = struct.unpack_from('<I', axml, sp + 4)[0]
        string_count  = struct.unpack_from('<I', axml, sp + 8)[0]
        flags         = struct.unpack_from('<I', axml, sp + 16)[0]
        strings_start = struct.unpack_from('<I', axml, sp + 20)[0]
        is_utf8       = bool(flags & 0x100)
        offsets_base  = sp + 28
        data_base     = sp + strings_start

        def get_string(idx):
            if idx < 0 or idx >= string_count:
                return None
            so = struct.unpack_from('<I', axml, offsets_base + idx * 4)[0]
            pos = data_base + so
            if pos < 0 or pos >= n:
                return None
            if is_utf8:
                # (char-count)(byte-count)(bytes)(0x00); each length is 1 or 2 bytes
                c = axml[pos]; pos += 2 if (c & 0x80) else 1
                b = axml[pos]
                if b & 0x80:
                    blen = ((b & 0x7f) << 8) | axml[pos + 1]; pos += 2
                else:
                    blen = b; pos += 1
                return axml[pos:pos + blen].decode('utf-8', 'ignore')
            else:
                c = struct.unpack_from('<H', axml, pos)[0]
                if c & 0x8000:
                    c = ((c & 0x7fff) << 16) | struct.unpack_from('<H', axml, pos + 2)[0]; pos += 4
                else:
                    pos += 2
                return axml[pos:pos + c * 2].decode('utf-16-le', 'ignore')

        # ---- walk chunks; the first START_ELEMENT is <manifest> ----
        pos = sp + sp_size
        while pos + 8 <= n:
            ctype  = struct.unpack_from('<H', axml, pos)[0]
            chsize = struct.unpack_from('<I', axml, pos + 4)[0]
            if chsize <= 0:
                break
            if ctype == 0x0102:  # RES_XML_START_ELEMENT_TYPE
                name_idx   = struct.unpack_from('<I', axml, pos + 20)[0]
                attr_start = struct.unpack_from('<H', axml, pos + 24)[0]
                attr_size  = struct.unpack_from('<H', axml, pos + 26)[0] or 20
                attr_count = struct.unpack_from('<H', axml, pos + 28)[0]
                if get_string(name_idx) == 'manifest':
                    abase = pos + 16 + attr_start
                    for a in range(attr_count):
                        ao = abase + a * attr_size
                        if ao + 12 > n:
                            break
                        a_name = struct.unpack_from('<I', axml, ao + 4)[0]
                        a_raw  = struct.unpack_from('<i', axml, ao + 8)[0]  # signed; -1 = none
                        if get_string(a_name) == 'package' and a_raw != -1:
                            return get_string(a_raw)
                    return None  # manifest found, no package attr
            pos += chsize
    except Exception:
        return None
    return None


# ─────────────────────────────────────────────
#  iOS — BUNDLE ID
# ─────────────────────────────────────────────

def get_bundle_id_ios(ipa_path):
    try:
        with zipfile.ZipFile(ipa_path, 'r') as z:
            # Find Info.plist
            for name in z.namelist():
                if re.match(r'Payload/[^/]+\.app/Info\.plist$', name):
                    with z.open(name) as f:
                        content = f.read()
                    
                    try:
                        plist_data = plistlib.loads(content)
                        if 'CFBundleIdentifier' in plist_data:
                            return plist_data['CFBundleIdentifier'].strip()
                    except Exception as parse_e:
                        print(f"\033[93m[!] Could not parse Info.plist data: {parse_e}\033[0m")
    except Exception as e:
        print(f"\033[93m[!] Could not read Info.plist from zip: {e}\033[0m")
    return None


# ─────────────────────────────────────────────
#  DEVICE / INPUT HELPERS  (--from-device, bundles, dirs)   — Added by CaptainHacX
# ─────────────────────────────────────────────

ABI_PREFERENCE = ['arm64-v8a', 'armeabi-v7a', 'x86_64', 'x86']


def _valid_package(pkg):
    """Strict Android package-name validation to prevent command injection in
    adb calls and path traversal in local filenames."""
    return bool(pkg) and re.match(r'^[A-Za-z0-9_][A-Za-z0-9_.]{0,254}$', pkg) is not None \
        and '..' not in pkg and pkg[0] != '.' and pkg[-1] != '.'


def resolve_serial(preferred=None):
    """Pick a single adb device. Returns (serial, error_message)."""
    try:
        r = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=15)
    except FileNotFoundError:
        return None, "adb not found on PATH"
    except Exception as e:
        return None, f"adb error: {e}"
    online = []
    for line in r.stdout.splitlines()[1:]:
        line = line.strip()
        if '\t' in line:
            s, state = (line.split('\t') + [''])[:2]
            if state.strip() == 'device':
                online.append(s)
    pref = preferred or os.environ.get('ANDROID_SERIAL')
    if pref:
        return (pref, None) if pref in online else (None, f"device '{pref}' is not online")
    if not online:
        return None, "no online adb device (check 'adb devices')"
    if len(online) > 1:
        return None, f"multiple devices {online} — pass --serial <id>"
    return online[0], None


def pull_apks_from_device(package, serial, out_dir):
    """Resolve every split of `package` via `pm path` and pull them locally.
    Returns the local directory holding the pulled APKs. Raises on failure.
    All adb args are passed as a list (no shell); package + remote paths are
    validated to avoid injection / traversal."""
    if not _valid_package(package):
        raise ValueError(f"invalid package name: {package!r}")
    adb = ['adb', '-s', serial]

    print(f"\033[96m[*]\033[0m Resolving APK paths on device for {package} ...")
    r = subprocess.run(adb + ['shell', 'pm', 'path', package],
                       capture_output=True, text=True, timeout=60)
    remotes = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith('package:'):
            rp = line[len('package:'):].strip()
            # only accept absolute paths ending in .apk (defensive)
            if rp.startswith('/') and rp.endswith('.apk') and '\n' not in rp:
                remotes.append(rp)
    if not remotes:
        raise RuntimeError(f"package '{package}' not found on device (is it installed?)")

    dest = os.path.join(out_dir, 'pulled_' + package)
    os.makedirs(dest, exist_ok=True)
    print(f"\033[96m[*]\033[0m Pulling {len(remotes)} APK(s) to {dest}")
    pulled = []
    for rp in remotes:
        r2 = subprocess.run(adb + ['pull', rp, dest],
                            capture_output=True, text=True, timeout=300)
        local = os.path.join(dest, os.path.basename(rp))
        if os.path.exists(local):
            print(f"\033[92m[+]\033[0m   {os.path.basename(rp)}")
            pulled.append(local)
        else:
            print(f"\033[93m[!]\033[0m   failed to pull {rp}: {r2.stderr.strip()}")
    if not pulled:
        raise RuntimeError("failed to pull any APK from device")
    return dest


def list_android_apks(input_path, out_dir):
    """Normalize an Android input into a list of .apk paths. Accepts a single
    .apk, a directory of APKs, or an .xapk/.apks/.apkm bundle (zip-slip safe)."""
    if os.path.isdir(input_path):
        return sorted(os.path.join(input_path, f) for f in os.listdir(input_path)
                      if f.lower().endswith('.apk'))
    ext = os.path.splitext(input_path)[1].lower()
    if ext in ('.xapk', '.apks', '.apkm', '.zip'):
        dest = os.path.join(out_dir, 'bundle_extracted')
        os.makedirs(dest, exist_ok=True)
        apks = []
        try:
            with zipfile.ZipFile(input_path, 'r') as z:
                for name in z.namelist():
                    if name.lower().endswith('.apk'):
                        safe = os.path.basename(name)  # zip-slip guard
                        if not safe:
                            continue
                        tp = os.path.join(dest, safe)
                        with z.open(name) as src, open(tp, 'wb') as dst:
                            shutil.copyfileobj(src, dst)
                        apks.append(tp)
        except Exception as e:
            print(f"\033[91m[-] Failed to read bundle {input_path}: {e}\033[0m")
        return apks
    if ext == '.apk':
        return [input_path]
    return []


# ─────────────────────────────────────────────
#  HOST IP AUTO-DETECTION   — Added by CaptainHacX
# ─────────────────────────────────────────────

def detect_host_ip():
    """Best-effort LAN IP of this machine. Uses a UDP socket 'connect' which
    selects a source interface WITHOUT sending any packets. Returns None on
    failure (offline, etc.)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))  # no traffic is sent for a UDP connect
            ip = s.getsockname()[0]
        finally:
            s.close()
        if ip and not ip.startswith('127.'):
            return ip
    except Exception:
        pass
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if ip and not ip.startswith('127.'):
            return ip
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────
#  PROTECTION / RASP SCANNER   — Added by CaptainHacX
# ─────────────────────────────────────────────

def scan_protections(targets, platform):
    """Fingerprint known anti-tamper / RASP / root-detection protections inside
    the app so the operator is warned BEFORE hitting a runtime crash.
    `targets` is a list of APK/IPA paths (base + splits). Read-only (inspects
    zip entries + dex/binary strings). Returns a list of (name, desc, strategy)."""
    if isinstance(targets, str):
        targets = [targets]

    # name -> (description, strategy)
    STRATEGY = {
        'Google PAIRIP':        ('VM-based anti-tamper + anti-Frida + anti-repackaging',
                                 'Expect Frida detection & repackaging blocks. Try Magisk DenyList+Zygisk+Shamiko, a stealth/renamed frida-server on a custom port, or an older app version.'),
        'Talsec / freeRASP':    ('RASP: root/hook/debugger/emulator detection',
                                 'Hide root (Magisk DenyList+Shamiko) and run frida-server stealthily; freeRASP also flags Frida.'),
        'Promon SHIELD':        ('Commercial app shielding / anti-tamper',
                                 'Strong anti-instrumentation; Magisk hiding + stealth Frida, expect resistance.'),
        'Appdome':              ('No-code app shielding (root/Frida/repackage detection)',
                                 'Magisk hiding + stealth Frida; repackaging is blocked.'),
        'DexGuard':             ('GuardSquare RASP + obfuscation',
                                 'May detect hooks/root; hide root and instrument carefully.'),
        'JailMonkey':           ('Root/jailbreak detection plugin',
                                 'Handled at runtime by the generated script + Magisk hiding.'),
        'flutter_jailbreak_detection': ('Flutter root/jailbreak plugin (uses RootBeer)',
                                 'Handled by the generated script (RootBeer hooks).'),
        'RootBeer':             ('Java root-detection library',
                                 'Handled by the generated script (RootBeer hooks).'),
        'IOSSecuritySuite':     ('iOS jailbreak/debugger/hook detection',
                                 'Hook its checks at runtime; use a jailbreak-hiding tweak (e.g. Shadow/A-Bypass).'),
        'TrustKit':             ('iOS certificate pinning framework',
                                 'Pinning also enforced natively; the SSL hook + a TrustKit bypass may both be needed.'),
    }
    HARD = {'Google PAIRIP', 'Talsec / freeRASP', 'Promon SHIELD', 'Appdome', 'DexGuard'}

    NATIVE = {
        'libpairipcore.so':   'Google PAIRIP',
        'libtoolchecker.so':  'Talsec / freeRASP',
        'libTalsecRuntime.so':'Talsec / freeRASP',
        'libshield.so':       'Promon SHIELD',
        'libdexguard.so':     'DexGuard',
        'libjailmonkey.so':   'JailMonkey',
    }
    DEX = {
        b'com/scottyab/rootbeer':          'RootBeer',
        b'gantix/jailmonkey':              'JailMonkey',
        b'flutter_jailbreak_detection':    'flutter_jailbreak_detection',
        b'com/aheaditec/talsec':           'Talsec / freeRASP',
    }

    findings = {}  # name -> (desc, strat), dedup by name

    for tgt in targets:
        try:
            with zipfile.ZipFile(tgt, 'r') as z:
                names = z.namelist()
                basenames = {nm.split('/')[-1] for nm in names}

                for lib, nm in NATIVE.items():
                    if lib in basenames and nm not in findings:
                        findings[nm] = STRATEGY.get(nm, ('native protection library', 'Investigate manually.'))

                lowered = [nm.lower() for nm in names]
                if any('appdome' in nm for nm in lowered) and 'Appdome' not in findings:
                    findings['Appdome'] = STRATEGY['Appdome']
                if platform == 'ios':
                    for marker, nm in [('iossecuritysuite', 'IOSSecuritySuite'),
                                       ('trustkit', 'TrustKit'),
                                       ('talsec', 'Talsec / freeRASP')]:
                        if any(marker in p for p in lowered) and nm not in findings:
                            findings[nm] = STRATEGY.get(nm, ('iOS protection', 'Investigate manually.'))

                if platform == 'android':
                    dex_entries = [nm for nm in names
                                   if re.match(r'^classes\d*\.dex$', nm.split('/')[-1])]
                    for dn in dex_entries:
                        try:
                            blob = z.read(dn)
                        except Exception:
                            continue
                        for marker, nm in DEX.items():
                            if nm not in findings and marker in blob:
                                findings[nm] = STRATEGY.get(nm, ('detected in dex', 'Investigate manually.'))
        except Exception as e:
            print(f"\033[93m[!] Protection scan skipped for {os.path.basename(str(tgt))}: {e}\033[0m")
            continue

    # ---- report ----
    print("")
    print(box_top())
    print(box_line("        PROTECTION / RASP SCAN", C_YELLOW))
    print(box_bottom())
    if not findings:
        print(f"\033[92m[+]\033[0m No known protections detected (root/RASP/anti-tamper).")
        return []

    result = []
    hard_hit = False
    for nm, (desc, strat) in findings.items():
        hard = nm in HARD
        hard_hit = hard_hit or hard
        tag = f"{C_RED}[HARD]{C_RESET}" if hard else f"{C_YELLOW}[soft]{C_RESET}"
        print(f"{tag} {C_PURPLE}{nm}{C_RESET} — {desc}")
        print(f"       {C_GREY}strategy:{C_RESET} {strat}")
        result.append((nm, desc, strat))

    if hard_hit:
        print(f"\n{C_RED}[!] Commercial anti-tamper present — dynamic instrumentation may crash "
              f"the app (e.g. SIGSEGV in the protection lib). Read the per-item strategy above.{C_RESET}")
    return result


# ─────────────────────────────────────────────
#  ANDROID — EXTRACT libflutter.so
# ─────────────────────────────────────────────

def extract_flutter_android(apks, out_dir):
    """Find & extract libflutter.so from a list of APK paths (base + splits).
    Searches every APK and every ABI, preferring arm64-v8a.
    Returns (so_path, abi) or (None, None).
    Added by CaptainHacX: multi-APK / multi-ABI search (was arm64-only, single APK)."""
    if not apks:
        print("\033[91m[-] No .apk found in the given input.\033[0m")
        return None, None

    print(f"\033[96m[*]\033[0m Searching {len(apks)} APK(s) for libflutter.so ...")
    found = {}  # abi -> (apk_path, entry_name)
    for ap in apks:
        try:
            with zipfile.ZipFile(ap, 'r') as z:
                for name in z.namelist():
                    m = re.match(r'lib/([^/]+)/libflutter\.so$', name)
                    if m and m.group(1) not in found:
                        found[m.group(1)] = (ap, name)
        except Exception:
            continue

    if not found:
        print("\033[91m[-] libflutter.so not found in any APK.\033[0m")
        print("\033[93m    If this is a split app, the native lib lives in the ABI split "
              "(split_config.*_v8a.apk). Pass the whole bundle/folder, or use --from-device.\033[0m")
        return None, None

    order = ABI_PREFERENCE + [a for a in found if a not in ABI_PREFERENCE]
    for abi in order:
        if abi not in found:
            continue
        ap, name = found[abi]
        so_path = os.path.join(out_dir, 'libflutter.so')
        try:
            with zipfile.ZipFile(ap, 'r') as z, z.open(name) as src, open(so_path, 'wb') as dst:
                shutil.copyfileobj(src, dst)
        except Exception as e:
            print(f"\033[91m[-] Failed to extract {name}: {e}\033[0m")
            return None, None
        print(f"\033[92m[+]\033[0m Found libflutter.so [{abi}] in {os.path.basename(ap)}")
        print(f"\033[92m[+]\033[0m Available ABIs: {', '.join(found.keys())}")
        if abi != 'arm64-v8a':
            print(f"\033[93m[!] Selected '{abi}' (no arm64-v8a present). Offset auto-detection "
                  f"supports arm64-v8a only; the binary is extracted for manual analysis.\033[0m")
        return so_path, abi
    return None, None


# ─────────────────────────────────────────────
#  iOS — EXTRACT Flutter framework binary
# ─────────────────────────────────────────────

def extract_flutter_ios(ipa_path, out_dir):
    fw_path = os.path.join(out_dir, 'Flutter')
    print(f"\033[96m[*]\033[0m Extracting Flutter framework from IPA...")
    with zipfile.ZipFile(ipa_path, 'r') as z:
        for name in z.namelist():
            if re.search(r'Payload/[^/]+\.app/Frameworks/Flutter\.framework/Flutter$', name):
                print(f"\033[92m[+]\033[0m Found: {name}")
                with z.open(name) as src, open(fw_path, 'wb') as dst:
                    dst.write(src.read())
                return fw_path
    print("\033[91m[-] Flutter.framework/Flutter not found — is this a Flutter IPA?\033[0m")
    return None


# ─────────────────────────────────────────────
#  ELF SEGMENT PARSER (Android ARM64)
# ─────────────────────────────────────────────

def parse_elf_segments(data, verbose=True):
    """Returns (base_vaddr, code_foff, code_vaddr, code_filesz) for the executable segment."""
    if data[:4] != b'\x7fELF':
        return None, None, None, None

    e_phoff     = struct.unpack_from('<Q', data, 0x20)[0]
    e_phentsize = struct.unpack_from('<H', data, 0x36)[0]
    e_phnum     = struct.unpack_from('<H', data, 0x38)[0]

    base_vaddr = None
    code_foff = code_vaddr = code_filesz = None
    
    for i in range(e_phnum):
        ph      = data[e_phoff + i*e_phentsize : e_phoff + (i+1)*e_phentsize]
        p_type  = struct.unpack_from('<I', ph, 0x00)[0]
        p_flags = struct.unpack_from('<I', ph, 0x04)[0]
        p_offset = struct.unpack_from('<Q', ph, 0x08)[0]
        p_vaddr  = struct.unpack_from('<Q', ph, 0x10)[0]

        # PT_LOAD
        if p_type == 1:
            if p_offset == 0 and base_vaddr is None:
                base_vaddr = p_vaddr
            # PF_X
            if (p_flags & 1):
                seg_filesz = struct.unpack_from('<Q', ph, 0x20)[0]
                if verbose:
                    print(f"\033[96m[*]\033[0m ELF code segment: file={hex(p_offset)} vaddr={hex(p_vaddr)} size={hex(seg_filesz)}")
                # Added by CaptainHacX: a .so can have multiple executable PT_LOAD
                # segments; keep the LARGEST one (the real .text), not the last parsed.
                if code_filesz is None or seg_filesz > code_filesz:
                    code_foff, code_vaddr, code_filesz = p_offset, p_vaddr, seg_filesz

    if code_foff is not None and verbose:
        print(f"\033[92m[+]\033[0m Selected code segment: file={hex(code_foff)} vaddr={hex(code_vaddr)} size={hex(code_filesz)}")

    if base_vaddr is None:
        base_vaddr = 0
        
    return base_vaddr, code_foff, code_vaddr, code_filesz


# ─────────────────────────────────────────────
#  MACH-O SEGMENT PARSER (iOS ARM64)
# ─────────────────────────────────────────────

def parse_macho_segments(data):
    """Returns (base_vaddr, code_foff, code_vaddr, code_filesz, data) for __TEXT executable segment.
    Always returns a 5-tuple; data may be a sliced arm64 view of a fat binary."""

    MH_MAGIC_64    = 0xFEEDFACF  # 64-bit little-endian
    FAT_MAGIC      = 0xCAFEBABE  # Fat binary (big-endian)
    LC_SEGMENT_64  = 0x19

    magic = struct.unpack_from('<I', data, 0)[0]

    # Handle fat binary — extract arm64 slice
    if struct.unpack_from('>I', data, 0)[0] == FAT_MAGIC:
        print(f"\033[96m[*]\033[0m Detected fat binary — extracting arm64 slice")
        nfat = struct.unpack_from('>I', data, 4)[0]
        for i in range(nfat):
            off = 8 + i * 20
            cputype      = struct.unpack_from('>I', data, off)[0]
            slice_offset = struct.unpack_from('>I', data, off + 8)[0]
            slice_size   = struct.unpack_from('>I', data, off + 12)[0]
            # ARM64 cputype = 0x0100000C
            if cputype == 0x0100000C:
                print(f"\033[92m[+]\033[0m arm64 slice found at offset {hex(slice_offset)}")
                data = data[slice_offset:slice_offset + slice_size]
                magic = struct.unpack_from('<I', data, 0)[0]
                break

    if magic != MH_MAGIC_64:
        print(f"\033[91m[-] Not a valid Mach-O 64-bit binary (magic={hex(magic)})\033[0m")
        return None, None, None, None, data

    ncmds    = struct.unpack_from('<I', data, 16)[0]
    cmd_off  = 32  # sizeof mach_header_64

    base_vaddr = None
    code_foff = code_vaddr = code_filesz = None

    for _ in range(ncmds):
        cmd     = struct.unpack_from('<I', data, cmd_off)[0]
        cmdsize = struct.unpack_from('<I', data, cmd_off + 4)[0]

        if cmd == LC_SEGMENT_64:
            # segname is 16 bytes at offset +8
            segname  = data[cmd_off + 8 : cmd_off + 24].rstrip(b'\x00').decode('utf-8', errors='ignore')
            vmaddr   = struct.unpack_from('<Q', data, cmd_off + 24)[0]
            vmsize   = struct.unpack_from('<Q', data, cmd_off + 32)[0]
            fileoff  = struct.unpack_from('<Q', data, cmd_off + 40)[0]
            filesize = struct.unpack_from('<Q', data, cmd_off + 48)[0]
            maxprot  = struct.unpack_from('<I', data, cmd_off + 56)[0]
            
            if fileoff == 0 and base_vaddr is None:
                base_vaddr = vmaddr

            # __TEXT segment with execute permission (VM_PROT_EXECUTE = 4)
            if segname == '__TEXT' and (maxprot & 4):
                code_foff   = fileoff
                code_vaddr  = vmaddr
                code_filesz = filesize
                print(f"\033[96m[*]\033[0m Mach-O __TEXT segment: file={hex(fileoff)} vaddr={hex(vmaddr)} size={hex(filesize)}")

        cmd_off += cmdsize
        
    if base_vaddr is None:
        base_vaddr = 0

    return base_vaddr, code_foff, code_vaddr, code_filesz, data  # return possibly-sliced data


# ─────────────────────────────────────────────
#  OFFSET CACHE + KNOWN-ENGINE DB   — Added by CaptainHacX
# ─────────────────────────────────────────────
#
# The cache key is the SHA-256 of the exact libflutter.so bytes: identical bytes
# => identical offset, so a hit is provably correct. Entries are additionally
# byte-verified (Android) before use, so a corrupt/poisoned cache can never
# produce a wrong hook — it just falls back to a full rescan.

_CACHE_DIR  = os.path.join(os.path.expanduser('~'), '.kill_flutter')
_CACHE_FILE = os.path.join(_CACHE_DIR, 'offset_cache.json')
_BUNDLED_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'known_offsets.json')


def _sha256_file(path):
    """Stream SHA-256 of a file. Returns hex digest or None on error."""
    try:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 20), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def _read_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _valid_cache_entry(entry):
    """Schema-check a cache entry so garbage can never reach the hook path."""
    if not isinstance(entry, dict):
        return False
    off = entry.get('offset')
    sig = entry.get('sig', '')
    try:
        if not isinstance(off, str) or int(off, 16) < 0:
            return False
        if sig and (len(sig) % 2 or bytes.fromhex(sig) is None):
            return False
    except Exception:
        return False
    return True


def _lookup_offset(sha):
    """Look up an offset entry by binary hash: user cache first, then the
    bundled read-only DB. Returns a validated entry dict or None."""
    if not sha:
        return None
    for store in (_read_json(_CACHE_FILE), _read_json(_BUNDLED_DB)):
        entry = store.get(sha)
        if entry and _valid_cache_entry(entry):
            return entry
    return None


def _save_offset(sha, entry):
    """Persist an entry to the user cache atomically. Never raises."""
    if not sha or not _valid_cache_entry(entry):
        return
    try:
        os.makedirs(_CACHE_DIR, mode=0o700, exist_ok=True)
        store = _read_json(_CACHE_FILE)
        store[sha] = entry
        tmp = _CACHE_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(store, f, indent=2, sort_keys=True)
        os.replace(tmp, _CACHE_FILE)
    except Exception:
        pass  # cache is best-effort; never break the run


def _verify_cached_offset(data, platform, rva, sig_hex):
    """Confirm the cached offset really points at the expected prologue bytes.
    Android: maps RVA->file offset via the ELF segments and compares. Other
    platforms: require the signature bytes to be present in the binary."""
    try:
        sig = bytes.fromhex(sig_hex) if sig_hex else b''
    except Exception:
        return False
    if len(sig) < 4:
        return False
    if platform == 'android':
        base_vaddr, code_foff, code_vaddr, code_filesz = parse_elf_segments(data, verbose=False)
        if code_foff is None:
            return False
        foff = (rva + base_vaddr) - code_vaddr + code_foff
        if foff < 0 or foff + len(sig) > len(data):
            return False
        return data[foff:foff + len(sig)] == sig
    return sig in data


# ─────────────────────────────────────────────
#  CORE — FIND SSL OFFSET (shared for both platforms)
# ─────────────────────────────────────────────

def find_offset(binary_path, platform, use_cache=True, refresh_cache=False):
    print(f"\033[96m[*]\033[0m Loading binary: {binary_path}")
    with open(binary_path, 'rb') as f:
        data = f.read()

    # Added by CaptainHacX: arch gate (Android/ELF). The ADRP+ADD scanner is
    # AArch64-only; refuse other architectures rather than emit a wrong offset.
    if platform == 'android' and len(data) >= 0x14 and data[:4] == b'\x7fELF':
        ei_class  = data[4]                                    # 1=32-bit, 2=64-bit
        e_machine = struct.unpack_from('<H', data, 0x12)[0]    # 0xB7 = AArch64
        if ei_class != 2 or e_machine != 0xB7:
            names = {0x28: 'ARM (32-bit)', 0x3E: 'x86-64', 0x03: 'x86', 0xB7: 'AArch64'}
            arch = names.get(e_machine, f'machine=0x{e_machine:x}')
            klass = '64-bit' if ei_class == 2 else '32-bit'
            print(f"\033[91m[-] Offset auto-detection supports arm64-v8a (AArch64) only.\033[0m")
            print(f"\033[93m    This binary is {klass} {arch}. Use an arm64-v8a build/device, "
                  f"or analyze it manually.\033[0m")
            return None

    # Added by CaptainHacX: offset cache / known-engine DB lookup (keyed by the
    # binary's SHA-256). A hit skips the expensive ADRP scan entirely.
    sha = _sha256_file(binary_path)
    if use_cache and not refresh_cache and sha:
        entry = _lookup_offset(sha)
        if entry:
            rva = int(entry['offset'], 16)
            if _verify_cached_offset(data, platform, rva, entry.get('sig', '')):
                print(f"\033[92m[+]\033[0m Cache hit ({sha[:12]}…) — SSL verify offset (RVA): "
                      f"\033[93m{hex(rva)}\033[0m")
                return rva
            else:
                print(f"\033[93m[!] Cached entry failed byte-verification — rescanning.\033[0m")

    # Find string anchors
    ssl_client = [m.start() for m in re.finditer(b'ssl_client\x00', data)]
    ssl_server  = [m.start() for m in re.finditer(b'ssl_server\x00', data)]

    if not ssl_client or not ssl_server:
        print("\033[91m[-] ssl_client/ssl_server strings not found — may not be a Flutter binary\033[0m")
        return None

    print(f"\033[92m[+]\033[0m ssl_client @ {[hex(x) for x in ssl_client]}")
    print(f"\033[92m[+]\033[0m ssl_server @ {[hex(x) for x in ssl_server]}")

    # Parse segments based on platform
    if platform == 'android':
        base_vaddr, code_foff, code_vaddr, code_filesz = parse_elf_segments(data)
    else:
        base_vaddr, code_foff, code_vaddr, code_filesz, data = parse_macho_segments(data)
        # Re-find strings in possibly-sliced data
        ssl_client = [m.start() for m in re.finditer(b'ssl_client\x00', data)]
        ssl_server  = [m.start() for m in re.finditer(b'ssl_server\x00', data)]
        if not ssl_client or not ssl_server:
            print("\033[91m[-] ssl_client/ssl_server strings not found in arm64 slice\033[0m")
            return None

    if code_foff is None:
        print("\033[91m[-] No executable segment found\033[0m")
        return None

    def foff_to_vaddr(fo):
        return fo - code_foff + code_vaddr
        
    def foff_to_rva(fo):
        return (fo - code_foff + code_vaddr) - base_vaddr

    def find_refs(target_va):
        lo12 = target_va & 0xfff
        refs = []
        for fi in range(code_foff, code_foff + code_filesz - 4, 4):
            instr = struct.unpack_from('<I', data, fi)[0]
            if (instr & 0xffc00000) == 0x91000000 and ((instr >> 10) & 0xfff) == lo12:
                if fi >= 4:
                    adrp = struct.unpack_from('<I', data, fi - 4)[0]
                    if (adrp & 0x9f000000) == 0x90000000:
                        immlo = (adrp >> 29) & 0x3
                        immhi = (adrp >> 5) & 0x7ffff
                        imm = ((immhi << 2) | immlo) << 12
                        if imm & (1 << 32):
                            imm -= (1 << 33)
                        pc_va = foff_to_vaddr(fi - 4)
                        if (pc_va & ~0xfff) + imm == (target_va & ~0xfff):
                            refs.append(fi)
        return refs

    print(f"\033[96m[*]\033[0m Scanning ADRP+ADD refs... (may take a moment)")
    sc_refs = find_refs(ssl_client[0])
    ss_refs = find_refs(ssl_server[0])
    print(f"\033[96m[*]\033[0m ssl_client code refs: {[hex(x) for x in sc_refs]}")
    print(f"\033[96m[*]\033[0m ssl_server code refs: {[hex(x) for x in ss_refs]}")

    for a in sc_refs:
        for b in ss_refs:
            if abs(a - b) < 0x800:
                start = min(a, b)
                for i in range(start, max(code_foff, start - 0x300), -4):
                    instr = struct.unpack_from('<I', data, i)[0]
                    if (instr & 0xff8003ff) == 0xd10003ff or (instr & 0xffe07fff) == 0xa9007bfd:
                        rva = foff_to_rva(i)
                        print(f"\033[92m[+]\033[0m SSL verify offset (RVA): \033[93m{hex(rva)}\033[0m")
                        print(f"\033[92m[+]\033[0m First bytes: {data[i:i+16].hex(' ')}")
                        # Added by CaptainHacX: persist to the offset cache
                        if use_cache and sha:
                            _save_offset(sha, {'offset': hex(rva), 'sig': data[i:i+16].hex(),
                                               'platform': platform})
                        return rva

    print("\033[91m[-] Could not find SSL verify function\033[0m")
    return None


# ─────────────────────────────────────────────
#  FRIDA SCRIPT GENERATOR
# ─────────────────────────────────────────────

def write_frida_script(offset, package, platform, out_path):
    # Added by CaptainHacX: emits a COMBINED script (SSL pinning + root/anti-Frida
    # bypass) with a Frida-17 export resolver, instead of the original SSL-only one.
    # Module name differs between platforms
    module_name = 'libflutter.so' if platform == 'android' else 'Flutter'

    config = f"""// ================================================
// K!ll Fl!utter - Combined bypass (SSL pinning + root/anti-Frida)
// By: f3rb
// Platform : {platform.upper()}
// Package  : {package}
// Offset   : {hex(offset)}
// Module   : {module_name}
// ================================================
//
// Best-effort. Simple/RootBeer-style checks are handled here. Commercial RASP
// (Talsec/freeRASP, Appdome, Promon) may still win — do Magisk DenyList +
// Zygisk + Shamiko hiding first.
//
// Toggle these if the app becomes unstable:
var ENABLE_SSL_BYPASS   = true;
var ENABLE_ROOT_BYPASS  = true;
var ENABLE_FRIDA_HIDE   = true;
var ENABLE_TLS_UNPIN    = true;   // Added by CaptainHacX: OkHttp/TrustManager (hybrid apps)

// ---- auto-filled by kill_flutter.py ----
var SSL_VERIFY_OFFSET = {hex(offset)};
var FLUTTER_MODULE    = "{module_name}";
// ----------------------------------------
"""

    body = r'''
function log(m) { console.log("[kill_flutter] " + m); }

var ROOT_TOKENS = [
    "magisk", "supersu", "superuser", "/sbin/su", "/system/xbin/su",
    "/system/bin/su", "/system/app/superuser", "daemonsu", "busybox",
    "xposed", "substrate", "/su/bin", "/system/sd/xbin", "/system/bin/failsafe",
    "/data/local/su", "/data/local/bin/su", "/data/local/xbin/su", "magisk.db",
    "/sbin/.magisk", "test-keys"
];
var FRIDA_TOKENS = ["frida", "gum-js", "gadget", "linjector", "re.frida", "/data/local/tmp"];

function tokenHit(path, list) {
    if (path === null || path === undefined) return false;
    var p = ("" + path).toLowerCase();
    for (var i = 0; i < list.length; i++) { if (p.indexOf(list[i]) !== -1) return true; }
    return false;
}
function pathIsBlocked(path) {
    if (tokenHit(path, ROOT_TOKENS)) return true;
    if (ENABLE_FRIDA_HIDE && tokenHit(path, FRIDA_TOKENS)) return true;
    return false;
}

// Added by CaptainHacX: resolve a libc export across Frida versions. Frida 17
// removed the static Module.findExportByName(null, name); the replacement is
// Module.findGlobalExportByName(name).
function resolveExport(name) {
    try { if (typeof Module.findGlobalExportByName === "function") return Module.findGlobalExportByName(name); } catch (e) {}
    try { if (typeof Module.getGlobalExportByName === "function") return Module.getGlobalExportByName(name); } catch (e) {}
    try { if (typeof Module.findExportByName === "function") return Module.findExportByName(null, name); } catch (e) {}
    return null;
}

// ---------------- SSL PINNING BYPASS ----------------
function hookSslVerify() {
    if (!ENABLE_SSL_BYPASS) return;
    var tries = 0;
    var iv = setInterval(function () {
        var m = Process.findModuleByName(FLUTTER_MODULE);
        if (m) {
            clearInterval(iv);
            var addr = m.base.add(SSL_VERIFY_OFFSET);
            log("[ssl] " + FLUTTER_MODULE + " base " + m.base + " -> hook " + addr);
            try {
                Interceptor.attach(addr, { onLeave: function (retval) { retval.replace(ptr("0x1")); } });
                log("[ssl] pinning bypass installed");
            } catch (e) { log("[ssl] attach failed: " + e); }
        } else if (++tries > 150) {
            clearInterval(iv);
            log("[ssl] " + FLUTTER_MODULE + " not found after waiting");
        }
    }, 100);
}

// ---------------- NATIVE (libc) ROOT/FRIDA PROBES ----------------
function hookLibc() {
    if (!ENABLE_ROOT_BYPASS && !ENABLE_FRIDA_HIDE) return;
    var fns = ["fopen", "open", "openat", "access", "faccessat", "stat", "lstat", "__xstat", "__lxstat"];
    fns.forEach(function (fn) {
        var p = resolveExport(fn);
        if (p === null) return;
        try {
            Interceptor.attach(p, {
                onEnter: function (args) {
                    var idx = (fn === "openat" || fn === "faccessat" || fn === "__xstat" || fn === "__lxstat") ? 1 : 0;
                    try { this.path = args[idx].readCString(); } catch (e) { this.path = null; }
                    this.blk = pathIsBlocked(this.path);
                },
                onLeave: function (retval) {
                    if (this.blk) {
                        if (fn === "fopen") retval.replace(ptr(0));
                        else retval.replace(ptr(-1));
                    }
                }
            });
        } catch (e) {}
    });
    log("[native] libc path probes hooked");
}

// ---------------- JAVA ROOT/FRIDA DETECTION ----------------
function hookJava() {
    if (typeof Java === "undefined" || !Java.available) { log("[java] not available"); return; }
    Java.perform(function () {
        try {
            var JFile = Java.use("java.io.File");
            JFile.exists.implementation = function () {
                try { if (pathIsBlocked(this.getAbsolutePath())) return false; } catch (e) {}
                return this.exists();
            };
        } catch (e) {}

        try {
            var Runtime = Java.use("java.lang.Runtime");
            var IOE = Java.use("java.io.IOException");
            function looksLikeRootCmd(s) {
                if (!s) return false;
                s = ("" + s).toLowerCase();
                return s === "su" || s.indexOf("su ") !== -1 || s.indexOf("/su") !== -1 ||
                       s.indexOf("which") !== -1 || s.indexOf("mount") !== -1 ||
                       s.indexOf("getprop") !== -1 || tokenHit(s, ROOT_TOKENS);
            }
            var execStr = Runtime.exec.overload('java.lang.String');
            execStr.implementation = function (cmd) {
                if (looksLikeRootCmd(cmd)) { log("[java] blocked exec: " + cmd); throw IOE.$new("not found"); }
                return execStr.call(this, cmd);
            };
            var execArr = Runtime.exec.overload('[Ljava.lang.String;');
            execArr.implementation = function (arr) {
                try {
                    var joined = "";
                    for (var i = 0; i < arr.length; i++) joined += arr[i] + " ";
                    if (looksLikeRootCmd(joined)) { log("[java] blocked exec[]: " + joined); throw IOE.$new("not found"); }
                } catch (e) { if (e.message && e.message.indexOf("not found") !== -1) throw e; }
                return execArr.call(this, arr);
            };
        } catch (e) {}

        try {
            var PM = Java.use("android.app.ApplicationPackageManager");
            var NNFE = Java.use("android.content.pm.PackageManager$NameNotFoundException");
            var rootPkgs = [
                "com.topjohnwu.magisk", "eu.chainfire.supersu", "com.noshufou.android.su",
                "com.noshufou.android.su.elite", "com.koushikdutta.superuser",
                "com.thirdparty.superuser", "com.yellowes.su", "com.zachspong.temprootremovejb",
                "com.ramdroid.appquarantine", "de.robv.android.xposed.installer",
                "io.va.exposed", "com.saurik.substrate"
            ];
            var gpi = PM.getPackageInfo.overload('java.lang.String', 'int');
            gpi.implementation = function (pkg, flags) {
                if (rootPkgs.indexOf(pkg) !== -1) { log("[java] hiding pkg: " + pkg); throw NNFE.$new(pkg); }
                return gpi.call(this, pkg, flags);
            };
        } catch (e) {}

        try { Java.use("android.os.Build").TAGS.value = "release-keys"; } catch (e) {}

        try {
            var RB = Java.use("com.scottyab.rootbeer.RootBeer");
            var meths = ["isRooted", "isRootedWithoutBusyBoxCheck", "isRootedWithBusyBoxCheck",
                "checkForSuBinary", "checkForDangerousProps", "checkForBusyBoxBinary",
                "checkForMagiskBinary", "checkSuExists", "detectRootManagementApps",
                "detectPotentiallyDangerousApps", "detectTestKeys", "checkForRWPaths",
                "checkForRootNative", "detectRootCloakingApps"];
            meths.forEach(function (mm) { try { if (RB[mm]) RB[mm].implementation = function () { return false; }; } catch (e) {} });
            log("[java] RootBeer neutralized");
        } catch (e) {}

        log("[java] hooks installed");
    });
}

// ---------------- TLS UNPINNING (Java layer: OkHttp / TrustManager) ----------------
// Added by CaptainHacX: covers hybrid Flutter apps that pin at the Java layer
// (OkHttp CertificatePinner, Conscrypt TrustManagerImpl, custom TrustManagers,
// the http_certificate_pinning plugin). Every hook is independently guarded so a
// missing class is a no-op and can never break the native SSL/root hooks.
function hookTls() {
    if (!ENABLE_TLS_UNPIN) return;
    if (typeof Java === "undefined" || !Java.available) return;
    Java.perform(function () {

        // OkHttp3 CertificatePinner.check(...) -> no-op (all overloads)
        try {
            var CP = Java.use("okhttp3.CertificatePinner");
            CP.check.overloads.forEach(function (ov) {
                try {
                    ov.implementation = function () {
                        log("[tls] okhttp CertificatePinner.check bypassed");
                        return;
                    };
                } catch (e) {}
            });
        } catch (e) {}

        // Conscrypt TrustManagerImpl.verifyChain(...) -> return the chain (trusted)
        try {
            var TMI = Java.use("com.android.org.conscrypt.TrustManagerImpl");
            if (TMI.verifyChain) {
                TMI.verifyChain.implementation = function (untrustedChain, trustAnchorChain,
                                                           host, clientAuth, ocspData, tlsSctData) {
                    log("[tls] conscrypt verifyChain bypassed (" + host + ")");
                    return untrustedChain;
                };
            }
        } catch (e) {}

        // Inject a trust-all X509TrustManager via SSLContext.init(...)
        try {
            var X509TM = Java.use("javax.net.ssl.X509TrustManager");
            var SSLContext = Java.use("javax.net.ssl.SSLContext");
            var TrustAll = Java.registerClass({
                name: "com.killflutter.TrustAll",
                implements: [X509TM],
                methods: {
                    checkClientTrusted: function (chain, authType) {},
                    checkServerTrusted: function (chain, authType) {},
                    getAcceptedIssuers: function () { return []; }
                }
            });
            var init = SSLContext.init.overload(
                '[Ljavax.net.ssl.KeyManager;', '[Ljavax.net.ssl.TrustManager;', 'java.security.SecureRandom');
            init.implementation = function (km, tm, sr) {
                log("[tls] SSLContext.init -> trust-all TrustManager");
                init.call(this, km, [TrustAll.$new()], sr);
            };
        } catch (e) {}

        // HostnameVerifier -> allow all
        try {
            var HUC = Java.use("javax.net.ssl.HttpsURLConnection");
            try { HUC.setDefaultHostnameVerifier.implementation = function (v) { log("[tls] setDefaultHostnameVerifier ignored"); }; } catch (e) {}
            try { HUC.setHostnameVerifier.implementation = function (v) { log("[tls] setHostnameVerifier ignored"); }; } catch (e) {}
        } catch (e) {}

        log("[tls] Java-layer unpinning installed");
    });
}

// ---------------- RUN ----------------
try { hookLibc(); } catch (e) { log("libc error: " + e); }
try { hookJava(); } catch (e) { log("java error: " + e); }
try { hookTls(); } catch (e) { log("tls error: " + e); }
hookSslVerify();
log("bypass loaded");
'''

    with open(out_path, 'w') as f:
        f.write(config + body)
    print(f"\033[92m[+]\033[0m Frida script saved: \033[93m{out_path}\033[0m")


# ─────────────────────────────────────────────
#  ANDROID — FRIDA-SERVER PRE-FLIGHT CHECK   — Added by CaptainHacX
# ─────────────────────────────────────────────

def preflight_frida_check(package):
    """Android only. Verify the on-device frida-server exists, matches the host
    frida version + device arch, and is running. If not, print the exact fix so
    the user never sees the cryptic 'need Gadget to attach on jailed Android'
    error. Best-effort and non-fatal: silently skips if adb/device is absent."""

    def run(args):
        try:
            return subprocess.run(args, capture_output=True, text=True, timeout=15)
        except Exception:
            return None

    print("")
    print(box_top())
    print(box_line("        FRIDA PRE-FLIGHT CHECK (device)", C_YELLOW))
    print(box_bottom())

    if run(['adb', 'version']) is None:
        print(f"{C_YELLOW}[!] adb not on PATH — skipping device pre-flight.{C_RESET}")
        return

    # Online devices
    r = run(['adb', 'devices'])
    serials = []
    if r:
        for line in r.stdout.splitlines()[1:]:
            line = line.strip()
            if '\t' in line:
                s, state = (line.split('\t') + [''])[:2]
                if state.strip() == 'device':
                    serials.append(s)
    if not serials:
        print(f"{C_YELLOW}[!] No online adb device — connect/authorize it, then run frida.{C_RESET}")
        return
    serial = os.environ.get('ANDROID_SERIAL') or serials[0]
    if len(serials) > 1:
        print(f"{C_YELLOW}[!] Multiple devices attached; using '{serial}'. Set ANDROID_SERIAL to override.{C_RESET}")

    def dev(cmd):
        # Run cmd via `su -c` on the device (cmd must not contain single quotes).
        return run(['adb', '-s', serial, 'shell', "su -c '" + cmd + "'"])

    # Host frida version
    host_ver = None
    r = run(['frida', '--version'])
    if r and r.returncode == 0:
        host_ver = r.stdout.strip()
    else:
        print(f"{C_YELLOW}[!] 'frida' not on PATH — install with: pip install frida-tools{C_RESET}")

    # Device ABI -> frida arch name
    r = run(['adb', '-s', serial, 'shell', 'getprop ro.product.cpu.abi'])
    abi = (r.stdout.strip() if r else '') or 'arm64-v8a'
    want_arch = {'arm64-v8a': 'arm64', 'armeabi-v7a': 'arm',
                 'x86_64': 'x86_64', 'x86': 'x86'}.get(abi, 'arm64')

    # Installed frida-server binaries in /data/local/tmp
    r = dev('ls /data/local/tmp/frida-server* 2>/dev/null')
    installed = [l.strip() for l in (r.stdout.splitlines() if r else []) if l.strip()
                 and 'No such' not in l and 'not found' not in l]

    # Running?
    r = dev('pgrep -f frida-server 2>/dev/null || ps -A 2>/dev/null | grep frida-server')
    running = bool(r and r.stdout.strip())

    problems = []
    match_found = False
    if not installed:
        problems.append("no frida-server found in /data/local/tmp")
    else:
        for fn in installed:
            m = re.search(r'frida-server-([0-9]+\.[0-9]+\.[0-9]+)-(?:android-)?([a-z0-9_]+)', fn)
            v, a = (m.group(1), m.group(2)) if m else (None, None)
            print(f"{C_CYAN}[*]{C_RESET} On device: {fn}  (version={v}, arch={a})")
            if host_ver and v == host_ver and a == want_arch:
                match_found = True
        if host_ver and not match_found:
            problems.append(f"no frida-server matching host {host_ver} / {want_arch}")
    if installed and not running:
        problems.append("frida-server is not running")

    if host_ver:
        print(f"{C_CYAN}[*]{C_RESET} Host frida: {host_ver}   Device abi: {abi} -> need arch '{want_arch}'")

    if not problems and running:
        print(f"{C_GREEN}[+]{C_RESET} frida-server OK (matching version/arch, running). You're good to go.")
        return

    print(f"{C_RED}[-] Frida will likely fail with 'need Gadget to attach on jailed Android'.{C_RESET}")
    for p in problems:
        print(f"{C_YELLOW}    - {p}{C_RESET}")

    ver = host_ver or "<HOST_FRIDA_VERSION>"
    fname = f"frida-server-{ver}-android-{want_arch}"
    print(f"\n{C_YELLOW}[FIX] Install & start the matching frida-server:{C_RESET}")
    print(f"  curl -fL -o /tmp/fs.xz https://github.com/frida/frida/releases/download/{ver}/{fname}.xz")
    print(f"  python3 -c \"import lzma,shutil; shutil.copyfileobj(lzma.open('/tmp/fs.xz'), open('/tmp/{fname}','wb'))\"")
    print(f"  adb -s {serial} push /tmp/{fname} /data/local/tmp/{fname}")
    print(f"  adb -s {serial} shell \"su -c 'chmod 755 /data/local/tmp/{fname}'\"")
    print(f"  adb -s {serial} shell \"su -c 'setsid /data/local/tmp/{fname} >/dev/null 2>&1 &'\"")
    print(f"  frida-ps -U | head   {C_GREY}# verify it responds{C_RESET}")


# ─────────────────────────────────────────────
#  RUN & VERIFY  (--run)   — Added by CaptainHacX
# ─────────────────────────────────────────────

def run_and_verify(package, script_path, serial, run_timeout):
    """Spawn the app via Frida with the generated script, confirm the SSL hook
    actually loaded, and detect anti-tamper/RASP crashes. Read-only w.r.t. the
    device (no iptables). Frida is imported lazily so the rest of the tool works
    without it."""
    print("")
    print(box_top())
    print(box_line("          RUN & VERIFY (Frida)", C_YELLOW))
    print(box_bottom())

    try:
        import frida
    except ImportError:
        print(f"{C_YELLOW}[!] --run needs the Frida python module: pip install frida{C_RESET}")
        return
    import time

    if not _valid_package(package):
        print(f"{C_RED}[-] Refusing to spawn: invalid package name {package!r}{C_RESET}")
        return
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            src = f.read()
    except Exception as e:
        print(f"{C_RED}[-] Cannot read script: {e}{C_RESET}")
        return

    try:
        dev = frida.get_device(serial, timeout=10) if serial else frida.get_usb_device(timeout=10)
    except Exception as e:
        print(f"{C_RED}[-] No Frida device: {e}{C_RESET}")
        print(f"{C_YELLOW}    Make sure frida-server is running (see the pre-flight above).{C_RESET}")
        return

    logs = []
    state = {'crashed': False, 'reason': None}

    def on_message(message, data):
        t = message.get('type')
        if t == 'log':
            payload = str(message.get('payload', ''))
            logs.append(payload)
            print(f"   {C_GREY}[app]{C_RESET} {payload}")
        elif t == 'send':
            logs.append(str(message.get('payload', '')))
        elif t == 'error':
            print(f"   {C_RED}[script error]{C_RESET} {message.get('stack', message.get('description', ''))}")

    def on_detached(reason, *_):
        state['reason'] = reason
        if reason in ('process-terminated', 'process-replaced'):
            state['crashed'] = True

    session = None
    try:
        pid = dev.spawn([package])
        session = dev.attach(pid)
        session.on('detached', on_detached)
        script = session.create_script(src)
        script.on('message', on_message)
        script.load()
        dev.resume(pid)
        print(f"{C_GREEN}[+]{C_RESET} Spawned {package} (pid {pid}); watching for up to {run_timeout}s ...")
    except Exception as e:
        print(f"{C_RED}[-] spawn/attach failed: {e}{C_RESET}")
        try:
            if session:
                session.detach()
        except Exception:
            pass
        return

    ok = False
    steps = int(max(3, run_timeout) / 0.5)
    for _ in range(steps):
        if state['crashed']:
            break
        if any('pinning bypass installed' in l for l in logs):
            ok = True
            break
        time.sleep(0.5)

    if state['crashed']:
        print(f"{C_RED}[-] App terminated (reason: {state['reason']}). Likely anti-tamper / RASP "
              f"(e.g. PAIRIP) killed it. See the protection scan above.{C_RESET}")
    elif ok:
        print(f"{C_GREEN}[+] VERIFIED: SSL pinning bypass installed and the app is alive.{C_RESET}")
    else:
        print(f"{C_YELLOW}[!] Hook not confirmed within {run_timeout}s (app still alive). "
              f"Check the [app] logs above; the module may load slower.{C_RESET}")

    # For interactive shells, keep the session so traffic can be captured; else detach.
    if ok and not state['crashed'] and sys.stdin.isatty():
        print(f"{C_CYAN}[*]{C_RESET} App running with hooks. Press Ctrl+C to stop.")
        try:
            while not state['crashed']:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print(f"\n{C_CYAN}[*]{C_RESET} Stopping.")
    try:
        if session:
            session.detach()
    except Exception:
        pass


# ─────────────────────────────────────────────
#  PRINT FINAL COMMANDS
# ─────────────────────────────────────────────

def print_commands_android(package, proxy, script_path):
    set_443   = f'adb shell su -c "iptables -t nat -A OUTPUT -p tcp --dport 443 -j DNAT --to-destination {proxy}"'
    set_80    = f'adb shell su -c "iptables -t nat -A OUTPUT -p tcp --dport 80  -j DNAT --to-destination {proxy}"'
    verify    = 'adb shell su -c "iptables -t nat -L OUTPUT --line-numbers"'
    frida_cmd = f'frida -U -f {package} -l "{script_path}"'
    del_443   = f'adb shell su -c "iptables -t nat -D OUTPUT -p tcp --dport 443 -j DNAT --to-destination {proxy}"'
    del_80    = f'adb shell su -c "iptables -t nat -D OUTPUT -p tcp --dport 80  -j DNAT --to-destination {proxy}"'

    print("")
    print(box_top())
    print(box_line("          ANDROID — COPY PASTE COMMANDS", C_YELLOW))
    print(box_bottom())
    print("")
    print("\033[93m[1] Set iptables on device:\033[0m")
    print("  " + set_443)
    print("  " + set_80)
    print("")
    print("\033[93m[2] Verify iptables rules:\033[0m")
    print("  " + verify)
    print("")
    print("\033[93m[3] Launch Frida:\033[0m")
    print("\033[92m  " + frida_cmd + "\033[0m")
    print("")
    print("\033[93m[4] Revert when done:\033[0m")
    print("  " + del_443)
    print("  " + del_80)
    print("\033[90m  # or just: adb reboot\033[0m")


def print_commands_ios(package, proxy, script_path, device_ip):
    frida_cmd = f'frida -U -f {package} -l "{script_path}"'
    set_443   = f'ssh root@{device_ip} "iptables -t nat -A OUTPUT -p tcp --dport 443 -j DNAT --to-destination {proxy}"'
    set_80    = f'ssh root@{device_ip} "iptables -t nat -A OUTPUT -p tcp --dport 80  -j DNAT --to-destination {proxy}"'
    del_443   = f'ssh root@{device_ip} "iptables -t nat -D OUTPUT -p tcp --dport 443 -j DNAT --to-destination {proxy}"'
    del_80    = f'ssh root@{device_ip} "iptables -t nat -D OUTPUT -p tcp --dport 80  -j DNAT --to-destination {proxy}"'

    print("")
    print(box_top())
    print(box_line("            iOS — COPY PASTE COMMANDS", C_YELLOW))
    print(box_bottom())
    print("")
    print("\033[93m[1] Set WiFi proxy on device:\033[0m")
    print(f"  Settings → WiFi → Your Network → HTTP Proxy → Manual")
    print(f"  Server: {proxy.split(':')[0]}  Port: {proxy.split(':')[1]}")
    print("")
    print("\033[93m[2] Set iptables on device (jailbroken via SSH):\033[0m")
    print("  " + set_443)
    print("  " + set_80)
    print("")
    print("\033[93m[3] Launch Frida:\033[0m")
    print("\033[92m  " + frida_cmd + "\033[0m")
    print("")
    print("\033[93m[4] Revert when done:\033[0m")
    print("  " + del_443)
    print("  " + del_80)
    print("\033[90m  # or just reboot the device\033[0m")


def print_summary(package, offset, script_path, proxy, platform):
    print("")
    print(box_top())
    print(box_line(f"  Platform : {platform.upper()}", C_GREEN))
    print(box_line(f"  Package  : {package}", C_GREEN))
    print(box_line(f"  Offset   : {hex(offset)}", C_GREEN))
    print(box_line(f"  Script   : {os.path.basename(script_path)}", C_GREEN))
    print(box_line(f"  Proxy    : {proxy}", C_GREEN))
    print(box_bottom())
    print("")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    if len(sys.argv) == 1 or '-h' in sys.argv or '--help' in sys.argv:
        print_help()
        sys.exit(0)

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('app', nargs='?', help='Path to APK or IPA')
    parser.add_argument('-i', '--ip', default='<YOUR_IP>', help='Your machine IP (auto-detected if omitted)')
    parser.add_argument('-p', '--port', default='8080', help='Burp port')
    parser.add_argument('-o', '--output', help='Output directory')
    parser.add_argument('--platform', choices=['android', 'ios'], help='Force platform')
    parser.add_argument('--device-ip', default='<DEVICE_IP>', help='iOS device IP (for SSH iptables)')
    # Added by CaptainHacX: --package/--bundle-id and --no-scan
    parser.add_argument('--package', '--bundle-id', dest='package', default=None,
                        help='Explicit package name / bundle id (skips auto-detection and the interactive prompt)')
    parser.add_argument('--no-scan', action='store_true',
                        help='Skip the protection/RASP pre-scan')
    # Added by CaptainHacX: new feature flags (--from-device, --serial, --run, --run-timeout)
    parser.add_argument('--from-device', metavar='PACKAGE', default=None,
                        help='Pull the app (all splits) from a connected device by package name (Android)')
    parser.add_argument('--serial', default=None,
                        help='adb / Frida device serial (for --from-device and --run)')
    parser.add_argument('--run', action='store_true',
                        help='After generating, spawn the app via Frida and verify the bypass loaded')
    parser.add_argument('--run-timeout', type=int, default=15,
                        help='Seconds to wait for the hook when using --run (default 15)')
    # Added by CaptainHacX: offset cache controls
    parser.add_argument('--no-cache', action='store_true',
                        help='Ignore the offset cache and always rescan')
    parser.add_argument('--refresh-cache', action='store_true',
                        help='Rescan and overwrite the cached offset for this binary')
    args = parser.parse_args()

    print_banner()

    # Added by CaptainHacX: input acquisition (--from-device pull, dir/bundle
    # inputs), auto host-IP, protection pre-scan, and the optional --run step.
    serial = args.serial
    package = args.package.strip() if args.package else None
    source_display = args.app

    # ---- Acquire input: either pull from device, or use a local path ----
    if args.from_device:
        platform = (args.platform or 'android')
        if platform != 'android':
            print("\033[91m[-] --from-device is Android only.\033[0m"); sys.exit(1)
        if not package:
            package = args.from_device.strip()
        if not _valid_package(package):
            print(f"\033[91m[-] Invalid package name: {package!r}\033[0m"); sys.exit(1)
        serial, err = resolve_serial(serial)
        if not serial:
            print(f"\033[91m[-] {err}\033[0m"); sys.exit(1)
        out_dir = args.output or os.path.join(os.getcwd(), 'kf_' + package)
        os.makedirs(out_dir, exist_ok=True)
        try:
            source = pull_apks_from_device(package, serial, out_dir)  # a directory
        except Exception as e:
            print(f"\033[91m[-] from-device failed: {e}\033[0m"); sys.exit(1)
        source_display = source
    else:
        app_path = args.app
        if not app_path:
            print("\033[91m[-] No APK/IPA provided (or use --from-device). Use -h for help.\033[0m")
            sys.exit(1)
        if not os.path.exists(app_path):
            print(f"\033[91m[-] Path not found: {app_path}\033[0m")
            sys.exit(1)
        platform = detect_platform(app_path, args.platform)
        if args.output:
            out_dir = args.output
        elif os.path.isdir(app_path):
            out_dir = app_path
        else:
            out_dir = os.path.dirname(os.path.abspath(app_path))
        os.makedirs(out_dir, exist_ok=True)
        source = app_path
        source_display = app_path

    # ---- Proxy / IP ----  (auto host-IP added by CaptainHacX)
    ip = args.ip
    if ip == '<YOUR_IP>':
        detected = detect_host_ip()
        if detected:
            ip = detected
            print(f"\033[96m[*]\033[0m Auto-detected host IP: \033[93m{ip}\033[0m (override with -i)")
    port      = args.port
    proxy     = ip + ":" + port
    device_ip = args.device_ip

    print(f"\033[96m[*]\033[0m Platform : \033[93m{platform.upper()}\033[0m")
    print(f"\033[96m[*]\033[0m Source   : {source_display}")
    print(f"\033[96m[*]\033[0m Output   : {out_dir}")
    print(f"\033[96m[*]\033[0m Proxy    : {proxy}")

    # Normalize Android input into a concrete list of APKs (base + splits)  — Added by CaptainHacX
    apk_list = list_android_apks(source, out_dir) if platform == 'android' else []
    if platform == 'android' and not apk_list:
        print("\033[91m[-] No APK found in the given input.\033[0m"); sys.exit(1)

    # Step 0: Protection / RASP pre-scan (warn before we hit a runtime crash)  — Added by CaptainHacX
    if not args.no_scan:
        scan_protections(apk_list if platform == 'android' else [source], platform)

    # Step 1: Get identifier (explicit flag > auto-detect > interactive prompt)
    if package:
        print(f"\033[92m[+]\033[0m Package: \033[93m{package}\033[0m")
    elif platform == 'android':
        base_apk = next((a for a in apk_list if os.path.basename(a).lower() == 'base.apk'), apk_list[0])
        package = get_package_name_android(base_apk)
        if package:
            print(f"\033[92m[+]\033[0m Package: \033[93m{package}\033[0m")
        else:
            package = input("\033[93m[?] Enter package name manually: \033[0m").strip()
    else:
        package = get_bundle_id_ios(source)
        if package:
            print(f"\033[92m[+]\033[0m Bundle ID: \033[93m{package}\033[0m")
        else:
            package = input("\033[93m[?] Enter bundle ID manually (e.g. com.example.app): \033[0m").strip()

    # Step 2: Extract Flutter binary
    if platform == 'android':
        binary_path, abi = extract_flutter_android(apk_list, out_dir)
    else:
        binary_path = extract_flutter_ios(source, out_dir)

    if not binary_path:
        sys.exit(1)

    # Step 3: Find SSL offset (uses the offset cache unless --no-cache)
    offset = find_offset(binary_path, platform,
                         use_cache=not args.no_cache, refresh_cache=args.refresh_cache)
    if offset is None:
        sys.exit(1)

    # Step 4: Write Frida script
    script_path = os.path.join(out_dir, 'flutter_bypass.js')
    write_frida_script(offset, package, platform, script_path)

    # Step 4.5: (Android) verify on-device frida-server before printing commands
    if platform == 'android':
        try:
            preflight_frida_check(package)
        except Exception as e:
            print(f"\033[93m[!] Pre-flight check skipped: {e}\033[0m")

    # Step 5: Print commands
    if platform == 'android':
        print_commands_android(package, proxy, script_path)
    else:
        print_commands_ios(package, proxy, script_path, device_ip)

    print_summary(package, offset, script_path, proxy, platform)

    # Step 6: (optional) spawn & verify the bypass actually loads  — Added by CaptainHacX
    if args.run:
        run_and_verify(package, script_path, serial, args.run_timeout)


if __name__ == '__main__':
    main()
