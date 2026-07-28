# Employer Registry

`config/employers.json` stores employer-level metadata separately from
provider-specific collection settings in `config/sources.json`.

## Status meanings

- `active`: a collector is configured and enabled or available for the employer.
- `candidate`: the employer is approved for research, but no collector is enabled.
- `paused`: a previously configured source is intentionally disabled.
- `retired`: the employer is no longer part of the intended coverage.

Candidate entries do not trigger collection. Before promoting one to `active`:

1. Verify the official careers URL.
2. Identify the recruitment platform and public endpoint.
3. Confirm that vacancy terms allow public collection.
4. Add a source entry containing the registry `employer_id`.
5. Run source validation and the full test suite.

Parent companies and brands are metadata for analysis. They do not merge vacancy
records during ingestion or deduplication.

## Pipeline integration

Every enabled supported source must include an `employer_id` that exactly matches
an employer registry `id`. Production collection rejects sources linked to
`candidate`, `paused` or `retired` employers.

New raw snapshot metadata includes the stable `employer_id`. Historical snapshots
without that field remain supported: transformation resolves the employer from
the provider and source token in `config/sources.json`. If a snapshot contains an
`employer_id`, it must agree with the current source configuration.

The canonical Parquet dataset includes:

- `employer_id`
- `employer_name`
- `parent_company`
- `industry`
- `employer_priority`
- `graduate_programme`
- `employer_remote_scope`

The quality report also includes employer, parent-company and industry counts.

Run the integration checks with:

```powershell
uv run pytest tests/test_employer_registry.py tests/test_transformation_dataset.py -v
uv run pytest
```
