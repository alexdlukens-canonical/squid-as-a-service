# CLI Interface Contract

## Command

```
terrasquid-render <definitions-dir> --output <output-dir>
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| definitions-dir | yes | Directory containing .yml/.yaml service definition files |
| --output, -o | yes | Directory where rendered .tf files will be written |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All definitions valid, all .tf files rendered successfully |
| 1 | Validation error or rendering error occurred |

## Output Behavior

- Scans all `.yml` and `.yaml` files in `<definitions-dir>` (non-recursive)
- Validates each file against its declared `service_type` schema
- Resolves cross-service references (ruleset names)
- Renders .tf files into `<output-dir>/<service-name>/`
- Each service gets: `main.tf`, `variables.tf`, `outputs.tf`

## Error Output

- All errors printed to stderr (not stdout)
- Format: `<filename>: <field_path>: <message>`
- Example: `ps7-prod.yaml: access_rules.0.ports.0: Input should be less than or equal to 65535`
- Multiple errors reported per run (does not stop at first)

## Logging

- Progress information printed to stderr at INFO level
- Use `--verbose` flag for DEBUG level output
- Use `--quiet` flag to suppress all non-error output
