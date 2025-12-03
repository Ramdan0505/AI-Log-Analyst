# inspect_registry.py
import os
from regipy.registry import RegistryHive

HIVE_PATH = r"C:\data\radlab_artifacts\test_case_evtx\SOFTWARE.hiv"

def list_keys_with_values(root_key_path: str, max_keys: int = 50):
    """
    Walks a key and prints subkeys that actually have values.
    Helps you discover the exact paths to use in REGISTRY_TARGETS.
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
        # keys that actually have values
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

        # dive into subkeys
        for sub in k.iter_subkeys():
            stack.append(sub)


if __name__ == "__main__":
    # Start from a high-value root; you can change this string to explore
    list_keys_with_values(r"Microsoft\Windows NT\CurrentVersion", max_keys=30)
