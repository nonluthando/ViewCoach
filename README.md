# South African Technology Job Market Analysis

## Overview

The South African Technology Job Market Analysis project is an end-to-end analytics engineering pipeline that collects public technology vacancies directly from employer career websites.

The project extracts, standardises and enriches job-posting data so that it can be used to analyse:

- Hiring trends
- In-demand technical skills
- Programming languages and frameworks
- Cloud platforms and development tools
- Career and experience levels
- Employment types
- Technical domains
- Geographic distribution
- Early-career opportunities

Instead of relying mainly on traditional job boards, the project collects vacancies from employer career portals. This provides an employer-direct view of the South African technology labour market and reduces duplicate observations through conservative deduplication.

Graduate, internship and junior roles are retained as a dedicated early-career analytical lens within the broader technology market.

## Project Objectives

The project aims to:

- Collect vacancies from major South African technology employers
- Support multiple recruitment platforms and provider structures
- Preserve reproducible raw job-posting snapshots
- Standardise inconsistent job data into a common schema
- Extract technical skills and capabilities from job descriptions
- Classify vacancies by role, seniority, domain and employment type
- Track repeated vacancies across collection runs
- Produce analysis-ready datasets
- Support dashboards and labour-market research

## Supported Recruitment Platforms

The current pipeline includes collectors for:

- Greenhouse
- Lever
- Workday
- SAP SuccessFactors
- Oracle HCM
- WordPress Job Manager

The provider-adapter architecture is designed so that additional recruitment platforms and custom employer APIs can be added without rewriting the full pipeline.

## Current Capabilities

### Multi-Provider Data Collection

The ingestion layer collects vacancies from recruitment platforms with different:

- API structures
- Pagination models
- Job-detail endpoints
- Location formats
- Metadata fields
- Response formats
- Failure behaviours

Each provider has a dedicated adapter responsible for retrieving vacancies and converting provider-specific responses into a consistent internal representation.

### Raw Snapshot Preservation

Raw provider responses are retained before transformation.

The pipeline stores:

- Raw JSON or HTML snapshots
- Source metadata
- Collection timestamps
- Integrity information
- SHA-256 hashes

Raw files remain unchanged after collection, allowing transformations to be reproduced and audited.

### Data Cleaning and Standardisation

The transformation pipeline:

- Cleans raw job descriptions
- Removes HTML formatting
- Standardises text values
- Normalises locations
- Parses workplace information
- Standardises employment metadata
- Handles missing and ambiguous values
- Produces a common structure across providers

### Deduplication and Observation History

Stable provider identifiers are used to identify repeated vacancies across collection runs.

The pipeline preserves:

- First-seen dates
- Last-seen dates
- Observation history
- Source identifiers
- Collection evidence

Deduplication is intentionally conservative to avoid incorrectly combining unrelated vacancies.

### Skills Extraction

The project automatically extracts and normalises skills mentioned in job descriptions.

Current skill categories include:

- Programming languages
- Frameworks and libraries
- Databases
- Cloud platforms
- Development tools
- Technical capabilities
- Soft skills

Normalisation allows employers using different terminology to be compared more consistently.

For example, related terms and naming variations can be mapped to a common analytical label instead of being treated as completely separate skills.

### Vacancy Classification

The pipeline classifies vacancies by:

- Career level
- Functional role
- Technical domain
- Employment type
- Workplace type
- Technology relevance
- Early-career suitability

Classification evidence is retained where possible so that labels remain explainable rather than operating as unsupported black-box predictions.

### Requirements Filtering

The project distinguishes and structures requirements found in vacancy descriptions, supporting later analysis of:

- Minimum requirements
- Preferred requirements
- Experience expectations
- Education requirements
- Technical capability requirements

### Dataset Generation

The pipeline produces a schema-controlled analytical dataset:

```text
data/processed/
├── jobs.parquet
├── job_skills.parquet
├── job_requirements.parquet
├── dashboard_jobs.parquet
├── dashboard_skills.parquet
├── quality-report.json
├── skills-quality-report.json
└── dashboard-quality-report.json
```

`jobs.parquet` remains the canonical, one-row-per-vacancy source of truth.

`job_skills.parquet` and `job_requirements.parquet` retain explainable extraction evidence. `dashboard_jobs.parquet` and `dashboard_skills.parquet` are validated data marts designed for Streamlit and DuckDB.

The three quality reports cover canonical transformation, skills extraction and dashboard-contract validation.

Parquet is used as the main analytical format because it:

