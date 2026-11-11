# Caching Reading Assignment

## Read strategies

**Cache-aside:** The application checks the cache first. On a miss, it loads
or computes from the source and fills the cache. It is flexible, but the
application owns cache population and freshness.

**Read-through:** The cache loads missing data from the backing store for the
caller. This simplifies callers, but requires the cache layer to understand
how to load the requested data.

## Write strategies

| Strategy | Behavior | Trade-off |
|---|---|---|
| **Write-through** | Update cache and backing store together. | Better freshness; writes wait for both. |
| **Write-behind / write-back** | Update cache first and persist later. | Fast writes; added complexity and possible loss of pending updates. |
| **Write-around** | Write to backing store, bypassing cache. | Avoids caching one-off writes; next read may be slower. |

## TTL, invalidation, and eviction

**TTL (time to live)** expires an entry after a set duration. Shorter TTLs
reduce the time stale data can linger, but increase cache misses.
**Invalidation** makes entries unusable when their source or assumptions
change; it improves freshness but needs reliable change tracking.
**Eviction** frees cache memory when its limit is reached. Unlike TTL, it can
remove an entry before its expiry.

| Policy | Evicts | Trade-off |
|---|---|---|
| **LRU** | Least recently used | Favors recent demand; can discard older useful data. |
| **LFU** | Least frequently used | Keeps popular items; popularity changes may be slow to reflect. |
| **FIFO** | Oldest inserted | Simple; ignores whether an item is still popular. |
| **Random** | A randomly selected item | Low selection overhead; may discard a hot item. |

Redis provides `allkeys-lru`, `allkeys-lfu`, and `allkeys-random`, plus
`volatile-lru`, `volatile-lfu`, and `volatile-random` (which select only
expiring keys). It also supports `volatile-ttl` and `noeviction`. Redis has
no named FIFO max-memory policy; its LRU and LFU policies are approximations,
not exact global rankings.

## Choices in LegalCheck

LegalCheck uses **cache-aside** for legal answers. The API checks Redis before
retrieval, embeddings, or language-model generation. On a miss, it retrieves
evidence, validates the answer citations, and caches only supported answers.
This avoids repeating costly work while keeping PostgreSQL and the RAG
pipeline authoritative. Read-through is a poor fit because Redis cannot run
LegalCheck's retrieval and evidence-validation workflow.

Legal-source updates are **write-around-like**: PostgreSQL is updated, not
the answer cache. Cache keys include a fingerprint of sources, provisions,
and indexed chunks, so content or review changes make old answers
unreachable. A one-hour TTL (`LEGAL_QA_CACHE_TTL_SECONDS=3600`) bounds how
long old keys occupy Redis; set it to `0` to disable answer caching.
Write-through would make source writes depend on cache updates, while
write-behind would risk delaying durable legal-record changes, so neither is
appropriate.

LegalCheck does not choose Redis's eviction policy in application code.
Because Redis also stores rate-limit counters, a memory policy can affect
request protection as well as answer-cache hit rate. Monitor the deployment
and consider separate Redis services when those workloads need isolation.
