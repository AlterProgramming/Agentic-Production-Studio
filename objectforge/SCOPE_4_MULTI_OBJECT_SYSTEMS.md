# ObjectForge Scope 4 — Multi-Object Coherent Systems

## Objective

Advance ObjectForge from individually coherent retained objects to coordinated systems whose members share explicit physical interfaces, compatibility rules, design grammar, spatial plans, and operational workflows.

Scope 4 does not pass when several models merely look related. The system must prove that the objects are useful independently and that their relationships are represented in geometry and machine-readable contracts.

## Fixed benchmark

The benchmark is a **Modular Observation and Service Cell**. It supports:

- a stable work surface;
- directional illumination;
- protected transport;
- visible instrument access;
- portable power;
- analysis and status display;
- shared mechanical mounting;
- shared power and data;
- transport stowage;
- deployment and recovery workflows.

The planner compares four bounded topologies:

1. shared operational hub plus protected transport carrier;
2. carrier-centric deployment;
3. distributed pairwise connections;
4. one integrated monolith.

The shared hub-and-carrier topology is selected because it preserves independent objects, reuses interfaces, supports both operational and transport states, and avoids a fragile web of one-off pairwise connections.

## System members

Each system contains six retained objects:

1. **Service hub** — stable surface, shared rails, power/data endpoints, and cartridge bays.
2. **Directional work emitter** — articulated illumination with rail and power interfaces.
3. **Protected carrier** — impact-resistant transport shell with module bays and a stack receiver.
4. **Instrument caddy** — visible instrument organization with operational rail and transport-stack interfaces.
5. **Portable power module** — serviceable power cartridge with status, protection, module-bay, and power-bus interfaces.
6. **Analysis and status module** — display, controls, sensor ports, processor, cooling, module-bay, and power/data interfaces.

The power and analysis cartridges are new Scope 4 members. The other four members inherit the Scope 2 functional architectures and Scope 3 design-language system before receiving Scope 4 interfaces.

## Shared interface standards

### OFX 240 keyed mechanical rail

A reusable mechanical host/module interface with:

- declared width, depth, height, and key offset;
- insertion axis;
- load capacity;
- host guides, module tongue, physical key, contact pads, and latch or detent;
- dimensional tolerance.

### OFX 24D power and data bus

A keyed power/data connector with:

- 24 V power contract;
- current capacity;
- six retained contacts;
- source/sink and host/device polarity;
- differential data identity;
- keyed housing and insertion direction.

### OFX 360 cartridge bay

A reusable host/cartridge interface with:

- dual guide geometry;
- front retention;
- mass limit;
- bay frame, guides, stop, lock, cartridge skids, and bumper;
- transport and operational compatibility.

### OFX 480 transport stack

A receiver/stacker interface with:

- four keyed capture points;
- stack mass limit;
- base-plane datum;
- transport retention contract.

## Compatibility and connection model

Every endpoint declares:

- owning object;
- standard identifier;
- polarity;
- local position and axis;
- capacity;
- operational or transport roles.

Every connection references two endpoint identifiers. Validation rejects:

- unknown objects, standards, or endpoints;
- different standards joined together;
- incompatible polarities;
- same-object connections presented as system integration;
- orphan objects;
- interface standards that are declared but not reused.

The retained compatibility matrix includes all possible compatible cross-object endpoint pairs as well as the nine declared system connections.

## System workflows

### Deploy and operate

1. Position the service hub.
2. Dock the power module.
3. Dock the analysis module.
4. Mount the work emitter.
5. Mount the instrument caddy.
6. Connect analysis power and data.
7. Connect emitter power.
8. Illuminate, analyze, and service the work item.

### Stow and transport

1. Disconnect active power/data links.
2. Undock the two cartridges.
3. Stow the power module in the protected carrier.
4. Stow the analysis module in the protected carrier.
5. Stack the instrument caddy on the carrier.
6. Close the protected shell.

Workflow validation checks that every referenced object and connection exists and that the required operational and transport states are represented.

## Design-language matrix

The same system plan is built under both canonical Scope 3 languages:

- Field Service;
- Precision Lab.

Both variants retain:

- the same six roles;
- the same selected topology;
- the same interface dimensions and compatibility graph;
- the same workflows;
- the same system-plan fingerprint.

Their retained member and system GLB hashes must differ because the design language changes geometry, materials, controls, protective massing, seams, hardware, and signature motifs.

## Delivery structure

```text
scope4/
  scope4-index.json
  field_service/
    manifest.json
    system/
      system.glb
      system-showcase.glb
      system-brief.json
      system-plan.json
      topology-comparison.json
      interface-standards.json
      interface-endpoints.json
      connections.json
      compatibility-matrix.json
      workflows.json
      layout.json
      design-language.json
      object-index.json
      validation.json
      viewer/index.html
    objects/
      service_hub/
      work_emitter/
      protected_carrier/
      instrument_caddy/
      power_module/
      analysis_module/
  precision_lab/
    ...same structure...
```

Every member directory contains a canonical GLB, showcase GLB, viewer, semantic and material contracts, physics and animation contracts, construction history, design-language receipt, physical interface contract, recovery receipt, validation, and manifest.

## Completion gates

Scope 4 passes only when:

- at least three system topologies were compared;
- ten mandatory system capabilities are covered;
- six independently useful objects are delivered;
- four interface standards and seventeen endpoints are retained;
- at least three standards are reused across multiple connections;
- all nine declared connections are compatible;
- no object is orphaned from the compatibility graph;
- operational and transport workflows are valid;
- combined layout remains inside the declared footprint;
- unconnected objects do not overlap;
- all members share one design-language fingerprint per system variant;
- all twelve member GLBs reopen;
- both combined system GLBs reopen;
- paired language variants retain the same system plan but distinct model hashes;
- Scopes 0–3 continue to rebuild.

## Boundary

Scope 4 proves bounded system decomposition, coordinated retained objects, reusable physical interfaces, compatibility, spatial layout, and workflow contracts.

It does not yet prove:

- manufacturing-grade tolerance analysis;
- assembly order or service manuals;
- cost or supply-chain optimization;
- automatic invention of arbitrary ecosystems;
- human or robot reachability;
- operational simulation under load;
- regulatory or engineering certification.
