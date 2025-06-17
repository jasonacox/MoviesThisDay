"""
stats.py - Analyze and display the distribution of 'popularity' in TMDB_movie_dataset_v11.csv as an ASCII percentage graph.
"""
import csv
import os
import math

CSV_PATH = os.path.join(os.path.dirname(__file__), 'TMDB_movie_dataset_v11.csv')

# Settings for histogram
NUM_BINS = 20
BAR_WIDTH = 40

# Read popularity values
def read_popularity(csv_path):
    pop_values_local = []
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                pop = float(row['popularity']) if row['popularity'] else 0.0
                pop_values_local.append(pop)
            except (ValueError, KeyError):
                continue
    return pop_values_local

def read_field(csv_path, field, numeric=True):
    values = []
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                val = row[field]
                if numeric:
                    val = float(val) if val else 0.0
                values.append(val)
            except (ValueError, KeyError):
                continue
    return values

def ascii_histogram_log(pop_values_arg, label, num_bins=NUM_BINS, bar_width=BAR_WIDTH):
    if not pop_values_arg:
        print(f"No data found for {label}.")
        return
    # Use log10 scale, ignore zeros for log
    filtered = [v for v in pop_values_arg if v > 0]
    if not filtered:
        print(f"No positive values for {label}.")
        return
    min_val, max_val = min(filtered), max(filtered)
    min_log, max_log = math.log10(min_val), math.log10(max_val)
    bin_size = (max_log - min_log) / num_bins if max_log > min_log else 1
    bins = [0] * num_bins
    for v in filtered:
        logv = math.log10(v)
        idx = int((logv - min_log) / bin_size) if bin_size > 0 else 0
        if idx == num_bins:  # Edge case for max value
            idx -= 1
        bins[idx] += 1
    total = len(filtered)
    # Determine max width for range values
    def fmt(val):
        if val >= 10_000:
            return f"{int(val):,}"
        return f"{val:,.2f}"
    range_samples = [
        (10 ** (min_log + i * bin_size), 10 ** (min_log + (i + 1) * bin_size))
        for i in range(num_bins)
    ]
    max_left = max(len(fmt(left)) for left, _ in range_samples)
    max_right = max(len(fmt(right)) for _, right in range_samples)
    range_fmt = f"{{:>{max_left}}} - {{:>{max_right}}}"
    print(f"\n{label} Distribution (log10 scale, n={total})\n")
    print(f"{'Range':>{max_left + max_right + 3}} | {'':{bar_width}s} | {'%':>7} {'Count':>7}")
    for i, count in enumerate(bins):
        left = 10 ** (min_log + i * bin_size)
        right = 10 ** (min_log + (i + 1) * bin_size)
        pct = (count / total) * 100
        bar = '#' * int((count / total) * bar_width)
        print(f"{range_fmt.format(fmt(left), fmt(right))} | {bar:<{bar_width}s} | {pct:6.2f}% {count:7d}")
    print(f"\nMin: {min_val:.2f}  Max: {max_val:.2f}  Mean: {sum(filtered)/total:.2f}")

def ascii_histogram_linear(values, label, num_bins=NUM_BINS, bar_width=BAR_WIDTH):
    filtered = [v for v in values if isinstance(v, (int, float))]
    if not filtered:
        print(f"No values for {label}.")
        return
    min_val, max_val = min(filtered), max(filtered)
    bin_size = (max_val - min_val) / num_bins if max_val > min_val else 1
    bins = [0] * num_bins
    for v in filtered:
        idx = int((v - min_val) / bin_size) if bin_size > 0 else 0
        if idx == num_bins:
            idx -= 1
        bins[idx] += 1
    total = len(filtered)
    def fmt(val):
        if val >= 1_000_000:
            return f"{int(val):,}"
        return f"{val:,.2f}"
    range_samples = [
        (min_val + i * bin_size, min_val + (i + 1) * bin_size)
        for i in range(num_bins)
    ]
    max_left = max(len(fmt(left)) for left, _ in range_samples)
    max_right = max(len(fmt(right)) for _, right in range_samples)
    range_fmt = f"{{:>{max_left}}} - {{:>{max_right}}}"
    print(f"\n{label} Distribution (linear, n={total})\n")
    print(f"{'Range':>{max_left + max_right + 3}} | {'':{bar_width}s} | {'%':>7} {'Count':>7}")
    for i, count in enumerate(bins):
        left = min_val + i * bin_size
        right = left + bin_size
        pct = (count / total) * 100
        bar = '#' * int((count / total) * bar_width)
        print(f"{range_fmt.format(fmt(left), fmt(right))} | {bar:<{bar_width}s} | {pct:6.2f}% {count:7d}")
    print(f"\nMin: {min_val:.2f}  Max: {max_val:.2f}  Mean: {sum(filtered)/total:.2f}\n")

def ascii_histogram_categorical(values, label):
    from collections import Counter
    counts = Counter(values)
    total = sum(counts.values())
    # Dynamically determine max width for category labels
    max_cat = max((len(str(k)) for k in counts), default=8)
    cat_fmt = f"{{:>{max_cat}}}"
    print(f"\n{label} Distribution (n={total})\n")
    print(f"{'Category':>{max_cat}} | {'':{BAR_WIDTH}s} | {'%':>7} {'Count':>7}")
    for k, v in counts.most_common():
        pct = (v / total) * 100
        bar = '#' * int((v / total) * BAR_WIDTH)
        print(f"{cat_fmt.format(str(k))} | {bar:<{BAR_WIDTH}s} | {pct:6.2f}% {v:7d}")
    print()

if __name__ == "__main__":
    # Popularity (already in original stats.py)
    pop_values_main = read_popularity(CSV_PATH)
    ascii_histogram_log(pop_values_main, 'Popularity')

    # vote_average (linear scale, 0-10)
    vote_avg_values = read_field(CSV_PATH, 'vote_average', numeric=True)
    ascii_histogram_linear(vote_avg_values, 'Vote Average')

    # runtime (log scale)
    runtime_values = read_field(CSV_PATH, 'runtime', numeric=True)
    ascii_histogram_log(runtime_values, 'Runtime (min)')

    # status (categorical)
    status_values = read_field(CSV_PATH, 'status', numeric=False)
    ascii_histogram_categorical(status_values, 'Status')

    # revenue (log scale)
    revenue_values = read_field(CSV_PATH, 'revenue', numeric=True)
    ascii_histogram_log(revenue_values, 'Revenue (USD)')
