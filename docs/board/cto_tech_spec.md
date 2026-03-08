# CTO Tech Spec: Infrastructure & Scalability

As the CTO, my responsibility is to ensure the technical integrity, security, and scalability of the PEX BC Tool. 

## Governance Standards

1. **Service Reliability**: All components must be hosted on Corp Run to ensure high availability and compliance with Google's internal infra standards.
2. **Security & Access**: Use `gcert` for authenticated access and follow the least privilege principle.
3. **Architecture Quality**: 
    - The `bot.bgl.json` configuration must be validated against the BGL schema.
    - Python dependencies in `requirements.txt` must be pinned and audited for vulnerabilities.
4. **Monitoring**: All deployments must include basic health checks and error logging.
5. **Integrations**: Cloud Tasks configured to target internal Cloud Run services must explicitly OMIT the `audience` field in their `oidc_token` payload. Attempting to manually inject an audience overrides SDK native resolution and leads to silent IAM `401 Unauthorized` blockades.

## Technical Debt & DRY

We strictly enforce the "DRY" principle on past issues. Any bug identified in production must be encoded into the `test_harness.py` to prevent regression.

> [!IMPORTANT]
> A failure in the technical regression suite MUST block deployment.
