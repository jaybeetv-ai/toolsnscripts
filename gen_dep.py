import csv, re, sys, argparse

def san(s):
    seg = s.split("/")[-1].split("@")[0].split(":")[0]
    seg = re.sub('[^a-z0-9.-]+','-', seg.lower()).strip('-')
    return seg or 'ctr'

def read_images(path):
    items=[]
    with open(path, newline='') as f:
        r=csv.reader(f)
        first = next(r, None)
        if not first: return items
        header = [h.lower() for h in first]
        if 'image' in header:
            idx = header.index('image')
            for row in r:
                if len(row)>idx and row[idx].strip():
                    items.append(row[idx].strip())
        else:
            if first and first[0].strip(): items.append(first[0].strip())
            for row in r:
                if row and row[0].strip(): items.append(row[0].strip())
    return items

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--csv', required=True)
    p.add_argument('--name', required=True)
    p.add_argument('--namespace')
    p.add_argument('--replicas', type=int, default=1)
    p.add_argument('--port', type=int)
    p.add_argument('--pull-policy', default='Always')
    args=p.parse_args()

    images = read_images(args.csv)
    if not images: sys.exit("No images found")

    lines=[]
    lines += ["apiVersion: apps/v1","kind: Deployment","metadata:",f"  name: {args.name}"]
    if args.namespace: lines.append(f"  namespace: {args.namespace}")
    lines += ["spec:",f"  replicas: {args.replicas}","  selector:","    matchLabels:",f"      app: {args.name}",
              "  template:","    metadata:","      labels:",f"        app: {args.name}",
              "    spec:","      containers:"]
    seen={}
    for img in images:
        nm = san(img)
        if nm in seen: seen[nm]+=1; nm=f"{nm}-{seen[nm]}"
        else: seen[nm]=0
        lines += [f"      - name: {nm}",f"        image: {img}",f"        imagePullPolicy: {args.pull_policy}"]
        if args.port:
:q            lines += ["        ports:",f"          - containerPort: {args.port}","            protocol: TCP"]
    print("\n".join(lines))

if __name__ == "__main__": main()