- Preserves column data types
- Supports efficient storage
- Loads faster than CSV for repeated analysis
- Works well with Python analytics tools
- Provides a stable contract for dashboards and later analysis

## Pipeline Architecture

```text
Employer career websites
           |
           v
Provider-specific collectors
           |
           v
Raw JSON or HTML snapshots
           |
           +--> metadata
           +--> timestamps
           +--> SHA-256 integrity hashes
           |
           v
Snapshot validation
           |
           v
Cleaning and standardisation
           |
           v
Skills and requirements extraction
           |
           v
Vacancy classification
           |
           v
Stable-key deduplication
           |
           v
Observation-history tracking
           |
           +--> jobs.parquet
           +--> quality-report.json
           |
           v
Market analysis and dashboards
```

## Repository Structure

```text
.
├── config/
│   └── sources.json
├── data/
│   ├── raw/
│   ├── processed/
│   └── source-test-results/
├── docs/
├── scripts/
├── src/
│   ├── ingestion/
│   ├── transformation/
│   ├── skills/
│   └── analytics/
├── tests/
├── requirements.txt
└── README.md
```

### `config/`

Contains source definitions and provider configuration.

### `data/raw/`

Contains immutable provider snapshots and associated metadata.

### `data/processed/`

Contains the canonical analytical dataset and data-quality reports.

### `src/ingestion/`

Contains provider-specific collection logic.

### `src/transformation/`

Contains cleaning, normalisation, extraction, classification, schema and dataset-building logic.

### `scripts/`

Contains validation, auditing and supporting utilities.

### `docs/`

Contains milestone reports, technical decisions, source assessments and implementation documentation.

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

## Running the Pipeline

### 1. Collect Raw Job-Posting Data

Run all configured sources:

```bash
python -m src.ingestion.collect
```

Run a specific configured source:

```bash
python -m src.ingestion.collect --source-token takealotgroup
```

Additional examples:

```bash
python -m src.ingestion.collect --source-token discovery
python -m src.ingestion.collect --source-token digioutsource
```

Collectors with page-based career sites follow result pages and retrieve individual vacancy details where required.

Completeness checks are used to reduce the risk of silently producing truncated datasets.

### 2. Build the Canonical Dataset

```bash
python -m src.transformation.build
```

This stage:

- Reads preserved raw snapshots
- Validates source integrity
- Cleans vacancy descriptions
- Standardises fields
- Applies classifications
- Deduplicates repeated observations
- Updates vacancy history
- Writes the canonical dataset
- Produces a data-quality report

### 3. Extract Skills and Requirements

```bash
python -m src.skills.build
```

This creates explainable job-skill and job-requirement datasets from the canonical jobs table.

### 4. Build Dashboard Data Marts

```bash
python -m src.analytics.build
```

This stage validates job keys and joins, then writes compact dashboard datasets with employer, role, location, workplace, skills and requirement dimensions.

All commands can also be run through uv, for example:

```bash
uv run python -m src.analytics.build
```

### 5. Validate Sources

```bash
python scripts/validate_sources.py
```

### 6. Run the Test Suite

```bash
pytest
```

## Important Design Decisions

### Raw Data Remains Immutable

Transformations never edit source snapshots.

This makes the pipeline reproducible and allows cleaning or classification logic to be improved without recollecting all historical data.

### No Early Destructive Filtering

The canonical dataset retains broader vacancy evidence.

Fields such as technology relevance and early-career suitability are represented as analytical flags rather than permanently removing records.

### Early Career Is an Analytical Lens

Graduate, internship and junior roles are reported separately, but they remain part of the broader South African technology market dataset.

### Unknown Is Better Than Guessing

Missing or ambiguous values remain unknown when there is insufficient evidence.

The project avoids creating false precision simply to increase classification coverage.

### Classifications Should Be Explainable

Classification rules retain evidence where practical so that labels can be reviewed and audited.

### Deduplication Is Conservative

Stable provider job identifiers are preferred.

Fuzzy matching is not used aggressively because similar job titles may still represent different vacancies.

### Parquet Is the Analytical Contract

Later analysis and dashboard components read the canonical Parquet dataset rather than repeating raw provider parsing.

### Provider Logic Is Isolated

Provider-specific behaviour is kept inside dedicated adapters.

This prevents changes to one recruitment platform from unnecessarily affecting the rest of the pipeline.

## Current Development Focus

Current work is focused primarily on improving provider reliability.

Recent improvements include:

