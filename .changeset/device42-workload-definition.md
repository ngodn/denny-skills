---
"denny-skills": patch
---

`device42`: define what a "workload" means in the sizing rule ("one RC per 1,000 workloads") and separate it from the job count. A workload is one discovered-and-monitored machine; jobs are the RC's concurrency unit. Notes that ongoing per-device RU/Storage polling is what actually loads the RC, so size by unique machine count rather than by how many discovery jobs are scheduled.
