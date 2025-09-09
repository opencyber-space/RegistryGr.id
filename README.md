# 📚 RegistryGr.id

[![Part of Ecosystem: OpenOS](https://img.shields.io/badge/⚡️Part%20of%20Ecosystem-OpenOS-0A84FF?style=for-the-badge)](https://github.com/your-org)

The **RegistryGr.id** is the **central repository** for all **AGIGrid** and **AIGrid** registries.
It consolidates **registries** into one unified system, ensuring **discoverability, governance, and execution** across the Grid ecosystem.

## 📑 Registries Overview

### Registries powering AGIGr.id

| **Registry**               | **Grid** | **Docs**                                                                    |
| -------------------------- | -------- | --------------------------------------------------------------------------- |
| **Assets Registry**        | AGIGrid  | Manages digital and physical asset metadata, lifecycle, and ownership.      |
| **Contracts Registry**     | AGIGrid  | Stores agreements, licenses, and governance rules linked to assets/orgs.    |
| **DSL Registry**           | AGIGrid  | Hosts Domain-Specific Languages for workflows, policies, and task graphs.   |
| **Exchanges Registry**     | AGIGrid  | Tracks exchanges of data, compute, and services between agents/orgs.        |
| **Functions Registry**     | AGIGrid  | Catalog of reusable serverless-style functions and callable units.          |
| **Orgs Registry**          | AGIGrid  | Stores organization metadata, hierarchies, and federation mappings.         |
| **Org Tasks Registry**     | AGIGrid  | Manages organization-level tasks, assignments, and workflows.               |
| **Registry of Registries** | AGIGrid  | The discovery hub — maps and resolves all available registries in the Grid. |
| **Subjects Registry**      | AGIGrid  | Handles known subjects (humans, agents, systems) and their identifiers.     |
| **Tools Registry**         | AGIGrid  | Repository of pluggable tools and executors accessible to agents.           |

---

### Registries powering AIGr.id

| **Registry**                | **Grid** | **Docs**                                                                    |
| --------------------------- | -------- | --------------------------------------------------------------------------- |
| **Assets DB**               | AIGrid   | Database backend for assets at runtime (files, datasets, models).           |
| **Blocks DB**               | AIGrid   | Tracks deployed blocks (AIOS building units) and their runtime states.      |
| **Clusters DB**             | AIGrid   | Manages compute clusters, nodes, GPUs, and scheduling metadata.             |
| **Components Registry**     | AIGrid   | Registry of modular system components (APIs, controllers, services).        |
| **Container Registries DB** | AIGrid   | Stores references to container images and registries for deployments.       |
| **Layers DB**               | AIGrid   | Tracks model layers for distributed or split inference.                     |
| **Model Splits**            | AIGrid   | Registry for pipeline-parallel or tensor-parallel model splits.             |
| **Networks Registry**       | AIGrid   | Stores definitions of virtual networks, overlays, and routing rules.        |
| **Policies DB**             | AIGrid   | Manages runtime policies (quota, quality, membership, security, etc.).      |
| **Spec Store**              | AIGrid   | Repository for specifications (schemas, protobufs, templates).              |
| **Tasks DB**                | AIGrid   | Tracks distributed tasks, job states, and execution metadata.               |
| **Template Store**          | AIGrid   | Stores reusable templates for deployments, jobs, and registry configs.      |
| **vDAGs DB**                | AIGrid   | Manages virtual Directed Acyclic Graphs (vDAGs) for workflow orchestration. |
| **Adhoc Servers DB**        | AIGrid   | Temporary server registry for dynamic or on-demand compute endpoints.       |
| **Inference Registry**      | AIGrid   | Tracks inference endpoints, configurations, and scaling metadata.           |
| **Model Layers Registry**   | AIGrid   | Specialized registry for mapping model layers across distributed clusters.  |
| **Splits Runners Registry** | AIGrid   | Tracks runtime workers handling split models and distributed execution.     |
| **System**                  | AIGrid   | Core system services, bootstrap logic, and orchestration backbone.          |


---

## 🚀 Features

* 🗂 **Single source of truth** for AGIGrid (governance) and AIGrid (runtime).
* 🔗 **Registry of Registries** provides unified discovery and resolution.
* 🛠 **Structured metadata** for assets, tasks, functions, and policies.
* ☁️ **Kubernetes-native manifests** for production-grade deployments.
* ⚡ **Extensible architecture** for new registries and DBs.

---

## 🔗 Links

* [RegistryGr.id Docs](https://github.com/your-org/agigrid)
* [RegistryGr.id](https://github.com/your-org/openos)

---

## 🤝 Contributing

This project is **community-driven**. Contributions welcome!

---
