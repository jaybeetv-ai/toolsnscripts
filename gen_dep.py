import csv, re, sys, argparse

def san(s):
    seg = s.split("/")[-1].split("@")[0].split(":")[0]
    seg = re.sub(r'[^a-z0-9.-]+','-', seg.lower()).strip('-')
    return seg or 'ctr'

def read_images(path):
    with open(path, newline='') as f:
        r = csv.reader(f)
        first = next(r, None)
        if not first: return []
        items = []
        header = [h.strip().lower() for h in first] if any(first) else []
        if 'image' in header:
            idx = header.index('image')
            for row in r:
                if len(row) > idx and row[idx].strip():
                    items.append(row[idx].strip())
        else:
            if first and first[0].strip(): items.append(first[0].strip())
            for row in r:
                if row and row[0].strip(): items.append(row[0].strip())
        return items

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True)
    ap.add_argument('--name', required=True)
    ap.add_argument('--namespace')
    ap.add_argument('--replicas', type=int, default=1)
    ap.add_argument('--port', type=int)
    ap.add_argument('--pull-policy', default='Always')
    args = ap.parse_args()

    images = read_images(args.csv)
    if not images:
        sys.exit("No images found")

    # Header
    out = []
    A = out.append
    A("apiVersion: apps/v1")
    A("kind: Deployment")
    A("metadata:")
    A(f"  name: {args.name}")
    if args.namespace:
        A(f"  namespace: {args.namespace}")
    A("spec:")
    A(f"  replicas: {args.replicas}")
    A("  selector:")
    A("    matchLabels:")
    A(f"      app: {args.name}")
    A("  template:")
    A("    metadata:")
    A("      labels:")
    A(f"        app: {args.name}")
    A("    spec:")
    A("      containers:")

    # Containers
    seen = {}
    for img in images:
        nm = san(img)
        n = seen.get(nm, 0)
        seen[nm] = n + 1
        if n: nm = f"{nm}-{n}"
        A("      - name: " + nm)
        A("        image: " + img)
        A("        imagePullPolicy: " + args.pull_policy)
        if args.port:
            A("        ports:")
            A(f"        - containerPort: {args.port}")
            A("          protocol: TCP")

    print("\n".join(out))

if __name__ == "__main__":
    main()
