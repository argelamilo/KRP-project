#
# This file is part of pyperplan.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#


import heapq
import logging
from collections import namedtuple

from . import searchspace


SearchResult = namedtuple(
    "SearchResult",
    ["solution", "expansions", "evaluations", "generated", "plan_length", "solved"]
)



#Open list implementations
class SingleOpenList:
    """
    Baseline open list. Equivalent to standard single-heuristic GBFS.
    """

    def __init__(self):
        self._heap = []
        self._tiebreaker = 0

    def push(self, node, h_values):
        heapq.heappush(self._heap, (h_values[0], self._tiebreaker, node, h_values))
        self._tiebreaker += 1

    def pop(self):
        _, _, node, h_values = heapq.heappop(self._heap)
        return node, h_values

    def __len__(self):
        return len(self._heap)


class MaxOpenList:
    #Orders nodes by max(h_values).

    def __init__(self):
        self._heap = []
        self._tiebreaker = 0

    def push(self, node, h_values):
        heapq.heappush(self._heap, (max(h_values), self._tiebreaker, node, h_values))
        self._tiebreaker += 1

    def pop(self):
        _, _, node, h_values = heapq.heappop(self._heap)
        return node, h_values

    def __len__(self):
        return len(self._heap)


class SumOpenList:
    #Orders nodes by sum(h_values).

    def __init__(self):
        self._heap = []
        self._tiebreaker = 0

    def push(self, node, h_values):
        heapq.heappush(self._heap, (sum(h_values), self._tiebreaker, node, h_values))
        self._tiebreaker += 1

    def pop(self):
        _, _, node, h_values = heapq.heappop(self._heap)
        return node, h_values

    def __len__(self):
        return len(self._heap)


class AlternationOpenList:

    def __init__(self, n_heuristics):
        self._queues = [[] for _ in range(n_heuristics)]
        self._n = n_heuristics
        self._tiebreaker = 0
        self._turn = 0

    def push(self, node, h_values):
        for i, h in enumerate(h_values):
            heapq.heappush(self._queues[i], (h, self._tiebreaker, node, h_values))
        self._tiebreaker += 1

    def pop(self):
        for _ in range(self._n):
            queue = self._queues[self._turn]

            if queue:
                _, _, node, h_values = heapq.heappop(queue)
                self._turn = (self._turn + 1) % self._n
                return node, h_values

            self._turn = (self._turn + 1) % self._n

        raise IndexError("pop from empty AlternationOpenList")

    def __len__(self):
        return sum(len(q) for q in self._queues)


class ParetoOpenList:
    """
    Pareto frontier open list.
    
    Only keeps states that are not dominated by others.
    A state s1 dominates s2 if:
    - h_i(s1) <= h_i(s2) for all heuristics i, AND
    - h_j(s1) < h_j(s2) for at least one heuristic j
    
    Selection strategy: FIFO (First In, First Out)
    """

    def __init__(self, n_heuristics):
        self._frontier = []
        self._n = n_heuristics

    def _dominates(self, h1, h2):
        better_or_equal = all(v1 <= v2 for v1, v2 in zip(h1, h2))
        strictly_better = any(v1 < v2 for v1, v2 in zip(h1, h2))
        return better_or_equal and strictly_better

    def push(self, node, h_values):
        for existing_h, _ in self._frontier:
            if self._dominates(existing_h, h_values):
                return

        self._frontier = [
            (h, n) for h, n in self._frontier
            if not self._dominates(h_values, h)
        ]

        self._frontier.append((h_values, node))

    def pop(self):
        if not self._frontier:
            raise IndexError("pop from empty ParetoOpenList")

        h_values, node = self._frontier.pop(0)
        return node, h_values

    def __len__(self):
        return len(self._frontier)


OPEN_LIST_TYPES = ("single", "max", "sum", "alternation", "pareto")


def make_open_list(open_list_type, n_heuristics):
    if open_list_type == "single":
        return SingleOpenList()
    elif open_list_type == "max":
        return MaxOpenList()
    elif open_list_type == "sum":
        return SumOpenList()
    elif open_list_type == "alternation":
        return AlternationOpenList(n_heuristics)
    elif open_list_type == "pareto":
        return ParetoOpenList(n_heuristics)
    else:
        raise ValueError(
            f"Unknown open list type '{open_list_type}'. "
            f"Choose from: {OPEN_LIST_TYPES}"
        )


# Search function
def gbfs_multi_search(task, heuristics, open_list_type="alternation"):
    
    if not isinstance(heuristics, list):
        heuristics = [heuristics]

    n = len(heuristics)

    open_list  = make_open_list(open_list_type, n)
    state_cost = {task.initial_state: 0}
    expansions = 0
    evaluations = 0
    generated = 0

    root   = searchspace.make_root_node(task.initial_state)
    init_h = _evaluate(root, heuristics)
    evaluations += 1

    if all(h == float("inf") for h in init_h): #pruning if all heuristics considers it a dead end
        logging.info("Initial state is a dead end.")
        return SearchResult(solution=None, expansions=0, evaluations=evaluations, generated=0, plan_length=None, solved=False)

    open_list.push(root, init_h)
    generated += 1

    while open_list:
        node, h_values = open_list.pop()

        # Discard stale entries.
        if state_cost.get(node.state, float("inf")) != node.g:
            continue

        expansions += 1

        if task.goal_reached(node.state):
            logging.info("Goal reached.")
            logging.info("Expanded nodes: %d" % expansions)
            logging.info("Generated nodes: %d" % generated)
            logging.info("Heuristic evaluations: %d" % evaluations)

            sol = node.extract_solution()
            return SearchResult(
                solution=sol,
                expansions=expansions,
                evaluations=evaluations,
                generated=generated,
                plan_length=len(sol),
                solved=True,
            )


        for op, succ_state in task.get_successor_states(node.state):
            succ_node = searchspace.make_child_node(node, op, succ_state)
            succ_h    = _evaluate(succ_node, heuristics)
            evaluations += 1

            # Prune if ALL heuristics agree the state is a dead end.
            if all(h == float("inf") for h in succ_h):
                continue

            old_g = state_cost.get(succ_state, float("inf"))
            if succ_node.g < old_g:
                state_cost[succ_state] = succ_node.g
                open_list.push(succ_node, succ_h)
                generated += 1

    logging.info(f"No solution found. Expansions: {expansions}")
    return SearchResult(solution=None, expansions=expansions, evaluations=evaluations, generated=generated, plan_length=None, solved=False)


def _evaluate(node, heuristics):
    return [float(h(node)) for h in heuristics]