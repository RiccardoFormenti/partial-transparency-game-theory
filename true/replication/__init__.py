"""Independent replication of the experiments of "Partial Transparency in OSGT".

Each module replaces a part of the original code in copy/app/src/pd_runner, and
checks/ compares the two.

  general/               what full and partial transparency both use: the zoo, payoffs
  partial_transparency/  signals, how a lifted bot plays on one, and the (t, α) sweep
"""
