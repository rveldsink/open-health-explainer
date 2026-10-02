# Connector architecture

Open Health Explainer is designed as an independent quality layer between source systems and target interoperability requirements.

~~~text
KIS / EHR / Database / FHIR Server
              |
              v
       Source Connector
              |
              v
   Open Health Explainer
              |
       +------+------+
       |             |
       v             v
 technical       FHIR/profile
 pre-check       validation
       \             /
        \           /
         v         v
      error normalization
              |
              v
    clustering / root cause
              |
              v
        local report
~~~

## Why a connector layer?

Healthcare organizations use many different products and storage technologies. Open Health Explainer should not require one vendor's database.

The connector boundary lets the same analysis engine work with different sources.

## Implemented

### Local folder

Reads individual FHIR JSON resources and FHIR Bundles from a local folder.

### Generic FHIR REST

A minimal read-only connector that follows normal FHIR search pagination and reads resources from a FHIR REST endpoint.

The current prototype intentionally supports unauthenticated endpoints only.

## Planned adapters

Potential integrations include:

- HAPI FHIR
- Firely Server
- Oracle Health FHIR endpoints
- Epic FHIR endpoints
- PostgreSQL / JSONB exports
- ZIP/archive imports
- vendor-specific integration exports

Vendor-specific authentication, OAuth2/SMART-on-FHIR, mTLS, audit logging and production security are future work.

## Design principle

The source system remains the source of truth.

Open Health Explainer should read and analyze data, not silently modify production patient records.
