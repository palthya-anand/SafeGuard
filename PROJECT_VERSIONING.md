# Project Versioning and Build Policy

## Current release

**v1.0.0-hackathon** is the target integrated release.

## Version progression

| Version | Stage | Meaning |
|---|---|---|
| v0.1.0 | Concept | Problem statement, requirements, architecture |
| v0.2.0 | Data | Data ingestion and preprocessing |
| v0.3.0 | Analytics | EDA and accident hotspot analysis |
| v0.4.0 | ML | Risk model and evaluation |
| v0.5.0 | Backend | FastAPI inference service |
| v0.6.0 | Mobile | Android GPS/speed monitoring |
| v0.7.0 | Context | Traffic and weather |
| v0.8.0 | Alerts | Notifications and voice |
| v0.9.0 | Integration | End-to-end system |
| v1.0.0 | Hackathon | Demonstrable integrated release |
| v1.1.0 | Safety | Crash detection + emergency workflow |
| v1.2.0 | Routing | Risk-aware route intelligence |
| v2.0.0 | Production | Scalable architecture |

## Git tag policy

Create a Git tag for every release:

```bash
git tag -a v0.1.0 -m "Project initialization"
git tag -a v0.2.0 -m "Data pipeline"
git tag -a v0.3.0 -m "EDA and hotspot analysis"
git tag -a v0.4.0 -m "ML risk engine"
git tag -a v0.5.0 -m "FastAPI backend"
git tag -a v0.6.0 -m "Android live monitoring"
git tag -a v0.7.0 -m "Traffic and weather"
git tag -a v0.8.0 -m "Notifications and voice"
git tag -a v0.9.0 -m "End-to-end integration"
git tag -a v1.0.0 -m "Hackathon release"
```

Push tags:

```bash
git push origin --tags
```

## Release rule

A version should be tagged only after its corresponding acceptance criteria are tested.

## Model versioning

Application version and ML model version are separate.

Example:

```text
Application: v1.0.0
Model:       risk-model-0.4.0
Dataset:     accidents-2026-09-01
```

This allows the model to be retrained without pretending that the whole application changed.

## Environment version record

Store a build record in:

```text
build/version.json
```

Example:

```json
{
  "application_version": "1.0.0-hackathon",
  "model_version": "0.4.0",
  "python": "3.13.15",
  "kotlin": "2.4.20",
  "android_compile_sdk": 36,
  "android_target_sdk": 36,
  "agp": "9.4.0",
  "gradle": "9.6.0",
  "jdk": "17"
}
```

## Why this matters for a B.Tech project

Your changelog gives the project an auditable development history. During the viva, you can show that the system was not presented as a single monolithic demo: it evolved from the original accident-warning concept into a data pipeline, ML model, backend service, Android client, traffic/weather integration, and notification workflow.
