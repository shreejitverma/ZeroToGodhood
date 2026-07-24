# Appendix P: CPython Memory Allocator Diagrams


This appendix provides visual descriptions (ASCII-art) of the memory pools and blocks used by `PyMalloc`.

### P.1 The Arena Structure
```text
+------------------------------------------------------------------+
|                           ARENA (1 MB)                           |
+------------+------------+------------+------------+--------------+
| POOL (16KB)| POOL (16KB)| POOL (16KB)| POOL (16KB)|     ...      |
+------------+------------+------------+------------+--------------+
| BLOCK(8B)  | BLOCK(8B)  |    ...     | BLOCK(8B)  |  BLOCK(8B)   |
+------------+------------+------------+------------+--------------+
```

> **Version note.** Arena and pool sizes are CPython implementation details and have
> changed across releases. The 1 MB arena and 16 KB pool above are the sizes reported by
> `sys._debugmallocstats()` on the verification interpreters (CPython 3.13.5 and 3.14.6,
> darwin/arm64). Earlier CPython used a 256 KB arena and a 4 KB pool. The exact release in
> which each changed is **not yet verified against `Objects/obmalloc.c`** and must be
> confirmed before print.

### P.2 The Small Object Allocator Workflow
1.  **Request**: Python requests 32 bytes for a small string.
2.  **Size Class**: `PyMalloc` identifies this as Size Class 3.
3.  **Pool Check**: It checks the `usedpools` array for Size Class 3.
4.  **Block Return**: It returns a pointer to the next free block in the pool.
5.  **Alignment**: Blocks are always 8-byte aligned to ensure hardware efficiency (Chapter 70).

---
