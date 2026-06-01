# MT5 Python Connect — Troubleshooting Reference

## Common Error: IPC Initialize Failed

```
Initialize failed: (-10003, "IPC initialize failed, Pipe server didn't answer in 60 sec")
```

**Cause**: The MT5 terminal has never been opened with the target account. The Python library (`MetaTrader5`) communicates with the terminal via a local named pipe (IPC). If the terminal hasn't cached the account session, initialize() starts a terminal process and waits 60s for the pipe to appear, which times out.

**Fix — manual first-time setup**:
1. Kill all terminal64.exe processes (`taskkill //F //IM terminal64.exe`)
2. Launch terminal64.exe from target path manually
3. Enter account credentials (server, login, password) in the login dialog
4. Wait for full sync — quotes, charts, and account info visible
5. Close terminal via **File → Exit** (NOT the window X button — this saves the session)
6. After that, Python's `mt5.initialize(path=...)` should connect immediately

## Correct Python Init Sequence

```python
import MetaTrader5 as mt5

# Always pass explicit path to terminal64.exe
path = r'C:\Program Files\MetaTrader 5\terminal64.exe'
init = mt5.initialize(path=path)
if not init:
    err = mt5.last_error()
    print(f'Initialize failed: {err}')
    mt5.shutdown()
    exit(1)
```

## Broker Server Names
- FXPro Demo: `FXPRO-Demo01` (or `FxPro-MT5 Demo`)
- FXPro Real: `FXPRO-Real01` (or similar — verify in terminal)
- Capital Point Trading: `CapitalPointTrading-MT5-4`

## Terminal Profile Discovery (when IPC fails)

When `mt5.initialize()` returns `(-10005, 'IPC timeout')` on an installation that IS running, the Python IPC pipe is already held by another process. You can still discover **which accounts are configured** on that installation:

### Profile storage
Terminal profiles live under:
```
C:\Users\<user>\AppData\Roaming\MetaQuotes\Terminal\<HASH>\bases\<server-name>\symbols\
```
Each hash = one terminal installation (but TWO installs of the same broker may SHARE a hash).

### How to find login-server pairs
```python
import os

roaming = r"C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal"
for h in os.listdir(roaming):
    bases_dir = os.path.join(roaming, h, "bases")
    if not os.path.isdir(bases_dir):
        continue
    for server in os.listdir(bases_dir):
        sym_dir = os.path.join(bases_dir, server, "symbols")
        if not os.path.isdir(sym_dir):
            continue
        for f in os.listdir(sym_dir):
            if f.startswith("symbols-") and f.endswith(".dat"):
                login = f.replace("symbols-", "").replace(".dat", "")
                print(f"Terminal {h[:8]}... / {server} → login {login}")
```

### Identifying which install has which hash
There's no direct filename mapping from install path to profile hash. You infer:
1. Probing one install via Python tells you its login (e.g. `591615558`)
2. Searching profile files tells you ALL logins across all installs
3. Any login NOT matching the probed one belongs to the other install

### Two FxPro installs sharing a profile
If both `C:\Program Files\FxPro - MetaTrader 5\` and `C:\Users\<user>\Desktop\FxPro - MetaTrader 5\` are installed, they share the same terminal profile hash. This means:
- Only ONE can hold the IPC pipe at any time
- The other will always return IPC timeout when Python tries to connect
- Both can access the same set of saved accounts (you can see all logins from the profile)
- To actually log into the other account, either log out of the current one, or use `mt5.login()` on the already-connected instance

Isolate a hidden account: create a THIRD copy on desktop, login with the hidden credentials, Python against that copy's unique path.

## Separate Installation Trick (for hidden accounts)
When two FxPro installations share a terminal profile hash and can't be probed independently:
1. Copy the entire FxPro - MetaTrader 5 folder to desktop
2. Rename it (e.g. `FxPro Account2`)
3. Open terminal64.exe from the copy, login with the hidden account's credentials
4. Now Python MT5 connects to that copy's unique IPC pipe — it's a separate session
5. This works because each physical copy has its own IPC pipe, even if they share the profile data directory