- Better SuccessFactors retry handling for transient failures
- More resilient Workday pagination
- Updated Oracle HCM vacancy-detail retrieval
- Fallback mechanisms for WordPress-based career portals
- Expanded automated tests for provider failures and incomplete responses
- Improved technology and capability dimensions
- Requirements filtering and classification improvements

These changes are intended to improve collection success across employers using recruitment systems with different reliability and response behaviours.

## Current Project Status

The core data engineering pipeline is operational.

Completed or substantially implemented functionality includes:

- Multi-provider vacancy ingestion
- Raw snapshot preservation
- Data cleaning and standardisation
- Location and metadata normalisation
- Vacancy deduplication
- Observation-history tracking
- Skills extraction
- Requirements filtering
- Vacancy classification
- Dataset generation
- Data-quality reporting

The remaining work focuses mainly on reliability, validation and presentation.

**Estimated overall completion: 85–90%.**

## Roadmap

| Phase | Outcome | Status |
|---|---|---|
| Source assessment | Identify suitable employer career sources | Complete |
| Raw ingestion | Collect and preserve provider snapshots | Complete |
| Cleaning and standardisation | Produce one consistent vacancy schema | Complete |
| Deduplication and history | Track vacancies across collection runs | Complete |
| Vacancy classification | Classify roles, levels, domains and employment types | Complete |
| Skills extraction | Extract and normalise technologies and capabilities | Complete |
| Requirements filtering | Structure minimum and preferred requirements | Complete |
| Provider hardening | Improve retries, pagination, fallbacks and compatibility | In progress |
| Dataset refresh | Re-run affected sources and publish updated datasets | Next |
| Dashboard data marts | Validate and publish dashboard-ready Parquet tables | Complete |
| Market analysis | Analyse hiring, skills, levels and locations | Next |
| Interactive dashboard | Publish visual labour-market insights | Next |
| Employer expansion | Add more South African technology employers | Ongoing |

## Planned Analysis

The analytical stage is intended to answer questions such as:

- Which programming languages are most frequently requested?
- Which frameworks and cloud platforms appear most often?
- Which technical roles have the highest vacancy counts?
- Which employers advertise the most early-career opportunities?
- How are technology vacancies distributed geographically?
- Which skills commonly appear together?
- How do minimum requirements differ by career level?
- Which roles are most accessible to graduates?
- How frequently are remote and hybrid roles advertised?
- Which technical domains are growing across collection periods?

## Dashboard Plans

The planned interactive dashboard will include views for:

- Technology demand
- Skills frequency
- Employer comparisons
- Career-level distribution
- Role and domain distribution
- Location trends
- Workplace-type distribution
- Early-career opportunities
- Requirement patterns
- Vacancy activity over time

## Limitations

The dataset represents vacancies collected from configured employer career portals and should not be interpreted as a complete census of every technology vacancy in South Africa.

Coverage depends on:

- Employers included in the source configuration
- Public availability of vacancy information
- Recruitment-platform reliability
- Collection dates
- Provider response completeness
- The accuracy of rule-based extraction and classification

Vacancy descriptions also differ substantially in detail, which affects skills and requirements extraction.

## Responsible Use

The project collects only publicly advertised vacancy information.

It does not:

- Submit job applications
- Collect applicant information
- Access authenticated candidate accounts
- Bypass platform access controls
- Infer protected personal attributes
- Collect private recruitment data
- Scrape sources whose access restrictions make collection inappropriate

## Technology Stack

- Python
- pandas
- PyArrow
- Parquet
- Requests and HTTP clients
- HTML parsing
- JSON APIs
- Provider-specific recruitment APIs
- pytest
- Git and GitHub

## Portfolio Context

This project demonstrates practical experience in:

- Python development
- Analytics engineering
- Data ingestion
- API integration
- Data cleaning
- Schema design
- Data-quality validation
- Rule-based classification
- Information extraction
- Error handling
- Retry and fallback strategies
- Automated testing
- Modular software architecture
- Labour-market analytics

## Interactive Dashboard

Patch 6.3 adds a Streamlit dashboard backed directly by the validated Patch 6.2 Parquet marts.

```bash
uv pip install -r requirements.txt
uv run streamlit run streamlit_app.py
```

The dashboard includes overview, employer, skills, early-career, location, opportunity and data-quality views. Global filters are executed through parameterised DuckDB queries rather than transformation logic inside the UI.

See [`docs/patch-6.3-streamlit-dashboard.md`](docs/patch-6.3-streamlit-dashboard.md) for the data requirements and deployment notes.
