"""Independent replication of the experiments of "Partial Transparency in OSGT".

Each module replaces a part of the original code in copy/app/src/pd_runner, and
checks/ compares the two.

  general/               what full and partial transparency both use: the zoo, payoffs,
                         Nash equilibria, replicator dynamics
  full_transparency/     the Nash equilibria and replicator dynamics of each zoo's game,
                         and the ladder of nested zoos (Table 8), saved under results/
  partial_transparency/  signals, how a lifted bot plays on one, the (t, α) sweep, and the
                         Nash equilibria and replicator dynamics of each grid point's game,
                         saved under results/
"""
