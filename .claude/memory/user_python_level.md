---
name: User Python level and background
description: User's programming background and Python knowledge level — use to tailor explanations
type: user
---

Professional Java and Clojure developer. Python is not a primary language.

- Strong OOP foundations from Java, functional programming intuition from Clojure
- Comfortable reasoning about code once explained, but Python idioms are not yet intuitive when reading cold
- Good instincts for code quality — spots deprecated patterns and deferred cleanup quickly
- Understands concepts (e.g. async/event loop) at a conceptual level once framed

When explaining Python, draw analogies to Java or Clojure where helpful:
- Context managers ~ Java try-with-resources
- `yield` in generators ~ lazy seqs in Clojure
- `async`/`await` ~ CompletableFuture in Java
- pytest fixtures ~ JUnit `@Before`/`@After`
