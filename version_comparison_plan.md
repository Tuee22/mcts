# MCTS Algorithm Validation Plan

## Goal
Verify that refactoring (Boost removal, naming cleanup) did not alter MCTS algorithm behavior or degrade performance.

## Versions to Compare
1. **v1 (baseline)**: `fd3b1e5` - Original with Boost
2. **v2 (intermediate)**: `ef0ea37` - Test cases added  
3. **v3 (current)**: `b51670b` - Post-refactoring (Boost removed)

## Validation Strategy

### Phase 1: Algorithm Correctness Verification
**Goal**: Ensure identical algorithm behavior across versions

1. **Deterministic Scenarios**
   - Use fixed seeds (42, 123, 456) for reproducible results
   - Run identical MCTS configurations:
     - c=1.4, min_sims=100, max_sims=500, increment=25
     - Same board positions, same flip parameters

2. **Tree Statistics Comparison**
   - Visit counts per action
   - Equity values per action  
   - Action rankings/ordering
   - Total simulations performed

3. **Move Sequence Verification**
   - Generate move sequences from identical starting positions
   - Compare first 10 moves of self-play games
   - Verify branching factor and search depth

### Phase 2: Performance Benchmarking
**Goal**: Ensure no performance regression

1. **Simulation Speed**
   - Time per simulation (μs/simulation)
   - Throughput (simulations/second)
   - Memory usage during runs

2. **Scaling Tests**
   - Performance at 100, 500, 1000, 2000 simulations
   - Linear scaling verification

3. **End-to-End Game Performance**  
   - Complete game duration
   - Average time per move
   - Tree size growth over game

### Phase 3: Game Quality Assessment
**Goal**: Verify strategic strength unchanged

1. **Self-Play Consistency**
   - Version A vs Version B tournaments
   - Win rates should be ~50% if identical
   - Move quality metrics

2. **Strategic Patterns**
   - Opening move preferences
   - Endgame accuracy
   - Wall placement strategies

## Implementation Approach

### Step 1: Environment Setup
```bash
# Create comparison directories
mkdir -p /tmp/mcts_v1 /tmp/mcts_v2 /tmp/mcts_v3

# Checkout each version
git clone /home/matt/mcts /tmp/mcts_v1 && cd /tmp/mcts_v1 && git checkout fd3b1e5
git clone /home/matt/mcts /tmp/mcts_v2 && cd /tmp/mcts_v2 && git checkout ef0ea37  
git clone /home/matt/mcts /tmp/mcts_v3 && cd /tmp/mcts_v3 && git checkout b51670b
```

### Step 2: Build All Versions
- Handle different build systems (v1 may use different setup)
- Ensure identical compiler flags where possible
- Document any build differences

### Step 3: Create Comparison Harness
```python
# comparison_harness.py
def run_standardized_test(mcts_module, seed, simulations):
    """Run identical test across all versions"""
    mcts = mcts_module.Corridors_MCTS(
        c=1.4, seed=seed, 
        min_simulations=simulations, 
        max_simulations=simulations
    )
    
    start_time = time.time()
    mcts.ensure_sims(simulations)
    duration = time.time() - start_time
    
    actions = mcts.get_sorted_actions(flip=False)
    
    return {
        'duration': duration,
        'actions': actions,
        'total_visits': sum(a[0] for a in actions),
        'top_action': actions[0] if actions else None
    }
```

### Step 4: Statistical Analysis
- Chi-square tests for action distribution changes
- T-tests for performance differences  
- Effect size calculations
- Confidence intervals on key metrics

## Success Criteria

### Algorithm Correctness ✓
- [ ] Identical action rankings (within statistical noise)
- [ ] Visit counts match within 5% 
- [ ] Same top moves for standard positions
- [ ] Identical self-play game trees (first 5 moves)

### Performance Maintenance ✓  
- [ ] <5% performance regression acceptable
- [ ] Same O(n) scaling behavior
- [ ] No memory leaks introduced
- [ ] Stable under load

### Quality Preservation ✓
- [ ] Cross-version win rates 45-55%
- [ ] Strategic patterns unchanged
- [ ] No obvious blunders introduced

## Expected Challenges

1. **Build Compatibility**: v1 may need different setup
2. **API Differences**: Interface changes between versions
3. **Random Variations**: Statistical noise in comparisons
4. **Environment Effects**: Different container/system states

## Contingency Plans

- If major differences found: Bisect commits to find regression
- If API incompatible: Create adapter layers
- If performance regressed: Profile and optimize hot paths
- If algorithm changed: Determine which version is "correct"