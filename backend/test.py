"""
MSE 131 Final Take-Home Assessment
Coffee Shop Queueing Simulation Model
Author: Divyam
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

# Set random seed for reproducibility
np.random.seed(42)

# ============================================================
# BASELINE MODEL PARAMETERS
# ============================================================
BASE_ARRIVAL_RATE = 20        # customers per hour (lambda)
BASE_SERVICE_RATE = 25        # customers per hour per server (mu)
NUM_SERVERS = 1               # number of baristas
SIM_HOURS = 8                 # simulate one 8-hour shift
NUM_RUNS = 50                 # Monte Carlo replications

# ============================================================
# EXTENSION PARAMETERS
# ============================================================
# Extension 1: Rush-hour arrivals
RUSH_MULTIPLIER = 2.0         # arrival rate doubles during rush
RUSH_START = 2.0              # rush starts at hour 2 (e.g., 9 AM if shop opens 7 AM)
RUSH_END = 4.0                # rush ends at hour 4

# Extension 2: Two customer types
PROB_COMPLEX = 0.35           # 35% of customers order complex drinks
SIMPLE_SERVICE_MEAN = 2.0     # minutes for simple order
COMPLEX_SERVICE_MEAN = 4.5    # minutes for complex order

# Extension 3: Worker breaks
BREAK_DURATION = 15.0 / 60.0  # 15 minutes in hours
BREAK_INTERVAL = 2.0          # break every 2 hours

# Extension 4: Rework / remakes
REWORK_PROB = 0.05            # 5% of drinks need to be remade
REWORK_TIME_MEAN = 2.0        # minutes for a remake

# Extension 5: Second server
# Toggled by setting NUM_SERVERS = 2


def get_arrival_rate(current_time, base_rate, use_rush=False):
    """Return the arrival rate at a given time. If rush-hour is enabled,
    the rate is higher during the rush window."""
    if use_rush and RUSH_START <= current_time <= RUSH_END:
        return base_rate * RUSH_MULTIPLIER
    return base_rate


def generate_service_time(use_two_types=False):
    """Generate a service time in hours. If two customer types are enabled,
    randomly pick simple or complex order."""
    if use_two_types:
        if np.random.random() < PROB_COMPLEX:
            return np.random.exponential(COMPLEX_SERVICE_MEAN / 60.0)
        else:
            return np.random.exponential(SIMPLE_SERVICE_MEAN / 60.0)
    else:
        return np.random.exponential(1.0 / BASE_SERVICE_RATE)


def check_rework(use_rework=False):
    """Return additional rework time if the drink needs to be remade."""
    if use_rework and np.random.random() < REWORK_PROB:
        return np.random.exponential(REWORK_TIME_MEAN / 60.0)
    return 0.0


def get_server_available(current_time, num_servers, use_breaks=False):
    """Return the number of servers actually available at a given time,
    accounting for scheduled breaks."""
    if not use_breaks:
        return num_servers
    available = num_servers
    for s in range(num_servers):
        # Stagger breaks: server s takes a break at BREAK_INTERVAL * (k+1) + s * 0.25
        for k in range(int(SIM_HOURS / BREAK_INTERVAL)):
            break_start = BREAK_INTERVAL * (k + 1) + s * 0.25
            break_end = break_start + BREAK_DURATION
            if break_start <= current_time < break_end:
                available -= 1
                break
    return max(available, 0)


def simulate_one_run(arrival_rate, num_servers, use_rush=False,
                     use_two_types=False, use_breaks=False,
                     use_rework=False):
    """
    Run one replication of the coffee shop simulation.
    Uses a simple event-stepping approach.
    Returns a dictionary of performance metrics.
    """
    # Generate arrivals using thinning for time-varying rate
    arrivals = []
    t = 0.0
    max_rate = arrival_rate * (RUSH_MULTIPLIER if use_rush else 1.0)

    while t < SIM_HOURS:
        # Generate next potential arrival
        t += np.random.exponential(1.0 / max_rate)
        if t >= SIM_HOURS:
            break
        # Accept or reject (thinning method)
        current_rate = get_arrival_rate(t, arrival_rate, use_rush)
        if np.random.random() < current_rate / max_rate:
            arrivals.append(t)

    n = len(arrivals)
    if n == 0:
        return {
            'avg_wait': 0, 'max_wait': 0, 'avg_queue': 0,
            'throughput': 0, 'utilization': 0, 'num_served': 0,
            'pct_wait_over_5min': 0
        }

    # Generate service times
    service_times = []
    for _ in range(n):
        st = generate_service_time(use_two_types)
        st += check_rework(use_rework)
        service_times.append(st)

    # Simulate the queue with multiple servers
    # Track when each server becomes free
    server_free = [0.0] * num_servers
    wait_times = []
    departures = []

    for i in range(n):
        arr = arrivals[i]

        # Find available servers considering breaks
        best_server = None
        best_free_time = float('inf')

        for s in range(num_servers):
            # Check if server is on break at the time they would start serving
            effective_free = max(server_free[s], arr)
            servers_up = get_server_available(effective_free, num_servers, use_breaks)

            if server_free[s] <= arr:
                # Server is already free
                if server_free[s] < best_free_time or best_server is None:
                    best_server = s
                    best_free_time = server_free[s]
            elif server_free[s] < best_free_time:
                best_server = s
                best_free_time = server_free[s]

        # If breaks make a server unavailable, add wait
        start_time = max(arrivals[i], server_free[best_server])

        # Check if server is on break when service would start
        if use_breaks:
            while True:
                avail = get_server_available(start_time, num_servers, use_breaks)
                if avail > 0:
                    break
                start_time += 0.01  # step forward until break ends

        wait = start_time - arr
        wait_times.append(wait)

        end_time = start_time + service_times[i]
        server_free[best_server] = end_time
        departures.append(end_time)

    # Compute performance measures
    wait_array = np.array(wait_times)
    avg_wait = np.mean(wait_array) * 60  # convert to minutes
    max_wait = np.max(wait_array) * 60
    pct_over_5 = np.mean(wait_array * 60 > 5.0) * 100

    # Average queue length using Little's Law approximation
    total_wait_hours = np.sum(wait_array)
    avg_queue = total_wait_hours / SIM_HOURS

    # Throughput
    served = sum(1 for d in departures if d <= SIM_HOURS)
    throughput = served / SIM_HOURS

    # Utilization
    total_service_hours = sum(service_times[:served])
    utilization = total_service_hours / (num_servers * SIM_HOURS) * 100

    return {
        'avg_wait': avg_wait,
        'max_wait': max_wait,
        'avg_queue': avg_queue,
        'throughput': throughput,
        'utilization': utilization,
        'num_served': served,
        'pct_wait_over_5min': pct_over_5
    }


def run_experiment(arrival_rate, num_servers, use_rush=False,
                   use_two_types=False, use_breaks=False,
                   use_rework=False, num_runs=NUM_RUNS):
    """Run multiple replications and return averaged results."""
    results = []
    for _ in range(num_runs):
        r = simulate_one_run(arrival_rate, num_servers, use_rush,
                             use_two_types, use_breaks, use_rework)
        results.append(r)

    avg_results = {}
    for key in results[0]:
        vals = [r[key] for r in results]
        avg_results[key] = np.mean(vals)
        avg_results[key + '_std'] = np.std(vals)

    return avg_results


# ============================================================
# PART 3A: SCENARIO COMPARISONS
# ============================================================
def run_scenario_comparison():
    print("=" * 65)
    print("SCENARIO COMPARISON: Low / Medium / High Demand")
    print("(All 5 extensions enabled, 1 server)")
    print("=" * 65)

    scenarios = {
        'Low Demand (12/hr)': 12,
        'Medium Demand (20/hr)': 20,
        'High Demand (30/hr)': 30
    }

    scenario_results = {}
    for name, rate in scenarios.items():
        r = run_experiment(rate, 1, use_rush=True, use_two_types=True,
                           use_breaks=True, use_rework=True)
        scenario_results[name] = r
        print(f"\n{name}:")
        print(f"  Avg Wait Time:      {r['avg_wait']:.2f} min")
        print(f"  Max Wait Time:      {r['max_wait']:.2f} min")
        print(f"  Avg Queue Length:   {r['avg_queue']:.2f} customers")
        print(f"  Throughput:         {r['throughput']:.1f} customers/hr")
        print(f"  Utilization:        {r['utilization']:.1f}%")
        print(f"  % Waiting > 5 min: {r['pct_wait_over_5min']:.1f}%")

    return scenario_results


# ============================================================
# PART 3A (EXTRA): 1 SERVER VS 2 SERVERS AT HIGH DEMAND
# ============================================================
def run_server_comparison():
    print("\n" + "=" * 65)
    print("SCENARIO COMPARISON: 1 Server vs 2 Servers at High Demand (30/hr)")
    print("(All extensions enabled)")
    print("=" * 65)

    for ns in [1, 2]:
        r = run_experiment(30, ns, use_rush=True, use_two_types=True,
                           use_breaks=True, use_rework=True)
        print(f"\n{ns} Server(s):")
        print(f"  Avg Wait Time:      {r['avg_wait']:.2f} min")
        print(f"  Max Wait Time:      {r['max_wait']:.2f} min")
        print(f"  Avg Queue Length:   {r['avg_queue']:.2f} customers")
        print(f"  Throughput:         {r['throughput']:.1f} customers/hr")
        print(f"  Utilization:        {r['utilization']:.1f}%")
        print(f"  % Waiting > 5 min: {r['pct_wait_over_5min']:.1f}%")

    return None


# ============================================================
# PART 3B: SENSITIVITY ANALYSIS
# ============================================================
def run_sensitivity_analysis():
    print("\n" + "=" * 65)
    print("SENSITIVITY ANALYSIS")
    print("=" * 65)

    # Sensitivity 1: Arrival rate (10 to 35 customers/hr)
    print("\n--- Sensitivity to Arrival Rate (1 server, all extensions) ---")
    arrival_rates = np.arange(10, 36, 5)
    sens_arrival = {}
    for ar in arrival_rates:
        r = run_experiment(ar, 1, use_rush=True, use_two_types=True,
                           use_breaks=True, use_rework=True)
        sens_arrival[ar] = r
        print(f"  Rate={ar}/hr: AvgWait={r['avg_wait']:.2f}min, "
              f"Util={r['utilization']:.1f}%, Throughput={r['throughput']:.1f}/hr")

    # Sensitivity 2: Number of servers (1, 2, 3) at high demand
    print("\n--- Sensitivity to Number of Servers (arrival=30/hr, all extensions) ---")
    server_counts = [1, 2, 3]
    sens_servers = {}
    for ns in server_counts:
        r = run_experiment(30, ns, use_rush=True, use_two_types=True,
                           use_breaks=True, use_rework=True)
        sens_servers[ns] = r
        print(f"  Servers={ns}: AvgWait={r['avg_wait']:.2f}min, "
              f"Util={r['utilization']:.1f}%, Throughput={r['throughput']:.1f}/hr")

    return sens_arrival, sens_servers


# ============================================================
# PART 3 (EXTRA): BASELINE VS EXTENDED MODEL COMPARISON
# ============================================================
def run_baseline_vs_extended():
    print("\n" + "=" * 65)
    print("BASELINE VS FULLY EXTENDED MODEL (20/hr, 1 server)")
    print("=" * 65)

    baseline = run_experiment(20, 1, use_rush=False, use_two_types=False,
                              use_breaks=False, use_rework=False)
    extended = run_experiment(20, 1, use_rush=True, use_two_types=True,
                              use_breaks=True, use_rework=True)

    print(f"\n{'Metric':<25} {'Baseline':>12} {'Extended':>12}")
    print("-" * 50)
    for key in ['avg_wait', 'max_wait', 'avg_queue', 'throughput', 'utilization', 'pct_wait_over_5min']:
        label = key.replace('_', ' ').title()
        unit = 'min' if 'wait' in key else ('%' if 'util' in key or 'pct' in key else '')
        print(f"  {label:<23} {baseline[key]:>10.2f}{unit}  {extended[key]:>10.2f}{unit}")


# ============================================================
# GENERATE FIGURES
# ============================================================
def generate_figures(sens_arrival, sens_servers, scenario_results):
    output_dir = '/home/claude/figures'
    os.makedirs(output_dir, exist_ok=True)

    # Figure 1: Scenario comparison bar chart
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    names = list(scenario_results.keys())
    short_names = ['Low (12/hr)', 'Medium (20/hr)', 'High (30/hr)']
    colors = ['#4CAF50', '#FF9800', '#F44336']

    metrics = [('avg_wait', 'Avg Wait Time (min)'),
               ('utilization', 'Utilization (%)'),
               ('throughput', 'Throughput (cust/hr)')]

    for idx, (key, ylabel) in enumerate(metrics):
        vals = [scenario_results[n][key] for n in names]
        axes[idx].bar(short_names, vals, color=colors, edgecolor='black', linewidth=0.5)
        axes[idx].set_ylabel(ylabel, fontsize=10)
        axes[idx].set_title(ylabel.split('(')[0].strip(), fontsize=11, fontweight='bold')
        for i, v in enumerate(vals):
            axes[idx].text(i, v + max(vals) * 0.02, f'{v:.1f}', ha='center', fontsize=9)

    plt.suptitle('Scenario Comparison: Low, Medium, and High Demand', fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/fig1_scenario_comparison.png', dpi=200, bbox_inches='tight')
    plt.close()

    # Figure 2: Sensitivity to arrival rate
    fig, ax1 = plt.subplots(figsize=(8, 5))
    rates = sorted(sens_arrival.keys())
    waits = [sens_arrival[r]['avg_wait'] for r in rates]
    utils = [sens_arrival[r]['utilization'] for r in rates]

    color1 = '#1976D2'
    color2 = '#D32F2F'

    ax1.plot(rates, waits, 'o-', color=color1, linewidth=2, markersize=6, label='Avg Wait Time')
    ax1.set_xlabel('Arrival Rate (customers/hr)', fontsize=11)
    ax1.set_ylabel('Avg Wait Time (min)', color=color1, fontsize=11)
    ax1.tick_params(axis='y', labelcolor=color1)

    ax2 = ax1.twinx()
    ax2.plot(rates, utils, 's--', color=color2, linewidth=2, markersize=6, label='Utilization')
    ax2.set_ylabel('Utilization (%)', color=color2, fontsize=11)
    ax2.tick_params(axis='y', labelcolor=color2)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=9)

    plt.title('Sensitivity Analysis: Effect of Arrival Rate', fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/fig2_sensitivity_arrival.png', dpi=200, bbox_inches='tight')
    plt.close()

    # Figure 3: Sensitivity to number of servers
    fig, ax = plt.subplots(figsize=(7, 5))
    servers = sorted(sens_servers.keys())
    waits_s = [sens_servers[s]['avg_wait'] for s in servers]
    utils_s = [sens_servers[s]['utilization'] for s in servers]

    x = np.arange(len(servers))
    width = 0.35

    bars1 = ax.bar(x - width/2, waits_s, width, label='Avg Wait (min)', color='#42A5F5', edgecolor='black', linewidth=0.5)
    ax2 = ax.twinx()
    bars2 = ax2.bar(x + width/2, utils_s, width, label='Utilization (%)', color='#EF5350', edgecolor='black', linewidth=0.5)

    ax.set_xlabel('Number of Servers', fontsize=11)
    ax.set_ylabel('Avg Wait Time (min)', fontsize=11)
    ax2.set_ylabel('Utilization (%)', fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels([str(s) for s in servers])

    lines = [bars1, bars2]
    labels = ['Avg Wait (min)', 'Utilization (%)']
    ax.legend(lines, labels, loc='upper right', fontsize=9)

    plt.title('Sensitivity Analysis: Effect of Number of Servers\n(Arrival Rate = 30/hr)', fontsize=12, fontweight='bold')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/fig3_sensitivity_servers.png', dpi=200, bbox_inches='tight')
    plt.close()

    print(f"\nFigures saved to {output_dir}/")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("MSE 131 Final Assessment: Coffee Shop Simulation")
    print("=" * 65)

    # Run all experiments
    scenario_results = run_scenario_comparison()
    run_server_comparison()
    sens_arrival, sens_servers = run_sensitivity_analysis()
    run_baseline_vs_extended()

    # Generate figures
    generate_figures(sens_arrival, sens_servers, scenario_results)

    print("\n" + "=" * 65)
    print("SIMULATION COMPLETE")
    print("=" * 65)