# 📚 RegistryGr.id

[![Part of Ecosystem: OpenOS](https://img.shields.io/badge/⚡️Part%20of%20Ecosystem-OpenOS-0A84FF?style=for-the-badge)](https://github.com/your-org)

The **RegistryGr.id** is the **central repository** for all **AGIGrid** and **AIGrid** registries.
It consolidates **registries** into one unified system, ensuring **discoverability, governance, and execution** across the Grid ecosystem.


---

## Contents

### Registries powering AGIGr.id

| **Registry**               | **Grid** | **Docs**                                                                    | **Docs Link**                                                        |
| -------------------------- | -------- | --------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| **Assets Registry**        | AGIGrid  | Manages digital and physical asset metadata, lifecycle, and ownership.      | [assets\_registry.md](agents/assets_regisry.md)                      |
| **Contracts Registry**     | AGIGrid  | Stores agreements, licenses, and governance rules linked to assets/orgs.    | [contracts-registry.md](agents/contracts-registry.md)                |
| **DSL Registry**           | AGIGrid  | Hosts Domain-Specific Languages for workflows, policies, and task graphs.   | [dsl\_registry.md](agents/dsl_registry.md)                           |
| **Exchanges Registry**     | AGIGrid  | Tracks exchanges of data, compute, and services between agents/orgs.        | [tasks-db-registry](./agents/tasks-db-registry.md)                                              |
| **Functions Registry**     | AGIGrid  | Catalog of reusable serverless-style functions and callable units.          | [function-registry.md](./agents/function-registry.md)                  |
| **Orgs Registry**          | AGIGrid  | Stores organization metadata, hierarchies, and federation mappings.         | [org-registry.md](./agents/org-registry.md)                            |
| **Org Tasks Registry**     | AGIGrid  | Manages organization-level tasks, assignments, and workflows.               | [org-tasks-db.md](./agents/org-tasks-db.md)                            |
| **Registry of Registries** | AGIGrid  | The discovery hub — maps and resolves all available registries in the Grid. | [registry-of-registries.md](./agents/registry-of-registries.md)        |
| **Subjects Registry**      | AGIGrid  | Handles known subjects (humans, agents, systems) and their identifiers.     | [tasks-db-registry.md](./agents/subjects-db.md) |
| **Tools Registry**         | AGIGrid  | Repository of pluggable tools and executors accessible to agents.           | [tools-registry.md](./agents/tools-registry.md)                        |

---

### Registries powering AIGr.id

| **Registry**                | **Grid** | **Docs**                                                                    | **Docs Link**                                                   |
| --------------------------- | -------- | --------------------------------------------------------------------------- | --------------------------------------------------------------- |
| **Assets DB**               | AIGrid   | Database backend for assets at runtime (files, datasets, models).           | [Docs](aios/assets-db-registry.md)             |
| **Blocks DB**               | AIGrid   | Tracks deployed blocks (AIOS building units) and their runtime states.      | [Docs](aios/block-registry.md)                     |
| **Clusters DB**             | AIGrid   | Manages compute clusters, nodes, GPUs, and scheduling metadata.             | [Docs](aios/cluster-registry.md)                 |
| **Components Registry**     | AIGrid   | Registry of modular system components (APIs, controllers, services).        | [Docs](aios/component-registry.md)             |
| **Container Registries DB** | AIGrid   | Stores references to container images and registries for deployments.       | [Docs](aios/container-registry.md)             |
| **Networks Registry**       | AIGrid   | Stores definitions of virtual networks, overlays, and routing rules.        | [Docs](./aios/network-registry.md)                                         |
| **Policies DB**             | AIGrid   | Manages runtime policies (quota, quality, membership, security, etc.).      | [policies-system.md](aios/policies-system.md)                   |
| **Spec Store**              | AIGrid   | Repository for specifications (schemas, protobufs, templates).              | [spec-store.md](aios/spec-store.md)                             |
| **Template Store**          | AIGrid   | Stores reusable templates for deployments, jobs, and registry configs.      | [Docs](aios/template-store.md)                     |
| **vDAGs DB**                | AIGrid   | Manages virtual Directed Acyclic Graphs (vDAGs) for workflow orchestration. | [Docs](aios/vdag-registry.md)                       |
| **Adhoc Servers DB**        | AIGrid   | Temporary server registry for dynamic or on-demand compute endpoints.       | [Docs](aios/adhoc-inference-server.md)     |
| **Splits Runners Registry** | AIGrid   | Tracks runtime workers handling split models and distributed execution.     | [Docs](aios/llm-model-splits-runners.md) |

---

## 🚀 Features

* 🗂 **Single source of truth** for AGIGrid (governance) and AIGrid (runtime).
* 🔗 **Registry of Registries** provides unified discovery and resolution.
* 🛠 **Structured metadata** for assets, tasks, functions, and policies.
* ☁️ **Kubernetes-native manifests** for production-grade deployments.
* ⚡ **Extensible architecture** for new registries and DBs.

---

## 🔗 Links

* 📄 Vision Paper - TBD
* 📚 [Documentation](https://registry-grid-internal-docs.pages.dev/)
* 💻 [Github](https://github.com/opencyber-space/RegistryGr.id)

---


## 🤝 Contributing

This project is **community-driven**. Contributions welcome!

---
