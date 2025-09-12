# 📚 RegistryGr.id

[![Part of Ecosystem: OpenOS](https://img.shields.io/badge/⚡️Part%20of%20Ecosystem-OpenOS-0A84FF?style=for-the-badge)](https://github.com/your-org)

**RegistryGrid** is a open trust and discovery layer. 

It aims to **democratize discovery and access  of AI commerce** by creating a grid of registries that list and keeps track of **all assets, services, exchanges, infrastructure and participants in AGI ecosystem**. Eg. AI assets, agents, agencies, systems, participants, policies, workflows, tools, tasks to name few. 

Together, these registries create an **open, interoperable AI network** that supports plural, diverse and comprehensive AI ecosystem for AI consumers, AI creators, infra providers, and operators. RegistryGrid ensures they are verified, discoverable, and facilitates interoperability.

It is how AI, Agents, agencies can find each other, connect and start transacting.

---

### Core Functionalities of the RegistryGrid

**Federated directory service**
Data is **not centralized**,  core registries maintain the root, while participants replicate, sync and cache portions locally for soverignity, efficiency.

**Onboarding & Verification**
Ensures that only respective governance authorized and valid entities (agents, organizations, infrastructures, tools, etc.) can join an AI network.

**Participant Directory**
Maintains a searchable directory of registries and participants, making them discoverable across the AI ecosystem.

**Interoperability Enabler**
Stores metadata and endpoints (APIs, models, services, workflows) so agents, tools, and infrastructures can interoperate seamlessly.

**Trust & Governance**
Tracks compliance, governance rules, and alignment policies, forming part of the AI network’s trust and accountability framework.

**Network Health Monitoring**
Monitors registries, participants, and services for activity, reliability, and performance to ensure ecosystem resilience.

**Synchronization**
Changes in main registry propagates across the network.

---

### Role of RegistryGrid in Decentralized AI Networks

**Scalable Inclusivity**
Allows AI models, AI forms, agents, organizations, and infrastructures to onboard once and become instantly discoverable across the entire AI network through distributed propagation.

**Trust without Central Lock-in**
Synchronization ensures fairness and reliability without creating centralized gatekeepers that dominate visibility or access.

**Interoperability at Scale**
Sync mechanisms guarantee that thousands of agents, tools, and services remain aligned without requiring manual integrations.

**Democratization of Access**
Ensures every legitimate participant - from small research labs to large infrastructure providers - is equally visible on the network.

**Trust & Safety Backbone**
By authenticating, certifying, and monitoring participants, the registry ensures interactions remain safe, credible, and trustworthy.

**Interoperability Fabric**
Maintains metadata on participants, capabilities, and endpoints, acting as the connective layer that binds the decentralized AI stack.

**Ensuring Openness**
Supports an open system where any compliant agent or infrastructure can join and be discovered without platform lock-in.

**Preventing Monopolies**
Guarantees that visibility and access aren’t controlled by a handful of dominant platforms, sustaining diversity in the ecosystem.

**Enabling Scalability**
Like UPI’s common directory for payments, RegistryGrid enables decentralized AI networks to scale globally by maintaining a shared participant directory.

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
