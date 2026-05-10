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
import random
from collections import namedtuple

from . import searchspace

SearchResult = namedtuple(
    "SearchResult",
    ["solution", "expansions", "plan_length", "solved"],
)

# Open list implementations

class SingleOpenList:
    """
    Standard single-heuristic GBFS open list.
    Orders states by h(s); 
    Ties broken by insertion order (FIFO).
    """

    def __init__(self):
        self._heap = []
        self._tiebreaker = 0

    def push(self, node, h_values):
        heapq.heappush(self._heap, (h_values[0], self._tiebreaker, node))
        self._tiebreaker += 1

    def pop(self):
        _, _, node = heapq.heappop(self._heap)
        return node

    def __len__(self):
        return len(self._heap)


class MaxOpenList:
    """
    Orders states by max(h_1(s), ..., h_n(s)).
    Ties broken by insertion order (FIFO).
    """

    def __init__(self):
        self._heap = []
        self._tiebreaker = 0

    def push(self, node, h_values):
        heapq.heappush(self._heap, (max(h_values), self._tiebreaker, node))
        self._tiebreaker += 1

    def pop(self):
        _, _, node = heapq.heappop(self._heap)
        return node

    def __len__(self):
        return len(self._heap)


class SumOpenList:
    """
    Orders states by sum(h_1(s), ..., h_n(s)).
    Ties broken by insertion order (FIFO).
    """

    def __init__(self):
        self._heap = []
        self._tiebreaker = 0

    def push(self, node, h_values):
        heapq.heappush(self._heap, (sum(h_values), self._tiebreaker, node))
        self._tiebreaker += 1

    def pop(self):
        _, _, node = heapq.heappop(self._heap)
        return node

    def __len__(self):
        return len(self._heap)


class AlternationOpenList:
    """
    One queue per heuristic, round-robin pop.
    Each node is pushed into all queues so every heuristic gets a turn.
    Duplicate pops are discarded by the closed set in gbfs_multi_search.
    """

    def __init__(self, n_heuristics):
        self._queues = [[] for _ in range(n_heuristics)]
        self._n = n_heuristics
        self._tiebreaker = 0
        self._turn = 0

    def push(self, node, h_values):
        for i, h in enumerate(h_values):
            heapq.heappush(self._queues[i], (h, self._tiebreaker, node))
        self._tiebreaker += 1

    def pop(self):
        # Try each queue starting from the current turn; skip empty ones.
        for _ in range(self._n):
            queue = self._queues[self._turn]
            self._turn = (self._turn + 1) % self._n
            if queue:
                _, _, node = heapq.heappop(queue)
                return node
        raise IndexError("pop from empty AlternationOpenList")

    def __len__(self):
        # A node is pushed into all n queues simultaneously. max() reflects
        # the number of distinct nodes still present in the open list
        # Returns 0 only when every queue is empty.
        return max(len(q) for q in self._queues)


class ParetoOpenList:
    """
    Keeps only non-dominated states on the frontier.

    State s dominates s' if:
      h_i(s) <= h_i(s')  for all i, AND
      h_j(s) <  h_j(s')  for at least one j.
      
    Pop selects uniformly at random.
"""

    def __init__(self):
        self._frontier = []   # list of (h_values_tuple, node)

    def _dominates(self, h1, h2):
        return (all(v1 <= v2 for v1, v2 in zip(h1, h2)) and
                any(v1 <  v2 for v1, v2 in zip(h1, h2)))

    def push(self, node, h_values):
        h_values = tuple(h_values)

        # Discard the new node if any existing frontier member dominates it.
        for existing_h, _ in self._frontier:
            if self._dominates(existing_h, h_values):
                return

        # Remove existing members that the new node dominates.
        self._frontier = [
            (h, n) for h, n in self._frontier
            if not self._dominates(h_values, h)
        ]

        self._frontier.append((h_values, node))

    def pop(self):
        if not self._frontier:
            raise IndexError("pop from empty ParetoOpenList")

        # Uniform random selection over the Pareto frontier.
        idx = random.randrange(len(self._frontier))
        _, node = self._frontier[idx]
        self._frontier[idx] = self._frontier[-1]
        self._frontier.pop()
        return node

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
        return ParetoOpenList()
    else:
        raise ValueError(
            f"Unknown open list type '{open_list_type}'. "
            f"Choose from: {OPEN_LIST_TYPES}"
        )


# Search algorithm

def gbfs_multi_search(task, heuristics, open_list_type="alternation"):
    """
    Greedy Best-First Search with multiple heuristics.

    All open list variants share the same graph-search loop. A closed set
    guarantees each state is expanded at most once. state_cost tracks the
    best known g-value per state to avoid pushing inferior duplicate paths
    onto the open list.
    """
    if not isinstance(heuristics, list):
        heuristics = [heuristics]

    n = len(heuristics)

    if open_list_type == "single" and n > 1:
        raise ValueError("Single open list supports only one heuristic.")

    open_list = make_open_list(open_list_type, n)
    #Best g seen so far per state: used only to suppress inferior duplicates
    #from entering the open list. Correctness is handled by the closed set.
    state_cost = {task.initial_state: 0}
    #Closed set: states already expanded, each at most once.
    closed = set()
    expansions = 0

    root = searchspace.make_root_node(task.initial_state)
    init_h = _evaluate(root, heuristics)

    #Prune if all heuristics agree the initial state is a dead end.
    if all(h == float("inf") for h in init_h):
        logging.info("Initial state is a dead end.")
        return SearchResult(solution=None, expansions=0,
                            plan_length=None, solved=False)

    open_list.push(root, init_h)

    while open_list:
        node = open_list.pop()

        # Skip states already expanded. (handles alternation's multi-queue
        # duplicates and any other redundant open-list entries)
        if node.state in closed:
            continue
        closed.add(node.state)

        expansions += 1

        if task.goal_reached(node.state):
            sol = node.extract_solution()

            return SearchResult(solution=sol, expansions=expansions,
                                plan_length=len(sol), solved=True)

        for op, succ_state in task.get_successor_states(node.state):
            #Skip already-expanded states 
            if succ_state in closed:
                continue

            succ_node = searchspace.make_child_node(node, op, succ_state)
            succ_h = _evaluate(succ_node, heuristics)

            #Prune only if ALL heuristics agree the state is a dead end.
            if all(h == float("inf") for h in succ_h):
                continue

            #Only push if we found a better path to succ_state.
            old_g = state_cost.get(succ_state, float("inf"))
            if succ_node.g < old_g:
                state_cost[succ_state] = succ_node.g
                open_list.push(succ_node, succ_h)

    return SearchResult(solution=None, expansions=expansions,
                        plan_length=None, solved=False)


def _evaluate(node, heuristics):
    return [float(h(node)) for h in heuristics]