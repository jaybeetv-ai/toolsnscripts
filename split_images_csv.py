import argparse, csv, os, re, sys
from collections import defaultdict

def read_images(csv_path):
    with open(csv_path, newline='') as f:
        r = csv.reader(f)
        first = next(r, None)
        if not first: return [], False
        header = [h.strip().lower() for h in first] if any(first) else []
        has_header = "image" in header
        rows = []
        if has_header:
            idx = header.index("image")
            for row in r:
                if len(row) > idx and row[idx].strip():
                    rows.append(row[idx].strip())
        else:
            if first and first[0].strip():
                rows.append(first[0].strip())
            for row in r:
                if row and row[0].strip():
                    rows.append(row[0].strip())
        return rows, has_header

def key_by_segment(image, seg_index):
    parts = image.split("/")
    if 0 <= seg_index < len(parts):
        return parts[seg_index]
    return "ungrouped"

def key_by_contains(image, mapping):
    for needle, group in mapping.items():
        if needle in image:
            return group
    return "ungrouped"

def key_by_regex(image, pattern):
    m = pattern.search(image)
    return m.group(1) if m else "ungrouped"

def main():
    ap = argparse.ArgumentParser(description="Split a master CSV of images into multiple CSVs by group.")
    ap.add_argument("--in", dest="in_csv", required=True, help="Master CSV (from Excel)")
    ap.add_argument("--out-dir", default="groups", help="Directory to write CSV files")
    # choose ONE of the grouping modes below:
    ap.add_argument("--segment", type=int, help="Group by Nth path segment of image (0-based). Example: --segment 3")
    ap.add_argument("--contains", help="Mapping list: needle=group,needle=group. Example: db2u=db2u,opensearch=opensearch")
    ap.add_argument("--regex", help="Regex with one capture group for key. Example: '(db2u|opensearch|cpfs)'")
    ap.add_argument("--prefix", default="images_", help="Output CSV filename prefix")
    args = ap.parse_args()

    images, _ = read_images(args.in_csv)
    if not images:
        sys.exit("No images found in input CSV")

    if sum(bool(x) for x in [args.segment is not None, args.contains, args.regex]) != 1:
        sys.exit("Choose exactly one of --segment, --contains, or --regex")

    if args.contains:
        mapping = {}
        for pair in args.contains.split(","):
            if "=" not in pair: 
                sys.exit(f"Bad --contains pair: {pair} (use needle=group)")
            needle, group = pair.split("=", 1)
            mapping[needle.strip()] = group.strip()
    else:
        mapping = None

    pattern = re.compile(args.regex) if args.regex else None

    groups = defaultdict(list)
    for img in images:
        if args.segment is not None:
            key = key_by_segment(img, args.segment)
        elif mapping is not None:
            key = key_by_contains(img, mapping)
        else:
            key = key_by_regex(img, pattern)
        groups[key].append(img)

    os.makedirs(args.out_dir, exist_ok=True)
    written = []
    for key, imgs in groups.items():
        safe_key = re.sub(r"[^A-Za-z0-9._-]+", "_", key)
        out_path = os.path.join(args.out_dir, f"{args.prefix}{safe_key}.csv")
        with open(out_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["image"])  # header for our generator
            for im in imgs:
                w.writerow([im])
        written.append((key, out_path, len(imgs)))

    print("Wrote:")
    for key, p, n in written:
        print(f"  {key:20s} -> {p}  ({n} rows)")
