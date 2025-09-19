### **Finalize Production Deployment View with High Availability and Observability**

*   **Problem:** Our current design, while functionally complete and performant, has not explicitly addressed resilience against large-scale infrastructure failures (like an entire data center outage) or the need for a comprehensive monitoring and logging solution. These are non-negotiable requirements for a production-grade service (**NFR3, NFR4, NFR5**).
*   **Solution:** We will finalize the architecture by incorporating High Availability (HA) and a dedicated Observability stack.
    1.  **High Availability:** The entire infrastructure will be designed as a multi-Availability Zone (Multi-AZ) deployment. All stateful and stateless components will be replicated across at least two separate physical data centers to ensure the service remains operational even if one AZ fails.
    2.  **Observability Stack:** We will introduce a standard monitoring and logging stack. All services will be instrumented to export metrics to a central `Monitoring Service` (Prometheus), and structured logs will be shipped to a `Logging Service` (OpenSearch). A `Dashboarding Service` (Grafana) will be used for visualization and alerting.
*   **Trade-offs:**
    *   **Pros:** The final design is highly resilient, fault-tolerant, and fully observable, meeting the stringent requirements for a production system. System health can be monitored in real-time, and issues can be diagnosed quickly.
    *   **Cons:** A multi-AZ deployment significantly increases infrastructure cost, as many components are now duplicated. A full observability stack also adds to the operational cost and management overhead.

#### Logical View (C4 Component Diagram) - FINAL

This is the final, complete logical diagram. It adds the key components of our observability stack and shows them gathering data from our core application services.

```mermaid
C4Component
    title Final Component Diagram for Axon AI Serving

    Person(user, "User")

    System_Boundary(c1, "Axon AI Serving") {
        Component(api_gateway, "API Gateway", "nginx/envoy", "Authenticates, rate limits, and routes requests.")
        Component(session_manager, "Session Manager", "Python/Go", "Manages session state via Redis and persists it to a durable DB.")
        Component(message_queue, "Message Queue", "RabbitMQ/SQS", "Decouples front-end from back-end.")
        
        System_Boundary(c2, "Inference Service (Tensor Parallel)") {
             Component(worker, "Inference Workers", "vLLM/TGI", "A pool of workers that hold model shards and execute inference.")
        }

        ContainerDb(kv_cache, "KV Cache", "GPU VRAM", "Sharded across all workers.")
        ContainerDb(in_memory_cache, "In-Memory Cache", "Redis", "Primary cache for sessions & rate limits.")
        ContainerDb(durable_store, "Durable Store", "PostgreSQL", "System of record for all conversation history.")

        System_Boundary(c3, "Observability Stack") {
            Component(monitoring, "Monitoring Service", "Prometheus", "Scrapes and stores metrics from all components.")
            Component(logging, "Logging Service", "OpenSearch/Loki", "Aggregates and indexes structured logs.")
            Component(dashboarding, "Dashboarding", "Grafana", "Provides visualization, dashboards, and alerting.")
        }
    }
    
    Rel(user, api_gateway, "Sends prompt")
    Rel(api_gateway, session_manager, "Forwards request")
    Rel(session_manager, message_queue, "Publishes job")
    Rel(message_queue, worker, "Consumes job")
    Rel(worker, in_memory_cache, "Publishes result tokens")
    Rel(session_manager, in_memory_cache, "Receives tokens")
    Rel(session_manager, durable_store, "Persists history")
    
    Rel_Back(session_manager, api_gateway, "Streams response")
    Rel_Back(api_gateway, user, "")

    Rel(api_gateway, monitoring, "Exposes /metrics")
    Rel(session_manager, monitoring, "Exposes /metrics")
    Rel(worker, monitoring, "Exposes /metrics")
    Rel(monitoring, dashboarding, "Provides data source")

    Rel(api_gateway, logging, "Ships logs")
    Rel(session_manager, logging, "Ships logs")
    Rel(worker, logging, "Ships logs")
```

#### Physical View (AWS Deployment Diagram) - FINAL

This is our final production deployment diagram. It shows the complete architecture deployed across two Availability Zones for high availability and includes the managed AWS services for our observability stack.

