# Deployment Adaptation Guide

## RAN / O-RAN control

Place the final enforcement adapter as close as practical to the component that can actually commit the RAN state transition. A prior xApp/rApp/RIC policy decision can feed PED validation but does not replace the final check.

## UPF / packet-processing state

For a UPF rule mutation, move the consume-and-effect primitive into the protected control path that commits the forwarding rule. SmartNIC/DPU or secure network-function state can hold the activation/consumption object.

## Network API gateway

For a consequence-bearing API, the gateway can act as a sink only if downstream state cannot be changed through an unguarded path that bypasses finality verification.

## RF enablement

A software policy check far from the radio-enable boundary is weaker than a gate associated with the actual RF/actuator transition. High-consequence paths should place the sink at the last technically enforceable point.

## Transport

The draft does not require one transport. Candidate Acts and authorities can be serialized over local IPC, operator HTTPS, service-based interfaces, or O-RAN-adjacent channels if integrity, sink binding, freshness, and non-bearer semantics survive the transport.

## Protected state

Replace Python objects/SQLite with appropriate protected state for the deployment: HSM, enclave, TEE, protected kernel service, secure network function, DPU/SmartNIC state, monotonic hardware counter, or another mechanism capable of resisting rollback/substitution at the required assurance level.
