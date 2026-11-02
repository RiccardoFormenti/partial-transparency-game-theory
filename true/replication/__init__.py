"""Independent replication of the experiments of "Partial Transparency in OSGT".

Each module replaces a part of the original code in copy/app/src/pd_runner, and
checks/ compares the two.

  general/               what full and partial transparency both use: the zoo, payoffs,
                         Nash equilibria
  full_transparency/     the Nash equilibria of each zoo's game, saved under results/
  partial_transparency/  signals, how a lifted bot plays on one, and the (t, α) sweep
"""
