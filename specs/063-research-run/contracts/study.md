# Contract — one research run

```
run_study(dataset, *, store, code, experiment, target, feature_names,
          dataset_ref, as_of_ns, minimum_observations) -> StudyResult
```

## Order, and why it is that order

1. run the comparison, refusing a dataset with nothing scorable;
2. combine each variant's fold artifacts;
3. **register** them;
4. put the whole field on record and publish the winner — the gate refuses an
   unreproducible run here;
5. check every cited artifact resolves;
6. report reliability per horizon.

Registration precedes citation because the gate refuses a winner whose field is
not on record, and the artifact check follows the gate because a caller fixing a
dirty tree should not have to fix an artifact complaint to discover it.

## Refuses

- a dataset where no fold could be scored;
- a run over a dirty working tree, naming the code component;
- a winner outside its own field, or a variant named twice;
- a cited artifact nobody registered, naming it.

## Does not

Read git, a clock, or a store for the dataset identity. Choose a horizon,
promote a model, or decide deployment.
