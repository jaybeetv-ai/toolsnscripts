
#!/usr/bin/env python3
"""
Generate a Kubernetes Deployment manifest (deployment.yaml) from a CSV of images.

CSV formats supported:
1) Single column (no header): each row contains an image reference
   Example:
       icr.io/cpopen/cpd/olm-utils-v3:latest
       cp.icr.io/cp/cpd/edb-postgres-license-provider@sha256:...

2) With header "image" (optional columns "name", "port"):
   image,name,port
   icr.io/cpopen/cpd/olm-utils-v3:latest,olm-utils,8080

By default, we create one Pod with multiple containers (one per image).
You can optionally include per-row "port" or use a global --container-port.

Example:
  python generate_deployment_from_csv.py --csv images.csv --name ibm-cp4d --namespace cp4d --replicas 1 --container-port 8080 --out deployment.yaml
"""

import argparse, csv, os, sys, re
from collections import Counter
try:
    import yaml  # PyYAML
except ImportError as e:
    print("This script requires PyYAML. Install with: pip install pyyaml", file=sys.stderr)
    raise

def sanitize_name(s: str) -> str:
    # Derive a valid DNS-1123 name for container from image ref
    # Take the last path segment (repo), strip tag/digest
    seg = s.split("/")[-1]
    seg = seg.split("@")[0]
    seg = seg.split(":")[0]
    seg = re.sub(r'[^a-z0-9.-]+', '-', seg.lower())
    seg = seg.strip('-') or "ctr"
    # Must start/end with alphanumeric
    seg = re.sub(r'^[^a-z0-9]+', '', seg)
    seg = re.sub(r'[^a-z0-9]+$', '', seg)
    return seg or "ctr"

def read_images(csv_path):
    rows = []
    with open(csv_path, newline='') as f:
        sniffer = csv.Sniffer()
        sample = f.read(2048)
        f.seek(0)
        dialect = sniffer.sniff(sample, delimiters=",;\t|")
        reader = csv.reader(f, dialect)
        # Peek first row to see if header exists
        first = next(reader, None)
        if first is None:
            return rows
        header_like = any(h.lower() in ("image","name","port") for h in first)
        if header_like:
            headers = [h.lower().strip() for h in first]
            idx_image = headers.index("image") if "image" in headers else 0
            idx_name = headers.index("name") if "name" in headers else None
            idx_port = headers.index("port") if "port" in headers else None
            for r in reader:
                if not r or not r[idx_image].strip():
                    continue
                image = r[idx_image].strip()
                name = r[idx_name].strip() if idx_name is not None and idx_name < len(r) and r[idx_name].strip() else sanitize_name(image)
                port = None
                if idx_port is not None and idx_port < len(r):
                    try:
                        port = int(r[idx_port])
                    except Exception:
                        port = None
                rows.append({"image": image, "name": name, "port": port})
        else:
            # Single-column CSV without header
            img = first[0].strip()
            if img:
                rows.append({"image": img, "name": sanitize_name(img), "port": None})
            for r in reader:
                if not r: 
                    continue
                img = r[0].strip()
                if img:
                    rows.append({"image": img, "name": sanitize_name(img), "port": None})
    return rows

def unique_names(containers):
    # Ensure container names are unique
    seen = Counter()
    for c in containers:
        base = c["name"]
        if seen[base] == 0:
            seen[base] += 1
            c["name"] = base
        else:
            i = seen[base]
            seen[base] += 1
            c["name"] = f"{base}-{i}"
    return containers

def build_deployment(args, items):
    metadata = {"name": args.name}
    if args.namespace:
        metadata["namespace"] = args.namespace

    labels = {"app": args.name}

    containers = []
    for it in items:
        c = {
            "name": it["name"],
            "image": it["image"],
            "imagePullPolicy": args.pull_policy,
        }
        port = it["port"] or args.container_port
        if port:
            c["ports"] = [{"containerPort": int(port), "protocol": "TCP"}]
        if args.requests_cpu or args.requests_memory or args.limits_cpu or args.limits_memory:
            c["resources"] = {"requests": {}, "limits": {}}
            if args.requests_cpu: c["resources"]["requests"]["cpu"] = args.requests_cpu
            if args.requests_memory: c["resources"]["requests"]["memory"] = args.requests_memory
            if args.limits_cpu: c["resources"]["limits"]["cpu"] = args.limits_cpu
            if args.limits_memory: c["resources"]["limits"]["memory"] = args.limits_memory
            # Drop empty dicts
            if not c["resources"]["requests"]:
                c["resources"].pop("requests")
            if not c["resources"]["limits"]:
                c["resources"].pop("limits")
            if not c["resources"]:
                c.pop("resources")

        containers.append(c)

    unique_names(containers)

    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": metadata,
        "spec": {
            "replicas": args.replicas,
            "selector": {"matchLabels": labels},
            "template": {
                "metadata": {"labels": labels},
                "spec": {
                    "containers": containers
                }
            },
            "strategy": {"type": "RollingUpdate"}
        }
    }
    return deployment

def main():
    p = argparse.ArgumentParser(description="Generate deployment.yaml from a CSV of images")
    p.add_argument("--csv", required=True, help="Path to CSV with image list")
    p.add_argument("--name", required=True, help="Deployment name")
    p.add_argument("--namespace", default=None, help="Kubernetes namespace")
    p.add_argument("--replicas", type=int, default=1, help="Replica count")
    p.add_argument("--container-port", type=int, default=None, help="Default container port if not provided per row")
    p.add_argument("--pull-policy", default="Always", choices=["Always","IfNotPresent","Never"], help="imagePullPolicy")
    p.add_argument("--requests-cpu", dest="requests_cpu", default=None)
    p.add_argument("--requests-memory", dest="requests_memory", default=None)
    p.add_argument("--limits-cpu", dest="limits_cpu", default=None)
    p.add_argument("--limits-memory", dest="limits_memory", default=None)
    p.add_argument("--out", default="deployment.yaml", help="Output YAML path")
    args = p.parse_args()

    items = read_images(args.csv)
    if not items:
        print(f"No images found in {args.csv}", file=sys.stderr)
        sys.exit(2)

    manifest = build_deployment(args, items)

    with open(args.out, "w") as f:
        yaml.safe_dump(manifest, f, sort_keys=False)

    print(f"Wrote {args.out} with {len(items)} container(s).")

if __name__ == "__main__":
    main()
