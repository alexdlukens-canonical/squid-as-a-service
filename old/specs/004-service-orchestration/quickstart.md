# Quickstart: Service Orchestration

**Amended**: 2026-05-13 — Simplified YAML examples. `lxd_project`, `network`, `credentials`, `model_name`, and access rule `src` are all computed from `service_name` or Terraform outputs.

## Installation

```bash
# Using uv (recommended)
uv tool install terrasquid-render

# Using pip
pip install terrasquid-render
```

## 1. Author a Compute Juju Model Definition

Create `my-service.yaml`:

```yaml
service_name: my-service
service_type: compute.juju_model
access_rules:
  - name: web-access
    dst: .ubuntu.com
    type: CONNECT
    ports: [443]
use_proxy_provider: true
```

What this creates:
- LXD project: `my-service`
- Network bridge: `my-service-br` (CIDR assigned by LXD at apply time)
- Credential: `my-service-credential`
- Juju model: `my-service`
- ACL rule: source = network CIDR (auto-computed), destination = `.ubuntu.com`, type = CONNECT

## 2. Render Terraform Code

```bash
terrasquid-render ./definitions --output ./terraform
```

## 3. Apply with Terraform

```bash
cd terraform/my-service
terraform init
terraform plan
terraform apply
```

## 4. Define a Reusable Ruleset

Create `canonical-repos.yaml`:

```yaml
service_name: canonical-repos
service_type: network.proxy_ruleset
destinations:
  - name: ubuntu-archive
    dst: archive.ubuntu.com
    type: ALLOW
    ports: [80]
```

## 5. Reference the Ruleset from a Model

Update `my-service.yaml`:

```yaml
access_rulesets:
  - canonical-repos
```

Re-render and re-apply. The model now includes both its inline `web-access` rule and the `ubuntu-archive` destination from the ruleset.

> To include a default set of proxy rules, add the default ruleset service name to `access_rulesets` (e.g., `- default-proxy-rules`).
