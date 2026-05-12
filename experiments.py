import csv
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BENCHMARKS_DIR = Path("benchmarks")
RESULTS_DIR = Path("experiment_results")
RESULTS_DIR.mkdir(exist_ok=True)

DOMAINS = ['blocks', 'logistics', 'zenotravel', 'parcprinter', 'sokoban']
TIME_LIMIT = 300


def run_pyperplan(domain, problem, heuristics, openlist, timeout=TIME_LIMIT):
    cmd = [
        sys.executable, '-m', 'pyperplan',
        '-s', 'gbfs_multi',
        '-H', heuristics,
        '-openlist', openlist,
        str(domain),
        str(problem)
    ]

    start = time.time()

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        elapsed = time.time() - start
        output = result.stdout + result.stderr
        solved = 'Goal reached' in output

        metrics = {'solved': solved, 'time': elapsed, 'timeout': False}

        if solved:
            match = re.search(r'Plan length:\s*(\d+)', output)
            metrics['plan_length'] = int(match.group(1)) if match else None

            match = re.search(r'Expanded nodes:\s*(\d+)', output)
            metrics['expansions'] = int(match.group(1)) if match else None
        else:
            metrics['plan_length'] = None
            metrics['expansions'] = None

        return metrics

    except subprocess.TimeoutExpired:
        return {
            'solved': False, 'time': timeout, 'timeout': True,
            'plan_length': None, 'expansions': None,
        }
    except Exception:
        return {
            'solved': False, 'time': None, 'timeout': False,
            'plan_length': None, 'expansions': None,
        }


def get_problems(domain_name):
    domain_dir = BENCHMARKS_DIR / domain_name
    problems = sorted(domain_dir.glob("task*.pddl"))
    return problems


def get_domain_file(domain_dir, problem_file):
    domain_file = domain_dir / "domain.pddl"
    if not domain_file.exists():
        task_num = problem_file.stem.replace('task', '')
        domain_file = domain_dir / f"domain{task_num}.pddl"
    return domain_file


# Experiment 1: Single heuristics baseline

def experiment_1():
    print("EXPERIMENT 1: Single Heuristics")
    print("=" * 70)

    heuristics = ['hff', 'hadd', 'hmax', 'lmcut', 'landmark']
    fieldnames = [
        'domain', 'problem', 'heuristic',
        'solved', 'time', 'timeout',
        'plan_length', 'expansions',
    ]
    filename = RESULTS_DIR / f"exp1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()

        for domain_name in DOMAINS:
            domain_dir = BENCHMARKS_DIR / domain_name
            problems = get_problems(domain_name)

            for h in heuristics:
                print(f"\n  {domain_name} / {h}")

                for prob in problems:
                    print(f"    {prob.stem}...", end=' ', flush=True)
                    domain_file = get_domain_file(domain_dir, prob)
                    result = run_pyperplan(domain_file, prob, h, 'single')

                    writer.writerow({
                        'domain': domain_name,
                        'problem': prob.stem,
                        'heuristic': h,
                        **result,
                    })
                    f.flush()

                    status = ("OK" if result['solved']
                              else "TIMEOUT" if result.get('timeout') else "FAIL")
                    print(status)

    print(f"\nSaved: {filename}")
    return filename


# Experiment 2: Multiple heuristics (2 heuristics)

def experiment_2():
    print("EXPERIMENT 2: Two Heuristics")
    print("=" * 70)

    print("\nChoose multi-heuristic strategy to run:")
    print("  1. Max")
    print("  2. Sum")
    print("  3. Alternation")
    print("  4. Pareto")
    print("  5. All strategies")

    choice = input("\nEnter choice (1-5): ").strip()

    strategy_map = {
        '1': ['max'],
        '2': ['sum'],
        '3': ['alternation'],
        '4': ['pareto'],
        '5': ['max', 'sum', 'alternation', 'pareto'],
    }
    strategies = strategy_map.get(choice, ['max', 'sum', 'alternation', 'pareto'])
    if choice not in strategy_map:
        print("Invalid choice: running all strategies.")

    pairs = [
    ('hff', 'hadd'), ('hmax', 'lmcut'),
    ('hff', 'landmark'), ('landmark', 'lmcut'),
    ]

    strategy_suffix = strategies[0] if len(strategies) == 1 else 'all'
    filename = RESULTS_DIR / (
    f"exp2_{strategy_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

    fieldnames = [
        'domain', 'problem', 'heuristics', 'strategy',
        'solved', 'time', 'timeout',
        'plan_length', 'expansions',
    ]

    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()

        for domain_name in DOMAINS:
            domain_dir = BENCHMARKS_DIR / domain_name
            problems = get_problems(domain_name)

            for h1, h2 in pairs:
                h_str = f"{h1},{h2}"

                for strategy in strategies:
                    print(f"\n  {domain_name} / {h_str} / {strategy}")

                    for prob in problems:
                        print(f"    {prob.stem}...", end=' ', flush=True)
                        domain_file = get_domain_file(domain_dir, prob)
                        result = run_pyperplan(domain_file, prob, h_str, strategy)

                        writer.writerow({
                            'domain': domain_name,
                            'problem': prob.stem,
                            'heuristics': h_str,
                            'strategy': strategy,
                            **result,
                        })
                        f.flush()

                        status = ("OK" if result['solved']
                                  else "TIMEOUT" if result.get('timeout') else "FAIL")
                        print(status)

    print(f"\nSaved: {filename}")
    return filename


# Experiment 3: Multiple heuristics (3 heuristics)

def experiment_3():
    print("EXPERIMENT 3: Three-Heuristic Combination")
    print("=" * 70)

    h_str = 'hadd,hff,landmark'
    strategies = ['max', 'alternation']

    fieldnames = [
        'domain', 'problem', 'heuristics', 'strategy', 'n_heuristics',
        'solved', 'time', 'timeout',
        'plan_length', 'expansions',
    ]
    filename = RESULTS_DIR / f"exp3_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()

        for domain_name in DOMAINS:
            domain_dir = BENCHMARKS_DIR / domain_name
            problems = get_problems(domain_name)

            for strategy in strategies:
                print(f"\n  {domain_name} / {h_str} / {strategy}")

                for prob in problems:
                    print(f"    {prob.stem}...", end=' ', flush=True)
                    domain_file = get_domain_file(domain_dir, prob)
                    result = run_pyperplan(domain_file, prob, h_str, strategy)

                    writer.writerow({
                        'domain': domain_name,
                        'problem': prob.stem,
                        'heuristics': h_str,
                        'strategy': strategy,
                        'n_heuristics': 3,
                        **result,
                    })
                    f.flush()

                    status = ("OK" if result['solved']
                              else "TIMEOUT" if result.get('timeout') else "FAIL")
                    print(status)

    print(f"\nSaved: {filename}")
    return filename


def main():
    print("\n1 - Experiment 1: Single Heuristics")
    print("2 - Experiment 2: Two Heuristics")
    print("3 - Experiment 3: Three Heuristics")
    print("4 - All experiments")

    choice = input("\nChoice: ").strip()

    if choice == '1':
        experiment_1()
    elif choice == '2':
        experiment_2()
    elif choice == '3':
        experiment_3()
    elif choice == '4':
        experiment_1()
        experiment_2()
        experiment_3()
    else:
        print("Invalid choice.")


if __name__ == '__main__':
    main()