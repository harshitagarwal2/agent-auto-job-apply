# Manual and export feed files

The checked-in `jobflow.example.toml` points local manual/export sources at top-level files such as:

- `manual/linkedin_leads.json`
- `manual/glassdoor_leads.json`
- `manual/ashby_jobs.json`
- `manual/workday_jobs.json`

Those files are intentionally **git-ignored** so you can keep personal lead data out of the repository.

## Getting started

1. Copy a sample file from `manual/examples/`.
2. Rename it to match the path in `jobflow.toml`.
3. Edit the payload with your own lead/export data.

Example:

```bash
mkdir -p manual
cp manual/examples/linkedin_leads.sample.json manual/linkedin_leads.json
```

## Supported shapes

### LinkedIn / Glassdoor manual leads

These adapters expect an array of objects like:

```json
[
  {
    "external_id": "linkedin-001",
    "title": "Product Manager",
    "company": "Discovery Corp",
    "location_text": "Remote, United States",
    "location_country": "US",
    "description": "Manual lead collected for assisted follow-up.",
    "job_url": "https://example.com/job/123",
    "apply_url": "https://example.com/job/123/apply"
  }
]
```

### Ashby exports

Ashby accepts either a top-level array or an object with `jobs`, `jobPosts`, `openings`, `results`, or `jobBoard.jobPostings`.

### Workday exports

Workday accepts either a top-level array or an object with `jobPostings`, `jobs`, or `positions`.

Use the sample files in `manual/examples/` as copy-ready templates.
