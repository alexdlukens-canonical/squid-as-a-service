# Squid as a Service - 26.04 AI Hackathon

Squid as a Service provides a Juju-managed Squid proxy with an API for defining source networks, destinations, ports, and ordered access-control rules. The charm stores policy data in PostgreSQL, renders a validated Squid configuration, and exposes the proxy as a service for workloads that need centrally managed egress control.

This repository contains the charm, a Django-based API and configuration renderer, operational dashboards and alert rules, and a Terraform provider for provisioning the proxy configuration. Supporting specifications and deployment documentation live alongside the implementation.