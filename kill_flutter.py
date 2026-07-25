#!/usr/bin/env python3
# K!ll Fl!utter - Flutter SSL Pinning Bypass Tool
# By: f3rb
# Supports: Android (APK) + iOS (IPA)
# For authorized penetration testing only

import struct, re, sys, os, zipfile, subprocess, argparse, plistlib, socket


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
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.apk':
        return 'android'
    elif ext == '.ipa':
        return 'ios'
    else:
        print("\033[93m[!] Cannot detect platform from extension. Use --platform android or --platform ios\033[0m")
        sys.exit(1)


# ─────────────────────────────────────────────
#  ANDROID — PACKAGE NAME
# ─────────────────────────────────────────────

def get_package_name_android(apk_path):
    """Resolve the package name with a graceful fallback chain so the tool does
    NOT hard-depend on aapt: aapt -> aapt2 -> binary-AndroidManifest parser."""
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
    AndroidManifest.xml without aapt. Fully defensive: returns None on any error."""
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
#  HOST IP AUTO-DETECTION
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
#  PROTECTION / RASP SCANNER
# ─────────────────────────────────────────────

def scan_protections(app_path, platform):
    """Fingerprint known anti-tamper / RASP / root-detection protections inside
    the APK/IPA so the operator is warned BEFORE hitting a runtime crash.
    Read-only (inspects zip entries + dex/binary strings). Returns a list of
    (name, description, strategy) tuples."""

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

    findings = {}  # name -> (desc, strat), dedup by name

    try:
        with zipfile.ZipFile(app_path, 'r') as z:
            names = z.namelist()
            basenames = {nm.split('/')[-1] for nm in names}

            # native .so / framework fingerprints (exact basename)
            NATIVE = {
                'libpairipcore.so':   'Google PAIRIP',
                'libtoolchecker.so':  'Talsec / freeRASP',
                'libTalsecRuntime.so':'Talsec / freeRASP',
                'libshield.so':       'Promon SHIELD',
                'libdexguard.so':     'DexGuard',
                'libjailmonkey.so':   'JailMonkey',
            }
            for lib, nm in NATIVE.items():
                if lib in basenames and nm not in findings:
                    findings[nm] = STRATEGY.get(nm, ('native protection library', 'Investigate manually.'))

            # path-substring fingerprints (Appdome / iOS frameworks)
            lowered = [nm.lower() for nm in names]
            if any('appdome' in nm for nm in lowered) and 'Appdome' not in findings:
                findings['Appdome'] = STRATEGY['Appdome']
            if platform == 'ios':
                for marker, nm in [('iossecuritysuite', 'IOSSecuritySuite'),
                                   ('trustkit', 'TrustKit'),
                                   ('talsec', 'Talsec / freeRASP')]:
                    if any(marker in p for p in lowered) and nm not in findings:
                        findings[nm] = STRATEGY.get(nm, ('iOS protection', 'Investigate manually.'))

            # dex string fingerprints (Java/Kotlin libraries), Android only
            if platform == 'android':
                DEX = {
                    b'com/scottyab/rootbeer':          'RootBeer',
                    b'gantix/jailmonkey':              'JailMonkey',
                    b'flutter_jailbreak_detection':    'flutter_jailbreak_detection',
                    b'com/aheaditec/talsec':           'Talsec / freeRASP',
                }
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
        print(f"\033[93m[!] Protection scan skipped: {e}\033[0m")
        return []

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

def extract_flutter_android(apk_path, out_dir):
    so_path = os.path.join(out_dir, 'libflutter.so')
    print(f"\033[96m[*]\033[0m Extracting libflutter.so from APK...")
    with zipfile.ZipFile(apk_path, 'r') as z:
        for name in z.namelist():
            if 'arm64-v8a/libflutter.so' in name:
                print(f"\033[92m[+]\033[0m Found: {name}")
                with z.open(name) as src, open(so_path, 'wb') as dst:
                    dst.write(src.read())
                return so_path
    print("\033[91m[-] libflutter.so (arm64-v8a) not found — is this a Flutter APK?\033[0m")
    return None


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

def parse_elf_segments(data):
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
                print(f"\033[96m[*]\033[0m ELF code segment: file={hex(p_offset)} vaddr={hex(p_vaddr)} size={hex(seg_filesz)}")
                # A .so can have multiple executable PT_LOAD segments; keep the
                # LARGEST one (the real .text), not simply the last one parsed.
                if code_filesz is None or seg_filesz > code_filesz:
                    code_foff, code_vaddr, code_filesz = p_offset, p_vaddr, seg_filesz

    if code_foff is not None:
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
#  CORE — FIND SSL OFFSET (shared for both platforms)
# ─────────────────────────────────────────────

def find_offset(binary_path, platform):
    print(f"\033[96m[*]\033[0m Loading binary: {binary_path}")
    with open(binary_path, 'rb') as f:
        data = f.read()

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
                        return rva

    print("\033[91m[-] Could not find SSL verify function\033[0m")
    return None


# ─────────────────────────────────────────────
#  FRIDA SCRIPT GENERATOR
# ─────────────────────────────────────────────

def write_frida_script(offset, package, platform, out_path):
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

// Resolve a libc export across Frida versions. Frida 17 removed the static
// Module.findExportByName(null, name); the replacement is
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

// ---------------- RUN ----------------
try { hookLibc(); } catch (e) { log("libc error: " + e); }
try { hookJava(); } catch (e) { log("java error: " + e); }
hookSslVerify();
log("bypass loaded");
'''

    with open(out_path, 'w') as f:
        f.write(config + body)
    print(f"\033[92m[+]\033[0m Frida script saved: \033[93m{out_path}\033[0m")


# ─────────────────────────────────────────────
#  ANDROID — FRIDA-SERVER PRE-FLIGHT CHECK
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
    parser.add_argument('--package', '--bundle-id', dest='package', default=None,
                        help='Explicit package name / bundle id (skips auto-detection and the interactive prompt)')
    parser.add_argument('--no-scan', action='store_true',
                        help='Skip the protection/RASP pre-scan')
    args = parser.parse_args()

    print_banner()

    app_path = args.app
    if not app_path:
        print("\033[91m[-] No APK/IPA provided. Use -h for help.\033[0m")
        sys.exit(1)

    if not os.path.exists(app_path):
        print(f"\033[91m[-] File not found: {app_path}\033[0m")
        sys.exit(1)

    platform = detect_platform(app_path, args.platform)
    out_dir  = args.output or os.path.dirname(os.path.abspath(app_path))
    os.makedirs(out_dir, exist_ok=True)

    ip        = args.ip
    if ip == '<YOUR_IP>':
        detected = detect_host_ip()
        if detected:
            ip = detected
            print(f"\033[96m[*]\033[0m Auto-detected host IP: \033[93m{ip}\033[0m (override with -i)")
    port      = args.port
    proxy     = ip + ":" + port
    device_ip = args.device_ip

    print(f"\033[96m[*]\033[0m Platform : \033[93m{platform.upper()}\033[0m")
    print(f"\033[96m[*]\033[0m App      : {app_path}")
    print(f"\033[96m[*]\033[0m Output   : {out_dir}")
    print(f"\033[96m[*]\033[0m Proxy    : {proxy}")

    # Step 0: Protection / RASP pre-scan (warn before we hit a runtime crash)
    if not args.no_scan:
        scan_protections(app_path, platform)

    # Step 1: Get identifier (explicit flag > auto-detect > interactive prompt)
    if args.package:
        package = args.package.strip()
        print(f"\033[92m[+]\033[0m Package (from --package): \033[93m{package}\033[0m")
    elif platform == 'android':
        package = get_package_name_android(app_path)
        if package:
            print(f"\033[92m[+]\033[0m Package: \033[93m{package}\033[0m")
        else:
            package = input("\033[93m[?] Enter package name manually: \033[0m").strip()
    else:
        package = get_bundle_id_ios(app_path)
        if package:
            print(f"\033[92m[+]\033[0m Bundle ID: \033[93m{package}\033[0m")
        else:
            package = input("\033[93m[?] Enter bundle ID manually (e.g. com.example.app): \033[0m").strip()

    # Step 2: Extract Flutter binary
    if platform == 'android':
        binary_path = extract_flutter_android(app_path, out_dir)
    else:
        binary_path = extract_flutter_ios(app_path, out_dir)

    if not binary_path:
        sys.exit(1)

    # Step 3: Find SSL offset
    offset = find_offset(binary_path, platform)
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


if __name__ == '__main__':
    main()
