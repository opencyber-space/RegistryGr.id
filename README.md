# 📚 RegistryGr.id

[![Part of Ecosystem: OpenOS](https://img.shields.io/badge/⚡️Part%20of%20Ecosystem-OpenOS-0A84FF?style=for-the-badge)](https://github.com/your-org)

The **RegistryGr.id** is the **central repository** for all **AGIGrid** and **AIGrid** registries.
It consolidates **registries** into one unified system, ensuring **discoverability, governance, and execution** across the Grid ecosystem.


---

## Contents

### Registries powering AGIGr.id

| **Registry**               | **Grid** | **Docs**                                                                    | **Docs Link**                                                        |
| -------------------------- | -------- | --------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| **Assets Registry**        | AGIGrid  | Manages digital and physical asset metadata, lifecycle, and ownership.      | [Docs](https://registry-grid-internal-docs.pages.dev/agents/assets_regisry)                      |
| **Contracts Registry**     | AGIGrid  | Stores agreements, licenses, and governance rules linked to assets/orgs.    | [Docs](https://registry-grid-internal-docs.pages.dev/agents/contracts-registry)                |
| **DSL Registry**           | AGIGrid  | Hosts Domain-Specific Languages for workflows, policies, and task graphs.   | [Docs](https://registry-grid-internal-docs.pages.dev/agents/dsl_registry)                           |
| **Exchanges Registry**     | AGIGrid  | Tracks exchanges of data, compute, and services between agents/orgs.        | [Docs](https://registry-grid-internal-docs.pages.dev/agents/tasks-db-registry)                                              |
| **Functions Registry**     | AGIGrid  | Catalog of reusable serverless-style functions and callable units.          | [Docs](https://registry-grid-internal-docs.pages.dev/agents/function-registry)                  |
| **Orgs Registry**          | AGIGrid  | Stores organization metadata, hierarchies, and federation mappings.         | [Docs](https://registry-grid-internal-docs.pages.dev/agents/org-registry)                            |
| **Org Tasks Registry**     | AGIGrid  | Manages organization-level tasks, assignments, and workflows.               | [Docs](https://registry-grid-internal-docs.pages.dev/agents/org-tasks-db)                            |
| **Registry of Registries** | AGIGrid  | The discovery hub — maps and resolves all available registries in the Grid. | [Docs](https://registry-grid-internal-docs.pages.dev/agents/registry-of-registries)        |
| **Subjects Registry**      | AGIGrid  | Handles known subjects (humans, agents, systems) and their identifiers.     | [Docs](https://registry-grid-internal-docs.pages.dev/agents/subjects-db) |
| **Tools Registry**         | AGIGrid  | Repository of pluggable tools and executors accessible to agents.           | [Docs](https://registry-grid-internal-docs.pages.dev/agents/tools-registry)                        |

---

### Registries powering AIGr.id

| **Registry**                | **Grid** | **Docs**                                                                    | **Docs Link**                                                   |
| --------------------------- | -------- | --------------------------------------------------------------------------- | --------------------------------------------------------------- |
| **Assets DB**               | AIGrid   | Database backend for assets at runtime (files, datasets, models).           | [Docs](https://registry-grid-internal-docs.pages.dev/aios/assets-db-registry)             |
| **Blocks DB**               | AIGrid   | Tracks deployed blocks (AIOS building units) and their runtime states.      | [Docs](https://registry-grid-internal-docs.pages.dev/aios/block-registry)                     |
| **Clusters DB**             | AIGrid   | Manages compute clusters, nodes, GPUs, and scheduling metadata.             | [Docs](https://registry-grid-internal-docs.pages.dev/aios/cluster-registry)                 |
| **Components Registry**     | AIGrid   | Registry of modular system components (APIs, controllers, services).        | [Docs](https://registry-grid-internal-docs.pages.dev/aios/component-registry)             |
| **Container Registries DB** | AIGrid   | Stores references to container images and registries for deployments.       | [Docs](https://registry-grid-internal-docs.pages.dev/aios/container-registry)             |
| **Networks Registry**       | AIGrid   | Stores definitions of virtual networks, overlays, and routing rules.        | [Docs](https://registry-grid-internal-docs.pages.dev//aios/network-registry)                                         |
| **Policies DB**             | AIGrid   | Manages runtime policies (quota, quality, membership, security, etc.).      | [Docs](https://registry-grid-internal-docs.pages.dev/aios/policies-system)                   |
| **Spec Store**              | AIGrid   | Repository for specifications (schemas, protobufs, templates).              | [Docs](https://registry-grid-internal-docs.pages.dev/aios/spec-store)                             |
| **Template Store**          | AIGrid   | Stores reusable templates for deployments, jobs, and registry configs.      | [Docs](https://registry-grid-internal-docs.pages.dev/aios/template-store)                     |
| **vDAGs DB**                | AIGrid   | Manages virtual Directed Acyclic Graphs (vDAGs) for workflow orchestration. | [Docs](https://registry-grid-internal-docs.pages.dev/aios/vdag-registry)                       |
| **Adhoc Servers DB**        | AIGrid   | Temporary server registry for dynamic or on-demand compute endpoints.       | [Docs](https://registry-grid-internal-docs.pages.dev/aios/adhoc-inference-server)     |
| **Splits Runners Registry** | AIGrid   | Tracks runtime workers handling split models and distributed execution.     | [Docs](https://registry-grid-internal-docs.pages.dev/aios/llm-model-splits-runners) |

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
