# Restoring COS exporter connectivity from the LXD model

The OpenTelemetry Collector is subordinate to `terrasquid/8` in the
`localhost-localhost:squidaas` model. Its LXD container is
`juju-18e76c-12`.

The COS Kubernetes service DNS names are not resolvable from that LXD
container. Map the Juju-published service addresses in `/etc/hosts`:

```sh
lxc exec juju-18e76c-12 -- sh -c '
  sed -i "/[[:space:]]\(cos-lite\.example\.com\|loki-0\.loki-endpoints\.cos-lite\.svc\.cluster\.local\|prometheus-0\.prometheus-endpoints\.cos-lite\.svc\.cluster\.local\)\([[:space:]]\|$\)/d" /etc/hosts
  printf "%s\n" \
    "10.152.183.153 loki-0.loki-endpoints.cos-lite.svc.cluster.local" \
    "10.152.183.219 prometheus-0.prometheus-endpoints.cos-lite.svc.cluster.local" \
    >> /etc/hosts
'
```

The container's default route through `lxdbr1` (`10.85.219.1`) already
reaches the Kubernetes service network. Do not add an LXD route: LXD rejects
the Calico pod-subnet route as a duplicate, and no route is needed for the
service addresses above.

Validate connectivity:

```sh
lxc exec juju-18e76c-12 -- sh -c '
  getent hosts \
    loki-0.loki-endpoints.cos-lite.svc.cluster.local \
    prometheus-0.prometheus-endpoints.cos-lite.svc.cluster.local
  curl -fsS http://loki-0.loki-endpoints.cos-lite.svc.cluster.local:3100/loki/api/v1/status/buildinfo
  curl -fsS http://prometheus-0.prometheus-endpoints.cos-lite.svc.cluster.local:9090/-/ready
'
```
