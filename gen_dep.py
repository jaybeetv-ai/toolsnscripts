import csv, sys, argparse, re

def read_images(path):
    with open(path, newline='') as f:
        r = csv.reader(f)
        first = next(r, None)
        if not first: return []
        items=[]
        hdr=[h.strip().lower() for h in first] if any(first) else []
        if 'image' in hdr:
            i=hdr.index('image')
            for row in r:
                if len(row)>i and row[i].strip(): items.append(row[i].strip())
        else:
            if first and first[0].strip(): items.append(first[0].strip())
            for row in r:
                if row and row[0].strip(): items.append(row[0].strip())
        return items

def main():
    ap=argparse.ArgumentParser(description="Generate CP4D-style Deployment with image-first container items")
    ap.add_argument('--csv', required=True, help='CSV containing images (single column or header "image")')
    ap.add_argument('--name', required=True, help='Deployment name; also used as container name')
    ap.add_argument('--namespace')
    ap.add_argument('--replicas', type=int, default=1)
    ap.add_argument('--port', type=int, default=8080)
    ap.add_argument('--pull-policy', default='Always')
    # strategy / history defaults (match your screenshot)
    ap.add_argument('--progress-deadline', type=int, default=600)
    ap.add_argument('--revision-history', type=int, default=10)
    ap.add_argument('--max-surge', default='25%')
    ap.add_argument('--max-unavailable', default='25%')
    # resources defaults (match your screenshot)
    ap.add_argument('--req-cpu', default='450m')
    ap.add_argument('--req-mem', default='512Mi')
    ap.add_argument('--lim-cpu', default='500m')
    ap.add_argument('--lim-mem', default='512Mi')
    args=ap.parse_args()

    images=read_images(args.csv)
    if not images: sys.exit("No images found")

    out=[]
    A=out.append
    A("apiVersion: apps/v1")
    A("kind: Deployment")
    A("metadata:")
    A("  annotations: null")
    A("  labels:")
    A(f"    app: {args.name}")
    A(f"  name: {args.name}")
    if args.namespace:
        A(f"  namespace: {args.namespace}")
    A("spec:")
    A(f"  progressDeadlineSeconds: {args.progress_deadline}")
    A(f"  replicas: {args.replicas}")
    A(f"  revisionHistoryLimit: {args.revision_history}")
    A("  selector:")
    A("    matchLabels:")
    A(f"      app: {args.name}")
    A("  strategy:")
    A("    rollingUpdate:")
    A(f"      maxSurge: {args.max_surge}")
    A(f"      maxUnavailable: {args.max_unavailable}")
    A("    type: RollingUpdate")
    A("  template:")
    A("    metadata:")
    A("      creationTimestamp: null")
    A("      labels:")
    A(f"        app: {args.name}")
    A("    spec:")
    A("      containers:")
    for img in images:
        # ===== EXACT ORDER BELOW =====
        A(f"      - image: {img}")
        A(f"        imagePullPolicy: {args.pull_policy}")
        A(f"        name: {args.name}")
        A("        ports:")
        A(f"          - containerPort: {args.port}")
        A("            protocol: TCP")
        A("        resources:")
        A("          limits:")
        A(f"            cpu: {args.lim_cpu}")
        A(f"            memory: {args.lim_mem}")
        A("          requests:")
        A(f"            cpu: {args.req_cpu}")
        A(f"            memory: {args.req_mem}")
        A("        securityContext:")
        A("          privileged: false")

    print("\n".join(out))

if __name__ == '__main__':
    main()
