### **Design Support for Large Models with Tensor Parallelism**

*   **Problem:** High-performance LLMs, such as the Llama 3 70B model mentioned in our requirements, often exceed the VRAM capacity of a single GPU. For example, a 70B parameter model requires ~140GB for weights in FP16, while a standard A100 GPU has only 80GB. Our current architecture, which assumes a model fits on one device, cannot serve these larger, more powerful models.
*   **Solution:** We will enhance the `Inference Service` to support **Tensor Parallelism**. This model parallelism technique shards the individual weight matrices (tensors) of the LLM across a group of GPUs.
    1.  A single logical `Inference Service` will now be composed of a pool of `Inference Worker` containers, each running on a separate GPU.
    2.  During a forward pass, each worker computes its part of the operation on its local slice of the model's weights.
    3.  The workers then use a high-speed interconnect (e.g., NVLink, AWS EFA) to execute an `all-reduce` collective communication operation, synchronizing their partial results to form the final correct output for that model layer.
    This allows the aggregated VRAM of multiple GPUs to host a single, massive model.
*   **Trade-offs:**
    *   **Pros:** Unlocks the ability to serve state-of-the-art models that are too large for any single accelerator, which is a critical business capability.
    *   **Cons:** Introduces significant communication overhead and latency due to the inter-GPU `all-reduce` operations. This requires specialized, expensive hardware with high-speed interconnects to be effective. Deployments become more complex as a single "inference endpoint" is now a tightly coupled group of containers that must be managed as a single unit.

#### Logical View (C4 Component Diagram)

The external view of the `Inference Service` remains the same, but we update its internal structure to show that it is now a composite of multiple workers. This illustrates the parallelism that is happening "under the hood."

```mermaid
C4Component
    title Component Diagram for Axon AI Serving (with Tensor Parallelism)

    Person(user, "User")

    System_Boundary(c1, "Axon AI Serving") {
        Component(api_gateway, "API Gateway", "nginx/envoy", "Routes requests.")
        Component(session_manager, "Session Manager", "Python/Go", "Enqueues inference jobs.")
        Component(message_queue, "Message Queue", "RabbitMQ/SQS", "Decouples front-end from back-end.")
        
        System_Boundary(c2, "Inference Service (Tensor Parallel)") {
             Component(worker_1, "Inference Worker 1", "vLLM/TGI", "Holds a shard of the model weights.")
             Component(worker_n, "Inference Worker N", "vLLM/TGI", "Holds a shard of the model weights.")
        }

        ContainerDb(kv_cache, "KV Cache", "GPU VRAM", "Sharded across all workers.")
        ContainerDb(in_memory_cache, "In-Memory Cache", "Redis", "Stores session history & rate limits.")
        ContainerDb(durable_store, "Durable Store", "PostgreSQL", "System of record for conversation history.")
    }
    
    Rel(user, api_gateway, "Sends prompt")
    Rel(api_gateway, session_manager, "Forwards request")
    Rel(session_manager, message_queue, "Publishes inference job")

    Rel(message_queue, worker_1, "Consumes job")
    Rel(worker_1, worker_n, "Synchronizes results (All-Reduce)")

    Rel(worker_1, kv_cache, "Manages local KV Cache shard")
    Rel(worker_n, kv_cache, "Manages local KV Cache shard")

    Rel(worker_1, in_memory_cache, "Publishes result tokens")

    Rel(session_manager, in_memory_cache, "Receives tokens")
    Rel_Back(session_manager, api_gateway, "Streams response")
    Rel_Back(api_gateway, user, "")
```

#### Physical View (AWS Deployment Diagram)

The physical view now explicitly shows a dedicated pool of GPU instances that are optimized for high-speed interconnects, such as **EC2 P4d instances equipped with Elastic Fabric Adapter (EFA)**. A single inference request for a large model will now be processed by multiple containers running across this pool.

```mermaid
graph TD
    subgraph "User's Device"
        U[User]
    end

    subgraph "AWS Cloud (us-east-1)"
        VPC("VPC")
        subgraph VPC
            subgraph "Public Subnet"
                ALB("Application Load Balancer");
            end

            subgraph "Private Subnet"
                EKS("EKS Cluster");
                ElastiCache("Amazon ElastiCache for Redis");
                MQ("Amazon MQ for RabbitMQ");
                RDS("Amazon RDS for PostgreSQL");
            end
        end

        subgraph EKS
            subgraph "CPU Node Group"
                Container1(fa:fa-cube API Gateway);
                Container2(fa:fa-cube Session Manager);
            end
            
            subgraph "GPU Node Group (with EFA Interconnect)"
                Node1("GPU Node 1 (p4d.24xlarge)")
                Node2("GPU Node 2 (p4d.24xlarge)")
                NodeN("...")
                
                subgraph Node1
                    IW1("fa:fa-cube Inference Worker 1")
                end
                subgraph Node2
                    IW2("fa:fa-cube Inference Worker 2")
                end
                
                IW1 <--> IW2
            end
        end
    end

    U -- HTTPS --> ALB;
    ALB --> Container1;
    Container1 --> Container2;
    
    Container1 -- "TCP" --> ElastiCache;
    Container2 -- "TCP (Session Cache)" --> ElastiCache;
    IW1 -- "TCP (Pub/Sub)" --> ElastiCache;

    Container2 -- "AMQP" --> MQ;
    IW1 -- "AMQP" --> MQ;
    IW2 -- "AMQP" --> MQ;
    
    Container2 -- "SQL" --> RDS;
```

#### Component-to-Resource Mapping Table

| Logical Component | Physical Resource | Rationale |
| :--- | :--- | :--- |
| API Gateway | Container on EKS CPU Node Group | Standard compute, no need for expensive GPU resources. |
| Session Manager | Container on EKS CPU Node Group | Standard compute, no need for expensive GPU resources. |
| Message Queue | Amazon MQ for RabbitMQ | Managed message broker for decoupling. |
| **Inference Service** | A pool of **Inference Worker** containers deployed across a dedicated **EKS GPU Node Group (e.g., EC2 P4d instances with EFA)** | (Updated Rationale) For models larger than a single GPU, we use a pool of specialized nodes. **EC2 P4d instances** are chosen because they provide multiple A100 GPUs and support **Elastic Fabric Adapter (EFA)**, which enables the low-latency, high-bandwidth interconnect required for efficient Tensor Parallelism. |
| KV Cache | GPU VRAM on each worker node in the GPU pool | The KV cache itself is now sharded. Each worker manages the cache for its portion of the batch. |
| In-Memory Cache | Amazon ElastiCache for Redis | High-speed store for session management and results communication. |
| Durable Store | Amazon RDS for PostgreSQL | Managed relational database for durable storage of conversation history. |
