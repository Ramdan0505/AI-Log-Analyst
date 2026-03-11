from windowsprefetch import Prefetch

pf_path = r"C:\Projects\radlab-preinvest\test.pf"

pf = Prefetch(pf_path)

print("TYPE:", type(pf))
print("ATTRS:", [x for x in dir(pf) if not x.startswith("_")])

for name in [x for x in dir(pf) if not x.startswith("_")]:
    try:
        print(f"{name} =", getattr(pf, name))
    except Exception as e:
        print(f"{name} = <error: {e}>")