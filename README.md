# Keepalived Charm

[Keepalived](http://www.keepalived.org/) is software which provides high
availability by assigning two or more nodes a virtual IP and monitoring
those nodes, failing over when one goes down.

## Usage

The Keepalived charm is a
[subordinate](https://jujucharms.com/docs/stable/authors-subordinate-services).

### Using with Kubernetes ([CDK](https://jujucharms.com/canonical-kubernetes))

Use keepalived with CDK to ensure kubeapi-load-balancer is not a single
point of failure.

```
juju deploy keepalived

juju relate keepalived:juju-info kubeapi-load-balancer:juju-info
juju relate keepalived:lb-sink kubeapi-load-balancer:website
juju relate keepalived:loadbalancer kubernetes-master:loadbalancer
juju relate keepalived:website kubernetes-worker:kube-api-endpoint

# this relation is also needed as usual so that the actual
# load-balancer knows about backend endpoints
juju relate kubernetes-master:kube-api-endpoint kubeapi-load-balancer:apiserver

# configure keepalived (values are examples, substitute your own)
export VIP_HOSTNAME=test.example.com
juju config keepalived virtual_ip=10.10.74.250
juju config keepalived port=443
juju config keepalived vip_hostname=$VIP_HOSTNAME

# set extra_sans to update api server ssl cert
juju config kubeapi-load-balancer extra_sans=$VIP_HOSTNAME
juju config kubernetes-master extra_sans=$VIP_HOSTNAME

# if you only have one kubeapi-load-balancer unit, add another one
juju add-unit kubeapi-load-balancer

```

### Using with HA Proxy
```
juju deploy keepalived
juju add-relation haproxy keepalived

```

## Build Instructions

With tox pre-installed, run the following in the top-level directory of this
source repository:

```
tox -e build
```

The charm will be present under `build/builds/keepalived`.

## Further information

- [Keepalived Homepage](http://www.keepalived.org/)
