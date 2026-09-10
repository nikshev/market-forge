# Contract — the metrics exposition

```python
MetricRegistry().register(name, kind, help)
registry.observe(name, value, **labels)
registry.render() -> str
```

## Guarantees

- A registered metric with no observation is absent from `render()`.
- A metric observed as zero is present and reads `0`.
- Each rendered metric carries one `# TYPE` line; label values are escaped for
  backslash, quote and newline.
- Series sharing a name are distinguished by their labels and never summed.
- A counter refuses a value below its current one.
- A name that is not a valid Prometheus metric name is refused at registration.
- Nothing reads a clock.

## Does not

Serve the exposition, define dashboards, or produce readings. Where the text is
served is a deployment question; the readings belong to the systems being
measured, most of which do not run yet — and `UNIMPLEMENTED` says which.
