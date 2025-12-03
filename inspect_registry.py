# inspect_registry.py
from regipy.registry import RegistryHive

# Path to the SOFTWARE hive you exported
HIVE_PATH = r"C:\data\radlab_artifacts\test_case_evtx\SOFTWARE.hiv"


def list_keys_with_values(root_key_path: str, max_keys: int = 30):
    """
    Walk a key and print subkeys that actually have values.
    This shows the exact key paths we should use in REGISTRY_TARGETS.
    """
    hive = RegistryHive(HIVE_PATH)

    # Try with and without leading backslash
    candidates = [root_key_path]
    if not root_key_path.startswith("\\"):
        candidates.append("\\" + root_key_path)

    key = None
    for kp in candidates:
        try:
            key = hive.get_key(kp)
            print(f"[+] Found root key: {kp}")
            break
        except Exception:
            continue

    if key is None:
        print(f"[!] Could not find key for any of: {candidates}")
        return

    stack = [key]
    seen = 0

    while stack and seen < max_keys:
        k = stack.pop()

        # If this key has values, print them
        if getattr(k, "values", []):
            print(f"\nKey: {k.path}")
            for v in k.values:
                try:
                    name = v.name or "(Default)"
                    value = v.value
                except Exception:
                    continue
                print(f"  {name} = {value}")
            seen += 1

        # Add subkeys to the stack
        try:
            for sub in k.iter_subkeys():
                stack.append(sub)
        except Exception:
            continue


if __name__ == "__main__":
    # You can change this root to explore other areas
    list_keys_with_values(r"Microsoft\Windows NT\CurrentVersion", max_keys=20)
