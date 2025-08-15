import csv, re, sys, argparse

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
    ap = argparse.ArgumentParser(description="Generate CP4D-style Deployment from CSV of images")
    ap.add_argument('--csv', required=True)
    ap.add_argument('--name', required=True, help='Deployment name (also used as container name, per screenshot)')
    ap.add_argument('--namespace')
    ap.add_argument('--replicas', type=int, default=1)
    ap.add_argument('--port', type=int, default=8080)
    ap.add_argument('--pull-policy', default='Always')
    # keep IBM-like defaults
    ap.add_argument('--progress-deadline', type=int, default=600)
    ap.add_argument('--revision-history', type=int, default=10)
    ap.add_argument('--max-surge', default='25%')
    ap.add_argument('--max-unavailable', default='25%')
    ap.add_argument('--req-cpu', default='450m')
    ap.add_argument('--req-mem', default='512Mi')
    ap.add_argument('--lim-cpu', default='500m')
    ap.add_argument('--lim-mem', default='512Mi')
    args = ap.parse_args()

    images = read_images(args.csv)
    if not images:
        sys.exit("No images found")

    A = []
    def add(s): A.append(s)

    add("apiVersion: apps/v1")
    add("kind: Deployment")
    add("metadata:")
    add("  annotations: null")
    add("  labels:")
    add(f"    app: {args.name}")
    add(f"  name: {args.name}")
    add("spec:")
    add(f"  progressDeadlineSeconds: {args.progress_deadline}")
    add(f"  replicas: {args.replicas}")
    add(f"  revisionHistoryLimit: {args.revision_history}")
    add("  selector:")
    add("    matchLabels:")
    add(f"      app: {args.name}")
    add("  strategy:")
    add("    rollingUpdate:")
    add(f"      maxSurge: {args.max_surge}")
    add(f"      maxUnavailable: {args.max_unavailable}")
    add("    type: RollingUpdate")
    add("  template:")
    add("    metadata:")
    add("      creationTimestamp: null")
    add("      labels:")
    add(f"        app: {args.name}")
    add("    spec:")
    add("      containers:")

    for img in images:
        add(f"      - image: {img}")
        add(f"        imagePullPolicy: {args.pull_policy}")
        add(f"        name: {args.name}")
        add("        ports:")
        add(f"          - containerPort: {args.port}")
        add("            protocol: TCP")
        add("        resources:")
        add("          limits:")
        add(f"            cpu: {args.lim_cpu}")
        add(f"            memory: {args.lim_mem}")
        add("          requests:")
        add(f"            cpu: {args.req_cpu}")
        add(f"            memory: {args.req_mem}")
        add("        securityContext:")
        add("          privileged: false")

    if args.namespace:
        # insert namespace under metadata (after name)
        # find index of "  name: ..."
        target = f"  name: {args.name}"
        idx = A.index(target)
        A.insert(idx+1, f"  namespace: {args.namespace}")

    print("\n".join(A))

if __name__ == "__main__":
    main()