```mermaid
graph LR
    subgraph User's Device
        U[User]
    end

    subgraph "AWS Cloud (us-east-1)"
        VPC("VPC")
        subgraph VPC
            subgraph Public Subnet
                ALB("Application Load Balancer");
            end

            subgraph Private Subnets
                subgraph "Availability Zone: us-east-1a"
                    EKS_A("EKS Cluster AZ-a");
                    subgraph EKS_A
                        CPU_A("CPU Node Group A");
                        GPU_A("GPU Node Group A (with EFA)");
                    end
                end

                subgraph "Availability Zone: us-east-1b"
                    EKS_B("EKS Cluster AZ-b");
                    subgraph EKS_B
                        CPU_B("CPU Node Group B");
                        GPU_B("GPU Node Group B (with EFA)");
                    end
                end
            end

            subgraph "Managed Backend Services (Multi-AZ)"
                RDS("Amazon RDS for PostgreSQL");
                ElastiCache("Amazon ElastiCache for Redis");
                MQ("Amazon MQ for RabbitMQ");
            end
            
            subgraph "Observability Services (Regional)"
                AMP("Amazon Managed Prometheus");
                AOS("Amazon OpenSearch Service");
                AMG("Amazon Managed Grafana");
            end
        end
    end

    %% Define Node Contents %%
    subgraph CPU_A
        Container1_A(fa:fa-cube API Gateway);
        Container2_A(fa:fa-cube Session Manager);
    end
    subgraph GPU_A
        IW_A("fa:fa-cube Inference Worker(s)");
    end
    subgraph CPU_B
        Container1_B(fa:fa-cube API Gateway);
        Container2_B(fa:fa-cube Session Manager);
    end
    subgraph GPU_B
        IW_B("fa:fa-cube Inference Worker(s)");
    end

    %% Define Connections %%
    U -- HTTPS --> ALB;
    ALB --> Container1_A & Container1_B;
    
    Container1_A & Container1_B --> Container2_A & Container2_B;
    
    Container2_A & Container2_B -- "Session Cache" --> ElastiCache;
    Container2_A & Container2_B -- "Durable Storage" --> RDS;
    Container2_A & Container2_B -- "Publishes Jobs" --> MQ;
    
    IW_A & IW_B -- "Consumes Jobs" --> MQ;
    IW_A & IW_B -- "Pub/Sub Results" --> ElastiCache;

    %% Observability Connections %%
    EKS_A & EKS_B --> AMP;
    EKS_A & EKS_B --> AOS;
    AMG --> AMP & AOS;
```

#### Component-to-Resource Mapping Table - FINAL

| Logical Component | Physical Resource | Rationale |
| :--- | :--- | :--- |
| API Gateway | Containers on EKS CPU Node Group (Multi-AZ) | Deployed across multiple AZs for high availability. |
| Session Manager | Containers on EKS CPU Node Group (Multi-AZ) | Deployed across multiple AZs for high availability. |
| Message Queue | Amazon MQ for RabbitMQ (Multi-AZ) | Managed broker configured in a primary/standby setup for fault tolerance. |
| Inference Service | Containers on EKS GPU Node Group with EFA (Multi-AZ) | GPU worker pools are spread across AZs to ensure inference capacity is always available. EFA enables high-performance inter-node communication. |
| KV Cache | GPU VRAM on each worker node | A distributed, in-memory cache managed by the inference framework. |
| In-Memory Cache | Amazon ElastiCache for Redis (Multi-AZ) | Managed cache configured with a primary and replica node in different AZs for failover. |
| Durable Store | Amazon RDS for PostgreSQL (Multi-AZ) | Managed database configured in a primary/standby setup for high availability and data durability. |
| **Monitoring Service** | **Amazon Managed Service for Prometheus (AMP)** | (New) A fully managed Prometheus-compatible service that handles the ingestion, storage, and querying of metrics at scale without manual overhead. |
| **Logging Service** | **Amazon OpenSearch Service** | (New) A managed service for log aggregation and analysis, providing powerful search and filtering capabilities for debugging. |
| **Dashboarding** | **Amazon Managed Grafana (AMG)** | (New) A managed Grafana instance for creating dashboards and alerts, tightly integrated with AMP and AOS as data sources. |
