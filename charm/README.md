# Terrasquid Charm

## Grafana Dashboards

The charm publishes the `Terrasquid Overview` and `Squid Metrics` dashboards through its `cos-agent` relation.

`Squid Metrics` is based on [Grafana dashboard 13582, "9103 - Squid"](https://grafana.com/grafana/dashboards/13582-9103-squid/). It retains the Prometheus Squid exporter coverage from that dashboard, but uses current Grafana panels and the COS-provisioned Prometheus datasource. The upstream export also contained Graylog/Elasticsearch queries and deprecated Grafana panels, which are not available in the Terrasquid COS integration.
