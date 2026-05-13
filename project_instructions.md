# Information & Instructions 
### Topic: Satisficing Search with Multiple Heuristics
#### Purpose: To understand the effect of using multiple heurics compared to using a single heuristic in GBFS.

For this project a new GBFS implementation which supports five open list strategies (single and multiple heuristics) is added in [Pyperplan](https://github.com/aibasel/pyperplan):
**Single**, **Max**, **Sum**, **Alternation**, and **Pareto**.



---
### Open list strategies (`-openlist`)

| Strategy | Description |
|----------|-------------|
| `single` | Standard single-heuristic GBFS (one heuristic only) |
| `max` | States ordered by max(h₁, ..., hₙ) |
| `sum` | States ordered by sum(h₁, ..., hₙ) |
| `alternation` | One queue per heuristic (Round-robin order) |
| `pareto` | Randomly selects from the Pareto frontier |


---

## Usage

The `gbfs_multi` implementation accepts a list of heuristics, an open list strategy, and a PDDL domain and problem file: 

    python -m pyperplan -H <heuristics> -s gbfs_multi -openlist <strategy> DOMAIN PROBLEM

To use multiple heuristics, separate them with a comma and no spaces: `-H hff,landmark`

##### Examples:

To use gbfs with a single hff heuristic, run:

    python -m pyperplan -H hff -s gbfs_multi -openlist single DOMAIN PROBLEM

To use alternation with two heuristics (hff and landmark), run:

    python -m pyperplan -H hff,landmark -s gbfs_multi -openlist alternation DOMAIN PROBLEM

To use max with two heuristics (hff and landmark):

    python -m pyperplan -H hff,landmark -s gbfs_multi -openlist max DOMAIN PROBLEM

Pareto with two heuristics (hff and hadd):

    python -m pyperplan -H hff,hadd -s gbfs_multi -openlist pareto DOMAIN PROBLEM

Same goes for using more than two heuristics, for example to use alternation with three heuristics run:
    
    python -m pyperplan -H hadd,hff,landmark -s gbfs_multi -openlist alternation DOMAIN PROBLEM
---

## Experiments

The experiments were designed to answer these questions:
 
1. Does using multiple heuristics improve search performance over a single heuristic?
2. If yes, which strategy works best and how does performance vary across domains?
3. Is it true that the more heuristics we use, the better search performance gets?
 
- **Experiment 1** - Single heuristic: each heuristic
  is run across all domains to choose a baseline.
- **Experiment 2** - Two-heuristic combinations: all four multi-heuristic open list strategies (Max, Sum,
  Alternation, Pareto) are tested on four heuristic pairs across all domains.
  Results are compared against the single heuristic baselines to answer the first and second question.
- **Experiment 3** - Three-heuristic combination: Alternation and Max are tested with three
  heuristics (hAdd, hFF, hLM) and compared against their two-heuristic counterparts.

`experiments.py` script runs all experiments mentioned above:

    python experiments.py

After run, the script shows an interactive menu to select which experiment
to run (single heuristics, two heuristics, three heuristics, or all at once). For the second experiment, you will be asked which strategy to run (Max, Sum, Alternation, Pareto, or all).

Results are saved to CSV files in `experiment_results/`:

- `experiment_results/exp1_<timestamp>.csv` - single heuristic baselines
- `experiment_results/exp2_<strategy>_<timestamp>.csv` - two-heuristic combinations
- `experiment_results/exp3_<timestamp>.csv` - three-heuristic combinations

## Benchmark Domains

The following domains from the `benchmarks/` were used for the experiments:

| Domain | Tasks | Description |
|--------|-------|-------|
| `blocks` | 35 | Classic blocks world |
| `logistics` | 28 | Package delivery |
| `zenotravel` | 20 | Travel planning |
| `parcprinter` | 30 | Large action costs |
| `sokoban` | 30 | NP-complete puzzle |

---

## Plots

To generate plots with the results of experiments, run:

    python plots.py

Plots are saved to the `plots/` directory:

- `coverage_over_time.png` - cactus plot comparing all strategies 
- `heatmap.png` - coverage per strategy per domain
- `heuristic_scaling.png` - effect of adding a third heuristic 

---

## Small Notes

#### Purpose of 'SearchResult':
To be able to run multiple configurations at once for the experiments, `gbfs_multi_search` returns a `SearchResult` namedtuple instead of plain plan or `None` like other search algorithms in Pyperplan do. So instead of calling the planner separately for each problem via the command line, `experiments.py` script is used. 
`SearchResult` tracks the solution, solved status, expansion count and    plan length in one object so all metrics can be in one place and for each experiment the domain, problem, heruristics, strategy, runtime and timeout status are saved in CSV files for analysis.

#### Pareto Results
The current experimental results for the Pareto approach were obtained from an earlier implementation in which I did a mistake filtering dominated states at insertion time instead at pop time. By the time I identified and fixed this issue it was too late to rerun all configurations for Pareto before the deadline. So the current Pareto implementation is correct, but the current reported results do not correspond to it. 

